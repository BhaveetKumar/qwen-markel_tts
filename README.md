# qwen-markel-tts

RTX 5090 megakernel-backed **Qwen3-TTS** talker decoder wired into a **Pipecat** voice pipeline.

```
STT → LLM → QwenMegakernelTTS → audio out
```

---

## Architecture

```
text
  │
  ▼
TalkerDecoder.stream_tokens()   ← autoregressive loop via KernelDecoder
  │   (yields speech token IDs at ~1000 tok/s on RTX 5090)
  ▼
vocoder.tokens_to_pcm()         ← flow-matching vocoder (Qwen3-TTS)
  │   (yields 16-bit PCM @ 24 kHz, ~40 ms chunks)
  ▼
FastAPI /tts/stream             ← NDJSON chunked HTTP
  │
  ▼
QwenMegakernelTTSService        ← Pipecat TTSService adapter
  │
  ▼
TTSAudioRawFrame → audio transport
```

### Components

| Directory | Role |
|---|---|
| `src/megakernel/` | Kernel adapter — wraps AlpinDale's CUDA ops, provides `KernelDecoder` |
| `src/qwen3_tts/` | Weight loader, `TalkerDecoder`, vocoder stub |
| `src/server/` | FastAPI streaming server (`POST /tts/stream`, `GET /metrics`) |
| `src/pipecat_adapter/` | `QwenMegakernelTTSService` — drop-in Pipecat TTS node |
| `tests/` | pytest suite (runs on CPU, no model download required) |
| `scripts/` | build, run-server, benchmark, demo |

---

## Kernel Modification Notes

AlpinDale's kernel targets **Qwen3-0.6B** with hardcoded constants:

```c
constexpr int HIDDEN_SIZE       = 1024;
constexpr int INTERMEDIATE_SIZE = 3072;
constexpr int NUM_Q_HEADS       = 16;
constexpr int NUM_KV_HEADS      = 8;
constexpr int NUM_LAYERS        = 28; // (loop bound from Python)
```

The **Qwen3-TTS talker decoder** uses a larger backbone (≈7B-class):

| Param | 0.6B kernel | Talker decoder |
|---|---|---|
| `hidden_size` | 1024 | **4096** |
| `intermediate_size` | 3072 | **22016** |
| `num_q_heads` | 16 | **32** |
| `num_kv_heads` | 8 | 8 |
| `num_layers` | 28 | **32** |

### Changes required in `kernel.cu`

Replace the `constexpr` literals with macro-overridable defines so the
`build.py` flag injection in `src/megakernel/adapter.py` takes effect:

```c
// Before
constexpr int HIDDEN_SIZE = 1024;

// After
#ifndef LDG_HIDDEN_SIZE
#define LDG_HIDDEN_SIZE 1024
#endif
constexpr int HIDDEN_SIZE = LDG_HIDDEN_SIZE;
```

Apply the same pattern for `INTERMEDIATE_SIZE`, `NUM_Q_HEADS`, `NUM_KV_HEADS`.

Scratch buffer sizes (`_q`, `_k`, `_v`, `_attn_out`, `_mlp_inter`) are
already computed from these constants in `model.py` so Python-side
allocations adjust automatically.

**Thread/block tuning for the 7B talker:** The 0.6B kernel uses
128 blocks × 512 threads (65 536 threads). For the larger model, weight
matrices are 4× wider; the same occupancy target suggests
`LDG_NUM_BLOCKS=128, LDG_BLOCK_SIZE=512` remain valid since the RTX 5090
has 170 SMs each capable of 2048 threads — no change needed.

**Expected performance at 7B scale:** ~250–300 tok/s (memory-bandwidth
bound; 7B model weights ≈ 14 GB BF16 vs 1.2 GB for 0.6B). At 25 Hz speech
tokenization that is RTF ≈ 0.08–0.10, comfortably under the 0.15 target.

---

## Prerequisites

