# API Reference

HTTP REST API for Qwen3-TTS streaming inference server.

## Server

**Base URL**: `http://localhost:8000` (or configured `$PORT`)

**Architecture**: FastAPI + uvicorn, async request handling

---

## Endpoints

### POST `/tts/stream`

**Synthesize text to speech, streaming PCM audio chunks.**

#### Request

```json
{
  "text": "Hello, this is a test.",
  "voice": "default",
  "temperature": 0.7
}
```

| Field | Type | Required | Default | Notes |
|-------|------|----------|---------|-------|
| `text` | string | ✓ | — | Speech text to synthesize |
| `voice` | string | ✗ | `"default"` | Voice profile (currently unused, reserved for future) |
| `temperature` | float | ✗ | `0.7` | Sampling temperature for token generation (0.0–1.0) |

#### Response

Streaming NDJSON (newline-delimited JSON). Each line is one message:

```ndjson
{"event":"start","timestamp":"2026-05-15T10:30:45Z"}
{"pcm":"<base64-encoded 16-bit PCM>","seq":0}
{"pcm":"<base64-encoded 16-bit PCM>","seq":1}
{"pcm":"<base64-encoded 16-bit PCM>","seq":2}
{"event":"end","seq":3,"metrics":{"num_tokens":96,"duration_ms":125.43,"tok_s":765.2,"ttfc_ms":12.3,"rtf":0.0018}}
```

| Field | Type | Notes |
|-------|------|-------|
| `event` | string | `"start"`, `"token"`, `"end"`, or absent for audio chunk |
| `timestamp` | string | ISO 8601 timestamp (start event only) |
| `pcm` | string | Base64-encoded 16-bit PCM (24 kHz mono), ~1 KB per chunk (40 ms audio) |
| `seq` | int | Chunk sequence number (0-indexed) |
| `metrics` | object | Performance metrics (end event only) |

**Audio Format**:
- Sample rate: 24 kHz
- Channels: 1 (mono)
- Bit depth: 16-bit signed PCM
- Byte order: little-endian
- Chunk size: ~1 KB (40 ms @ 24 kHz)

**Metrics Object** (end event):
```json
{
  "num_tokens": 96,
  "duration_ms": 125.43,
  "tok_s": 765.2,
  "ttfc_ms": 12.3,
  "rtf": 0.0018
}
```

| Field | Type | Notes |
|-------|------|-------|
| `num_tokens` | int | Total speech tokens generated |
| `duration_ms` | float | Total synthesis time (server-side) |
| `tok_s` | float | Throughput: tokens/second |
| `ttfc_ms` | float | Time-to-first-chunk: ms until first audio received |
| `rtf` | float | Real-time factor: duration / audio_length |

#### Example (curl)

```bash
curl -s -X POST http://localhost:8000/tts/stream \
  -H "Content-Type: application/json" \
  -d '{"text":"Hello world, this is a test of streaming synthesis."}' \
  | python3 -c "
import sys, json, base64

for line in sys.stdin:
    msg = json.loads(line.strip())
    if 'pcm' in msg:
        pcm = base64.b64decode(msg['pcm'])
        print(f'Chunk {msg[\"seq\"]}: {len(pcm)} bytes')
    elif msg.get('event') == 'end':
        print(f'Done. Metrics: {msg[\"metrics\"]}')
"
```

#### Example (Python + aiohttp)

```python
import aiohttp
import asyncio
import json
import base64

async def synthesize(text: str):
    async with aiohttp.ClientSession() as session:
        async with session.post(
            'http://localhost:8000/tts/stream',
            json={'text': text}
        ) as resp:
            async for line in resp.content:
                msg = json.loads(line.strip())
                if 'pcm' in msg:
                    pcm_bytes = base64.b64decode(msg['pcm'])
                    print(f'Got {len(pcm_bytes)} bytes of audio')
                elif msg.get('event') == 'end':
                    print(f'Metrics: {msg["metrics"]}')

asyncio.run(synthesize("Hello, this is a test."))
```

#### Error Responses

```json
{"detail": "Invalid request: text too long (max 1000 chars)"}
```

HTTP status codes:
- `200`: Success
- `400`: Bad request (invalid text, etc.)
- `500`: Server error (model not loaded, GPU failure, etc.)

---

### GET `/health`

**Check server health and model status.**

#### Response

```json
{
  "status": "ok",
  "model_loaded": true,
  "uptime_s": 123.45,
  "device": "cuda:0"
}
```

