#!/usr/bin/env python3
"""
demo.py — STT → LLM → TTS Pipecat voice pipeline demo.

Requires pipecat-ai, a running Qwen3-TTS server (run_server.sh),
and a Deepgram API key for STT (or substitute any Pipecat STT service).

Usage:
    python scripts/demo.py \
        --tts-url http://localhost:8000 \
        --deepgram-key $DEEPGRAM_API_KEY \
        --openai-key $OPENAI_API_KEY
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys

_SRC = os.path.join(os.path.dirname(__file__), "../src")
sys.path.insert(0, os.path.abspath(_SRC))


async def run_demo(tts_url: str, deepgram_key: str, openai_key: str):
    try:
        import aiohttp
        from pipecat.pipeline.pipeline import Pipeline
        from pipecat.pipeline.runner import PipelineRunner
        from pipecat.pipeline.task import PipelineParams, PipelineTask
        from pipecat.services.deepgram import DeepgramSTTService
        from pipecat.services.openai import OpenAILLMService
        from pipecat.transports.local.audio import LocalAudioTransport, LocalAudioParams
    except ImportError as e:
        print(f"Missing dependency: {e}")
        print("Install with: pip install pipecat-ai[deepgram,openai]")
        return

    from pipecat_adapter.tts import QwenMegakernelTTSService

    async with aiohttp.ClientSession() as session:
        tts = QwenMegakernelTTSService(
            base_url=tts_url,
            aiohttp_session=session,
            sample_rate=16000,
        )

        if not await tts.is_healthy():
            print(f"ERROR: TTS server at {tts_url} is not reachable. Start it with scripts/run_server.sh")
            return

        stt = DeepgramSTTService(api_key=deepgram_key)
        llm = OpenAILLMService(api_key=openai_key, model="gpt-4o-mini")
        transport = LocalAudioTransport(LocalAudioParams(audio_in_enabled=True, audio_out_enabled=True))

        pipeline = Pipeline([
            transport.input(),
            stt,
            llm,
            tts,
            transport.output(),
        ])

        task = PipelineTask(
            pipeline,
            params=PipelineParams(allow_interruptions=True),
        )

        print("Voice agent running. Speak into your microphone (Ctrl+C to stop).")
        runner = PipelineRunner()
        await runner.run(task)


def main():
    parser = argparse.ArgumentParser(description="Qwen3-TTS Pipecat voice demo")
    parser.add_argument("--tts-url", default="http://localhost:8000")
    parser.add_argument("--deepgram-key", default=os.getenv("DEEPGRAM_API_KEY", ""))
    parser.add_argument("--openai-key", default=os.getenv("OPENAI_API_KEY", ""))
    args = parser.parse_args()

    if not args.deepgram_key:
        print("Set DEEPGRAM_API_KEY or pass --deepgram-key")
        sys.exit(1)
    if not args.openai_key:
        print("Set OPENAI_API_KEY or pass --openai-key")
        sys.exit(1)

    asyncio.run(run_demo(args.tts_url, args.deepgram_key, args.openai_key))


if __name__ == "__main__":
    main()
