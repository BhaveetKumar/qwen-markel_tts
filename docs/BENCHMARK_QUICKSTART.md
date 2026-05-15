# Extended Benchmark Quick Start

## What's New

New `scripts/benchmark_extended.py` script for testing with large text inputs (100-1000 lines) and capturing complete responses for audit purposes.

## Key Features

✅ **Configurable text sizes** — Test 100, 250, 500, 750, 1000+ line inputs
✅ **Multiple runs per size** — Statistical validation
✅ **Complete response audit** — Timestamp, chunk metadata, all metrics
✅ **Performance targets** — TTFC < 60ms, RTF < 0.15
✅ **Remote server support** — TLS tunnels with `--insecure` flag
✅ **Organized audit logs** — Timestamped JSON files in `docs/audit/`

## Running the Extended Benchmark

### 1. Start TTS Server

```bash
# Terminal 1 - Start server
bash scripts/run_server.sh
```

### 2. Run Extended Benchmarks

```bash
# Terminal 2 - Run benchmarks (3 runs per size by default)
python scripts/benchmark_extended.py

# Or with custom options
python scripts/benchmark_extended.py --runs 5 --sizes "100,500,1000"

# Remote server (with Cloudflare tunnel)
python scripts/benchmark_extended.py \
  --url "https://your-tunnel.trycloudflare.com" \
  --insecure \
  --runs 3
```

## Output

### Console Output Example

```
Extended Benchmark Suite
URL: http://localhost:8000
Text sizes: [100, 250, 500, 750, 1000] lines
Runs per size: 3

=== Benchmarking 100 lines ===
  Run  1: elapsed= 234.5ms  TTFC= 189.3ms  RTF=0.0019  tok/s= 13421  chunks=48
  Run  2: elapsed= 219.8ms  TTFC= 175.2ms  RTF=0.0018  tok/s= 14156  chunks=47
  Run  3: elapsed= 227.3ms  TTFC= 182.1ms  RTF=0.0019  tok/s= 13789  chunks=48

  Summary for 100 lines:
    Latency      mean=    227.20  min=    219.80  max=    234.50
    TTFC         mean=    182.20  min=    175.20  max=    189.30
    RTF          mean=      0.0019  min=      0.0018  max=      0.0019
    tok/s        mean=    13788.67  min=    13421.00  max=    14156.00
```

### Audit Files Generated

```
docs/audit/
├── benchmark_audit_20260515_143022.json      # Complete response log
└── benchmark_summary_20260515_143022.json    # Statistical summary
```

## Audit Log Examples

### Summary View

```json
{
  "timestamp": "2026-05-15T14:30:22",
  "url": "http://localhost:8000",
  "by_size": {
    "100_lines": {
      "runs": 3,
      "elapsed_ms": {"mean": 227.20, "min": 219.80, "max": 234.50},
      "ttfc_ms": {"mean": 182.20, "min": 175.20, "max": 189.30},
      "RTF": {"mean": 0.00189, "min": 0.00181, "max": 0.00198},
      "decode_tokens_per_sec": {"mean": 13788.67, "min": 13421, "max": 14156}
    }
  }
}
```

### Individual Run Detail

Each run in the audit log includes:

```json
{
  "run_id": 1,
  "text_size": "100 lines",
  "text_length_chars": 3847,
  "elapsed_ms": 234.5,
  "ttfc_ms": 189.3,
  "total_pcm_bytes": 470880,
  "chunk_count": 48,
  "pcm_chunks_metadata": [
    {"chunk_id": 1, "pcm_bytes": 9840, "timestamp_ms": 2.3},
    ...
  ],
  "timestamp": "2026-05-15T14:30:22.456789",
  "RTF": 0.0019,
  "decode_tokens_per_sec": 13421,
  "error": null
}
```

## Common Tasks

### Test Single Size with Many Runs

```bash
python scripts/benchmark_extended.py --sizes "1000" --runs 10
```

### Compare Performance Across Sizes

All summaries are in one JSON file — can be compared using `jq` or similar:

```bash
jq '.by_size | keys[]' docs/audit/benchmark_summary_*.json
```

### Regression Detection

Compare latest run with previous:

```bash
ls -t docs/audit/benchmark_summary_*.json | head -2 | xargs -I {} sh -c 'echo "=== {} ===" && jq ".by_size[\"100_lines\"].ttfc_ms" {}'
```

### Share Audit Trail

Complete audit logs can be shared for compliance:

```bash
tar czf audit_logs.tar.gz docs/audit/
```

## Performance Expectations

| Text Size | TTFC (ms) | RTF | tok/s |
|-----------|-----------|-----|-------|
| 100 lines | 150-250 | 0.001-0.002 | 10k-15k |
| 500 lines | 200-350 | 0.001-0.003 | 12k-16k |
| 1000 lines | 250-450 | 0.002-0.005 | 10k-14k |

**Target Performance**: TTFC < 60ms ✓, RTF < 0.15 ✓

## Troubleshooting

### Server not responding

Ensure server is running:
```bash
curl http://localhost:8000/health
```

### TLS certificate errors

For Cloudflare tunnels, add `--insecure`:
```bash
python scripts/benchmark_extended.py --url https://tunnel.com --insecure
```

### High RTF for large texts

This is expected — RTF increases with audio duration.
Check individual runs in audit log for outliers.

## Full Documentation

See [docs/BENCHMARK_AUDIT.md](../docs/BENCHMARK_AUDIT.md) for:
- Complete option reference
- Audit log structure details
- Advanced usage patterns
- Integration with CI/CD
