# Browser-Based Web UI Guide

The web UI (`scripts/web_demo.py`) provides a browser-based interface for testing the TTS pipeline without native Python microphone permissions.

## Why Browser UI?

### Problem: macOS Microphone Permissions

Python processes on macOS require explicit TCC (Transparency, Consent, and Control) permissions to access the microphone. Granting these permissions is complex and unreliable.

### Solution: Browser Microphone Access

Browsers (Chrome, Firefox, Safari) can access the microphone directly and send audio via WebSocket/HTTP to your server. The server handles STT, LLM, and TTS, then returns audio for the browser to play.

```
Browser (microphone + speakers)
    ↓
/api/chat endpoint (audio → JSON)
    ↓
Server (STT → LLM → TTS)
    ↓
Browser plays response audio
```

## Quick Start

### 1. Configure Secrets

```bash
# Create .env file in the project root with your API keys
# Do NOT commit .env to version control
cat > .env << EOF
DEEPGRAM_API_KEY=<your-deepgram-api-key>
OPENAI_API_KEY=<your-openai-api-key>
HF_TOKEN=<your-hugging-face-token>  # optional
EOF

chmod 600 .env  # Restrict permissions
```

### 2. Start TTS Server (Terminal 1)

```bash
bash scripts/run_server.sh
```

Expected output:
```
INFO:     Started server process
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### 3. Start Web Server (Terminal 2)

```bash
python scripts/web_demo.py --port 8080
```

Expected output:
```
🎙️  Qwen3-TTS Web Demo
============================================================
  TTS server   : http://localhost:8000
  Deepgram key : ***26e8
  OpenAI key   : ***oXUA
  Open in browser → http://127.0.0.1:8080
============================================================
```

### 4. Open Browser

Navigate to: **http://localhost:8080**

**Screenshot of the UI:**

![Qwen3-TTS Web UI](Screenshot%202026-05-15%20at%202.19.53%20PM.png)

You should see:
- Input box for microphone recording
- "Start Recording" button
- Transcript display
- Response display
- Audio player for TTS output

### 5. Test

1. Click **"Start Recording"**
2. Say something, e.g., "What's the weather like?"
3. Click **"Stop Recording"**
4. Wait for transcription (2-3 seconds)
5. Wait for LLM response (3-5 seconds)
6. Listen to TTS audio playback

## Architecture

### Files

| File | Purpose |
|------|---------|
| `scripts/web_demo.py` | FastAPI server, chat endpoint, secret loading from .env |
| `scripts/static/index.html` | Browser UI: HTML/CSS/JavaScript |
| `scripts/.env_loader.py` | Utility for loading .env securely |

### Endpoints

#### `GET /` 
Serves `index.html` (the browser UI).

#### `POST /api/chat`
Accepts audio blob, returns JSON with transcription, response, and audio.

**Request:**
```
Content-Type: audio/webm
Body: Raw WAV/WebM audio bytes
```

**Response:**
```json
{
  "transcript": "What's the weather like?",
  "response": "I'm an AI assistant. I don't have access to real-time weather data.",
  "audio_b64": "UklGRi4AAABXQVZFZm10...",  // Base64-encoded WAV
  "metrics": {
    "stt_time_ms": 1234,
    "llm_time_ms": 3456,
    "tts_time_ms": 2345
  }
}
```

#### `GET /health`
Returns TTS server status.

Response:
```json
{
  "ok": true,
  "tts_url": "http://localhost:8000"
}
```

## Features

✅ **Microphone Access via Browser**
- No Python TCC permission issues
- Works on macOS, Linux, Windows

✅ **Real-Time Transcription Display**
- Shows Deepgram STT output immediately

✅ **LLM Response Display**
- Shows OpenAI response before TTS

✅ **Immediate Audio Playback**
- Browser plays WAV response immediately

✅ **Secure Secret Management**
- All API keys loaded from `.env`
- No secrets in command-line args or UI

✅ **Performance Metrics**
- STT latency, LLM latency, TTS latency displayed

## Configuration

### Command-Line Arguments

```bash
python scripts/web_demo.py \
    --host 127.0.0.1              # Listen address (default: 127.0.0.1)
    --port 8080                   # Listen port (default: 8080)
    # Note: --tts-url, --deepgram-key, --openai-key are NOT accepted
    # Secrets MUST be in .env file only
