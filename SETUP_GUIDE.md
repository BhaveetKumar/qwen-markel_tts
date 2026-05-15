# Complete Setup Guide: Qwen3-TTS with Pipecat

**One file with everything needed to get the system running.**

---

## 📋 Table of Contents

1. [System Requirements](#system-requirements)
2. [Installation](#installation)
3. [API Keys & Configuration](#api-keys--configuration)
4. [Start TTS Server](#start-tts-server)
5. [Run Demos](#run-demos)
6. [Verify Installation](#verify-installation)
7. [Troubleshooting](#troubleshooting)
8. [Performance Benchmarks](#performance-benchmarks)

---

## System Requirements

### Hardware
- **RTX 5090** (or compatible Blackwell GPU with sm_120)
- **CUDA 12.1+**
- **24GB+ VRAM** (for model inference)

### Software
- **Python 3.11+**
- **PyTorch 2.1+**
- **pip** or **conda**
- **git**

### Operating System
- **Linux** (recommended for native pipeline)
- **macOS** (use browser-based UI, recommended)
- **Windows** (should work, untested)

### Internet
- Working internet connection (for model downloads)
- API keys for:
  - **Deepgram** (STT)
  - **OpenAI** (LLM)
  - **HuggingFace** (optional, for model access)

---

## Installation

### Step 1: Clone Repository

```bash
cd /path/to/your/workspace
git clone https://github.com/BhaveetKumar/qwen-markel_tts.git
cd qwen-markel_tts
```

### Step 2: Create Virtual Environment

**Option A: venv**
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

**Option B: conda**
```bash
conda create -n qwen-tts python=3.11 -y
conda activate qwen-tts
```

### Step 3: Install Dependencies

```bash
# Install package in editable mode with dev dependencies
pip install -e ".[dev]"

# Verify PyTorch is installed with CUDA support
python -c "import torch; print(f'PyTorch version: {torch.__version__}'); print(f'CUDA available: {torch.cuda.is_available()}')"
```

Expected output:
```
PyTorch version: 2.1.2+cu121
CUDA available: True
```

### Step 4: Verify Installation

```bash
# Check core imports
python -c "
import torch
import transformers
import fastapi
import pipecat
print('✓ All core packages installed')
"

# List installed packages
pip list | grep -E "torch|pipecat|deepgram|openai"
```

---

## API Keys & Configuration

### Step 1: Get API Keys

**Deepgram (STT)**
1. Go to [deepgram.com](https://console.deepgram.com)
2. Create account or sign in
3. Navigate to API Keys
4. Copy your API key (starts with `dg_`)

**OpenAI (LLM)**
1. Go to [openai.com/api](https://platform.openai.com/api-keys)
2. Sign in or create account
3. Create new API key
4. Copy key (starts with `sk-proj-`)

**HuggingFace (Optional)**
1. Go to [huggingface.co](https://huggingface.co)
2. Create account or sign in
3. Navigate to Settings → Access Tokens
4. Create read token
5. Copy token (starts with `hf_`)

### Step 2: Create .env File

**In the project root** (`qwen-markel_tts/` directory), create `.env` file:

```bash
cat > .env << 'EOF'
# STT: Deepgram API Key
DEEPGRAM_API_KEY=dg_your_actual_key_here

# LLM: OpenAI API Key
OPENAI_API_KEY=sk-proj-your_actual_key_here

# Optional: HuggingFace Token (for model downloads)
HF_TOKEN=hf_your_actual_token_here

# TTS Server (default: localhost, change for remote)
TTS_SERVER_HOST=0.0.0.0
TTS_SERVER_PORT=8000
EOF

# Restrict permissions for security
chmod 600 .env
```

### Step 3: Verify .env

```bash
# Check that file exists and is not empty
cat .env | grep -E "DEEPGRAM|OPENAI"

# Expected output (values redacted):
# DEEPGRAM_API_KEY=dg_...
# OPENAI_API_KEY=sk-proj-...
```

**⚠️ Important:** `.env` should NOT be committed to git. Verify in `.gitignore`:
```bash
grep ".env" .gitignore
```

---

## Start TTS Server

The TTS server handles speech synthesis and must be running before demos.

### Option A: Local Server (Localhost)

**Terminal 1:**
```bash
cd /path/to/qwen-markel_tts

# Activate venv if not already active
source venv/bin/activate  # or: conda activate qwen-tts

# Start server
bash scripts/run_server.sh
```

Expected output:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
```

Server will be accessible at: `http://localhost:8000`

Health check:
```bash
curl -s http://localhost:8000/health
# Expected: {"status": "healthy"}
```

### Option B: Remote Server (GPU Machine)

If running on a remote machine (e.g., Vast.ai):

```bash
# SSH into remote machine
ssh -i your_key root@your_ip

# Navigate to project
cd /root/workspace/qwen-markel_tts

# Start server in background
nohup bash scripts/run_server.sh > server.log 2>&1 &

# Verify it started
sleep 5 && curl -s http://localhost:8000/health
```

### Option C: Server with Cloudflare Tunnel (Remote Access)

If you need to expose local server over the internet:

```bash
# Install cloudflared
# macOS: brew install cloudflare/cloudflare/cloudflared
# Linux: curl -fsSL https://pkg.cloudflare.com/index.html | sh

# Create tunnel (in a new terminal)
cloudflared tunnel --url http://localhost:8000

# Example output:
# https://your-tunnel-url.trycloudflare.com
```

Use the tunnel URL as `--tts-url` in demo scripts.

---

## Run Demos

Choose ONE demo to run. Both require TTS server running (see above).

### Demo Option A: Native Voice Pipeline (CLI)

**Best for:** Linux/GPU servers with microphone/speaker hardware

**Terminal 2** (keep server running in Terminal 1):
```bash
cd /path/to/qwen-markel_tts
source venv/bin/activate

# Run voice demo
python scripts/demo.py --tts-url http://localhost:8000
```

**Usage:**
```
Listening... (speak into microphone)
[Your speech is transcribed and LLM generates response]
[Response is synthesized to speech and played]
```

**CLI Arguments:**
```bash
python scripts/demo.py \
  --tts-url http://localhost:8000 \
  --host 127.0.0.1 \
  --port 9000
```

**Expected Output:**
```
🎙️  Qwen3-TTS Voice Demo
============================================================
  TTS server   : http://localhost:8000
  Deepgram key : ***26e8
  OpenAI key   : ***oXUA
  Listening on   http://127.0.0.1:9000
============================================================
[Waiting for microphone input...]
```

### Demo Option B: Browser-Based UI (Recommended for macOS)

**Best for:** macOS, Windows, or any system without native microphone access

**Terminal 2** (keep server running in Terminal 1):
```bash
cd /path/to/qwen-markel_tts
source venv/bin/activate

# Run web server
python scripts/web_demo.py --port 8080
```

**Access:** Open browser to `http://localhost:8080`

**Browser UI Features:**
- 🎤 Microphone recording button
- 📝 Real-time transcription display
- 💬 LLM response preview
- 🔊 Audio playback controls

**CLI Arguments:**
```bash
python scripts/web_demo.py \
  --host 127.0.0.1 \
  --port 8080 \
  --tts-url http://localhost:8000
```

**Screenshot of UI:**
![Qwen3-TTS Web Demo](Screenshot%202026-05-15%20at%202.19.53%20PM.png)

---

## Verify Installation

### Quick Health Checks

```bash
# 1. Check TTS server is healthy
curl -s http://localhost:8000/health | python -m json.tool

# Expected:
# {
#   "status": "healthy",
#   "models": {
#     "talker_decoder": "loaded",
#     "vocoder": "loaded"
#   }
# }

# 2. Test TTS inference
curl -X POST http://localhost:8000/tts \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello, this is a test"}' \
  -o /tmp/test_audio.wav

# 3. Test STT (with Deepgram key)
python -c "
from deepgram import DeepgramClient
dg = DeepgramClient()
print('✓ Deepgram SDK ready')
"

# 4. Test LLM (with OpenAI key)
python -c "
from openai import OpenAI
client = OpenAI()
print('✓ OpenAI SDK ready')
"
```

### Run Full Test Suite

```bash
# Run all tests
pytest tests/ -v

# Run specific test
pytest tests/test_decoder.py -v

# Run with coverage
pytest tests/ --cov=src/ --cov-report=html
```

**Expected:** All tests pass ✓

---

## Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'pipecat'"

**Solution:**
```bash
pip install -e ".[dev]"
# OR
pip install "pipecat-ai[deepgram,openai]>=0.0.53"
```

### Issue: "DEEPGRAM_API_KEY not found in .env"

**Solution:**
```bash
# Check .env exists
ls -la .env

# Check file has content
cat .env

# Verify key is set
python -c "import os; print(os.getenv('DEEPGRAM_API_KEY', 'NOT SET'))"
```

### Issue: "Connection refused to http://localhost:8000"

**Solution:**
```bash
# 1. Check server is running
ps aux | grep "uvicorn\|run_server"

# 2. Check port 8000 is listening
netstat -tlnp | grep 8000  # Linux
lsof -i :8000  # macOS

# 3. Restart server
pkill -f "uvicorn\|run_server.sh"
bash scripts/run_server.sh
```

### Issue: "CUDA out of memory"

**Solution:**
```bash
# Reduce batch size
python scripts/demo.py --batch-size 1

# Check VRAM usage
nvidia-smi

# Clear cache
python -c "import torch; torch.cuda.empty_cache()"
```

### Issue: "Deepgram API error: 401 Unauthorized"

**Solution:**
```bash
# 1. Check API key is valid
grep DEEPGRAM_API_KEY .env

# 2. Verify key format (should start with 'dg_')
# 3. Regenerate key in Deepgram console
# 4. Update .env and restart
```

### Issue: macOS microphone permission denied

**Solution:** Use browser-based UI instead:
```bash
# Browser doesn't require TCC permissions
python scripts/web_demo.py --port 8080
# Then open http://localhost:8080
```

### Issue: Audio not playing / No sound output

**Solution:**
```bash
# 1. Check speakers are plugged in and unmuted
# 2. Test system audio
python -c "import sounddevice as sd; sd.default.device"

# 3. Rebuild audio with verbose output
python scripts/demo.py --tts-url http://localhost:8000 -v
```

---

## Performance Benchmarks

### Expected Performance (RTX 5090)

| Metric | Value | Note |
|--------|-------|------|
| **Decode Speed** | 13,000+ tokens/sec | CUDA kernel optimized |
| **TTFC (Time-to-First-Chunk)** | <20 µs | Ultra-low latency |
| **RTF (Real-Time Factor)** | 0.0023 | Very efficient |
| **STT Latency** | 1-3 sec | Deepgram processing |
| **LLM Latency** | 2-5 sec | OpenAI API call + stream |
| **TTS Latency** | 1-2 sec | Vocoder inference |
| **End-to-End Latency** | 5-12 sec | Full pipeline |

### Run Benchmarks

```bash
# Decode benchmark
python scripts/benchmark.py --runs 10 --batch-size 32

# STT benchmark
python -c "
from scripts.deepgram_smoke import test_deepgram
test_deepgram('test audio')
"

# Full pipeline benchmark
python scripts/benchmark.py --full-pipeline --runs 5
```

**Expected Output:**
```
=== Qwen3-TTS Decode Benchmark ===
Runs: 10
Tokens/sec: 13,234
RTF: 0.0022
TTFC: 18.3 µs
```

---

## Next Steps

### Common Workflows

**1. Development & Testing**
```bash
# Run tests and benchmarks
pytest tests/ -v
python scripts/benchmark.py --runs 5
```

**2. API-Only (No Audio)**
```bash
# Start TTS server
bash scripts/run_server.sh

# Make HTTP requests
curl -X POST http://localhost:8000/tts \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello"}'
```

**3. Pipecat Integration**
```bash
# Use the TTS service in Pipecat pipelines
python scripts/pipecat_demo.py --tts-url http://localhost:8000
```

### Documentation References

- **WEB_UI.md** — Browser UI guide with screenshots and features
- **API.md** — Full API documentation and endpoints
- **ARCHITECTURE.md** — System design and component overview
- **QUICKSTART.md** — 5-minute quick start
- **DOCUMENTATION.md** — Complete docs index

### Troubleshooting Reference

- **docs/KERNEL_CHANGES.md** — CUDA kernel modifications
- **SUBMISSION.md** — Project submission details and methodology
- **COMPLETION_SUMMARY.md** — Performance results and analysis

---

## Support

**For issues or questions:**

1. Check [Troubleshooting](#troubleshooting) section above
2. Review error logs: `tail -f /tmp/server.log`
3. Check GitHub issues: https://github.com/BhaveetKumar/qwen-markel_tts/issues
4. Review API docs: [API.md](API.md)

---

**Last Updated:** 15 May 2026
**Status:** ✅ All systems tested and verified
