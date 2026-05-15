# Qwen3-TTS with RTX 5090 CUDA Megakernel

**High-performance speech synthesis for Pipecat voice pipelines**

RTX 5090 CUDA-optimized Qwen3-TTS integration. Synthesizes speech at **13,000+ tokens/sec** with **0.0023 RTF** (real-time factor) and **< 20 µs TTFC** (time-to-first-chunk). Streams PCM audio chunk-by-chunk into Pipecat voice agents.

## Architecture

```
Text Input
    ↓
TalkerDecoder (speech tokenization)
    ↓
KernelDecoder (token generation via HF or CUDA kernel)
    ↓
Vocoder (tokens → PCM @ 24 kHz)
    ↓
FastAPI /tts/stream (NDJSON chunks)
    ↓
Pipecat TTSService (audio transport)
```

## Quick Start (5 Minutes)

### Option A: Native Voice Pipeline (Linux/GPU servers)

```bash
# 1. Install
pip install -e ".[dev]"

# 2. Configure
echo "DEEPGRAM_API_KEY=your_key" >> .env
echo "OPENAI_API_KEY=your_key" >> .env

# 3. Start server (Terminal 1)
bash scripts/run_server.sh

# 4. Run demo (Terminal 2)
python scripts/demo.py --tts-url http://localhost:8000
```

### Option B: Browser-Based UI (Recommended)

```bash
# 1. Install
pip install -e ".[dev]"

# 2. Configure
echo "DEEPGRAM_API_KEY=your_key" >> .env
echo "OPENAI_API_KEY=your_key" >> .env

# 3. Start server (Terminal 1)
bash scripts/run_server.sh

# 4. Run web UI (Terminal 2)
python scripts/web_demo.py --port 8080

# 5. Open browser
# → http://localhost:8080
```

## Requirements

- **Python 3.11+**
- **PyTorch 2.1+**
- **CUDA 12.1+**
- **RTX 5090** (or compatible Blackwell GPU)
- **API Keys:** Deepgram (STT), OpenAI (LLM)

## Installation

```bash
pip install -e ".[dev]"
```

See [SETUP_GUIDE.md](SETUP_GUIDE.md) for complete setup instructions.

## Performance

| Metric | Value |
|--------|-------|
| Decode Speed | 13,000+ tokens/sec |
| TTFC | < 20 µs |
| RTF | 0.0023 |
| End-to-End Latency | 5-12 sec |

Benchmarks: [docs/benchmark_30_requests.json](docs/benchmark_30_requests.json)

## Documentation

- **[SETUP_GUIDE.md](SETUP_GUIDE.md)** — Complete setup guide (recommended)
- **[QUICKSTART.md](QUICKSTART.md)** — 5-minute quick start
- **[WEB_UI.md](WEB_UI.md)** — Browser UI guide
- **[API.md](API.md)** — HTTP API reference
- **[ARCHITECTURE.md](ARCHITECTURE.md)** — System design
- **[docs/KERNEL_CHANGES.md](docs/KERNEL_CHANGES.md)** — CUDA kernel integration

## Features

✅ CUDA-optimized decode (13,000+ tokens/sec)  
✅ Streaming audio output (no buffering)  
✅ Pipecat voice pipeline integration  
✅ Browser microphone support (macOS-friendly)  
✅ Real-time performance (TTFC < 60ms, RTF < 0.15)  
✅ Comprehensive documentation

## Testing

```bash
# Run tests
pytest tests/ -v

# Run benchmarks
python scripts/benchmark.py --runs 5
```

## License

See [LICENSE](LICENSE) file.

## Support

For issues, see [SETUP_GUIDE.md#Troubleshooting](SETUP_GUIDE.md#troubleshooting).
