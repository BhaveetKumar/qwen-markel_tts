"""
Pipecat TTSService adapter for the Qwen3-TTS megakernel streaming server.

This service connects a running qwen-markel-tts server to a Pipecat
voice pipeline. It streams audio frames as they arrive — never buffering
the full utterance — matching the zero-buffering requirement.

Pipeline position
-----------------
    STT → LLM → QwenMegakernelTTSService → audio transport

Usage
-----
    import aiohttp
    from pipecat_adapter import QwenMegakernelTTSService

    async with aiohttp.ClientSession() as session:
        tts = QwenMegakernelTTSService(
            base_url="http://localhost:8000",
            aiohttp_session=session,
            sample_rate=16000,
        )
        # Add to a Pipecat pipeline as any other TTS service.
"""

from __future__ import annotations

import base64
import json
import os
import sys
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from typing import Optional

from loguru import logger

# ---------------------------------------------------------------------------
# Pipecat import — optional so the module can be imported without pipecat
# installed (needed for unit tests).
# ---------------------------------------------------------------------------

try:
    import aiohttp
    from pipecat.frames.frames import (
        ErrorFrame,
        Frame,
        StartFrame,
        TTSAudioRawFrame,
    )
    from pipecat.services.settings import TTSSettings
    from pipecat.services.tts_service import TTSService
    from pipecat.utils.tracing.service_decorators import traced_tts
    _PIPECAT_AVAILABLE = True
except ImportError:
    _PIPECAT_AVAILABLE = False
    logger.warning(
        "pipecat-ai not installed. QwenMegakernelTTSService will be a stub."
    )


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

if _PIPECAT_AVAILABLE:
    @dataclass
    class QwenTTSSettings(TTSSettings):
        """Settings for QwenMegakernelTTSService."""
        model: str = "Qwen3-TTS-12Hz-0.6B-Base"
        language: str = "en"
        voice: str = "default"

    _BaseService = TTSService
else:
    # Minimal stub base so the module still imports without pipecat
    class QwenTTSSettings:
        voice: str = "default"
        sample_rate: Optional[int] = 16000

    class _BaseService:
        def __init__(self, **kwargs):
            pass


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class QwenMegakernelTTSService(_BaseService):
    """
    Pipecat TTS service that streams audio from the qwen-markel-tts server.

    The server must be running (see scripts/run_server.sh) before starting
    the Pipecat pipeline.

    Parameters
    ----------
    base_url : str
        Base URL of the megakernel TTS server, e.g. ``http://localhost:8000``.
    aiohttp_session : aiohttp.ClientSession
        Shared HTTP session.
    sample_rate : int
        Output PCM sample rate expected by Pipecat. Server currently delivers
        24 kHz and this adapter forwards that sample rate in emitted frames.
    settings : QwenTTSSettings, optional
        Configures voice and other runtime settings.
    """

    if _PIPECAT_AVAILABLE:
        Settings = QwenTTSSettings
        _settings: Settings

    def __init__(
        self,
        *,
        base_url: str = "http://localhost:8000",
        aiohttp_session,
        sample_rate: Optional[int] = None,
        settings: Optional[QwenTTSSettings] = None,
        **kwargs,
    ):
        if _PIPECAT_AVAILABLE:
            settings = settings or QwenTTSSettings()
            super().__init__(sample_rate=sample_rate, settings=settings, **kwargs)
        else:
            super().__init__(**kwargs)

        self._base_url = base_url.rstrip("/")
        self._session = aiohttp_session
        self._server_sample_rate = 24000  # server always delivers 24 kHz

    # ------------------------------------------------------------------
    # TTSService interface
    # ------------------------------------------------------------------

    if _PIPECAT_AVAILABLE:
        @traced_tts
        async def run_tts(self, text: str) -> AsyncGenerator[Frame, None]:
            """
            Stream audio frames for *text*.

            Yields TTSAudioRawFrame objects as PCM chunks arrive from the
            server — no full-utterance buffering.
            """
            async for pcm_bytes in self._stream_from_server(text):
                if pcm_bytes:
                    yield TTSAudioRawFrame(
                        audio=pcm_bytes,
                        sample_rate=self._server_sample_rate,
                        num_channels=1,
                    )

    else:
        async def run_tts(self, text: str) -> AsyncGenerator[bytes, None]:
            """Stub used when pipecat is not installed."""
            async for pcm in self._stream_from_server(text):
                yield pcm

    # ------------------------------------------------------------------
    # Internal HTTP streaming
    # ------------------------------------------------------------------

    async def _stream_from_server(self, text: str) -> AsyncGenerator[bytes, None]:
        url = f"{self._base_url}/tts/stream"
        payload = {"text": text, "voice": "default"}

        try:
            async with self._session.post(url, json=payload) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    logger.error(f"TTS server returned {resp.status}: {body}")
                    if _PIPECAT_AVAILABLE:
                        yield ErrorFrame(f"TTS server error {resp.status}")
                    return

                async for raw_line in resp.content:
                    line = raw_line.strip()
                    if not line:
                        continue
                    try:
                        msg = json.loads(line)
                    except json.JSONDecodeError:
                        logger.warning(f"Non-JSON line from server: {line!r}")
                        continue

                    if "error" in msg:
                        logger.error(f"Server stream error: {msg['error']}")
                        break

                    if msg.get("event") == "end":
                        metrics = msg.get("metrics", {})
                        logger.info(
                            f"TTS complete — "
                            f"TTFC={metrics.get('TTFC_ms', 0):.1f}ms "
                            f"RTF={metrics.get('RTF', 0):.3f} "
                            f"tok/s={metrics.get('decode_tokens_per_sec', 0):.0f}"
                        )
                        break

                    pcm_b64 = msg.get("pcm")
                    if pcm_b64:
                        yield base64.b64decode(pcm_b64)

        except Exception as exc:
            logger.error(f"HTTP error communicating with TTS server: {exc}")
            if _PIPECAT_AVAILABLE:
                yield ErrorFrame(str(exc))

    # ------------------------------------------------------------------
    # Health check helper
    # ------------------------------------------------------------------

    async def is_healthy(self) -> bool:
        """Return True if the backend server is reachable."""
        try:
            async with self._session.get(
                f"{self._base_url}/health", timeout=aiohttp.ClientTimeout(total=3)
            ) as resp:
                return resp.status == 200
        except Exception:
            return False
