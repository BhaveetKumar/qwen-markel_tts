"""
Vocoder adapter: converts Qwen3-TTS speech token IDs → raw PCM bytes.

Qwen3-TTS uses a flow-matching-based vocoder to reconstruct waveforms from
discrete speech token sequences. This module provides:

  tokens_to_pcm(token_ids, cfg) → bytes   (16-bit little-endian, mono)

When the full vocoder model is not loaded (e.g. local testing), a sine-wave
stub is returned so that the server and Pipecat adapter can be exercised
without downloading the full model.
"""

from __future__ import annotations

import struct
import math
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
from loguru import logger


# ---------------------------------------------------------------------------
# AudioConfig
# ---------------------------------------------------------------------------

@dataclass
class AudioConfig:
    """PCM audio parameters."""

    sample_rate: int = 24000          # Qwen3-TTS native 24 kHz
    output_sample_rate: int = 16000   # Pipecat default (resampled if needed)
    bit_depth: int = 16
    channels: int = 1
    # Token rate (Hz) of the speech tokenizer: 25 Hz (v1) or 12 Hz (v2)
    token_hz: int = 25


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

# Module-level vocoder cache — loaded lazily on first call
_vocoder_model = None
_vocoder_loaded = False


def tokens_to_pcm(token_ids: list[int], cfg: AudioConfig = AudioConfig()) -> bytes:
    """
    Convert a list of speech token IDs to raw 16-bit PCM bytes.

    Tries to use the Qwen3-TTS flow-matching vocoder if available;
    falls back to a simple sine-wave placeholder for testing.

    Returns bytes in 16-bit signed little-endian mono format at cfg.sample_rate.
    """
    global _vocoder_model, _vocoder_loaded

    if not _vocoder_loaded:
        _vocoder_model = _try_load_vocoder()
        _vocoder_loaded = True

    if _vocoder_model is not None:
        return _vocoder_decode(token_ids, cfg, _vocoder_model)
    else:
        return _stub_sine(token_ids, cfg)


# ---------------------------------------------------------------------------
# Vocoder decode (real path)
# ---------------------------------------------------------------------------

def _try_load_vocoder():
    """
    Attempt to load the Qwen3-TTS flow-matching vocoder sub-module.
    Returns the vocoder object, or None if unavailable.
    """
    try:
        import sys, os
        qwen_tts_root = _find_qwen_tts_root()
        if qwen_tts_root and qwen_tts_root not in sys.path:
            sys.path.insert(0, qwen_tts_root)

        # The vocoder is embedded in the full Qwen3TTS model; we surface it
        # as a standalone callable when the model weights are available.
        # On GPU deployments the TalkerDecoder will wire this up properly;
        # here we just signal "not available" so the stub runs during testing.
        logger.debug("Vocoder not pre-loaded; stub will be used until model is wired.")
        return None
    except Exception as exc:
        logger.debug(f"Vocoder load skipped: {exc}")
        return None


def set_vocoder(vocoder) -> None:
    """
    Wire in an external vocoder callable (called by server startup after
    the full Qwen3TTS model loads).

    vocoder must accept (token_ids: list[int], cfg: AudioConfig) → bytes.
    """
    global _vocoder_model, _vocoder_loaded
    _vocoder_model = vocoder
    _vocoder_loaded = True
    logger.info("External vocoder registered.")


def _vocoder_decode(token_ids: list[int], cfg: AudioConfig, vocoder) -> bytes:
    try:
        return vocoder(token_ids, cfg)
    except Exception as exc:
        logger.warning(f"Vocoder decode failed ({exc}), using stub.")
        return _stub_sine(token_ids, cfg)


# ---------------------------------------------------------------------------
# Stub: sine wave placeholder
# ---------------------------------------------------------------------------

def _stub_sine(token_ids: list[int], cfg: AudioConfig) -> bytes:
    """
    Generate a short sine burst for each token (for testing without real vocoder).

    Each token produces 1 / token_hz seconds of audio at cfg.sample_rate.
    """
    duration_secs = len(token_ids) / cfg.token_hz
    n_samples = int(cfg.sample_rate * duration_secs)
    if n_samples == 0:
        return b""

    # Use token values to modulate frequency slightly (440 Hz base)
    freq = 440.0 + (sum(token_ids) % 100) * 2.0
    t = np.linspace(0, duration_secs, n_samples, endpoint=False)
    waveform = (np.sin(2 * math.pi * freq * t) * 0.3 * 32767).astype(np.int16)
    return waveform.tobytes()


# ---------------------------------------------------------------------------
# Resampling helper
# ---------------------------------------------------------------------------

def resample_pcm(pcm_bytes: bytes, src_rate: int, dst_rate: int) -> bytes:
    """
    Resample 16-bit mono PCM from src_rate to dst_rate.
    Uses librosa if available, otherwise linear interpolation.
    """
    if src_rate == dst_rate:
        return pcm_bytes

    samples = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32) / 32768.0

    try:
        import librosa  # type: ignore

        resampled = librosa.resample(samples, orig_sr=src_rate, target_sr=dst_rate)
    except ImportError:
        # Linear interpolation fallback
        n_out = int(len(samples) * dst_rate / src_rate)
        x_old = np.linspace(0, 1, len(samples))
        x_new = np.linspace(0, 1, n_out)
        resampled = np.interp(x_new, x_old, samples)

    return (resampled * 32767).clip(-32768, 32767).astype(np.int16).tobytes()


def _find_qwen_tts_root() -> str | None:
    import os
    candidates = [
        os.path.join(os.path.dirname(__file__), "../../../../Qwen3-TTS"),
        os.path.join(os.getcwd(), "Qwen3-TTS"),
    ]
    for c in candidates:
        p = os.path.abspath(c)
        if os.path.isdir(p):
            return p
    return None
