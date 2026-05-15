# Troubleshooting HTTP 422 Errors

## Overview

HTTP 422 (Unprocessable Entity) indicates the server rejected the request due to validation errors. This guide helps diagnose and fix 422 errors during benchmarking.

## Common Causes

### 1. Invalid Text Content

**Symptom**: 422 error when sending certain text inputs

**Solutions**:
- Ensure text is valid UTF-8 encoded
- Avoid very long single lines (try breaking into multiple lines)
- Check for null bytes or control characters
- Verify no special characters that might cause parsing issues

**Test**:
```bash
python3 -c "
text = 'This is a test with émojis 😀 and spëcial chars'
import json
print(json.dumps({'text': text}))
"
```

### 2. Request Format Issues

**Symptom**: All requests return 422

**Check request format**:
```bash
curl -s -X POST http://localhost:8000/tts/stream \
  -H "Content-Type: application/json" \
  -d '{"text":"Hello world"}'
```

**Required fields**:
- `text` (string, required)

**Optional fields**:
- `voice` (string, default: "default")
- `temperature` (float, default: 0.7, range: 0.0-1.0)

### 3. Temperature Out of Range

**Symptom**: 422 when setting temperature

**Solution**:
```python
# Valid range: 0.0 to 1.0
{"text": "hello", "temperature": 0.7}  # ✓ Valid
{"text": "hello", "temperature": 1.5}  # ✗ Invalid (too high)
{"text": "hello", "temperature": -0.5} # ✗ Invalid (too low)
```

### 4. Server Validation

**Symptom**: 422 with validation error message

**What the error message tells you**:
```json
{
  "detail": [
    {
      "loc": ["body", "text"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

Means: The `text` field in the request body is required.

### 5. Empty Text

**Symptom**: 422 for empty or whitespace-only text

**Solution**: Ensure text has content
```python
# ✗ Invalid
{"text": ""}
{"text": "   "}

# ✓ Valid
{"text": "Hello"}
{"text": "This is a test sentence."}
```

## Debugging with Enhanced Benchmark

The updated `benchmark_extended.py` now shows detailed error messages:

```
=== Benchmarking 100 lines ===
  Run  1: ERROR — Server error 422: {"detail":[{"loc":["body","text"],...}]}
  Run  2: elapsed= 234.5ms  TTFC= 189.3ms  RTF=0.0019  tok/s= 13421  chunks=48
```

## Testing Endpoints

### Single Request Test

```bash
python3 << 'EOF'
import asyncio
import aiohttp
import json

async def test():
    async with aiohttp.ClientSession() as session:
        payload = {"text": "This is a test sentence."}
        async with session.post(
            "http://localhost:8000/tts/stream",
            json=payload
        ) as resp:
            print(f"Status: {resp.status}")
            if resp.status != 200:
                print("Error:", await resp.text())
            else:
                print("✓ Success")

asyncio.run(test())
EOF
```

### Multiple Requests Test

```bash
python3 << 'EOF'
import asyncio
import aiohttp

async def test():
    async with aiohttp.ClientSession() as session:
        for i in range(3):
            payload = {"text": f"Test request {i+1}"}
            async with session.post(
                "http://localhost:8000/tts/stream",
                json=payload
            ) as resp:
                status = resp.status
                if status == 422:
                    error = await resp.text()
                    print(f"Request {i+1}: 422 ERROR - {error[:100]}")
                else:
                    print(f"Request {i+1}: {status}")

asyncio.run(test())
EOF
```

## Server Side Debugging

Check server logs for validation errors:

```bash
# Terminal running server
# Look for pydantic validation errors in logs
```

## Extended Benchmark Specific Issues

### Issue: All runs report 422

**Solution**: Verify server is running and responding

```bash
# Test health endpoint
curl http://localhost:8000/health

# Test with curl
curl -s -X POST http://localhost:8000/tts/stream \
  -H "Content-Type: application/json" \
  -d '{"text":"test"}'
```

### Issue: Some runs fail with 422

**Likely cause**: Text content validation

**Fix**:
1. Check `benchmark_extended.py` text generation function
2. Ensure generated text doesn't have problematic characters
3. Test with simpler text first: `--sizes "10" --runs 1`

## Performance vs Validation

422 errors are validation errors (bad input format).
Different from:
- **5xx errors** = server crashes or internal errors
- **503 errors** = server overloaded
- **Connection timeouts** = network issues

## Getting Help

When reporting 422 issues, include:
1. **Exact request**: `{"text": "...", "voice": "..."}`
2. **Server response**: Full error message from 422 response
3. **Benchmark output**: Show which runs failed
4. **Server logs**: Any validation errors from server

**Example bug report**:
```
Running: python scripts/benchmark_extended.py --runs 3
Got 422 on runs 2 and 3
Error message: {"detail": [...]}
```

## Related

- [API.md](../API.md) - Request/response format reference
- [SETUP_GUIDE.md](../SETUP_GUIDE.md) - Server setup
- [BENCHMARK_AUDIT.md](../docs/BENCHMARK_AUDIT.md) - Benchmark details
