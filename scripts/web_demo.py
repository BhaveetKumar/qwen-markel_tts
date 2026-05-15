#!/usr/bin/env python3
"""
web_demo.py — Browser-based UI for the STT → LLM → TTS pipeline.

The browser captures the microphone (avoiding macOS Python TCC issues),
posts the audio to this server, which:
  1. Sends audio to Deepgram REST API for transcription.
  2. Sends the transcript to OpenAI for a response.
  3. Streams the response through the Qwen3-TTS server.
  4. Returns concatenated 24 kHz mono PCM (wrapped as WAV) to the browser.

Usage:
    python3 scripts/web_demo.py \
        --tts-url https://collectibles-wrapped-studied-hazards.trycloudflare.com \
        --deepgram-key $DEEPGRAM_API_KEY \
        --openai-key $OPENAI_API_KEY \
        --port 8083

Then open http://localhost:8080 in your browser.
"""


from __future__ import annotations
from pathlib import Path
import importlib.util
import sys as _sys
_env_loader_path = str(Path(__file__).parent / ".env_loader.py")
spec = importlib.util.spec_from_file_location("_env_loader", _env_loader_path)
_env_loader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(_env_loader)
_env_loader.load_dotenv()

import argparse
import asyncio
import base64
import io
import json
import os
import ssl
import struct
import sys
from pathlib import Path

import aiohttp
import certifi
from aiohttp import web
from openai import AsyncOpenAI

STATIC_DIR = Path(__file__).parent / "static"


# Globals populated from .env only
TTS_URL: str = os.environ.get("TTS_URL", "http://localhost:8000")
DEEPGRAM_KEY: str = os.environ.get("DEEPGRAM_API_KEY", "")
OPENAI_KEY: str = os.environ.get("OPENAI_API_KEY", "")
SSL_CONTEXT: ssl.SSLContext | None = None


def make_wav(pcm: bytes, sample_rate: int = 24000, channels: int = 1, bits: int = 16) -> bytes:
    """Wrap raw PCM in a minimal WAV container."""
    byte_rate = sample_rate * channels * bits // 8
    block_align = channels * bits // 8
    data_size = len(pcm)
    header = b"RIFF" + struct.pack("<I", 36 + data_size) + b"WAVE"
    header += b"fmt " + struct.pack("<IHHIIHH", 16, 1, channels, sample_rate, byte_rate, block_align, bits)
    header += b"data" + struct.pack("<I", data_size)
    return header + pcm


async def transcribe_with_deepgram(session: aiohttp.ClientSession, audio_bytes: bytes, content_type: str) -> str:
    """Send audio to Deepgram pre-recorded REST endpoint and return transcript."""
    url = "https://api.deepgram.com/v1/listen?model=nova-2&smart_format=true&punctuate=true"
    headers = {
        "Authorization": f"Token {DEEPGRAM_KEY}",
        "Content-Type": content_type or "audio/webm",
    }
    async with session.post(url, headers=headers, data=audio_bytes) as resp:
        if resp.status != 200:
            body = await resp.text()
            raise RuntimeError(f"Deepgram {resp.status}: {body}")
        data = await resp.json()
    try:
        return data["results"]["channels"][0]["alternatives"][0]["transcript"].strip()
    except (KeyError, IndexError):
        return ""


async def chat_with_openai(transcript: str) -> str:
    """Get a short conversational reply from OpenAI."""
    client = AsyncOpenAI(api_key=OPENAI_KEY)
    resp = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a friendly voice assistant. Reply in 1-2 short sentences."},
            {"role": "user", "content": transcript},
        ],
        max_tokens=120,
    )
    return (resp.choices[0].message.content or "").strip()


