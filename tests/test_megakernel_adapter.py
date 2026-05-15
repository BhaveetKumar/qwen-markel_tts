"""
Tests for the megakernel adapter layer.

These run without a GPU by exercising the stub/fallback paths.
"""

import sys
import os

# Ensure src/ is importable
_SRC = os.path.join(os.path.dirname(__file__), "../src")
sys.path.insert(0, os.path.abspath(_SRC))

import pytest
import torch

from megakernel.adapter import (
    KernelDecoder,
    ModelConfig,
    QWEN3_0_6B_CONFIG,
    QWEN3_TTS_TALKER_CONFIG,
    _pack_layer_weights,
)
from qwen3_tts.loader import _make_stub_weights, _make_stub_tokenizer


# ---------------------------------------------------------------------------
# ModelConfig
# ---------------------------------------------------------------------------

def test_model_configs_defined():
    assert QWEN3_0_6B_CONFIG.hidden_size == 1024
    assert QWEN3_0_6B_CONFIG.num_layers == 28
    assert QWEN3_TTS_TALKER_CONFIG.hidden_size == 4096
    assert QWEN3_TTS_TALKER_CONFIG.num_layers == 32


def test_custom_config():
    cfg = ModelConfig(
        name="test",
        hidden_size=64,
        intermediate_size=128,
        num_q_heads=2,
        num_kv_heads=2,
        head_dim=16,
        num_layers=2,
        vocab_size=256,
        max_seq_len=128,
    )
    assert cfg.name == "test"


# ---------------------------------------------------------------------------
# KernelDecoder (CPU fallback path via stub weights)
# ---------------------------------------------------------------------------

class _DummyHFModel:
    """Minimal HF-style model stub for CPU fallback testing."""

    def __init__(self, vocab=256, hidden=64):
        self._vocab = vocab
        self._hidden = hidden
        self._counter = 0

    def parameters(self):
        yield torch.zeros(1)

    @property
    def device(self):
        return torch.device("cpu")

    def __call__(self, input_ids, past_key_values=None, use_cache=False):
        batch, seq = input_ids.shape
        # Return deterministic next-token logits for testing
        logits = torch.zeros(batch, seq, self._vocab)
        # Always predict token 42
        logits[0, -1, 42] = 10.0

        class _Out:
            def __init__(self, logits, pkv):
                self.logits = logits
                self.past_key_values = pkv

        return _Out(logits, past_key_values or ())


class _FailingHFModel:
    """HF-style model stub that always raises on decode calls."""

    def parameters(self):
        yield torch.zeros(1)

    def __call__(self, input_ids, past_key_values=None, use_cache=False):
        raise TypeError("expected Tensor as element 0 in argument 0, but got NoneType")


@pytest.fixture
def stub_decoder():
    """KernelDecoder in HF-fallback mode with a tiny stub."""
    stub_w = _make_stub_weights()
    cfg = ModelConfig(
        name="stub",
        hidden_size=64,
        intermediate_size=128,
        num_q_heads=2,
        num_kv_heads=2,
        head_dim=16,
        num_layers=2,
        vocab_size=256,
        max_seq_len=128,
    )
    weights_dict = {
        "embed_weight": stub_w.embed_weight,
        "layer_weights": stub_w.layer_weights,
        "final_norm_weight": stub_w.final_norm_weight,
        "lm_head_weight": stub_w.lm_head_weight,
        "cos_table": stub_w.cos_table,
        "sin_table": stub_w.sin_table,
    }
    hf_model = _DummyHFModel()
    return KernelDecoder(weights_dict, cfg, hf_model=hf_model)


def test_kernel_decoder_instantiates(stub_decoder):
    assert stub_decoder is not None
    assert stub_decoder._use_kernel is False  # no CUDA in CI


def test_kernel_decoder_step_returns_int(stub_decoder):
    stub_decoder.reset()
    result = stub_decoder.step(1)
    assert isinstance(result, int)
    assert result == 42  # our DummyHFModel always returns 42


def test_kernel_decoder_reset_clears_position(stub_decoder):
    stub_decoder.reset()
    stub_decoder.step(1)
    assert stub_decoder.position == 1
    stub_decoder.reset()
    assert stub_decoder.position == 0


def test_kernel_decoder_raises_without_model():
    cfg = ModelConfig(
        name="no_model",
        hidden_size=64,
        intermediate_size=128,
        num_q_heads=2,
        num_kv_heads=2,
        head_dim=16,
        num_layers=2,
        vocab_size=256,
        max_seq_len=128,
    )
    stub_w = _make_stub_weights()
    weights_dict = {
        "embed_weight": stub_w.embed_weight,
        "layer_weights": stub_w.layer_weights,
        "final_norm_weight": stub_w.final_norm_weight,
        "lm_head_weight": stub_w.lm_head_weight,
        "cos_table": stub_w.cos_table,
        "sin_table": stub_w.sin_table,
    }
    decoder = KernelDecoder(weights_dict, cfg, hf_model=None)
    with pytest.raises(RuntimeError, match="Cannot decode token"):
        decoder.step(0)


def test_kernel_decoder_falls_back_when_hf_decode_raises():
    cfg = ModelConfig(
        name="failing_model",
        hidden_size=64,
        intermediate_size=128,
        num_q_heads=2,
        num_kv_heads=2,
        head_dim=16,
        num_layers=2,
        vocab_size=256,
        max_seq_len=128,
    )
    stub_w = _make_stub_weights()
    weights_dict = {
        "embed_weight": stub_w.embed_weight,
        "layer_weights": stub_w.layer_weights,
        "final_norm_weight": stub_w.final_norm_weight,
        "lm_head_weight": stub_w.lm_head_weight,
        "cos_table": stub_w.cos_table,
        "sin_table": stub_w.sin_table,
    }

    decoder = KernelDecoder(weights_dict, cfg, hf_model=_FailingHFModel())
    tok = decoder.step(7)
    assert isinstance(tok, int)
    assert tok != 1  # first fallback token should not be EOS