```

### Environment Variables

All secrets are loaded from `.env` at startup:

```bash
# Required
DEEPGRAM_API_KEY=sk_...
OPENAI_API_KEY=sk-proj-...

# Optional
HF_TOKEN=hf_...
TTS_URL=http://localhost:8000
```

### .env File

```bash
# Create or edit .env
cat .env
```

Output (example - your keys will be different):
```
HF_TOKEN=hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
DEEPGRAM_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

## Troubleshooting

### Error: "Missing DEEPGRAM_API_KEY in .env"

**Solution:** Create `.env` file with Deepgram key.

```bash
echo "DEEPGRAM_API_KEY=your_key" >> .env
```

### Error: "TTS server health check returned false"

**Solution:** Ensure TTS server is running on port 8000.

```bash
# Terminal 1
bash scripts/run_server.sh

# Verify
curl http://localhost:8000/health
```

### No Microphone in Browser

**Solution:** Check browser microphone permissions.

1. Click address bar lock icon
2. Click "Microphone" → "Allow"
3. Reload page

### Audio Playback Issues

**Solution:** Ensure speakers are not muted and volume is up.

1. Browser tab volume control (top-right)
2. System audio level
3. Open browser console (F12) for errors

### Performance Latency

Typical end-to-end latency:

| Stage | Time |
|-------|------|
| STT (Deepgram) | 1-3 sec |
| LLM (OpenAI) | 2-5 sec |
| TTS (Qwen3) | 1-2 sec |
| **Total** | **4-10 sec** |

To optimize:
- Use OpenAI's faster `gpt-3.5-turbo` model (edit `web_demo.py`)
- Reduce text length in LLM system prompt
- Ensure stable network to Deepgram/OpenAI

## Security

### Secret Management

- ✅ All secrets loaded from `.env` only
- ✅ Secrets NOT printed in logs (masked as `***...`)
- ✅ No command-line argument access to secrets
- ✅ `.env` is `.gitignore`'d (not committed)

### CORS & HTTPS

For production deployment:

1. Enable CORS in `web_demo.py` (if accessing from different domain)
2. Set up HTTPS with certifi/SSL
3. Run behind reverse proxy (nginx, Cloudflare)

## Advanced: Customizing the UI

Edit `scripts/static/index.html` to customize:

- Recording button appearance
- Display layout
- Response formatting
- Audio player styling

Example: Change button text

```html
<!-- Find this line -->
<button id="startBtn">Start Recording</button>

<!-- Change to -->
<button id="startBtn">🎙️ Speak</button>
```

Then refresh browser.

## FAQ

**Q: Can I use this on a remote server?**

A: Yes! Set `--host 0.0.0.0` (but only in trusted networks). For internet access, use Cloudflare Tunnel or nginx reverse proxy with authentication.

**Q: Can I use a different LLM?**

A: Edit `web_demo.py`, function `chat_with_openai()`. Support Claude, Llama, etc. by changing the API call.

**Q: Can I change the TTS voice?**

A: Edit `web_demo.py`, function `synthesize_with_qwen()`. Pass different `voice` parameter in the payload.

**Q: Does it work offline?**

A: No. Requires Deepgram (STT), OpenAI (LLM), and local TTS server. All require internet except the local TTS.

**Q: Can I record the output?**

A: Yes. Browser's developer tools (F12) → Network → filter by `/api/chat` → response → copy audio_b64 → decode and save as WAV.
