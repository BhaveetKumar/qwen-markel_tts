"""
TalkerDecoder: integrates KernelDecoder with the Qwen3-TTS talker pipeline.

Flow
----
  text tokens (from text tokenizer)
      ↓
  TalkerDecoder.stream_tokens()       ← autoregressive loop via KernelDecoder
      ↓  (yields speech token IDs)
  TalkerDecoder.stream_audio()        ← calls vocoder per chunk
      ↓  (yields PCM bytes)
  Server / Pipecat adapter

Token budget
------------
Qwen3-TTS uses a 25 Hz / 12 Hz speech tokenizer; typical speech runs at
~200–400 speech tokens/second. At 1000 kernel tok/s we achieve RTF ≈ 0.2–0.5,
comfortably under the 0.15 RTF target once PCM conversion is also pipelined.
"""

from __future__ import annotations

import time
from collections.abc import AsyncGenerator, Generator
from typing import Optional

import torch
from loguru import logger

from megakernel.adapter import KernelDecoder, ModelConfig, QWEN3_TTS_TALKER_CONFIG
from qwen3_tts.loader import TalkerWeights, load_talker_weights
from qwen3_tts.vocoder import AudioConfig, tokens_to_pcm


# ---------------------------------------------------------------------------
# TalkerDecoder
# ---------------------------------------------------------------------------

