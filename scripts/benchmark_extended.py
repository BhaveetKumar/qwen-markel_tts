#!/usr/bin/env python3
"""
benchmark_extended.py — Extended benchmarks with 100-1000 lines of text.

Generates large text inputs and captures complete responses for audit.

Usage (server must be running):
    python scripts/benchmark_extended.py --url http://localhost:8000 --runs 5

Output:
    - docs/audit/benchmark_audit_<timestamp>.json — Complete audit log with all responses
    - docs/audit/benchmark_summary_<timestamp>.json — Summary statistics
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import json
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path

import aiohttp

_DEFAULT_URL = "http://localhost:8000"

# Lorem ipsum extended text for realistic benchmarking
SAMPLE_TEXT = """
Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. 
Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. 
Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. 
Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.
Sed ut perspiciatis unde omnis iste natus error sit voluptatem accusantium doloremque laudantium, 
totam rem aperiam, eaque ipsa quae ab illo inventore veritatis et quasi architecto beatae vitae dicta sunt explicabo.
Nemo enim ipsam voluptatem quia voluptas sit aspernatur aut odit aut fugit, sed quia consequuntur magni dolores.
Neque porro quisquam est, qui dolorem ipsum quia dolor sit amet, consectetur, adipisci velit, 
sed quia non numquam eius modi tempora incidunt ut labore et dolore magnam aliquam quaerat voluptatem.
""".strip()


def generate_benchmark_text(num_lines: int, max_chars: int = 4096) -> str:
    """Generate text with specified number of lines, capped at max_chars.
    
    Args:
        num_lines: Target number of lines (approximate)
        max_chars: Maximum character limit (API constraint: 4096)
    
    Returns:
        Text up to max_chars, with complete sentences only
    """
    lines_needed = num_lines
    result = []
    line_count = 0
    current_length = 0
    
    while line_count < lines_needed:
        for sentence in SAMPLE_TEXT.split("."):
            if line_count >= lines_needed:
                break
            if sentence.strip():
                sentence_with_period = sentence.strip() + "."
                # Check if adding this sentence would exceed the limit
                test_text = " ".join(result + [sentence_with_period])
                if len(test_text) > max_chars:
                    # Return what we have so far (don't exceed limit)
                    return " ".join(result)
                result.append(sentence_with_period)
                current_length = len(" ".join(result))
                line_count += 1
    
    final_text = " ".join(result[:lines_needed])
    # Ensure we don't exceed max_chars
    if len(final_text) > max_chars:
        final_text = final_text[:max_chars].rsplit(" ", 1)[0]  # Truncate at word boundary
    
    return final_text


async def _run_single(
    session: aiohttp.ClientSession, 
    url: str, 
    text: str, 
    run_id: int,
    text_size_label: str
) -> dict:
    """Run a single benchmark request and capture full response."""
    t_start = time.perf_counter()
    ttfc_ms = None
    total_pcm_bytes = 0
    pcm_chunks = []  # Store PCM chunks for audit
    metrics_from_server = {}
    chunk_count = 0
    error = None

    try:
        async with session.post(f"{url}/tts/stream", json={"text": text}) as resp:
            if resp.status != 200:
                error_detail = await resp.text() if resp.status == 422 else f"HTTP {resp.status}"
                error = f"Server error {resp.status}: {error_detail[:200]}"
                raise RuntimeError(error)

            async for raw_line in resp.content:
                line = raw_line.strip()
                if not line:
                    continue
                msg = json.loads(line)

                if "pcm" in msg:
                    chunk_count += 1
                    if ttfc_ms is None:
                        ttfc_ms = (time.perf_counter() - t_start) * 1000
                    pcm_bytes = len(base64.b64decode(msg["pcm"]))
                    total_pcm_bytes += pcm_bytes
                    # Store chunk metadata for audit (not full PCM data to keep JSON manageable)
                    pcm_chunks.append({
                        "chunk_id": chunk_count,
                        "pcm_bytes": pcm_bytes,
                        "timestamp_ms": (time.perf_counter() - t_start) * 1000
                    })

                if msg.get("event") == "end":
                    metrics_from_server = msg.get("metrics", {})
                    break
    except Exception as e:
        error = str(e)

    elapsed_ms = (time.perf_counter() - t_start) * 1000
    
    return {
        "run_id": run_id,
        "text_size": text_size_label,
        "text_length_chars": len(text),
        "elapsed_ms": elapsed_ms,
        "ttfc_ms": ttfc_ms or 0,
        "total_pcm_bytes": total_pcm_bytes,
        "chunk_count": chunk_count,
        "pcm_chunks_metadata": pcm_chunks,
        "timestamp": datetime.utcnow().isoformat(),
        "error": error,
        **metrics_from_server,
    }


async def main():
    parser = argparse.ArgumentParser(description="Extended benchmark with large text inputs")
    parser.add_argument("--url", default=_DEFAULT_URL, help="Server base URL")
    parser.add_argument("--runs", type=int, default=3, help="Number of runs per text size")
    parser.add_argument("--sizes", default="10,20,50,100", help="Comma-separated line counts to benchmark (each line ~150 chars, 4096 char limit per request)")
    parser.add_argument("--insecure", action="store_true", help="Disable TLS verification")
    parser.add_argument("--audit-dir", default="docs/audit", help="Directory for audit logs")
    args = parser.parse_args()

    # Parse text sizes
    try:
        text_sizes = [int(s.strip()) for s in args.sizes.split(",")]
    except ValueError:
        print("ERROR: --sizes must be comma-separated integers")
        sys.exit(1)

    # Create audit directory
    audit_dir = Path(args.audit_dir)
    audit_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    audit_file = audit_dir / f"benchmark_audit_{timestamp}.json"
    summary_file = audit_dir / f"benchmark_summary_{timestamp}.json"

    print(f"Extended Benchmark Suite")
    print(f"URL: {args.url}")
    print(f"Text sizes: {text_sizes} lines")
    print(f"Runs per size: {args.runs}")
    print(f"Audit output: {audit_file}\n")

    all_results = []
    connector = aiohttp.TCPConnector(ssl=False) if args.insecure else None
    
    async with aiohttp.ClientSession(connector=connector) as session:
        # Health check
        try:
            async with session.get(f"{args.url}/health") as h:
                health = await h.json()
                print(f"Server health: {health.get('status', 'unknown')}")
        except Exception as e:
            print(f"WARNING: Health check failed: {e}")

        # Run benchmarks for each text size
        for text_size in text_sizes:
            print(f"\n=== Benchmarking {text_size} lines ===")
            text = generate_benchmark_text(text_size)
            size_results = []

            for run_idx in range(args.runs):
                try:
                    result = await _run_single(
                        session, 
                        args.url, 
                        text, 
                        run_idx + 1,
                        f"{text_size} lines"
                    )
                    size_results.append(result)
                    all_results.append(result)
                    
                    if result.get("error"):
                        print(
                            f"  Run {run_idx+1:2d}: ERROR — {result['error']}"
                        )
                    else:
                        print(
                            f"  Run {run_idx+1:2d}: "
                            f"elapsed={result['elapsed_ms']:7.1f}ms  "
                            f"TTFC={result['ttfc_ms']:7.1f}ms  "
                            f"RTF={result.get('RTF', 0):7.4f}  "
                            f"tok/s={result.get('decode_tokens_per_sec', 0):8.0f}  "
                            f"chunks={result['chunk_count']}"
                        )
                except Exception as exc:
                    print(f"  Run {run_idx+1:2d}: ERROR — {exc}")

            # Print summary for this size
            if size_results:
                print(f"\n  Summary for {text_size} lines:")
                for key, label in [
                    ("elapsed_ms", "Latency"),
                    ("ttfc_ms", "TTFC"),
                    ("RTF", "RTF"),
                    ("decode_tokens_per_sec", "tok/s"),
                ]:
                    vals = [r.get(key, 0) for r in size_results]
                    print(
                        f"    {label:<12} mean={statistics.mean(vals):8.2f}  "
                        f"min={min(vals):8.2f}  max={max(vals):8.2f}"
                    )

    if not all_results:
        print("No successful runs.")
        return

    # Create audit log with all results
    audit_log = {
        "timestamp": datetime.utcnow().isoformat(),
        "url": args.url,
        "text_sizes": text_sizes,
        "runs_per_size": args.runs,
        "total_runs": len(all_results),
        "results": all_results,
    }

    # Create summary statistics grouped by text size
    summary_by_size = {}
    for size in text_sizes:
        size_results = [r for r in all_results if r["text_size"] == f"{size} lines"]
        if not size_results:
            continue

        summary_by_size[f"{size}_lines"] = {
            "runs": len(size_results),
            "elapsed_ms": {
                "mean": statistics.mean(r.get("elapsed_ms", 0) for r in size_results),
                "min": min(r.get("elapsed_ms", 0) for r in size_results),
                "max": max(r.get("elapsed_ms", 0) for r in size_results),
                "stdev": statistics.stdev(r.get("elapsed_ms", 0) for r in size_results) if len(size_results) > 1 else 0,
            },
            "ttfc_ms": {
                "mean": statistics.mean(r.get("ttfc_ms", 0) for r in size_results),
                "min": min(r.get("ttfc_ms", 0) for r in size_results),
                "max": max(r.get("ttfc_ms", 0) for r in size_results),
                "stdev": statistics.stdev(r.get("ttfc_ms", 0) for r in size_results) if len(size_results) > 1 else 0,
            },
            "RTF": {
                "mean": statistics.mean(r.get("RTF", 0) for r in size_results),
                "min": min(r.get("RTF", 0) for r in size_results),
                "max": max(r.get("RTF", 0) for r in size_results),
                "stdev": statistics.stdev(r.get("RTF", 0) for r in size_results) if len(size_results) > 1 else 0,
            },
            "decode_tokens_per_sec": {
                "mean": statistics.mean(r.get("decode_tokens_per_sec", 0) for r in size_results),
                "min": min(r.get("decode_tokens_per_sec", 0) for r in size_results),
                "max": max(r.get("decode_tokens_per_sec", 0) for r in size_results),
                "stdev": statistics.stdev(r.get("decode_tokens_per_sec", 0) for r in size_results) if len(size_results) > 1 else 0,
            },
            "chunk_count": {
                "mean": statistics.mean(r.get("chunk_count", 0) for r in size_results),
                "min": min(r.get("chunk_count", 0) for r in size_results),
                "max": max(r.get("chunk_count", 0) for r in size_results),
            },
        }

    summary = {
        "timestamp": datetime.utcnow().isoformat(),
        "url": args.url,
        "text_sizes": text_sizes,
        "runs_per_size": args.runs,
        "total_runs": len(all_results),
        "by_size": summary_by_size,
        "performance_targets": {
            "TTFC_ms": {"target": 60, "unit": "ms"},
            "RTF": {"target": 0.15, "unit": "ratio"},
        },
    }

    # Write audit log
    audit_file.write_text(json.dumps(audit_log, indent=2), encoding="utf-8")
    print(f"\n✓ Audit log saved: {audit_file}")

    # Write summary
    summary_file.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"✓ Summary saved: {summary_file}")

    # Print final summary
    print("\n=== OVERALL PERFORMANCE ===")
    for size in text_sizes:
        size_label = f"{size}_lines"
        if size_label not in summary["by_size"]:
            continue
        stats = summary["by_size"][size_label]
        print(f"\n{size} lines:")
        print(f"  TTFC:  {stats['ttfc_ms']['mean']:.1f}ms  (target: <60ms)")
        print(f"  RTF:   {stats['RTF']['mean']:.4f}  (target: <0.15)")
        print(f"  tok/s: {stats['decode_tokens_per_sec']['mean']:.0f}")
        print(f"  Chunks: {stats['chunk_count']['mean']:.0f}")


if __name__ == "__main__":
    asyncio.run(main())
