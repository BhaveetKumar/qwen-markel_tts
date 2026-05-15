#!/usr/bin/env python3
"""
Generate sample audio files for demonstration.

Creates a set of sample audio outputs with different input texts
to showcase the system's capabilities.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import aiohttp

# Sample texts covering various speech patterns
SAMPLES = [
    "Hello, welcome to the Qwen speech synthesis system.",
    "The quick brown fox jumps over the lazy dog.",
    "Machine learning and artificial intelligence are transforming the world.",
    "This is a streaming audio sample generated in real time.",
    "Thank you for listening to this demonstration.",
]


async def generate_samples(
    url: str = "http://localhost:8000",
    output_dir: str = "audio_samples",
) -> None:
    """Generate sample audio files."""
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    print(f"📁 Output directory: {output_path.absolute()}")
    print(f"🎤 Generating {len(SAMPLES)} sample audio files...\n")
    
    import base64
    import wave
    
    for i, text in enumerate(SAMPLES, 1):
        print(f"[{i}/{len(SAMPLES)}] {text[:50]}...", end="", flush=True)
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{url}/tts/stream",
                    json={"text": text},
                ) as resp:
                    if resp.status != 200:
                        print(f" ✗ Server error {resp.status}")
                        continue
                    
                    pcm_data = b""
                    async for line in resp.content:
                        if not line.strip():
                            continue
                        msg = json.loads(line)
                        if "pcm" in msg:
                            pcm_data += base64.b64decode(msg["pcm"])
                    
                    # Save as WAV
                    filename = f"sample_{i:02d}.wav"
                    filepath = output_path / filename
                    
                    with wave.open(str(filepath), "wb") as wf:
                        wf.setnchannels(1)
                        wf.setsampwidth(2)
                        wf.setframerate(24000)
                        wf.writeframes(pcm_data)
                    
                    size_kb = len(pcm_data) / 1024
                    duration_s = len(pcm_data) / (2 * 24000)  # 2 bytes per sample
                    print(f" ✓ {size_kb:.1f} KB ({duration_s:.2f}s)")
                    
        except Exception as e:
            print(f" ✗ {e}")
    
    print(f"\n✓ Samples saved to {output_path.absolute()}")
    print(f"\nYou can now listen to the samples:")
    print(f"  ffplay {output_path}/sample_01.wav")
    print(f"  aplay {output_path}/sample_01.wav")


async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate sample audio files")
    parser.add_argument(
        "--url", default="http://localhost:8000", help="Server URL"
    )
    parser.add_argument(
        "--output", "-o", default="audio_samples", help="Output directory"
    )
    
    args = parser.parse_args()
    
    # Check server health
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{args.url}/health", timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status != 200:
                    print(f"❌ Server at {args.url} returned {resp.status}")
                    return 1
    except Exception as e:
        print(f"❌ Cannot connect to server at {args.url}: {e}")
        print("\nStart the server with: bash scripts/run_server.sh")
        return 1
    
    await generate_samples(args.url, args.output)
    return 0


if __name__ == "__main__":
    import sys
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