- NVIDIA RTX 5090 (sm_120 / Blackwell), CUDA 12.x
- Python 3.11+
- All sub-repos cloned alongside this folder:
  ```

## Setup Command Matrix (Where To Execute)

1. Create/open three terminals.

2. Terminal A (workspace root):
```bash
cd /Users/fc20136/Desktop/poc
```

3. Terminal B (project root):
```bash
cd /Users/fc20136/Desktop/poc/qwen-markel_tts
```

4. Terminal C (project root):
```bash
cd /Users/fc20136/Desktop/poc/qwen-markel_tts
```

5. Install runtime + dev dependencies (Terminal B):
```bash
python3 -m pip install -e ".[dev]"
```

6. Validate local tests before GPU run (Terminal B):
```bash
pytest tests/ -v
```

7. Build CUDA extension for megakernel (Terminal B):
```bash
bash scripts/build.sh
```

8. Start streaming TTS server (Terminal B):
```bash
bash scripts/run_server.sh
```

9. Run benchmark (Terminal C):
```bash
python scripts/benchmark.py --runs 10
```

10. Run Pipecat pipeline demo (Terminal C):
```bash
python scripts/demo.py \
  --tts-url http://localhost:8000 \
  --deepgram-key "$DEEPGRAM_API_KEY" \
  --openai-key "$OPENAI_API_KEY"
```
  poc/
    qwen_megakernel/    ← AlpinDale's kernel
    Qwen3-TTS/          ← HuggingFace model code
    pipecat/            ← Pipecat framework
    qwen-markel_tts/    ← this repo
  ```

---

## Quick Start

### 1. Build the CUDA extension

```bash
bash scripts/build.sh
```

This sets the dimension override env-vars for the 7B talker, then calls
`qwen_megakernel.build.get_extension()` which triggers JIT compilation via
`torch.utils.cpp_extension.load`. Compilation takes ~2–5 minutes on first run.

### 2. Start the inference server

```bash
bash scripts/run_server.sh
```

The server loads Qwen3-TTS weights from HuggingFace on startup (~30 s on
first run with network access). Check `GET /health` to confirm:

```bash
curl http://localhost:8000/health
# {"status":"ok","model_loaded":true}
```

### 3. Test a TTS request

```bash
curl -s -X POST http://localhost:8000/tts/stream \
     -H "Content-Type: application/json" \
     -d '{"text": "Hello, this is a streaming TTS test."}' \
   | python3 -c "
import sys, json, base64, wave, struct, io
samples = b''
for line in sys.stdin:
    m = json.loads(line)
    if 'pcm' in m:
        samples += base64.b64decode(m['pcm'])
with open('/tmp/out.wav', 'wb') as f:
    with wave.open(f, 'w') as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(24000)
        wf.writeframes(samples)
print('Wrote /tmp/out.wav')
"
```

### 4. Benchmark

```bash
python scripts/benchmark.py --runs 10
```

Expected output on RTX 5090:

```
Run  1: elapsed=310ms  TTFC=41ms  RTF=0.10  tok/s=273
...
=== Summary ===
  TTFC (ms)            mean=43.2  min=40.1  max=52.4
  RTF                  mean=0.11  min=0.09  max=0.13
  tok/s                mean=268.0 min=255.0 max=281.0

Targets:
  TTFC < 60 ms  → PASS (43.2ms)
  RTF  < 0.15   → PASS (0.11)
```

### 5. Run the Pipecat voice demo

```bash
python scripts/demo.py \
    --tts-url http://localhost:8000 \
    --deepgram-key $DEEPGRAM_API_KEY \
    --openai-key $OPENAI_API_KEY
```

---

## Running Tests (no GPU required)

```bash
pip install -e ".[dev]"
cd qwen-markel_tts
pytest tests/ -v
```

All tests use stub weights and a deterministic HF-model mock — no model
downloads, no CUDA hardware required. They verify:

- `KernelDecoder` fallback path (CPU)
- `TalkerDecoder` streaming generators
- Vocoder stub (sine wave)
- FastAPI server routes (health, metrics, streaming with stub decoder)
- Pipecat adapter HTTP streaming and error handling

---

## Pipecat as UI: Can We Use It?

Yes, with one caveat:

- Pipecat is primarily an orchestration/runtime framework, not a standalone visual UI framework.
- In this project, Pipecat acts as the real-time voice runtime and transport layer.
- For user-facing UI, pair Pipecat with a transport-backed client (for example WebRTC/Daily transport and a browser client).

### Integration pattern used here

1. Pipecat receives STT frames.
2. LLM generates assistant text.
3. QwenMegakernelTTSService calls POST /tts/stream.
4. Adapter converts streaming chunks into TTSAudioRawFrame.
5. Pipecat transport plays audio to the user.

