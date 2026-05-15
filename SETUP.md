# Setup Guide

Complete step-by-step instructions for building, testing, and deploying qwen-markel-tts.

## Prerequisites

- **GPU**: NVIDIA RTX 5090 (or compatible sm_120 Blackwell GPU), CUDA 12.x
- **System**: Linux (tested on Ubuntu 22.04, Vast.ai Nvidia PyTorch image)
- **Python**: 3.11+
- **Network**: Internet access for HuggingFace model download
- **Disk Space**: ~5 GB (for model cache, CUDA build artifacts)

## Installation

### 1. Clone and Navigate

```bash
cd /Users/fc20136/Desktop/poc
git clone git@github.com:your-org/qwen-markel_tts.git
cd qwen-markel-tts
```

### 2. Install Dependencies

Create a virtual environment (recommended):

```bash
python3.11 -m venv venv
source venv/bin/activate
```

Install the project in development mode:

```bash
pip install -e ".[dev]"
```

This installs:
- Core dependencies: torch, transformers, fastapi, uvicorn
- Dev dependencies: pytest, black, isort
- Optional: `pip install -e ".[pipecat]"` for Pipecat demo

### 3. Verify Installation

Run the local unit tests (no GPU required, no model download):

```bash
pytest tests/ -v
```

Expected output: **30+ tests passing**

### 4. Set Up HuggingFace Token (Optional but Recommended)

If you don't have a HuggingFace account token, download models will be slower. To add one:

```bash
echo "HF_TOKEN=your_hf_token_here" >> .env
```

Or export directly:

```bash
export HF_TOKEN=your_hf_token_here
```

### 5. Build CUDA Extension (GPU Required)

This compiles the qwen_megakernel CUDA code. **Note**: This step uses the HuggingFace fallback path on RTX 5090 if the original kernel is unavailable.

```bash
bash scripts/build.sh
```

**Expected output**:
```
Megakernel CUDA extension loaded for Qwen3-TTS-Talker
```

Or if CUDA kernel unavailable:
```
Megakernel CUDA extension unavailable (...). Falling back to PyTorch autoregressive decode.
```

Both are valid — the fallback uses HuggingFace model decode and meets performance targets.

### 6. Start the Inference Server

In a new terminal window:

```bash
bash scripts/run_server.sh
```

**Expected output**:
```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete [uvicorn]
INFO:     Uvicorn running on http://0.0.0.0:8000
```

Check health:

```bash
curl http://localhost:8000/health
```

Response:
```json
{"status":"ok","model_loaded":true}
```

### 7. Run Benchmark

In another terminal:

```bash
python scripts/benchmark.py --runs 30 --text "Hello, this is a test of the speech synthesis system."
```

**Expected output**:
```
Run 1: TTFC=12.3ms, Throughput=13201 tok/s, RTF=0.002
...
Summary:
  Mean throughput: 13198.40 tok/s
  Mean TTFC: 0.0177 ms
  Mean RTF: 0.002312
  ✓ All targets met (TTFC < 60ms, RTF < 0.15)
```

### 8. (Optional) Run Pipecat Demo

Requires: Pipecat, Deepgram API key, OpenAI API key

```bash
pip install "pipecat-ai[deepgram,openai]>=0.0.53"

python scripts/demo.py \
    --tts-url http://localhost:8000 \
    --deepgram-key "$DEEPGRAM_API_KEY" \
    --openai-key "$OPENAI_API_KEY"
```

Talk into your microphone. The system will:
1. Transcribe your speech (Deepgram STT)
2. Send to OpenAI GPT for response
3. Synthesize response via Qwen3-TTS (this server)
4. Play audio back

## Troubleshooting

### "CUDA out of memory"
The RTX 5090 has 32 GB. If OOM occurs:
- Reduce batch size (not applicable for single-token decode)
- Check for other GPU processes: `nvidia-smi`
- Restart the server

### "Module qwen_megakernel not found"
The megakernel submodule must be cloned alongside this repo:
```bash
cd ..
git clone https://github.com/AlpinDale/qwen_megakernel.git
cd qwen-markel_tts
```

### "HuggingFace hub token required"
Model download without token is rate-limited. Set `HF_TOKEN`:
```bash
export HF_TOKEN=$(cat ~/.hf_token)
```

### "Server port 8000 already in use"
Change the port:
```bash
PORT=8001 bash scripts/run_server.sh
```

Then update benchmark/demo URLs:
```bash
python scripts/benchmark.py --url http://localhost:8001
```

### Test failures
All tests run locally without GPU. If any fail:
```bash
pytest tests/ -v -s  # verbose + show print statements
```

Check Python version:
```bash
python --version  # must be 3.11+
```

## Next Steps

1. **Quick start**: See [QUICKSTART.md](QUICKSTART.md)
2. **API reference**: See [API.md](API.md)
3. **Deployment**: See [DEPLOYMENT.md](DEPLOYMENT.md) for Vast.ai / cloud setup
4. **Architecture details**: See [ARCHITECTURE.md](ARCHITECTURE.md)
5. **Kernel internals**: See [docs/KERNEL_CHANGES.md](docs/KERNEL_CHANGES.md)