| Field | Type | Notes |
|-------|------|-------|
| `status` | string | `"ok"` if healthy, `"error"` if failed |
| `model_loaded` | bool | True if Qwen3-TTS model successfully loaded |
| `uptime_s` | float | Seconds since server started |
| `device` | string | Device used for inference (`"cuda:0"`, `"cpu"`, etc.) |

#### Example

```bash
curl http://localhost:8000/health
```

---

### GET `/metrics`

**Aggregated inference metrics (all requests since startup).**

#### Response

```json
{
  "total_requests": 42,
  "total_tokens": 3840,
  "mean_ttfc_ms": 15.2,
  "mean_tok_s": 13145.7,
  "mean_rtf": 0.00231,
  "p50_ttfc_ms": 14.8,
  "p95_ttfc_ms": 21.3,
  "p99_ttfc_ms": 28.5
}
```

| Field | Type | Notes |
|-------|------|-------|
| `total_requests` | int | Cumulative requests processed |
| `total_tokens` | int | Total speech tokens generated |
| `mean_ttfc_ms` | float | Mean time-to-first-chunk |
| `mean_tok_s` | float | Mean throughput (tok/s) |
| `mean_rtf` | float | Mean real-time factor |
| `p50_ttfc_ms` | float | Median TTFC |
| `p95_ttfc_ms` | float | 95th percentile TTFC |
| `p99_ttfc_ms` | float | 99th percentile TTFC |

#### Example

```bash
curl http://localhost:8000/metrics | python3 -m json.tool
```

---

## Pipecat Integration

### QwenMegakernelTTSService

Drop-in Pipecat `TTSService` for use in voice pipelines.

```python
from pipecat_adapter.tts import QwenMegakernelTTSService
import aiohttp

async with aiohttp.ClientSession() as session:
    tts = QwenMegakernelTTSService(
        base_url="http://localhost:8000",
        aiohttp_session=session,
        sample_rate=16000,
    )
    
    # Use in Pipecat pipeline
    pipeline = Pipeline([
        stt,
        llm,
        tts,          # ← insert here
        transport,
    ])
```

#### Constructor Parameters

| Parameter | Type | Default | Notes |
|-----------|------|---------|-------|
| `base_url` | str | — | Server URL (e.g., `http://localhost:8000`) |
| `aiohttp_session` | ClientSession | — | Shared aiohttp session |
| `sample_rate` | int | `16000` | Output sample rate (24000 recommended for quality) |
| `voice` | str | `"default"` | Voice profile (reserved) |
| `temperature` | float | `0.7` | Token sampling temperature |

#### Methods

```python
async def process_text(text: str) -> None
```
Queue text for synthesis. Yields `TTSAudioRawFrame` chunks to pipeline.

```python
async def is_healthy() -> bool
```
Check if server is reachable and model loaded. Useful for startup validation.

---

## Status Codes and Error Handling

### HTTP Status Codes

| Code | Meaning | Example |
|------|---------|---------|
| `200` | Success | Request processed, streaming response |
| `400` | Bad Request | Invalid JSON, missing required field |
| `422` | Validation Error | Text exceeds length limit |
| `500` | Internal Server Error | GPU failure, OOM, model load error |
| `503` | Service Unavailable | Server starting up, model loading |

### Error Response Format

```json
{
  "detail": "Text exceeds maximum length (1000 chars)"
}
```

---

## Performance Benchmarks

Based on RTX 5090 benchmarks (30 requests, 96 tokens/request):

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| Throughput (tok/s) | 13,198 | — | ✓ Excellent |
| TTFC (ms) | 0.0177 avg | < 60 | ✓ Pass |
| RTF | 0.00231 avg | < 0.15 | ✓ Pass |
| End-to-end latency | ~512 ms | — | ✓ Good |

See [docs/implementation_audit_2026-05-15.md](docs/implementation_audit_2026-05-15.md) for detailed metrics.

---

## Limits and Defaults

| Parameter | Limit | Notes |
|-----------|-------|-------|
| Text length | 1000 characters | Per request |
| Max tokens | 256 | Autoregressive generation cutoff |
| Request timeout | 60 seconds | Server-side |
| Concurrent requests | Unlimited | One GPU, sequential kernel/HF forward passes |

---

## Rate Limiting

Currently: **No rate limiting**. Server handles requests sequentially (single GPU).

For production, add:
- Token bucket rate limiter
- Per-IP request limit
- Queue management

See [DEPLOYMENT.md](DEPLOYMENT.md) for production recommendations.
