# Deployment Guide

Instructions for deploying qwen-markel-tts to production (cloud, on-premises, etc.).

## Quick Deploy Checklist

- [ ] Hardware: NVIDIA RTX 5090 (or equivalent sm_120 GPU)
- [ ] CUDA: Version 12.x installed and in PATH
- [ ] Python: 3.11+ installed
- [ ] Internet: For initial model download (~2 GB)
- [ ] Disk: ~5 GB free (models, CUDA cache)
- [ ] Networking: Port 8000 (or custom) accessible to clients

---

## Local Development

### Prerequisites

```bash
# Check GPU
nvidia-smi

# Check CUDA version
nvcc --version

# Check Python
python3 --version  # must be 3.11+
```

### Installation

```bash
cd /path/to/qwen-markel_tts
python3.11 -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
pytest tests/ -v
```

### Running

```bash
# Terminal 1: Start server
bash scripts/run_server.sh

# Terminal 2: Test
curl http://localhost:8000/health

# Terminal 3: Benchmark
python scripts/benchmark.py --runs 10
```

---

## Remote Deployment (Vast.ai / Cloud GPU)

### 1. Rent GPU Instance

**Example: Vast.ai RTX 5090**

1. Go to [vast.ai](https://vast.ai)
2. Filter: RTX 5090, sm_120 (Blackwell)
3. Select instance with:
   - 32+ GB VRAM
   - CUDA 12.x pre-installed
   - Ubuntu 22.04 or later
   - ≥ 100 GB disk space
4. Click "Rent"
5. Get instance IP and SSH key

### 2. SSH Setup

```bash
# On your local machine
ssh-keygen -f ~/.ssh/vastai_key -N ""

# Copy public key to Vast.ai dashboard
# SSH into instance
ssh -i ~/.ssh/vastai_key root@<instance_ip>
```

### 3. Initial Setup on Remote

```bash
# Update system
apt-get update && apt-get upgrade -y
apt-get install -y git curl wget ca-certificates

# Check GPU
nvidia-smi

# Install Python (if needed)
apt-get install -y python3.11 python3.11-venv python3.11-dev
```

### 4. Clone and Deploy

```bash
# Create workspace
mkdir -p /root/workspace
cd /root/workspace

# Clone project
git clone https://github.com/your-org/qwen-markel_tts.git
cd qwen-markel_tts

# Set up venv
python3.11 -m venv venv
source venv/bin/activate

# Install
pip install -e ".[dev]"

# Test
pytest tests/ -v

# Start server
bash scripts/run_server.sh &
```

### 5. Set HuggingFace Token

If download is slow or you hit rate limits:

```bash
# Option A: Environment variable
export HF_TOKEN=$(cat ~/.hf_token)

# Option B: Create .env file
echo "HF_TOKEN=$(cat ~/.hf_token)" > .env
source .env
```

### 6. Test Server

```bash
# From another SSH session
curl http://localhost:8000/health
```

### 7. Expose via Cloudflare Tunnel (Optional Public Access)

Install Cloudflare Tunnel:

```bash
curl -L --output cloudflared.tgz https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.tgz
tar -xzf cloudflared.tgz
sudo mv cloudflared /usr/local/bin/

# Authenticate
cloudflared tunnel login
```

Create tunnel:

```bash
cloudflared tunnel create tts-server
cloudflared tunnel route dns tts-server tts.yourdomain.com
```

Create config (`~/.cloudflared/config.yml`):

```yaml
tunnel: tts-server
credentials-file: ~/.cloudflared/<tunnel-id>.json

ingress:
  - hostname: tts.yourdomain.com
    service: http://localhost:8000
  - service: http_status:404
```

Start tunnel:

```bash
cloudflared tunnel run tts-server
```

Access publicly:

```bash
curl https://tts.yourdomain.com/health
```

---

## Docker Deployment

### Dockerfile

```dockerfile
FROM nvidia/cuda:12.4.1-runtime-ubuntu22.04

WORKDIR /app

# Install Python 3.11
RUN apt-get update && apt-get install -y \
    python3.11 python3.11-venv python3.11-dev \
    git curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Copy project
COPY . /app

# Install dependencies
RUN python3.11 -m venv venv && \
    . venv/bin/activate && \
    pip install -e ".[dev]"

# HuggingFace cache
ENV HF_HOME=/cache/huggingface
RUN mkdir -p /cache/huggingface

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python3.11 -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

# Run server
ENTRYPOINT ["bash", "scripts/run_server.sh"]
```

### Build and Run

```bash
docker build -t qwen-markel-tts:latest .

docker run --gpus all \
    -p 8000:8000 \
    -v /cache:/cache \
    -e HF_TOKEN=$HF_TOKEN \
    qwen-markel-tts:latest
```

---

## Kubernetes Deployment

### values.yaml

```yaml
replicaCount: 1

image:
  repository: your-registry/qwen-markel-tts
  tag: latest

resources:
  limits:
    nvidia.com/gpu: 1  # RTX 5090

service:
  type: LoadBalancer
  port: 8000

env:
  - name: HF_TOKEN
    valueFrom:
      secretKeyRef:
        name: hf-token
        key: token
  - name: PORT
    value: "8000"
```

Deploy:

```bash
helm install qwen-markel-tts ./helm -f values.yaml

# Monitor
kubectl get pods
kubectl logs -f deployment/qwen-markel-tts
```

---

## Load Testing

### Single-Machine Benchmark

```bash
python scripts/benchmark.py --runs 100 --text "Your test text here."
```

Expected:
- Mean tok/s: 13,000+
- TTFC: < 20 ms
- RTF: < 0.003

### Concurrent Request Test

```bash
# Use Apache Bench
ab -n 100 -c 10 -p request.json -T application/json http://localhost:8000/tts/stream

# Or use custom script
python3 << 'EOF'
import asyncio
import aiohttp
import json
import time

async def load_test(num_concurrent=10, num_requests=100):
    start = time.perf_counter()
    
    async def single_request():
        async with aiohttp.ClientSession() as session:
            async with session.post(
                'http://localhost:8000/tts/stream',
                json={'text': 'Hello, this is a test request.'}
            ) as resp:
                await resp.read()
    
    tasks = [single_request() for _ in range(num_concurrent)]
    for _ in range(num_requests // num_concurrent):
        await asyncio.gather(*tasks)
    
    elapsed = time.perf_counter() - start
    print(f"Completed {num_requests} requests in {elapsed:.2f}s")
    print(f"Throughput: {num_requests / elapsed:.1f} req/s")

asyncio.run(load_test(num_concurrent=10, num_requests=100))
EOF
```

---

## Monitoring and Observability

### Metrics Collection

Server exposes `GET /metrics`:

```bash
curl http://localhost:8000/metrics | jq
```

Response:

```json
{
  "total_requests": 42,
  "mean_ttfc_ms": 15.2,
  "mean_tok_s": 13145.7,
  "mean_rtf": 0.00231,
  "p95_ttfc_ms": 21.3
}
```

### Integration with Prometheus

Modify `src/server/app.py` to export metrics:

```python
from prometheus_client import Counter, Histogram

token_count = Counter('tts_tokens_total', 'Total tokens synthesized')
ttfc_histogram = Histogram('tts_ttfc_ms', 'Time to first chunk (ms)')
```

### Health Checks

Kubernetes/Docker health check:

```bash
curl -f http://localhost:8000/health || exit 1
```

---

## Performance Tuning

### GPU Memory Optimization

If OOM occurs (unlikely on RTX 5090 with 32 GB):

```python
# In KernelDecoder.__init__
torch.cuda.empty_cache()

# Reduce KV cache size (tradeoff: limits context)
cfg.max_seq_len = 2048  # from 4096
```

### CPU Optimization

Maximize throughput:

```bash
export CUDA_LAUNCH_BLOCKING=0  # Enable async kernel launches
export CUDA_DEVICE_ORDER=PCI_BUS_ID
export OMP_NUM_THREADS=16
bash scripts/run_server.sh
```

### Network Optimization

For remote deployments:

1. **Compression**: Add gzip middleware
   ```python
   from fastapi.middleware.gzip import GZIPMiddleware
   app.add_middleware(GZIPMiddleware, minimum_size=1000)
   ```

2. **Caching**: Enable HTTP caching headers
   ```python
   @app.get("/health", response_class=JSONResponse)
   async def health():
       return {"status": "ok"}, headers={"Cache-Control": "max-age=10"}
   ```

3. **CDN**: Use Cloudflare Workers to cache audio responses

---

## Troubleshooting

### "Out of Memory" Error

```
RuntimeError: CUDA out of memory. Tried to allocate X.XX GiB
```

**Fix**:
1. Restart server: `pkill -f run_server.sh`
2. Clear cache: `nvidia-smi | grep python | awk '{print $5}' | xargs kill`
3. Reduce batch size (if applicable)

### "Model Not Loading"

```
OSError: Can't find 'Qwen/Qwen3-TTS-12Hz-0.6B-Base' in Hugging Face Hub
```

**Fix**:
1. Check HF_TOKEN: `echo $HF_TOKEN`
2. Test connectivity: `curl https://huggingface.co`
3. Set cache directory: `export HF_HOME=/path/to/cache`

### Server Hanging

```
curl: (28) Operation timed out after X seconds
```

**Fix**:
1. Check GPU: `nvidia-smi` (if 100% util but no output, deadlock)
2. Restart server: `pkill -9 uvicorn`
3. Check logs: `journalctl -u qwen-tts.service` (if systemd)

---

## Production Checklist

Before going live:

- [ ] SSL/TLS enabled (HTTPS)
- [ ] API authentication (API keys / OAuth)
- [ ] Rate limiting (token bucket)
- [ ] Request logging + monitoring
- [ ] Error tracking (Sentry, etc.)
- [ ] Automated backups (if needed)
- [ ] Health checks scheduled
- [ ] Incident response plan documented
- [ ] Performance SLA defined
- [ ] Cost monitoring enabled

---

## Cost Estimation

**Vast.ai RTX 5090** (~$1.50–2.00/hour):
- Monthly (24/7): ~$1,000–1,500
- Annual: ~$12,000–18,000

**Per-request cost** (at 100 req/min):
- ~$0.01–0.02 per request

See [Vast.ai pricing](https://vast.ai/pricing) for current rates.
