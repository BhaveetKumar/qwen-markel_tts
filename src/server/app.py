"""
FastAPI streaming TTS inference server.

Endpoints
---------
POST /tts/stream
    Body:  { "text": "...", "voice": "default" }
    Returns: chunked streaming response — JSON lines:
        {"chunk_id": 0, "pcm": "<base64>"}
        ...
        {"event": "end", "metrics": {...}}

GET /metrics
    Returns last-request performance numbers.

GET /health
    Liveness check.
"""

from __future__ import annotations

import base64
import json
import os
import sys
import time
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from loguru import logger
from pydantic import BaseModel, field_validator

# ---------------------------------------------------------------------------
# Path setup: allow running from the src/ directory
# ---------------------------------------------------------------------------

_SRC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class TTSRequest(BaseModel):
    text: str
    voice: str = "default"

    @field_validator("text")
    @classmethod
    def text_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("text must not be empty")
        if len(v) > 4096:
            raise ValueError("text exceeds maximum length of 4096 characters")
        return v


class MetricsResponse(BaseModel):
    decode_tokens_per_sec: float
    TTFC_ms: float
    RTF: float
    avg_latency_ms: float


# ---------------------------------------------------------------------------
# Application state
# ---------------------------------------------------------------------------

class _AppState:
    decoder = None
    tokenizer = None
    last_metrics: dict = {}


_state = _AppState()


# ---------------------------------------------------------------------------
# Lifespan: load model once at startup
# ---------------------------------------------------------------------------

@asynccontextmanager
async def _lifespan(app: FastAPI):
    model_name = os.getenv("QWEN_TTS_MODEL", "Qwen/Qwen3-TTS")
    logger.info(f"Loading Qwen3-TTS talker decoder: {model_name}")
    try:
        from qwen3_tts.loader import load_talker_weights
        from qwen3_tts.decoder import TalkerDecoder

        weights, tokenizer = load_talker_weights(
            model_name,
            verbose=True,
            use_hf_fallback=False,
        )
        _state.decoder = TalkerDecoder(weights, tokenizer)
        _state.tokenizer = tokenizer
        logger.info("Model loaded successfully.")
    except Exception as exc:
        logger.error(f"Model load failed: {exc}. Server will return 503 for TTS requests.")
    yield
    logger.info("Shutting down.")


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

def create_app() -> FastAPI:
    app = FastAPI(
        title="Qwen3-TTS Megakernel Server",
        version="0.1.0",
        lifespan=_lifespan,
    )

    # ----------------------------------------------------------------
    # POST /tts/stream
    # ----------------------------------------------------------------

    @app.post("/tts/stream")
    async def tts_stream(req: TTSRequest):
        if _state.decoder is None:
            raise HTTPException(status_code=503, detail={
                "error": {
                    "type": "ServiceUnavailable",
                    "message": "Model not loaded. Check server logs.",
                }
            })

        prompt_ids = _encode_text(req.text, _state.tokenizer)
        if not prompt_ids:
            raise HTTPException(status_code=400, detail={
                "error": {
                    "type": "ValueError",
                    "message": "Tokenization produced empty token list.",
                }
            })

        async def _generate():
            chunk_id = 0
            t_request_start = time.perf_counter()

            try:
                async for pcm_bytes in _state.decoder.astream_audio(prompt_ids):
                    payload = {
                        "chunk_id": chunk_id,
                        "pcm": base64.b64encode(pcm_bytes).decode("ascii"),
                    }
                    yield json.dumps(payload) + "\n"
                    chunk_id += 1

                latency_ms = (time.perf_counter() - t_request_start) * 1000
                _state.last_metrics = {
                    "decode_tokens_per_sec": _state.decoder.last_tok_per_sec,
                    "TTFC_ms": _state.decoder.last_ttfc_ms,
                    "RTF": _state.decoder.last_rtf,
                    "avg_latency_ms": latency_ms,
                }
                yield json.dumps({"event": "end", "metrics": _state.last_metrics}) + "\n"

            except Exception as exc:
                logger.error(f"Streaming error: {exc}")
                yield json.dumps({
                    "error": {
                        "type": type(exc).__name__,
                        "message": str(exc),
                    }
                }) + "\n"

        return StreamingResponse(
            _generate(),
            media_type="application/x-ndjson",
        )

    # ----------------------------------------------------------------
    # GET /metrics
    # ----------------------------------------------------------------

    @app.get("/metrics", response_model=MetricsResponse)
    async def get_metrics():
        if not _state.last_metrics:
            return MetricsResponse(
                decode_tokens_per_sec=0.0,
                TTFC_ms=0.0,
                RTF=0.0,
                avg_latency_ms=0.0,
            )
        m = _state.last_metrics
        return MetricsResponse(
            decode_tokens_per_sec=m.get("decode_tokens_per_sec", 0.0),
            TTFC_ms=m.get("TTFC_ms", 0.0),
            RTF=m.get("RTF", 0.0),
            avg_latency_ms=m.get("avg_latency_ms", 0.0),
        )

    # ----------------------------------------------------------------
    # GET /health
    # ----------------------------------------------------------------

    @app.get("/health")
    async def health():
        return {
            "status": "ok",
            "model_loaded": _state.decoder is not None,
        }

    return app


# ---------------------------------------------------------------------------
# Tokenization helper
# ---------------------------------------------------------------------------

def _encode_text(text: str, tokenizer) -> list[int]:
    """Encode input text using whatever tokenizer the talker loaded."""
    if hasattr(tokenizer, "encode"):
        return tokenizer.encode(text, add_special_tokens=True)
    # Processor-style (Qwen3TTSProcessor)
    if hasattr(tokenizer, "__call__"):
        enc = tokenizer(text=text, return_tensors="pt")
        return enc["input_ids"][0].tolist()
    raise TypeError(f"Unknown tokenizer type: {type(tokenizer)}")


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "server.app:create_app",
        factory=True,
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        log_level="info",
    )
