#!/usr/bin/env python3
"""
CLI tool for TTS synthesis.

Usage:
    python scripts/cli.py "Your text here"
    python scripts/cli.py --text "Hello world" --output /tmp/out.wav --runs 5
    python scripts/cli.py --interactive
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import json
import sys
import wave
from pathlib import Path

import aiohttp


async def synthesize(
    text: str,
    url: str = "http://localhost:8000",
    output_file: str | None = None,
    temperature: float = 0.7,
    voice: str = "default",
) -> bytes:
    """Synthesize text to speech and return PCM bytes."""
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{url}/tts/stream",
            json={"text": text, "voice": voice, "temperature": temperature},
        ) as resp:
            if resp.status != 200:
                raise RuntimeError(f"Server returned {resp.status}: {await resp.text()}")

            pcm_data = b""
            async for line in resp.content:
                if not line.strip():
                    continue
                msg = json.loads(line)
                if "pcm" in msg:
                    pcm_data += base64.b64decode(msg["pcm"])

    # Save to file if requested
    if output_file:
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with wave.open(str(output_path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(24000)
            wf.writeframes(pcm_data)
        
        print(f"✓ Saved to {output_path}")

    return pcm_data


async def interactive_mode(url: str):
    """Interactive synthesis mode."""
    print("TTS Interactive Mode (type 'quit' to exit)")
    print("─" * 50)
    
    while True:
        try:
            text = input("\n📝 Enter text: ").strip()
            if text.lower() in ("quit", "exit", "q"):
                break
            if not text:
                continue
            
            print("⏳ Synthesizing...", end="", flush=True)
            pcm_data = await synthesize(text, url=url)
            print(f" ✓ Generated {len(pcm_data)} bytes")
            
            # Save with timestamp
            import time
            timestamp = int(time.time())
            output = f"/tmp/tts_{timestamp}.wav"
            await synthesize(text, url=url, output_file=output)
            
        except KeyboardInterrupt:
            print("\n\nExiting...")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")


async def main():
    parser = argparse.ArgumentParser(
        description="Qwen3-TTS CLI tool for text-to-speech synthesis"
    )
    parser.add_argument("text", nargs="?", help="Text to synthesize")
    parser.add_argument(
        "--output", "-o", help="Output WAV file path (default: stdout)"
    )
    parser.add_argument(
        "--url", "-u", default="http://localhost:8000", help="Server URL"
    )
    parser.add_argument(
        "--temperature", "-t", type=float, default=0.7, help="Sampling temperature"
    )
    parser.add_argument(
        "--voice", "-v", default="default", help="Voice profile"
    )
    parser.add_argument(
        "--interactive", "-i", action="store_true", help="Interactive mode"
    )
    parser.add_argument(
        "--runs", "-r", type=int, default=1, help="Number of synthesis runs"
    )
    parser.add_argument(
        "--check-health", action="store_true", help="Check server health and exit"
    )

    args = parser.parse_args()

    # Check health
    if args.check_health:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{args.url}/health") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        print(f"✓ Server healthy: {data}")
                        return 0
                    else:
                        print(f"✗ Server returned {resp.status}")
                        return 1
        except Exception as e:
            print(f"✗ Server unreachable: {e}")
            return 1

    # Interactive mode
    if args.interactive:
        await interactive_mode(args.url)
        return 0

    # Text synthesis
    if not args.text:
        parser.print_help()
        return 1

    try:
        for run in range(args.runs):
            if args.runs > 1:
                print(f"[Run {run + 1}/{args.runs}] ", end="")
            
            output_path = None
            if args.output:
                if args.runs > 1:
                    # Add run number to filename
                    p = Path(args.output)
                    output_path = str(p.parent / f"{p.stem}_{run+1:02d}{p.suffix}")
                else:
                    output_path = args.output
            
            await synthesize(
                args.text,
                url=args.url,
                output_file=output_path,
                temperature=args.temperature,
                voice=args.voice,
            )
        
        return 0

    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
