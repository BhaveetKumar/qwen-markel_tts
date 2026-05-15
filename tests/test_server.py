"""
Tests for the FastAPI TTS server.

Uses an ASGI test client (httpx) — no real model download required.
The server will report model_loaded=False but routes must still return
correct status codes and shapes.
"""

import sys, os, asyncio, json, base64

_SRC = os.path.join(os.path.dirname(__file__), "../src")
sys.path.insert(0, os.path.abspath(_SRC))

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from server.app import create_app, _state


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def app():
    """Return the FastAPI app with the lifespan skipped (model not loaded)."""
    return create_app()


@pytest_asyncio.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


# ---------------------------------------------------------------------------
# /health
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_health_returns_200(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert data["status"] == "ok"


# ---------------------------------------------------------------------------
# /metrics
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_metrics_empty_returns_zeros(client):
    _state.last_metrics = {}
    resp = await client.get("/metrics")
    assert resp.status_code == 200
    data = resp.json()
    assert data["decode_tokens_per_sec"] == 0.0
    assert data["TTFC_ms"] == 0.0


# ---------------------------------------------------------------------------
# /tts/stream — model not loaded (503)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_tts_stream_503_when_no_model(client):
    _state.decoder = None
    resp = await client.post("/tts/stream", json={"text": "hello"})
    assert resp.status_code == 503


# ---------------------------------------------------------------------------
# /tts/stream — validation errors
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_tts_stream_400_on_empty_text(client):
    resp = await client.post("/tts/stream", json={"text": "   "})
    assert resp.status_code == 422  # pydantic validation


@pytest.mark.asyncio
async def test_tts_stream_422_on_missing_text(client):
    resp = await client.post("/tts/stream", json={})
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# /tts/stream — with stub decoder wired in
# ---------------------------------------------------------------------------

class _StubDecoder:
    """Minimal decoder stub that emits 3 audio chunks then ends."""

    last_ttfc_ms = 5.0
    last_tok_per_sec = 900.0
    last_rtf = 0.12

    async def astream_audio(self, prompt_ids):
        for _ in range(3):
            yield b"\x00\x01" * 480  # ~20 ms @ 24 kHz 16-bit


class _StubTokenizer:
    def encode(self, text, add_special_tokens=True):
        return [1, 2, 3]


@pytest.mark.asyncio
async def test_tts_stream_with_stub_decoder(client):
    _state.decoder = _StubDecoder()
    _state.tokenizer = _StubTokenizer()

    resp = await client.post(
        "/tts/stream",
        json={"text": "test sentence"},
    )
    assert resp.status_code == 200

    lines = [l for l in resp.text.strip().split("\n") if l]
    assert len(lines) >= 1

    # First lines should be audio chunks
    first = json.loads(lines[0])
    assert "chunk_id" in first
    assert "pcm" in first
    # pcm must be valid base64
    raw = base64.b64decode(first["pcm"])
    assert isinstance(raw, bytes)

    # Last line must be the "end" event
    last = json.loads(lines[-1])
    assert last.get("event") == "end"
    assert "metrics" in last
