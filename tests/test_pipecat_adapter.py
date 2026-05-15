"""
Tests for the Pipecat adapter (no pipecat-ai required — stub mode).
"""

import sys, os, asyncio

_SRC = os.path.join(os.path.dirname(__file__), "../src")
sys.path.insert(0, os.path.abspath(_SRC))

import pytest
import json
import base64
from unittest.mock import AsyncMock, MagicMock, patch

from pipecat_adapter.tts import QwenMegakernelTTSService, _PIPECAT_AVAILABLE


# ---------------------------------------------------------------------------
# Mock aiohttp session
# ---------------------------------------------------------------------------

def _make_mock_session(chunks: list[bytes], status: int = 200):
    """Build an aiohttp.ClientSession mock that streams *chunks* as NDJSON."""

    async def _mock_response_iter():
        for i, chunk in enumerate(chunks):
            payload = json.dumps({
                "chunk_id": i,
                "pcm": base64.b64encode(chunk).decode(),
            })
            yield (payload + "\n").encode()
        end_payload = json.dumps({"event": "end", "metrics": {}})
        yield (end_payload + "\n").encode()

    mock_resp = MagicMock()
    mock_resp.status = status
    mock_resp.content.__aiter__ = lambda self: _mock_response_iter()

    mock_cm = AsyncMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_cm.__aexit__ = AsyncMock(return_value=False)

    mock_session = MagicMock()
    mock_session.post = MagicMock(return_value=mock_cm)
    mock_session.get = AsyncMock()

    return mock_session


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_service_instantiates_without_pipecat():
    session = MagicMock()
    svc = QwenMegakernelTTSService(
        base_url="http://localhost:8000",
        aiohttp_session=session,
    )
    assert svc._base_url == "http://localhost:8000"


@pytest.mark.asyncio
async def test_stream_from_server_yields_audio_bytes():
    test_chunks = [b"\x00\x01" * 100, b"\x02\x03" * 100]
    session = _make_mock_session(test_chunks)
    svc = QwenMegakernelTTSService(
        base_url="http://localhost:8000",
        aiohttp_session=session,
    )

    received = []
    async for item in svc._stream_from_server("hello world"):
        received.append(item)

    assert len(received) == 2
    assert received[0] == test_chunks[0]
    assert received[1] == test_chunks[1]


@pytest.mark.asyncio
async def test_stream_handles_server_error():
    """503 from server must not raise — just log and return."""
    mock_resp = MagicMock()
    mock_resp.status = 503
    mock_resp.text = AsyncMock(return_value="unavailable")

    mock_cm = AsyncMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_cm.__aexit__ = AsyncMock(return_value=False)

    session = MagicMock()
    session.post = MagicMock(return_value=mock_cm)

    svc = QwenMegakernelTTSService(
        base_url="http://localhost:8000",
        aiohttp_session=session,
    )
    received = []
    async for item in svc._stream_from_server("hello"):
        received.append(item)

    # In non-pipecat mode, nothing is yielded on error
    assert received == [] or all(not isinstance(r, bytes) for r in received)


@pytest.mark.asyncio
async def test_is_healthy_false_on_connection_error():
    session = MagicMock()
    session.get = MagicMock(side_effect=Exception("connection refused"))
    svc = QwenMegakernelTTSService(
        base_url="http://localhost:8000",
        aiohttp_session=session,
    )
    result = await svc.is_healthy()
    assert result is False