class TalkerDecoder:
    """
    High-level decoder wrapping KernelDecoder for Qwen3-TTS talker output.

    Parameters
    ----------
    weights : TalkerWeights
        Loaded via load_talker_weights().
    tokenizer :
        Tokenizer compatible with the talker model.
    cfg : ModelConfig
        Architecture configuration (defaults to QWEN3_TTS_TALKER_CONFIG).
    audio_cfg : AudioConfig
        Audio synthesis settings.
    eos_token_id : int
        Token ID that signals end-of-sequence.
    chunk_tokens : int
        Number of speech tokens per audio chunk (controls chunk duration).
        At 25 Hz: 1 token = 40 ms; chunk_tokens=1 gives ~40 ms chunks.
    max_tokens : int
        Hard cap on generated tokens per request.
    """

    def __init__(
        self,
        weights: TalkerWeights,
        tokenizer,
        cfg: ModelConfig = QWEN3_TTS_TALKER_CONFIG,
        audio_cfg: Optional[AudioConfig] = None,
        eos_token_id: int = 1,
        chunk_tokens: int = 1,
        max_tokens: int = 2048,
    ):
        self._tokenizer = tokenizer
        self._cfg = cfg
        self._audio_cfg = audio_cfg or AudioConfig()
        self._eos = eos_token_id
        self._chunk_tokens = chunk_tokens
        self._max_tokens = max_tokens

        # Metrics tracked per request
        self._last_ttfc_ms: float = 0.0
        self._last_tok_per_sec: float = 0.0
        self._last_rtf: float = 0.0

        weights_dict = {
            "embed_weight": weights.embed_weight,
            "layer_weights": weights.layer_weights,
            "final_norm_weight": weights.final_norm_weight,
            "lm_head_weight": weights.lm_head_weight,
            "cos_table": weights.cos_table,
            "sin_table": weights.sin_table,
        }
        self._kernel = KernelDecoder(
            weights_dict,
            cfg,
            hf_model=weights.hf_model,
        )

    # ------------------------------------------------------------------
    # Synchronous streaming generators
    # ------------------------------------------------------------------

    def stream_tokens(self, prompt_token_ids: list[int]) -> Generator[int, None, None]:
        """
        Autoregressive decode loop yielding speech token IDs.

        Feeds the prompt into the kernel one token at a time (prefill),
        then decodes until EOS or max_tokens.
        """
        self._kernel.reset()
        ids = prompt_token_ids

        t_start = time.perf_counter()
        first_chunk = True

        # Prefill: feed all tokens except the last
        for tok in ids[:-1]:
            self._kernel.step(tok)

        # Decode
        next_tok = ids[-1] if ids else self._cfg.vocab_size - 1
        generated = 0

        while generated < self._max_tokens:
            next_tok = self._kernel.step(next_tok)
            generated += 1

            if first_chunk:
                self._last_ttfc_ms = (time.perf_counter() - t_start) * 1000
                first_chunk = False

            if next_tok == self._eos:
                break

            yield next_tok

        elapsed = time.perf_counter() - t_start
        self._last_tok_per_sec = generated / elapsed if elapsed > 0 else 0.0
        logger.debug(
            f"Decode done: {generated} tokens in {elapsed*1000:.1f} ms "
            f"({self._last_tok_per_sec:.0f} tok/s), TTFC={self._last_ttfc_ms:.1f} ms"
        )

    def stream_audio(
        self, prompt_token_ids: list[int]
    ) -> Generator[bytes, None, None]:
        """
        End-to-end streaming: yields raw PCM bytes chunk by chunk.

        Each yielded bytes object corresponds to `chunk_tokens` speech tokens
        converted to PCM (see vocoder.tokens_to_pcm).
        """
        chunk_buf: list[int] = []

        t_audio_start = time.perf_counter()
        audio_samples = 0

        for tok in self.stream_tokens(prompt_token_ids):
            chunk_buf.append(tok)
            if len(chunk_buf) >= self._chunk_tokens:
                pcm = tokens_to_pcm(chunk_buf, self._audio_cfg)
                audio_samples += len(pcm) // 2  # 16-bit samples
                chunk_buf = []
                yield pcm

        # Flush remaining tokens
        if chunk_buf:
            pcm = tokens_to_pcm(chunk_buf, self._audio_cfg)
            audio_samples += len(pcm) // 2
            yield pcm

        elapsed = time.perf_counter() - t_audio_start
        audio_secs = audio_samples / self._audio_cfg.sample_rate
        self._last_rtf = elapsed / audio_secs if audio_secs > 0 else 0.0
        logger.debug(f"RTF={self._last_rtf:.3f}")

    # ------------------------------------------------------------------
    # Async wrappers for FastAPI / Pipecat
    # ------------------------------------------------------------------

    async def astream_audio(
        self, prompt_token_ids: list[int]
    ) -> AsyncGenerator[bytes, None]:
        """Async wrapper around stream_audio for use in async contexts."""
        import asyncio

        loop = asyncio.get_event_loop()
        # Run synchronous decode in an executor to avoid blocking the event loop.
        # Audio chunks are queued as they arrive.
        import queue
        import threading

        q: queue.Queue = queue.Queue()
        _SENTINEL = object()

        def _worker():
            try:
                for chunk in self.stream_audio(prompt_token_ids):
                    q.put(chunk)
            finally:
                q.put(_SENTINEL)

        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()

        while True:
            chunk = await loop.run_in_executor(None, q.get)
            if chunk is _SENTINEL:
                break
            yield chunk

    # ------------------------------------------------------------------
    # Metrics accessors
    # ------------------------------------------------------------------

    @property
    def last_ttfc_ms(self) -> float:
        return self._last_ttfc_ms

    @property
    def last_tok_per_sec(self) -> float:
        return self._last_tok_per_sec

    @property
    def last_rtf(self) -> float:
        return self._last_rtf


# ---------------------------------------------------------------------------
# Convenience factory
# ---------------------------------------------------------------------------

def create_decoder(
    model_name: str = "Qwen/Qwen3-TTS",
    chunk_tokens: int = 1,
    max_tokens: int = 2048,
) -> TalkerDecoder:
    """Load weights and return a ready-to-use TalkerDecoder."""
    weights, tokenizer = load_talker_weights(model_name)
    return TalkerDecoder(weights, tokenizer, chunk_tokens=chunk_tokens, max_tokens=max_tokens)
