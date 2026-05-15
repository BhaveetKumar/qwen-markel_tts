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
import os
import ssl
import sys

_SRC = os.path.join(os.path.dirname(__file__), "../src")
sys.path.insert(0, os.path.abspath(_SRC))


def configure_ssl():
    """Configure SSL certificate handling for HTTPS connections."""
    try:
        import certifi
        
        # Set environment variables for SSL certificate verification
        os.environ.setdefault("SSL_CERT_FILE", certifi.where())
        os.environ.setdefault("REQUESTS_CA_BUNDLE", certifi.where())
        os.environ.setdefault("CURL_CA_BUNDLE", certifi.where())
        
        # Create SSL context
        ssl_context = ssl.create_default_context()
        ssl_context.load_verify_locations(certifi.where())
        
        print(f"  • SSL certificates configured: {certifi.where()}", flush=True)
        return ssl_context
    except Exception as e:
        print(f"  ⚠ Warning: Could not configure SSL: {e}", flush=True)
        return None


async def run_demo(tts_url: str, deepgram_key: str, openai_key: str):
    print("[0/5] Configuring SSL certificates...", flush=True)
    ssl_context = configure_ssl()
    
    print("[1/5] Importing core dependencies...", flush=True)
    try:
        print("  - aiohttp...", flush=True)
        import aiohttp
        print("  - Pipeline...", flush=True)
        from pipecat.pipeline.pipeline import Pipeline
        print("  - PipelineRunner...", flush=True)
        from pipecat.pipeline.runner import PipelineRunner
        print("  - PipelineTask...", flush=True)
        from pipecat.pipeline.task import PipelineParams, PipelineTask
        print("  ✓ Core dependencies loaded", flush=True)
    except ImportError as e:
        print(f"  ✗ Missing dependency: {e}", flush=True)
        print("Install with: pip install pipecat-ai[deepgram,openai]")
        return

    print("[2/5] Importing audio transport...")
    try:
        from pipecat.transports.local.audio import LocalAudioTransport
        try:
            from pipecat.transports.local.audio import LocalAudioParams as _LocalAudioParams
            print("  ✓ Using LocalAudioParams (older Pipecat)")
        except ImportError:
            from pipecat.transports.local.audio import (
                LocalAudioTransportParams as _LocalAudioParams,
            )
            print("  ✓ Using LocalAudioTransportParams (newer Pipecat)")
    except Exception as e:
        print(f"  ✗ Missing local audio dependency: {e}")
        print("To run microphone/speaker demo on macOS:")
        print("  1) brew install portaudio")
        print("  2) python3 -m pip install pyaudio")
        print("  3) python3 -m pip install 'pipecat-ai[local,deepgram,openai]'")
        print("Then re-run scripts/demo.py")
        return

    print("[3/5] Importing STT/LLM/TTS services...")
    # Support both older and newer Pipecat import layouts.
    try:
        from pipecat.services.deepgram import DeepgramSTTService
        print("  ✓ DeepgramSTTService (root import)")
    except ImportError:
        from pipecat.services.deepgram.stt import DeepgramSTTService
        print("  ✓ DeepgramSTTService (submodule import)")

    try:
        from pipecat.services.openai import OpenAILLMService
        print("  ✓ OpenAILLMService (root import)")
    except ImportError:
        from pipecat.services.openai.llm import OpenAILLMService
        print("  ✓ OpenAILLMService (submodule import)")

    from pipecat_adapter.tts import QwenMegakernelTTSService
    print("  ✓ QwenMegakernelTTSService imported")

    print(f"[4/5] Initializing services (TTS: {tts_url})...")
    
    # Create aiohttp session with SSL context if available
    if ssl_context:
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        session_ctx = aiohttp.ClientSession(connector=connector)
    else:
        session_ctx = aiohttp.ClientSession()
    
    async with session_ctx as session:
        tts = QwenMegakernelTTSService(
            base_url=tts_url,
            aiohttp_session=session,
            sample_rate=16000,
        )
        print("  ✓ TTS service created")
        
        print("  • Checking TTS server health...")
        try:
            if await tts.is_healthy():
                print("  ✓ TTS server is healthy", flush=True)
            else:
                print("  ⚠ TTS server health check returned false, proceeding anyway...", flush=True)
        except Exception as e:
            print(f"  ⚠ TTS server unreachable ({e}), proceeding anyway - will retry on first request", flush=True)

        print("  • Creating STT service (Deepgram)...")
        stt = DeepgramSTTService(api_key=deepgram_key)
        print("  ✓ STT service created")
        
        print("  • Creating LLM service (OpenAI gpt-4o-mini)...")
        llm = OpenAILLMService(
            api_key=openai_key, 
            settings=OpenAILLMService.Settings(model="gpt-4o-mini")
        )
        print("  ✓ LLM service created")
        
        print("  • Creating audio transport (local microphone/speaker)...")
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


def main():
    print("🎙️  Qwen3-TTS Pipecat Voice Pipeline Demo")
    print("="*60)
    

    parser = argparse.ArgumentParser(description="Qwen3-TTS Pipecat voice demo")
    parser.add_argument("--tts-url", default="http://localhost:8000")
    parser.add_argument("--host", default=None)  # ignored, for compatibility
    parser.add_argument("--port", default=None)  # ignored, for compatibility
    args = parser.parse_args()

    # Only load secrets from .env, never from CLI or shell env
    tts_url = args.tts_url
    deepgram_key = os.environ.get("DEEPGRAM_API_KEY", "")
    openai_key = os.environ.get("OPENAI_API_KEY", "")

    if not deepgram_key:
        print("✗ Missing DEEPGRAM_API_KEY in .env", file=sys.stderr)
        sys.exit(1)
    if not openai_key:
        print("✗ Missing OPENAI_API_KEY in .env", file=sys.stderr)
        sys.exit(1)

    print(f"• TTS server: {tts_url}")
    print(f"• Deepgram API key: {'***' + deepgram_key[-4:]}")
    print(f"• OpenAI API key: {'***' + openai_key[-4:]}")
    print()

    try:
        asyncio.run(run_demo(tts_url, deepgram_key, openai_key))
    except KeyboardInterrupt:
        print("\n✓ Pipeline stopped by user")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
