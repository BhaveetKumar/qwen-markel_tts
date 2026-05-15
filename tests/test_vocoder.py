"""
Tests for the vocoder stub and AudioConfig.
"""

import sys, os

_SRC = os.path.join(os.path.dirname(__file__), "../src")
sys.path.insert(0, os.path.abspath(_SRC))

import pytest
import numpy as np

from qwen3_tts.vocoder import (
    AudioConfig,
    tokens_to_pcm,
    resample_pcm,
    _stub_sine,
)


def test_audio_config_defaults():
    cfg = AudioConfig()
    assert cfg.sample_rate == 24000
    assert cfg.bit_depth == 16
    assert cfg.channels == 1
    assert cfg.token_hz == 25


def test_stub_sine_returns_bytes():
    cfg = AudioConfig()
    pcm = _stub_sine([100, 200, 300], cfg)
    assert isinstance(pcm, bytes)
    # 3 tokens @ 25 Hz = 0.12 s; 24000 * 0.12 * 2 bytes = 5760
    assert len(pcm) > 0


def test_stub_sine_empty_on_zero_tokens():
    cfg = AudioConfig()
    pcm = _stub_sine([], cfg)
    assert pcm == b""


def test_tokens_to_pcm_returns_bytes():
    cfg = AudioConfig()
    pcm = tokens_to_pcm([10, 20, 30], cfg)
    assert isinstance(pcm, bytes)
    assert len(pcm) > 0


def test_resample_same_rate_is_identity():
    cfg = AudioConfig(sample_rate=16000)
    pcm = _stub_sine([50, 51], cfg)
    result = resample_pcm(pcm, 16000, 16000)
    assert result == pcm


def test_resample_changes_length():
    pcm = _stub_sine([50, 51, 52], AudioConfig(sample_rate=24000))
    resampled = resample_pcm(pcm, 24000, 16000)
    # Resampled at 2/3 rate → should be shorter
    assert len(resampled) < len(pcm)
    assert len(resampled) > 0
