# Quick Start

Get a working TTS server running in 5 minutes.

## 1. Install (2 min)

```bash
cd qwen-markel_tts
pip install -e ".[dev]"
```

## 2. Test (1 min)

```bash
pytest tests/ -v
```

Should see: **30+ tests passing**

## 3. Configure Secrets (1 min)

Create a `.env` file with your API keys (required for all demos):

```bash
cp .env.example .env
# Edit .env and add:
# - DEEPGRAM_API_KEY=your_key
# - OPENAI_API_KEY=your_key
# - HF_TOKEN=your_token
```

## 4. Run Demo (Choose One)

### Option A: Native Pipecat Voice Pipeline (requires microphone/speaker)

```bash
# Start TTS server (Terminal 1)
bash scripts/run_server.sh

# Run voice pipeline (Terminal 2)
python scripts/demo.py --tts-url http://localhost:8000
```

✅ Speak into your microphone → transcribed → LLM response → TTS playback

### Option B: Browser-Based UI (recommended for macOS)

Use the browser for microphone access (sidesteps OS-level permission issues):

```bash
# Start TTS server (Terminal 1)
bash scripts/run_server.sh

# Run web server (Terminal 2)
python scripts/web_demo.py --port 8080
```

Then open: **http://localhost:8080** in your browser 🎙️

**UI Preview:**

![Qwen3-TTS Web Demo](Screenshot%202026-05-15%20at%202.19.53%20PM.png)

## 5. Test (1 min)

```bash
pytest tests/ -v
```

Expected: **30+ tests passing**

Response:
```json
{"status":"ok","model_loaded":true}
```

## 4. Synthesize Speech (1 min)

```bash
curl -s -X POST http://localhost:8000/tts/stream \
  -H "Content-Type: application/json" \
  -d '{"text":"Hello, this is a test of the speech synthesis system."}' \
  | head -20
```

You'll see NDJSON-formatted audio chunks (base64-encoded PCM).

Decode and save to file:

```bash
python3 << 'EOF'
import sys, json, base64

chunks = []
for line in sys.stdin:
    msg = json.loads(line.strip())
    if 'pcm' in msg:
        chunks.append(base64.b64decode(msg['pcm']))

import wave
with wave.open('/tmp/output.wav', 'wb') as w:
    w.setnchannels(1)
    w.setsampwidth(2)
    w.setframerate(24000)
    w.writeframes(b''.join(chunks))
print("Saved to /tmp/output.wav")
EOF
```

Play it back:

```bash
ffplay /tmp/output.wav
# or
aplay /tmp/output.wav
```

## 5. Benchmark (1 min)

```bash
python scripts/benchmark.py --runs 5
```

Output:
```
Run 1: TTFC=12.3ms, Throughput=13201 tok/s, RTF=0.002
...
Summary:
  Mean throughput: 13198.40 tok/s
  Mean TTFC: 0.0177 ms
  Mean RTF: 0.002312
```

✓ **All performance targets met!**

---

## Next Steps

- **Full setup guide**: [SETUP.md](SETUP.md)
- **API docs**: [API.md](API.md)
- **Architecture**: [ARCHITECTURE.md](ARCHITECTURE.md)
- **Deployment**: [DEPLOYMENT.md](DEPLOYMENT.md)
- **Pipecat demo**: [scripts/demo.py](scripts/demo.py)