### Minimal integration checklist

1. Keep TTS backend running at http://localhost:8000.
2. Instantiate QwenMegakernelTTSService in your Pipecat pipeline.
3. Use a Pipecat transport (local audio for dev, Daily/WebRTC for web UX).
4. Ensure sample rates are consistent across transport and TTS frames.

---

## Machine Requirements

Minimum (recommended for target metrics):

- GPU: RTX 5090 (Blackwell, sm_120)
- VRAM: 32 GB+
- CPU: 16 vCPU+
- RAM: 64 GB+
- Disk: 100 GB+ NVMe (model cache + build artifacts)
- OS: Ubuntu 22.04+
- NVIDIA driver: recent branch supporting Blackwell
- CUDA: 12.x
- Python: 3.11+

Notes:

- Talker decoder bfloat16 weights are large; avoid small VRAM instances.
- Fast local NVMe significantly improves first model load and cache reuse.

---

## Vast.ai Setup Guide

1. In Vast.ai search filters:
  - GPU: RTX 5090
  - CUDA version support: 12.x
  - Disk: >= 100 GB
  - Internet: enabled

2. Select template/image:
  - Base: Ubuntu + NVIDIA CUDA runtime image
  - Ensure Python 3.11 is available (or install it)

3. On instance startup:
```bash
sudo apt update
sudo apt install -y git python3 python3-pip python3-venv build-essential
```

4. Clone repositories under same parent folder:
```bash
mkdir -p ~/poc && cd ~/poc
git clone https://github.com/AlpinDale/qwen_megakernel.git
git clone https://github.com/QwenLM/Qwen3-TTS.git
git clone https://github.com/pipecat-ai/pipecat.git
# clone your fork/copy of this repo
git clone https://github.com/BhaveetKumar/qwen-markel_tts.git qwen-markel_tts
```

5. Build and run:
```bash
cd ~/poc/qwen-markel_tts
python3 -m pip install -e ".[dev]"
bash scripts/build.sh
bash scripts/run_server.sh
```

6. Validate:
```bash
curl http://localhost:8000/health
python scripts/benchmark.py --runs 10
```

7. Optional: run Pipecat demo from a second shell:
```bash
cd ~/poc/qwen-markel_tts
python scripts/demo.py --tts-url http://localhost:8000 --deepgram-key "$DEEPGRAM_API_KEY" --openai-key "$OPENAI_API_KEY"
```

---

## API Reference

### `POST /tts/stream`

```json
{ "text": "hello world", "voice": "default" }
```

Response (NDJSON stream):
```
{"chunk_id": 0, "pcm": "<base64 16-bit 24kHz PCM>"}
{"chunk_id": 1, "pcm": "..."}
...
{"event": "end", "metrics": {"TTFC_ms": 42.1, "RTF": 0.11, "decode_tokens_per_sec": 271, "avg_latency_ms": 310}}
```

### `GET /metrics`

```json
{
  "decode_tokens_per_sec": 271.0,
  "TTFC_ms": 42.1,
  "RTF": 0.11,
  "avg_latency_ms": 310.0
}
```

### `GET /health`

```json
{ "status": "ok", "model_loaded": true }
```

---

## Performance Targets

| Metric | Target | Expected (RTX 5090) |
|---|---|---|
| TTFC | < 60 ms | ~40–50 ms |
| RTF | < 0.15 | ~0.09–0.12 |
| Decode tok/s | — | ~250–280 |
| Audio streaming | chunk-by-chunk | ✓ (1 token per chunk) |

---

## Limitations & Known Issues

1. **Vocoder stub on non-GPU systems.** Without the full Qwen3-TTS model
   loaded, `tokens_to_pcm()` returns a sine-wave placeholder. Call
   `vocoder.set_vocoder(fn)` after server startup to wire in the real vocoder.

2. **Kernel.cu source modification required.** The upstream kernel has
   hardcoded 0.6B constants. The `LDG_HIDDEN_SIZE` / `LDG_INTERMEDIATE_SIZE`
   / `LDG_NUM_Q_HEADS` env-var injection in `adapter.py` only works after the
   corresponding `#ifdef` guards are added to `kernel.cu` (see section above).

3. **No quantization.** Weights remain bfloat16 throughout, matching the
   kernel's design. Memory footprint for the 7B talker: ~14 GB BF16.
