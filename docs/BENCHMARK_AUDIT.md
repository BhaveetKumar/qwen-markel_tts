# Extended Benchmark & Audit Guide

## Overview

The extended benchmark suite (`scripts/benchmark_extended.py`) tests the TTS system with progressively larger text inputs (100-1000 lines) and captures complete responses for audit purposes.

## Purpose

- **Load Testing**: Verify performance with realistic long-form text
- **Consistency Monitoring**: Track metrics across different input sizes
- **Compliance Auditing**: Record all requests and responses with timestamps
- **Regression Detection**: Compare runs over time to detect performance degradation

## Running Extended Benchmarks

### Basic Usage

```bash
# Single server (localhost:8000)
python scripts/benchmark_extended.py

# Remote/tunnel server
python scripts/benchmark_extended.py --url "https://your-cloudflare-tunnel.com" --insecure

# Custom sizes and runs
python scripts/benchmark_extended.py --sizes "50,100,500,1000" --runs 5
```

### Options

| Option | Default | Description |
|--------|---------|-------------|
| `--url` | `http://localhost:8000` | Server base URL |
| `--runs` | `3` | Number of runs per text size |
| `--sizes` | `100,250,500,750,1000` | Comma-separated line counts |
| `--insecure` | - | Disable TLS verification (for tunnels) |
| `--audit-dir` | `docs/audit` | Directory for audit logs |

### Example Output

```
Extended Benchmark Suite
URL: http://localhost:8000
Text sizes: [100, 250, 500, 750, 1000] lines
Runs per size: 3
Audit output: docs/audit/benchmark_audit_20260515_143022.json

Server health: healthy

=== Benchmarking 100 lines ===
  Run  1: elapsed= 234.5ms  TTFC= 189.3ms  RTF=0.0019  tok/s= 13421  chunks=48
  Run  2: elapsed= 219.8ms  TTFC= 175.2ms  RTF=0.0018  tok/s= 14156  chunks=47
  Run  3: elapsed= 227.3ms  TTFC= 182.1ms  RTF=0.0019  tok/s= 13789  chunks=48

  Summary for 100 lines:
    Latency      mean=    227.20  min=    219.80  max=    234.50
    TTFC         mean=    182.20  min=    175.20  max=    189.30
    RTF          mean=      0.0019  min=      0.0018  max=      0.0019
    tok/s        mean=    13788.67  min=    13421.00  max=    14156.00

...
```

## Audit Log Structure

### `benchmark_audit_<timestamp>.json`

Complete audit log with all individual run details:

```json
{
  "timestamp": "2026-05-15T14:30:22.123456",
  "url": "http://localhost:8000",
  "text_sizes": [100, 250, 500, 750, 1000],
  "runs_per_size": 3,
  "total_runs": 15,
  "results": [
    {
      "run_id": 1,
      "text_size": "100 lines",
      "text_length_chars": 3847,
      "elapsed_ms": 234.5,
      "ttfc_ms": 189.3,
      "total_pcm_bytes": 470880,
      "chunk_count": 48,
      "pcm_chunks_metadata": [
        {
          "chunk_id": 1,
          "pcm_bytes": 9840,
          "timestamp_ms": 2.3
        },
        ...
      ],
      "timestamp": "2026-05-15T14:30:22.456789",
      "RTF": 0.0019,
      "decode_tokens_per_sec": 13421,
      "error": null
    },
    ...
  ]
}
```

### `benchmark_summary_<timestamp>.json`

Statistical summary grouped by text size:

