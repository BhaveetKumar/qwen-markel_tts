#!/bin/bash
# Wrapper to run demo.py with system Python instead of broken venv

cd "$(dirname "$0")/.."

export PYTHONPATH="/Users/fc20136/Desktop/poc/qwen-markel_tts/src:$PYTHONPATH"

echo "🎙️  Using system Python 3.11 for voice pipeline demo"
echo "======================================================="

python3 -u - "$@" << 'PYTHON_EOF'
import sys
import os
import argparse
import asyncio

# Setup path
_SRC = os.path.join(os.path.dirname(__file__), "src")
sys.path.insert(0, os.path.abspath(_SRC))

async def run_demo(tts_url: str, deepgram_key: str, openai_key: str):
    print("[1/5] Importing core dependencies...")
    try:
        import aiohttp
        from pipecat.pipeline.pipeline import Pipeline
        from pipecat.pipeline.runner import PipelineRunner
        from pipecat.pipeline.task import PipelineParams, PipelineTask
        print("  ✓ Core dependencies loaded")
    except ImportError as e:
        print(f"  ✗ Missing dependency: {e}")
        return

    print("[2/5] Importing audio transport...")
    try:
        from pipecat.transports.local.audio import LocalAudioTransport
        try:
            from pipecat.transports.local.audio import LocalAudioParams as _LocalAudioParams
            print("  ✓ Using LocalAudioParams")
        except ImportError:
            from pipecat.transports.local.audio import LocalAudioTransportParams as _LocalAudioParams
            print("  ✓ Using LocalAudioTransportParams")
    except Exception as e:
        print(f"  ✗ Missing local audio: {e}")
        return

    print("[3/5] Importing STT/LLM/TTS services...")
    try:
        try:
            from pipecat.services.deepgram import DeepgramSTTService
        except ImportError:
            from pipecat.services.deepgram.stt import DeepgramSTTService

        try:
            from pipecat.services.openai import OpenAILLMService
        except ImportError:
            from pipecat.services.openai.llm import OpenAILLMService

        from pipecat_adapter.tts import QwenMegakernelTTSService
        print("  ✓ All services imported")
    except Exception as e:
        print(f"  ✗ Service import error: {e}")
        return

    print(f"[4/5] Initializing services (TTS: {tts_url})...")
    try:
        async with aiohttp.ClientSession() as session:
            tts = QwenMegakernelTTSService(
                base_url=tts_url,
                aiohttp_session=session,
                sample_rate=16000,
            )
            print("  ✓ TTS service created")
            
            if not await tts.is_healthy():
                print(f"  ✗ TTS server at {tts_url} is not responding")
                return
            print("  ✓ TTS server is healthy")

            stt = DeepgramSTTService(api_key=deepgram_key)
            print("  ✓ STT service created")
            
            llm = OpenAILLMService(
                api_key=openai_key, 
                settings=OpenAILLMService.Settings(model="gpt-4o-mini")
            )
            print("  ✓ LLM service created")
            
            transport = LocalAudioTransport(_LocalAudioParams(audio_in_enabled=True, audio_out_enabled=True))
            print("  ✓ Audio transport created")

            print("[5/5] Building pipeline...")
            pipeline = Pipeline([
                transport.input(),
                stt,
                llm,
                tts,
                transport.output(),
            ])
            print("  ✓ Pipeline assembled")

            task = PipelineTask(
                pipeline,
                params=PipelineParams(allow_interruptions=True),
            )
            print("  ✓ Pipeline task created")

            print("\n" + "="*60)
            print("✓ Voice agent ready!")
            print("="*60)
            print("Speak into your microphone (Ctrl+C to stop)")
            print("You should see transcriptions, responses, and hear TTS output")
            print("="*60 + "\n")
            
            runner = PipelineRunner()
            await runner.run(task)
    except Exception as e:
        print(f"  ✗ Error during initialization: {e}")
        import traceback
        traceback.print_exc()
        return

def main():
    parser = argparse.ArgumentParser(description="Qwen3-TTS Pipecat voice demo")
    parser.add_argument("--tts-url", default="http://localhost:8000")
    parser.add_argument("--deepgram-key", default=os.getenv("DEEPGRAM_API_KEY", ""))
    parser.add_argument("--openai-key", default=os.getenv("OPENAI_API_KEY", ""))
    args = parser.parse_args()

    if not args.deepgram_key:
        print("✗ Set DEEPGRAM_API_KEY or pass --deepgram-key")
        sys.exit(1)
    if not args.openai_key:
        print("✗ Set OPENAI_API_KEY or pass --openai-key")
        sys.exit(1)

    print(f"• TTS server: {args.tts_url}")
    print(f"• Deepgram API key: {'***' + args.deepgram_key[-4:]}")
    print(f"• OpenAI API key: {'***' + args.openai_key[-4:]}")
    print()

    try:
        asyncio.run(run_demo(args.tts_url, args.deepgram_key, args.openai_key))
    except KeyboardInterrupt:
        print("\n✓ Pipeline stopped by user")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
PYTHON_EOF
