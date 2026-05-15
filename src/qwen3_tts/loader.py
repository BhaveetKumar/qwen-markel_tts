"""
Weight loading for the Qwen3-TTS talker decoder.

The Qwen3-TTS model has three components:
  1. Speaker encoder (ECAPA-TDNN)
  2. Talker decoder  ← the megakernel target
  3. Vocoder / flow matching decoder

We load only the talker decoder weights and expose them in the layout
expected by KernelDecoder (same 11-tensor-per-layer format as qwen_megakernel).
When no GPU is present (local testing), we load the model in float32 on CPU
and route through the HuggingFace fallback path.
"""

from __future__ import annotations

import math
import os
import sys
from dataclasses import dataclass
from typing import Optional, Tuple

import torch
from loguru import logger


# ---------------------------------------------------------------------------
# Data container
# ---------------------------------------------------------------------------

@dataclass
class TalkerWeights:
    """All tensors needed by KernelDecoder for the talker backbone."""

    embed_weight: torch.Tensor
    layer_weights: list  # flat list, 11 tensors × num_layers
    final_norm_weight: torch.Tensor
    lm_head_weight: torch.Tensor
    cos_table: torch.Tensor
    sin_table: torch.Tensor
    hf_model: Optional[object] = None  # kept for fallback path


# ---------------------------------------------------------------------------
# Public loader
# ---------------------------------------------------------------------------

def load_talker_weights(
    model_name: str = "Qwen/Qwen3-TTS",
    *,
    device: str = "cuda",
    verbose: bool = True,
    use_hf_fallback: bool = True,
) -> Tuple[TalkerWeights, object]:
    """
    Load the Qwen3-TTS talker decoder weights.

    Returns
    -------
    weights : TalkerWeights
        Tensors packed for KernelDecoder.
    tokenizer : transformers tokenizer
        Text tokenizer for the talker.

    Strategy
    --------
    1. Try to load via the Qwen3-TTS qwen_tts package (local clone).
    2. Fall back to AutoModel from HuggingFace hub.

    On a machine without CUDA we load to CPU with float32 so the HF
    fallback path can still be exercised for import / integration testing.
    """
    if not torch.cuda.is_available():
        device = "cpu"
        logger.warning("CUDA not available — loading weights to CPU (testing mode).")

    dtype = torch.bfloat16 if device != "cpu" else torch.float32

    # Inject the local Qwen3-TTS clone into sys.path so the registrations run.
    qwen_tts_root = _find_qwen_tts_root()
    if qwen_tts_root and qwen_tts_root not in sys.path:
        sys.path.insert(0, qwen_tts_root)
        logger.debug(f"Injected Qwen3-TTS root: {qwen_tts_root}")

    hf_model = None
    state = None
    tokenizer = None

    try:
        hf_model, tokenizer, state = _load_via_qwen_tts_package(
            model_name, device, dtype, verbose
        )
    except Exception as exc:
        logger.warning(f"qwen_tts package load failed ({exc}), trying AutoModel.")
        try:
            hf_model, tokenizer, state = _load_via_automodel(
                model_name, device, dtype, verbose
            )
        except Exception as exc2:
            if use_hf_fallback:
                logger.warning(
                    f"AutoModel load also failed ({exc2}). "
                    "Returning stub weights for import testing."
                )
                return _make_stub_weights(), _make_stub_tokenizer()
            raise

    weights = _extract_talker_weights(state, device, dtype)
    if use_hf_fallback:
        weights.hf_model = hf_model

    return weights, tokenizer


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _find_qwen_tts_root() -> Optional[str]:
    """Locate the local Qwen3-TTS clone."""
    candidates = [
        os.path.join(os.path.dirname(__file__), "../../../../Qwen3-TTS"),
        os.path.join(os.path.dirname(__file__), "../../../../../Qwen3-TTS"),
        "/root/workspace/Qwen3-TTS",
        os.path.join(os.getcwd(), "Qwen3-TTS"),
        os.path.join(os.getcwd(), "../Qwen3-TTS"),
    ]
    for c in candidates:
        p = os.path.abspath(c)
        if os.path.isdir(p):
            return p
    return None


def _load_via_qwen_tts_package(model_name, device, dtype, verbose):
    """Load via local qwen_tts package (preferred — uses registered model classes)."""
    from qwen_tts.inference.qwen3_tts_model import Qwen3TTSModel  # type: ignore

    token = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_HUB_TOKEN")

    model_obj = Qwen3TTSModel.from_pretrained(
        model_name,
        torch_dtype=dtype,
        device_map=device,
        token=token,
    )
    hf_model = model_obj.model
    processor = model_obj.processor
    # Extract the talker decoder sub-module state dict.
    # The talker is hf_model.talker (Qwen3TTSTalkerModel).
    talker = getattr(hf_model, "talker", None)
    if talker is None:
        raise AttributeError("Could not find .talker attribute on Qwen3TTS model.")
    state = talker.state_dict()
    tokenizer = processor
    return talker, tokenizer, state


