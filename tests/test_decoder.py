"""
Tests for the TalkerDecoder (streaming generator).
"""

import sys, os

_SRC = os.path.join(os.path.dirname(__file__), "../src")
sys.path.insert(0, os.path.abspath(_SRC))

import pytest
import torch

from megakernel.adapter import ModelConfig, KernelDecoder
from qwen3_tts.loader import _make_stub_weights, _make_stub_tokenizer
from qwen3_tts.decoder import TalkerDecoder
from qwen3_tts.vocoder import AudioConfig


# ---------------------------------------------------------------------------
# Minimal DummyHFModel for CPU testing
# ---------------------------------------------------------------------------

class _CountingModel:
    """HF-stub that cycles through token IDs 10, 20, 30, ... then EOS."""

    def __init__(self, tokens_before_eos: int = 5, eos: int = 1):
        self._seq = list(range(10, 10 + tokens_before_eos * 10, 10)) + [eos]
        self._idx = 0

    def parameters(self):
        yield torch.zeros(1)

    @property
    def device(self):
        return torch.device("cpu")

    def __call__(self, input_ids, past_key_values=None, use_cache=False):
        next_tok = self._seq[min(self._idx, len(self._seq) - 1)]
        self._idx += 1
        vocab = 256
        logits = torch.zeros(1, 1, vocab)
        logits[0, 0, next_tok] = 10.0

        class _Out:
            def __init__(self, logits, pkv):
                self.logits = logits
                self.past_key_values = pkv

        return _Out(logits, past_key_values or ())


def _make_decoder(eos=1, max_tokens=20):
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
    stub_w = _make_stub_weights()
    stub_tok = _make_stub_tokenizer()
    weights_dict = {
        "embed_weight": stub_w.embed_weight,
        "layer_weights": stub_w.layer_weights,
        "final_norm_weight": stub_w.final_norm_weight,
        "lm_head_weight": stub_w.lm_head_weight,
        "cos_table": stub_w.cos_table,
        "sin_table": stub_w.sin_table,
    }
    hf_model = _CountingModel(tokens_before_eos=5, eos=eos)
    kernel = KernelDecoder(weights_dict, cfg, hf_model=hf_model)

    # Monkey-patch weights into TalkerDecoder by constructing it manually
    td = TalkerDecoder.__new__(TalkerDecoder)
    td._tokenizer = stub_tok
    td._cfg = cfg
    td._audio_cfg = AudioConfig(sample_rate=24000, token_hz=25)
    td._eos = eos
    td._chunk_tokens = 1
    td._max_tokens = max_tokens
    td._last_ttfc_ms = 0.0
    td._last_tok_per_sec = 0.0
    td._last_rtf = 0.0
    td._kernel = kernel
    return td


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_stream_tokens_yields_before_eos():
    td = _make_decoder(eos=1, max_tokens=20)
    tokens = list(td.stream_tokens([5]))
    # _CountingModel emits [10, 20, 30, 40, 50, 1(EOS)]
    # Prompt is [5], so step(5) in prefill, then step(5) as first decode → returns 10, 20, ...
    # Actually: prefill=[], first step is step(5)→10, step(10)→20, etc.
    # With prompt [5]: no prefill (5 is the only token, used as first step)
    # So: step(5)→10, step(10)→20, step(20)→30, step(30)→40, step(40)→50, step(50)→EOS
    # Yields [10, 20, 30, 40, 50]
    assert len(tokens) == 5
    assert tokens == [10, 20, 30, 40, 50]


def test_stream_tokens_respects_max_tokens():
    td = _make_decoder(eos=99, max_tokens=3)  # EOS=99 never emitted by model
    tokens = list(td.stream_tokens([1]))
    assert len(tokens) <= 3


def test_stream_audio_yields_bytes():
    td = _make_decoder(eos=1, max_tokens=20)
    chunks = list(td.stream_audio([5, 6]))
    assert len(chunks) > 0
    for chunk in chunks:
        assert isinstance(chunk, bytes)
        assert len(chunk) > 0


def test_talker_decoder_metrics_populated():
    td = _make_decoder(eos=1, max_tokens=20)
    list(td.stream_audio([5, 6]))
    assert td.last_ttfc_ms >= 0
    assert td.last_tok_per_sec >= 0


@pytest.mark.asyncio
async def test_astream_audio_yields_bytes():
    td = _make_decoder(eos=1, max_tokens=20)
    chunks = []
    async for chunk in td.astream_audio([5, 6]):
        chunks.append(chunk)
    assert len(chunks) > 0
    for chunk in chunks:
        assert isinstance(chunk, bytes)
