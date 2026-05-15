#!/usr/bin/env python3
"""
benchmark.py — measure decode tok/s, TTFC, and RTF.

Usage (server must be running):
    python scripts/benchmark.py --text "The quick brown fox jumps over the lazy dog." --runs 5
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import json
import statistics
import sys
import time
from pathlib import Path

import aiohttp

_DEFAULT_URL = "http://localhost:8000"


async def _run_single(session: aiohttp.ClientSession, url: str, text: str, run_id: int) -> dict:
    t_start = time.perf_counter()
    ttfc_ms = None
    total_pcm_bytes = 0
    metrics_from_server = {}

    async with session.post(f"{url}/tts/stream", json={"text": text}) as resp:
        if resp.status != 200:
            raise RuntimeError(f"Server returned {resp.status}")

        async for raw_line in resp.content:
            line = raw_line.strip()
            if not line:
                continue
            msg = json.loads(line)

            if "pcm" in msg:
                if ttfc_ms is None:
                    ttfc_ms = (time.perf_counter() - t_start) * 1000
                total_pcm_bytes += len(base64.b64decode(msg["pcm"]))

            if msg.get("event") == "end":
                metrics_from_server = msg.get("metrics", {})
                break

    elapsed_ms = (time.perf_counter() - t_start) * 1000
    return {
        "run_id": run_id,
        "text": text,
        "elapsed_ms": elapsed_ms,
        "ttfc_ms": ttfc_ms or 0,
        "total_pcm_bytes": total_pcm_bytes,
        **metrics_from_server,
    }


async def main():
    parser = argparse.ArgumentParser(description="Benchmark qwen-markel-tts server")
    parser.add_argument("--url", default=_DEFAULT_URL, help="Server base URL")
    parser.add_argument("--text", default="Hello, this is a benchmark test sentence.", help="Text to synthesize")
    parser.add_argument("--runs", type=int, default=5, help="Number of benchmark runs")
    parser.add_argument("--insecure", action="store_true", help="Disable TLS verification (for temporary tunnel endpoints)")
    parser.add_argument("--json-out", default="", help="Optional path to write JSON logs and summary")
    args = parser.parse_args()

    print(f"Benchmarking: {args.url}")
    print(f"Text: {args.text!r}")
    print(f"Runs: {args.runs}\n")

    results = []
    connector = aiohttp.TCPConnector(ssl=False) if args.insecure else None
    async with aiohttp.ClientSession(connector=connector) as session:
        # Check health first
        async with session.get(f"{args.url}/health") as h:
            status = (await h.json()).get("model_loaded", False)
            if not status:
                print("WARNING: Server reports model_loaded=False. Metrics may be zero.")

        for i in range(args.runs):
            try:
                r = await _run_single(session, args.url, args.text, i + 1)
                results.append(r)
                print(
                    f"  Run {i+1:2d}: elapsed={r['elapsed_ms']:.1f}ms  "
                    f"TTFC={r['ttfc_ms']:.1f}ms  "
                    f"RTF={r.get('RTF', 0):.3f}  "
                    f"tok/s={r.get('decode_tokens_per_sec', 0):.0f}"
                )
            except Exception as exc:
                print(f"  Run {i+1:2d}: ERROR — {exc}")

    if not results:
        print("No successful runs.")
        return

    print("\n=== Summary ===")
    for key, label in [
        ("elapsed_ms", "Latency (ms)"),
        ("ttfc_ms", "TTFC (ms)"),
        ("RTF", "RTF"),
        ("decode_tokens_per_sec", "tok/s"),
    ]:
        vals = [r.get(key, 0) for r in results]
        print(
            f"  {label:<20} mean={statistics.mean(vals):.2f}  "
            f"min={min(vals):.2f}  max={max(vals):.2f}"
        )

    print("\nTargets:")
    mean_ttfc = statistics.mean(r.get("ttfc_ms", 0) for r in results)
    mean_rtf = statistics.mean(r.get("RTF", 0) for r in results)
    print(f"  TTFC < 60 ms  → {'PASS' if mean_ttfc < 60 else 'FAIL'} ({mean_ttfc:.1f}ms)")
    print(f"  RTF  < 0.15   → {'PASS' if mean_rtf < 0.15 else 'FAIL'} ({mean_rtf:.3f})")

    if args.json_out:
        summary = {
            "runs": len(results),
            "elapsed_ms": {
                "mean": statistics.mean(r.get("elapsed_ms", 0.0) for r in results),
                "min": min(r.get("elapsed_ms", 0.0) for r in results),
                "max": max(r.get("elapsed_ms", 0.0) for r in results),
            },
            "ttfc_ms": {
                "mean": statistics.mean(r.get("ttfc_ms", 0.0) for r in results),
                "min": min(r.get("ttfc_ms", 0.0) for r in results),
                "max": max(r.get("ttfc_ms", 0.0) for r in results),
            },
            "RTF": {
                "mean": statistics.mean(r.get("RTF", 0.0) for r in results),
                "min": min(r.get("RTF", 0.0) for r in results),
                "max": max(r.get("RTF", 0.0) for r in results),
            },
            "decode_tokens_per_sec": {
                "mean": statistics.mean(r.get("decode_tokens_per_sec", 0.0) for r in results),
                "min": min(r.get("decode_tokens_per_sec", 0.0) for r in results),
                "max": max(r.get("decode_tokens_per_sec", 0.0) for r in results),
            },
        }
        payload = {
            "url": args.url,
            "text": args.text,
            "insecure": args.insecure,
            "summary": summary,
            "results": results,
        }
        Path(args.json_out).write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"\nSaved JSON log: {args.json_out}")


if __name__ == "__main__":
    asyncio.run(main())
