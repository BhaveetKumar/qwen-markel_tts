#!/usr/bin/env python3
"""
Simple STT test - captures microphone and prints what Deepgram transcribes.

Usage:
    python scripts/simple_stt_test.py --deepgram-key $DEEPGRAM_API_KEY
"""

import argparse
import asyncio
import os
import sys

async def test_stt(deepgram_key: str):
    try:
        import aiohttp
        from pipecat.transports.local.audio import LocalAudioTransport
        try:
            from pipecat.transports.local.audio import LocalAudioParams as _LocalAudioParams
        except ImportError:
            from pipecat.transports.local.audio import LocalAudioTransportParams as _LocalAudioParams
    except Exception as e:
        print(f"Missing dependency: {e}")
        print("Install with: pip install 'pipecat-ai[local,deepgram]'")
        return

    try:
        from pipecat.services.deepgram import DeepgramSTTService
    except ImportError:
        from pipecat.services.deepgram.stt import DeepgramSTTService

    from pipecat.pipeline.pipeline import Pipeline
    from pipecat.pipeline.runner import PipelineRunner
    from pipecat.pipeline.task import PipelineTask, PipelineParams

    # Simple passthrough processor to print STT output
    from pipecat.processors.frame_processor import FrameProcessor
    from pipecat.frames.frames import TextFrame
    
    class PrintProcessor(FrameProcessor):
        async def process_frame(self, frame):
            if isinstance(frame, TextFrame):
                print(f"\n🎤 You said: {frame.text}")
            await self.push_frame(frame)

    transport = LocalAudioTransport(_LocalAudioParams(audio_in_enabled=True, audio_out_enabled=False))
    stt = DeepgramSTTService(api_key=deepgram_key)
    printer = PrintProcessor()

    pipeline = Pipeline([
        transport.input(),
        stt,
        printer,
        transport.output(),
    ])

    task = PipelineTask(
        pipeline,
        params=PipelineParams(allow_interruptions=True),
    )

    print("🎙️  STT Test - Speak into your microphone (Ctrl+C to stop)")
    print("=" * 50)
    
    runner = PipelineRunner()
    await runner.run(task)


def main():
    parser = argparse.ArgumentParser(description="Simple STT test")
    parser.add_argument("--deepgram-key", default=os.getenv("DEEPGRAM_API_KEY", ""))
    args = parser.parse_args()

    if not args.deepgram_key:
        print("Set DEEPGRAM_API_KEY or pass --deepgram-key")
        sys.exit(1)

    asyncio.run(test_stt(args.deepgram_key))


if __name__ == "__main__":
    main()