```json
{
  "timestamp": "2026-05-15T14:30:22.123456",
  "url": "http://localhost:8000",
  "text_sizes": [100, 250, 500, 750, 1000],
  "by_size": {
    "100_lines": {
      "runs": 3,
      "elapsed_ms": {
        "mean": 227.20,
        "min": 219.80,
        "max": 234.50,
        "stdev": 7.15
      },
      "ttfc_ms": {
        "mean": 182.20,
        "min": 175.20,
        "max": 189.30,
        "stdev": 6.82
      },
      "RTF": {
        "mean": 0.00189,
        "min": 0.00181,
        "max": 0.00198,
        "stdev": 0.00008
      },
      "decode_tokens_per_sec": {
        "mean": 13788.67,
        "min": 13421.00,
        "max": 14156.00,
        "stdev": 321.45
      },
      "chunk_count": {
        "mean": 47.67,
        "min": 47,
        "max": 48
      }
    },
    ...
  },
  "performance_targets": {
    "TTFC_ms": {"target": 60, "unit": "ms"},
    "RTF": {"target": 0.15, "unit": "ratio"}
  }
}
```

## Key Metrics

### TTFC (Time-To-First-Chunk)
- **Measure**: Milliseconds until first PCM audio is returned
- **Target**: < 60 ms
- **Importance**: Affects user experience (how quickly they hear response)

### RTF (Real-Time Factor)
- **Measure**: Synthesis time / Audio duration
- **Target**: < 0.15
- **Importance**: Must be much faster than playback for streaming

### Decode Speed
- **Measure**: Tokens per second
- **Importance**: Throughput indicator

### Chunk Count
- **Measure**: Number of PCM chunks returned
- **Importance**: Indicates streaming granularity

## Interpreting Results

### Expected Performance by Text Size

| Size | Expected TTFC (ms) | Expected RTF | Expected tok/s |
|------|-------------------|--------------|----------------|
| 100 lines | 150-250 | 0.001-0.002 | 10k-15k |
| 250 lines | 180-300 | 0.001-0.003 | 12k-16k |
| 500 lines | 200-350 | 0.001-0.003 | 12k-16k |
| 750 lines | 220-400 | 0.002-0.004 | 11k-15k |
| 1000 lines | 250-450 | 0.002-0.005 | 10k-14k |

### Regression Detection

Compare summaries across runs:

```bash
# Run new benchmark
python scripts/benchmark_extended.py --audit-dir docs/audit

# Compare with previous (in JSON viewer or custom script)
cat docs/audit/benchmark_summary_20260515_143022.json
cat docs/audit/benchmark_summary_20260515_140000.json  # previous run
```

If new TTFC or RTF exceeds target, investigate:
1. Server resource contention
2. Network latency
3. Model/codec changes
4. System configuration changes

## Audit Compliance

The audit logs provide:

✅ **Traceability**: Timestamp, URL, input text length
✅ **Reproducibility**: Input size, run count, server state
✅ **Completeness**: All requests and response metrics
✅ **Integrity**: Chunked response capture with metadata
✅ **Performance**: Detailed latency and throughput metrics

## Advanced Usage

### Save with custom audit directory

```bash
python scripts/benchmark_extended.py --audit-dir /path/to/compliance/logs
```

### Test specific sizes

```bash
# Only test 1000-line requests
python scripts/benchmark_extended.py --sizes "1000" --runs 10
```

### Remote server with TLS tunnel

```bash
python scripts/benchmark_extended.py \
  --url "https://cloudflare-tunnel-domain.com" \
  --insecure \
  --runs 5
```

## Integration

The audit logs can be integrated into:
- **CI/CD pipelines**: Automatic regression detection
- **Compliance reports**: Audit trails and performance evidence
- **Dashboards**: Real-time performance monitoring
- **Alerting**: Threshold-based notifications

## Troubleshooting

### Server returns 500 error

```
Run 1: ERROR — Server returned 500
```

Check server logs and ensure sufficient GPU memory for large inputs.

### TLS certificate errors

```
ERROR: SSL certificate verification failed
```

Use `--insecure` flag for Cloudflare tunnels (they use self-signed certs).

### Very high RTF for large texts

Expected for 1000+ line texts due to longer audio duration.
Check individual run details in audit log for outliers.

## See Also

- [SETUP_GUIDE.md](../SETUP_GUIDE.md) - Server setup
- [API.md](../API.md) - `/tts/stream` endpoint details
- `docs/benchmark_30_requests.json` - Previous benchmark data
