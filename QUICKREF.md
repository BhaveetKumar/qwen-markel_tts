# Quick Reference Guide

## ⚡ Most Common Commands

### Starting the Server

```bash
# Option 1: Direct (requires venv + dependencies)
bash scripts/run_server.sh

# Option 2: Using make (easiest)
make run

# Option 3: Docker
docker-compose up -d

# Option 4: Custom port
PORT=8001 bash scripts/run_server.sh
```

Check it's running:
```bash
curl http://localhost:8000/health
```

### Using the CLI Tool

```bash
# Check server is up
python scripts/cli.py --check-health

# Simple synthesis
python scripts/cli.py "Your text here"

# Save to file
python scripts/cli.py "Hello" --output output.wav

# Multiple runs
python scripts/cli.py "Test" --runs 3 --output test.wav

# Interactive mode (type text, get audio)
python scripts/cli.py --interactive

# Different voice
python scripts/cli.py "Hi" --voice talker_name
```

### Generating Samples

```bash
# Start server first
make run &

# Generate 5 sample files
python scripts/generate_samples.py

# Listen to them
ffplay audio_samples/sample_01.wav
```

### Testing

```bash
# Run all tests
make test

# Quick test
make test-quick

# Watch mode (auto-rerun on changes)
make watch-test

# Specific test file
pytest tests/test_decoder.py -v
```

### Performance Benchmarking

```bash
# Quick benchmark (10 runs)
make benchmark

# Extended benchmark (30 runs)
make benchmark-long

# Custom params
python scripts/benchmark.py --runs 50 --text "Your long text here"
```

### Code Quality

```bash
# Format code
make format

# Check formatting
make lint

# Both
make format && make lint
```

---

## 📦 Docker Quick Start

```bash
# Build image
docker build -t qwen-markel-tts:latest .

# Run standalone
docker run --gpus all -p 8000:8000 qwen-markel-tts:latest

# Using docker-compose (recommended)
docker-compose up -d

# Check logs
docker-compose logs -f tts-server

# Stop
docker-compose down
```

---

## 🔧 Configuration

### Environment Variables

```bash
# .env (git-ignored, for local overrides)
export HF_TOKEN="your_huggingface_token"
export CUDA_VISIBLE_DEVICES="0"
export PORT=8000
export LOG_LEVEL=INFO
```

### Common Configuration

| Variable | Default | Purpose |
|----------|---------|---------|
| `PORT` | 8000 | Server port |
| `HF_TOKEN` | (none) | HuggingFace token |
| `HF_HOME` | `~/.cache/huggingface` | Model cache dir |
| `TORCH_HOME` | `~/.cache/torch` | Torch cache dir |
| `CUDA_VISIBLE_DEVICES` | (all) | GPU selection |
| `LOG_LEVEL` | INFO | Logging level |

---

## 🐛 Troubleshooting

### Server won't start

```bash
# Check CUDA
nvidia-smi

# Check Python
python3 --version

# Check dependencies
pip list | grep -E "torch|transformers|fastapi"

# Run with verbose logging
LOG_LEVEL=DEBUG bash scripts/run_server.sh
```

### Out of memory

```bash
# Reduce batch size (if supported)
# Check available memory
nvidia-smi

# Monitor during run
watch -n 1 nvidia-smi
```

### Model download fails

```bash
# Check HF token
echo $HF_TOKEN

# Set it properly
export HF_TOKEN="hf_xxxxxxxxxxxxx"

# Try manual download
huggingface-cli download Qwen/Qwen3-TTS-12Hz-0.6B-Base
```

### CLI can't connect to server

```bash
# Check server is running
curl http://localhost:8000/health

# Try different URL
python scripts/cli.py "text" --url http://127.0.0.1:8000
```

---

## 📊 Monitoring

### Real-time GPU usage

```bash
watch -n 1 nvidia-smi
```

### Server metrics

```bash
curl http://localhost:8000/metrics | jq
```

### Performance stats

```bash
make benchmark
```

---

## 🚀 Deployment

### Local (single machine)
```bash
make run
```

### Docker (recommended)
```bash
docker-compose up -d
```

### Production (RTX 5090)
See [DEPLOYMENT.md](DEPLOYMENT.md) for:
- Vast.ai setup with Cloudflare tunnel
- Kubernetes deployment
- Load testing procedures
- Monitoring setup

---

## 📚 Documentation Index

| Document | Purpose |
|----------|---------|
| [README.md](README.md) | Project overview |
| [QUICKSTART.md](QUICKSTART.md) | 5-minute setup |
| [SETUP.md](SETUP.md) | Complete installation |
| [API.md](API.md) | HTTP API reference |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System design |
| [DEPLOYMENT.md](DEPLOYMENT.md) | Production guide |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Developer guide |
| [SECURITY.md](SECURITY.md) | Security policy |
| [CHANGELOG.md](CHANGELOG.md) | Version history |
| [MISSING_PIECES.md](MISSING_PIECES.md) | Infrastructure summary |

---

## 🤝 Getting Help

1. **Setup issues** → [SETUP.md](SETUP.md)
2. **Usage questions** → [API.md](API.md)
3. **Development help** → [CONTRIBUTING.md](CONTRIBUTING.md)
4. **Architecture question** → [ARCHITECTURE.md](ARCHITECTURE.md)
5. **Deployment** → [DEPLOYMENT.md](DEPLOYMENT.md)

---

## ✨ Pro Tips

### Development Workflow

```bash
# Full setup
make dev

# Watch tests while coding
make watch-test &

# In another terminal, code away
# Tests rerun automatically when you save
```

### Benchmark Before/After

```bash
# Baseline
make benchmark > before.json

# Make changes...

# Compare
make benchmark > after.json
diff before.json after.json
```

### Interactive Testing

```bash
# Start server
make run &

# Use interactive CLI
python scripts/cli.py --interactive

# Type text, hear audio instantly
```

### Monitor in Real-Time

```bash
# Terminal 1: Server logs
bash scripts/run_server.sh

# Terminal 2: GPU usage
watch -n 1 nvidia-smi

# Terminal 3: Testing
python scripts/cli.py "Test text"
```

---

## 🎯 Common Task Combinations

### "I want to test my changes quickly"
```bash
make format && make lint && make test
```

### "I want to benchmark before deployment"
```bash
make run &
sleep 5
make benchmark-long
```

### "I want to generate demo audio"
```bash
make run &
python scripts/generate_samples.py
ffplay audio_samples/sample_01.wav
```

### "I want to deploy with Docker"
```bash
docker build -t qwen-markel-tts:latest .
docker-compose up -d
docker-compose logs -f
```

### "I want to check everything works"
```bash
make clean
make install
make test
python scripts/cli.py --check-health
```

---

## 📞 Quick Links

- **GitHub**: [your-org/qwen-markel-tts](https://github.com/your-org/qwen-markel-tts)
- **Issues**: [Open an issue](https://github.com/your-org/qwen-markel-tts/issues)
- **Discussions**: [Ask a question](https://github.com/your-org/qwen-markel-tts/discussions)
- **Model Card**: [Qwen/Qwen3-TTS](https://huggingface.co/Qwen/Qwen3-TTS-12Hz-0.6B-Base)

---

**Need more details?** Check the full documentation index above.

*Last updated: 15 May 2026*
