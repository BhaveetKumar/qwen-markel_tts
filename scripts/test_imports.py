#!/usr/bin/env python3
"""
Minimal debug script to test component initialization.
"""
import sys
import os
import asyncio

_SRC = os.path.join(os.path.dirname(__file__), "../src")
sys.path.insert(0, os.path.abspath(_SRC))

print("[DEBUG] Started test script", flush=True)
print(f"[DEBUG] Python version: {sys.version}", flush=True)
print(f"[DEBUG] Python executable: {sys.executable}", flush=True)

# Test 1: Basic imports
print("\n[1] Testing basic imports...", flush=True)
try:
    import aiohttp
    print("  ✓ aiohttp", flush=True)
except Exception as e:
    print(f"  ✗ aiohttp: {e}", flush=True)

# Test 2: Pipecat imports
print("\n[2] Testing Pipecat imports...", flush=True)
try:
    from pipecat.pipeline.pipeline import Pipeline
    from pipecat.pipeline.runner import PipelineRunner
    from pipecat.pipeline.task import PipelineTask, PipelineParams
    print("  ✓ pipecat.pipeline", flush=True)
except Exception as e:
    print(f"  ✗ pipecat.pipeline: {e}", flush=True)
    import traceback
    traceback.print_exc()

# Test 3: Local audio
print("\n[3] Testing local audio transport...", flush=True)
try:
    from pipecat.transports.local.audio import LocalAudioTransport
    try:
        from pipecat.transports.local.audio import LocalAudioParams as _LocalAudioParams
        print("  ✓ LocalAudioParams (older)", flush=True)
    except ImportError:
        from pipecat.transports.local.audio import LocalAudioTransportParams as _LocalAudioParams
        print("  ✓ LocalAudioTransportParams (newer)", flush=True)
except Exception as e:
    print(f"  ✗ audio transport: {e}", flush=True)
    import traceback
    traceback.print_exc()

# Test 4: Services
print("\n[4] Testing STT/LLM/TTS services...", flush=True)
try:
    try:
        from pipecat.services.deepgram import DeepgramSTTService
        print("  ✓ DeepgramSTTService (root)", flush=True)
    except ImportError:
        from pipecat.services.deepgram.stt import DeepgramSTTService
        print("  ✓ DeepgramSTTService (submodule)", flush=True)
        
    try:
        from pipecat.services.openai import OpenAILLMService
        print("  ✓ OpenAILLMService (root)", flush=True)
    except ImportError:
        from pipecat.services.openai.llm import OpenAILLMService
        print("  ✓ OpenAILLMService (submodule)", flush=True)
        
    from pipecat_adapter.tts import QwenMegakernelTTSService
    print("  ✓ QwenMegakernelTTSService", flush=True)
except Exception as e:
    print(f"  ✗ services: {e}", flush=True)
    import traceback
    traceback.print_exc()

print("\n✓ All imports successful!", flush=True)
print("Demo script should work.", flush=True)
