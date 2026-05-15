"""
Tests for stub weights and tokenizer loader.
"""

import sys, os

_SRC = os.path.join(os.path.dirname(__file__), "../src")
sys.path.insert(0, os.path.abspath(_SRC))

import pytest
import torch

from qwen3_tts.loader import _make_stub_weights, _make_stub_tokenizer, TalkerWeights


def test_stub_weights_fields():
    w = _make_stub_weights()
    assert isinstance(w, TalkerWeights)
    assert isinstance(w.embed_weight, torch.Tensor)
    assert isinstance(w.layer_weights, list)
    # 2 layers × 11 tensors = 22
    assert len(w.layer_weights) == 22


def test_stub_tokenizer_encode_decode():
    tok = _make_stub_tokenizer()
    ids = tok.encode("hello world")
    assert isinstance(ids, list)
    assert all(isinstance(i, int) for i in ids)
    text = tok.decode(ids)
    assert isinstance(text, str)


def test_stub_tokenizer_eos():
    tok = _make_stub_tokenizer()
    assert tok.eos_token_id == 1