def _load_via_automodel(model_name, device, dtype, verbose):
    """Generic HuggingFace AutoModel fallback."""
    from transformers import AutoModel, AutoProcessor  # type: ignore

    token = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_HUB_TOKEN")

    model = AutoModel.from_pretrained(
        model_name,
        torch_dtype=dtype,
        device_map=device,
        token=token,
    )
    processor = AutoProcessor.from_pretrained(model_name, token=token)
    talker = getattr(model, "talker", model)
    state = talker.state_dict()
    return talker, processor, state


def _extract_talker_weights(state: dict, device: str, dtype) -> TalkerWeights:
    """
    Convert a talker decoder state_dict into the KernelDecoder weight layout.

    The talker backbone follows the same Qwen3 transformer layout as the 0.6B
    kernel expects, just with different dimensions. Weight key names follow
    the standard HuggingFace Qwen3 naming convention.
    """
    def g(key: str) -> torch.Tensor:
        return state[key].to(dtype=dtype, device=device).contiguous()

    # Detect num_layers from state_dict keys
    num_layers = max(
        int(k.split(".")[2])
        for k in state.keys()
        if k.startswith("model.layers.")
    ) + 1

    # Detect hidden_size from embedding
    embed_weight = g("model.embed_tokens.weight")
    hidden_size = embed_weight.shape[1]
    head_dim = 128

    # RoPE tables
    rope_theta = 10000.0
    inv_freq = 1.0 / (
        rope_theta ** (torch.arange(0, head_dim, 2, dtype=torch.float32) / head_dim)
    )
    max_seq = 4096
    positions = torch.arange(max_seq, dtype=torch.float32)
    freqs = torch.outer(positions, inv_freq)
    cos_table = torch.cos(freqs).repeat(1, 2).to(dtype).to(device).contiguous()
    sin_table = torch.sin(freqs).repeat(1, 2).to(dtype).to(device).contiguous()

    # Per-layer weights (11 tensors each)
    layer_weights = []
    for i in range(num_layers):
        p = f"model.layers.{i}."
        layer_weights.extend([
            g(p + "input_layernorm.weight"),
            g(p + "self_attn.q_proj.weight"),
            g(p + "self_attn.k_proj.weight"),
            g(p + "self_attn.v_proj.weight"),
            g(p + "self_attn.q_norm.weight"),
            g(p + "self_attn.k_norm.weight"),
            g(p + "self_attn.o_proj.weight"),
            g(p + "post_attention_layernorm.weight"),
            g(p + "mlp.gate_proj.weight"),
            g(p + "mlp.up_proj.weight"),
            g(p + "mlp.down_proj.weight"),
        ])

    final_norm = g("model.norm.weight")
    lm_head = g("lm_head.weight") if "lm_head.weight" in state else embed_weight

    return TalkerWeights(
        embed_weight=embed_weight,
        layer_weights=layer_weights,
        final_norm_weight=final_norm,
        lm_head_weight=lm_head,
        cos_table=cos_table,
        sin_table=sin_table,
    )


# ---------------------------------------------------------------------------
# Stub helpers for import-only testing (no model download required)
# ---------------------------------------------------------------------------

def _make_stub_weights() -> TalkerWeights:
    """Tiny CPU-only stub so import tests pass without downloading a model."""
    hidden = 64
    layers = 2
    intermediate = 128
    vocab = 256
    head_dim = 16
    num_q_heads = 2
    num_kv_heads = 2
    max_seq = 128

    embed = torch.randn(vocab, hidden, dtype=torch.float32)
    final_norm = torch.ones(hidden, dtype=torch.float32)
    lm_head = embed.clone()
    cos_table = torch.ones(max_seq, head_dim, dtype=torch.float32)
    sin_table = torch.zeros(max_seq, head_dim, dtype=torch.float32)

    lw = []
    for _ in range(layers):
        lw += [
            torch.ones(hidden),                        # input_layernorm
            torch.randn(num_q_heads * head_dim, hidden),  # q_proj
            torch.randn(num_kv_heads * head_dim, hidden), # k_proj
            torch.randn(num_kv_heads * head_dim, hidden), # v_proj
            torch.ones(num_q_heads * head_dim),         # q_norm
            torch.ones(num_kv_heads * head_dim),        # k_norm
            torch.randn(hidden, num_q_heads * head_dim),  # o_proj
            torch.ones(hidden),                        # post_attn_norm
            torch.randn(intermediate, hidden),         # gate_proj
            torch.randn(intermediate, hidden),         # up_proj
            torch.randn(hidden, intermediate),         # down_proj
        ]
    return TalkerWeights(
        embed_weight=embed,
        layer_weights=lw,
        final_norm_weight=final_norm,
        lm_head_weight=lm_head,
        cos_table=cos_table,
        sin_table=sin_table,
    )


def _make_stub_tokenizer():
    """Minimal tokenizer stub for testing."""

    class _Stub:
        eos_token_id = 1

        def encode(self, text, add_special_tokens=True):
            return [ord(c) % 256 for c in text[:64]] + [0]

        def decode(self, ids, skip_special_tokens=True):
            return "".join(chr(max(32, i % 127)) for i in ids)

    return _Stub()
