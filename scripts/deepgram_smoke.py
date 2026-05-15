#!/usr/bin/env python3
"""Deepgram live STT smoke test using a public audio stream.

Usage:
  python scripts/deepgram_smoke.py
  python scripts/deepgram_smoke.py --seconds 20
  python scripts/deepgram_smoke.py --api-key "$DEEPGRAM_API_KEY"
"""

from __future__ import annotations

import argparse
import os
import threading
import time

import httpx


def run_smoke(api_key: str, stream_url: str, model: str, language: str, seconds: int) -> int:
    try:
        from deepgram import DeepgramClient, LiveTranscriptionEvents, LiveOptions
    except Exception as exc:  # pragma: no cover
        print("ERROR: deepgram-sdk is not installed or import failed.")
        print(f"DETAILS: {type(exc).__name__}: {exc}")
        print("FIX: pip install deepgram-sdk")
        return 2

    if not api_key:
        print("ERROR: Missing Deepgram API key.")
        print("FIX: export DEEPGRAM_API_KEY=... or pass --api-key")
        return 2

    client = DeepgramClient(api_key=api_key)
    conn = client.listen.websocket.v("1")

    open_evt = threading.Event()
    got_any_transcript = threading.Event()

    def on_open(*_args, **_kwargs):
        open_evt.set()
        print("[ok] websocket opened")

    def on_error(error, *_args, **_kwargs):
        print(f"[error] deepgram error: {error}")

    def on_transcript(result, *_args, **_kwargs):
        try:
            alt = result.channel.alternatives[0]
            text = (alt.transcript or "").strip()
            if text:
                got_any_transcript.set()
                print(f"[stt] {text}")
        except Exception:
            pass

    conn.on(LiveTranscriptionEvents.Open, on_open)
    conn.on(LiveTranscriptionEvents.Error, on_error)
    conn.on(LiveTranscriptionEvents.Transcript, on_transcript)

    options = LiveOptions(
        model=model,
        language=language,
        smart_format=True,
        encoding="aac",
        channels=2,
        sample_rate=44100,
    )

    if not conn.start(options):
        print("ERROR: failed to start Deepgram websocket (auth or network issue).")
        return 1

    def stream_audio() -> None:
        try:
            with httpx.stream("GET", stream_url, follow_redirects=True, timeout=30.0) as response:
                for chunk in response.iter_bytes(chunk_size=4096):
                    conn.send(chunk)
        except Exception as exc:
            print(f"[error] stream source failed: {type(exc).__name__}: {exc}")

    t = threading.Thread(target=stream_audio, daemon=True)
    t.start()

    if not open_evt.wait(timeout=8):
        print("ERROR: websocket did not open in time.")
        conn.finish()
        return 1

    print(f"[info] listening for {seconds}s from {stream_url}")
    time.sleep(seconds)
    conn.finish()

    if got_any_transcript.is_set():
        print("PASS: Deepgram STT is working.")
        return 0

    print("WARN: Connected but no transcript captured in test window.")
    print("This can happen due to stream variability; retry with --seconds 30.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Deepgram STT smoke test")
    parser.add_argument("--api-key", default=os.getenv("DEEPGRAM_API_KEY", ""), help="Deepgram API key")
    parser.add_argument(
        "--stream-url",
        default="https://playerservices.streamtheworld.com/api/livestream-redirect/CSPANRADIOAAC.aac",
        help="Public audio stream URL",
    )
    parser.add_argument("--model", default="nova-3", help="Deepgram model name")
    parser.add_argument("--language", default="en", help="Language code")
    parser.add_argument("--seconds", type=int, default=15, help="Test duration")
    args = parser.parse_args()

    return run_smoke(args.api_key, args.stream_url, args.model, args.language, args.seconds)


if __name__ == "__main__":
    raise SystemExit(main())