async def synthesize_with_qwen(session: aiohttp.ClientSession, text: str) -> tuple[bytes, dict]:
    """Stream audio chunks from Qwen TTS server and concatenate PCM."""
    url = f"{TTS_URL.rstrip('/')}/tts/stream"
    payload = {"text": text, "voice": "default"}
    pcm_chunks: list[bytes] = []
    metrics: dict = {}
    async with session.post(url, json=payload) as resp:
        if resp.status != 200:
            body = await resp.text()
            raise RuntimeError(f"TTS server {resp.status}: {body}")
        async for raw_line in resp.content:
            line = raw_line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue
            if msg.get("event") == "end":
                metrics = msg.get("metrics", {})
                break
            if "error" in msg:
                raise RuntimeError(f"TTS stream error: {msg['error']}")
            pcm_b64 = msg.get("pcm")
            if pcm_b64:
                pcm_chunks.append(base64.b64decode(pcm_b64))
    return b"".join(pcm_chunks), metrics


# --------------------------------------------------------------------------
# HTTP handlers
# --------------------------------------------------------------------------

async def handle_index(request: web.Request) -> web.Response:
    return web.FileResponse(STATIC_DIR / "index.html")


async def handle_chat(request: web.Request) -> web.Response:
    """Receive audio blob, return JSON with transcript, response text, audio (base64 WAV) and metrics."""
    audio_bytes = await request.read()
    content_type = request.headers.get("Content-Type", "audio/webm")
    if not audio_bytes:
        return web.json_response({"error": "empty audio"}, status=400)

    connector = aiohttp.TCPConnector(ssl=SSL_CONTEXT) if SSL_CONTEXT else None
    async with aiohttp.ClientSession(connector=connector) as session:
        try:
            transcript = await transcribe_with_deepgram(session, audio_bytes, content_type)
        except Exception as e:
            return web.json_response({"error": f"transcribe: {e}"}, status=500)

        if not transcript:
            return web.json_response({
                "transcript": "",
                "response": "",
                "audio_b64": "",
                "metrics": {},
                "warning": "No speech detected.",
            })

        try:
            reply = await chat_with_openai(transcript)
        except Exception as e:
            return web.json_response({"error": f"llm: {e}", "transcript": transcript}, status=500)

        try:
            pcm, metrics = await synthesize_with_qwen(session, reply)
        except Exception as e:
            return web.json_response({"error": f"tts: {e}", "transcript": transcript, "response": reply}, status=500)

    wav_bytes = make_wav(pcm, sample_rate=24000)
    return web.json_response({
        "transcript": transcript,
        "response": reply,
        "audio_b64": base64.b64encode(wav_bytes).decode("ascii"),
        "metrics": metrics,
    })


async def handle_health(request: web.Request) -> web.Response:
    return web.json_response({"ok": True, "tts_url": TTS_URL})


def configure_ssl() -> ssl.SSLContext | None:
    try:
        os.environ.setdefault("SSL_CERT_FILE", certifi.where())
        os.environ.setdefault("REQUESTS_CA_BUNDLE", certifi.where())
        ctx = ssl.create_default_context(cafile=certifi.where())
        return ctx
    except Exception as e:
        print(f"[ssl] warning: {e}", flush=True)
        return None



def main() -> int:
    global SSL_CONTEXT

    # Only allow host/port override for local dev, not secrets
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()

    if not DEEPGRAM_KEY:
        print("✗ Missing DEEPGRAM_API_KEY in .env", file=sys.stderr)
        return 1
    if not OPENAI_KEY:
        print("✗ Missing OPENAI_API_KEY in .env", file=sys.stderr)
        return 1

    SSL_CONTEXT = configure_ssl()

    app = web.Application(client_max_size=50 * 1024 * 1024)
    app.router.add_get("/", handle_index)
    app.router.add_get("/health", handle_health)
    app.router.add_post("/api/chat", handle_chat)
    app.router.add_static("/static/", path=str(STATIC_DIR), show_index=False)

    print("🎙️  Qwen3-TTS Web Demo")
    print("=" * 60)
    print(f"  TTS server   : {TTS_URL}")
    print(f"  Deepgram key : ***{DEEPGRAM_KEY[-4:]}")
    print(f"  OpenAI key   : ***{OPENAI_KEY[-4:]}")
    print(f"  Open in browser → http://{args.host}:{args.port}")
    print("=" * 60)

    web.run_app(app, host=args.host, port=args.port, print=None)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
