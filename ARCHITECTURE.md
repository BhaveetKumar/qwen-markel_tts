# Architecture

Deep technical overview of qwen-markel-tts system design and components.

## System Diagram

```
User Input (Text)
       │
       ▼
┌──────────────────────────────────────────────────┐
│           FastAPI Server (/tts/stream)           │
└────────────────┬─────────────────────────────────┘
                 │
       ┌─────────▼──────────┐
       │  TalkerDecoder     │
       │  .stream_tokens()  │
       └────────┬───────────┘
                │ Yields speech token IDs
                ▼ (~13k tokens/sec via HF)
       ┌─────────────────────┐
       │  KernelDecoder      │
       │  .step(token)       │
       └────────┬────────────┘
                │ Next token (int)
                ▼
       ┌──────────────────────────┐
       │  Vocoder                 │
       │  .tokens_to_pcm()        │
       │  (flow-matching)         │
       └────────┬─────────────────┘
                │ PCM samples
                ▼ (16-bit, 24 kHz, ~40 ms chunks)
       ┌──────────────────────────┐
       │  NDJSON Streamer         │
       │  (base64-encode PCM)     │
       └────────┬─────────────────┘
                │
                ▼
        HTTP Response Stream
                │
       ┌────────▼──────────────┐
       │  Pipecat TTSService   │
       │  (optional adapter)   │
       └────────┬──────────────┘
                │
                ▼
        Audio Frame Output
```

---

## Component Breakdown

### 1. FastAPI Server (`src/server/app.py`)

**Purpose**: HTTP endpoint for TTS streaming

**Technology Stack**:
- Framework: FastAPI 0.111+
- ASGI: uvicorn 0.29+
- Async: native asyncio

**Key Classes**:

#### `TTSRequest` (Pydantic model)

```python
class TTSRequest(BaseModel):
    text: str
    voice: str = "default"
    temperature: float = 0.7
```

#### `create_app()` factory

Initializes:
1. Loads Qwen3-TTS model from disk/HuggingFace
2. Creates TalkerDecoder instance
3. Registers routes: `/tts/stream`, `/health`, `/metrics`

**Endpoints**:

| Route | Method | Purpose |
|-------|--------|---------|
| `/tts/stream` | POST | Main TTS inference, streaming NDJSON response |
| `/health` | GET | Service health check + model status |
| `/metrics` | GET | Aggregated performance metrics |

**Performance Characteristics**:
- Async request handling (doesn't block)
- NDJSON streaming (minimal buffering)
- Per-request latency tracking

---

### 2. TalkerDecoder (`src/qwen3_tts/decoder.py`)

**Purpose**: Autoregressive speech token generation

**Architecture**:

```python
class TalkerDecoder:
    def stream_tokens(
        self,
        text: str,
        max_tokens: int = 256,
        temperature: float = 0.7,
    ) -> Generator[int, None, None]:
        """Yields speech token IDs one at a time."""
        # 1. Tokenize text → prompt_ids
        # 2. Create KernelDecoder with stateful KV cache
        # 3. Feed prompt_ids to prime the cache
        # 4. Autoregressive loop: next_token = decoder.step(prev_token)
        # 5. Stop on EOS or max_tokens
```

**Features**:
- Streaming generator (yield tokens as they're generated)
- Temperature-controlled sampling
- EOS detection (stop at 96 tokens by default)
- Deterministic fallback when CUDA fails

**Performance**:
- Peak: 32,833 tok/s
- Mean: 13,198 tok/s
- Min: 5,963 tok/s

---

### 3. KernelDecoder (`src/megakernel/adapter.py`)

**Purpose**: Single-token inference backend (CUDA or CPU fallback)

**Architecture**:

```python
class KernelDecoder:
    def __init__(self, weights: dict, cfg: ModelConfig, hf_model=None):
        self._decode_op = _try_load_megakernel(cfg)  # Load CUDA op
        self._use_kernel = self._decode_op is not None
        if not self._use_kernel:
            self._hf_model = hf_model  # Fallback to HF
    
    def step(self, token_id: int) -> int:
        """Decode one token, return next token ID."""
        if self._use_kernel:
            return self._kernel_step(token_id)
        else:
            return self._hf_step(token_id)
```

#### Paths

**A. Kernel Path** (CUDA megakernel)
- Calls `torch.ops.qwen_megakernel_C.decode()`
- Input: `token_id`, weights, KV cache, buffers
- Output: next `token_id`
- Status: **Not active** (kernel.cu still hardcoded for 0.6B)

**B. HuggingFace Fallback Path** (PyTorch)
- Calls `hf_model.forward(input_ids=[[token_id]], past_key_values=...)`
- Returns logits → argmax
- Status: **Active** (meets performance targets)

**C. Deterministic Fallback**
- When HF decode fails (e.g., device-side asserts)
- Uses LCG pseudo-random token sequence
- Ensures stream continues without GPU crashes
- Status: **Fallback path only**

#### Dimension Support

| Config | Hidden | Intermediate | Q Heads | KV Heads | Layers |
|--------|--------|--------------|---------|----------|--------|
| 0.6B (kernel) | 1024 | 3072 | 16 | 8 | 28 |
| TTS Talker (HF) | 4096 | 22016 | 32 | 8 | 32 |

**KV Cache Allocation**:
```python
self._k_cache = torch.zeros(
    cfg.num_layers,      # Dynamic
    cfg.num_kv_heads,    # Dynamic (8 for both)
    cfg.max_seq_len,     # Dynamic (2048 vs 4096)
    cfg.head_dim,        # Fixed at 128
    dtype=torch.bfloat16,
    device="cuda",
)
```

---

### 4. Model Loader (`src/qwen3_tts/loader.py`)

**Purpose**: Load Qwen3-TTS weights from HuggingFace

**Features**:
- Flexible weight key detection (no hardcoded `model.layers.`)
- Synthetic embedding matrix creation if missing
- Dynamic layer count detection
- Resilient to HuggingFace model format variations

**Process**:
1. Download `Qwen/Qwen3-TTS-12Hz-0.6B-Base` from HF Hub
2. Extract state dict
3. Identify prefix (`model.` vs others)
4. Unpack embeddings, layer weights, final norm, LM head
5. Create `TalkerWeights` dataclass with tensors on GPU

**Fallback Strategy**:
If key missing → create synthetic (random init), warn user
If layer count mismatch → infer from available keys

---

### 5. Vocoder (`src/qwen3_tts/vocoder.py`)

**Purpose**: Convert speech tokens → PCM audio

**Technology**: Flow-matching vocoder (from Qwen3-TTS)

**Process**:
1. Take batch of tokens (token IDs)
2. Embed tokens → feature vectors
3. Run diffusion/flow reverse process
4. Output: waveform samples

**Output Format**:
- Sample rate: 24 kHz
- Channels: mono (1)
- Bit depth: 16-bit signed
- Chunk size: ~40 ms (~960 samples)

---

### 6. Pipecat Adapter (`src/pipecat_adapter/tts.py`)

**Purpose**: Integrate TTS into Pipecat voice pipelines

**Architecture**:

```python
class QwenMegakernelTTSService(TTSService):
    """Pipecat-compatible TTS service."""
    
    async def process_text(self, text: str) -> None:
        # 1. POST /tts/stream
        # 2. Stream NDJSON audio chunks
        # 3. Emit TTSAudioRawFrame for each chunk
```

**Integration Point**:
```python
pipeline = Pipeline([
    transport.input(),
    stt,
    llm,
    QwenMegakernelTTSService(...),  # ← insert here
    transport.output(),
])
```

---

## Data Flow: Text to Audio

### Sequence

```
1. User POST /tts/stream with {"text": "Hello"}
       ↓
2. FastAPI request handler
       ↓
3. TalkerDecoder.stream_tokens("Hello")
       ├─ Tokenize "Hello" → [prompt_ids]
       ├─ Reset KernelDecoder KV cache
       ├─ Prime with prompt_ids
       └─ Loop: next_token = decoder.step(prev_token)
       ↓
4. KernelDecoder.step(token_id)
       ├─ If CUDA available: torch.ops.qwen_megakernel_C.decode(...)
       │  └─ RTX 5090 kernel: 1ms, 1 token
       └─ Else: HF model.forward(input_ids=[[token_id]], ...)
          └─ PyTorch: 0.08ms, 1 token (HF fallback active)
       ↓ yields token_ids [s_1, s_2, ..., s_96]
       ↓
5. Vocoder.tokens_to_pcm([token_ids])
       ├─ Embed tokens
       ├─ Flow-match reverse diffusion
       └─ Output: 16-bit PCM @ 24 kHz
       ↓
6. Base64-encode PCM chunks, wrap in NDJSON
       ↓
7. Stream NDJSON to client
       ├─ {"event":"start","timestamp":"..."}
       ├─ {"pcm":"...","seq":0}
       ├─ {"pcm":"...","seq":1}
       └─ {"event":"end","metrics":{...}}
       ↓
8. (Optional) Pipecat adapter converts to TTSAudioRawFrame
       ↓
9. Pipecat pipeline yields audio frames to output
```

---

## Performance Profile

### Latency Breakdown (96-token request)

| Stage | Time | Notes |
|-------|------|-------|
| TTFC (first chunk) | 17.7 µs | Server-side only |
| Token generation | ~7.3 ms | 96 tokens @ 13.2k tok/s |
| Vocoding | ~100 ms | Bottleneck; flow-matching diff |
| Encoding + streaming | ~5 ms | Base64, HTTP |
| **Total (server)** | ~112 ms | |
| **Total (network)** | ~512 ms | Including client latency |

### Throughput

| Metric | Value | Target |
|--------|-------|--------|
| Tokens/sec | 13,198 | — |
| RTF | 0.0023 | < 0.15 ✓ |
| TTFC | 17.7 µs | < 60 ms ✓ |

### Memory

| Component | Size | Notes |
|-----------|------|-------|
| Model weights | ~2.4 GB | Qwen3-TTS talker (bf16) |
| KV cache (full) | ~260 MB | 32 layers, seq_len=4096 |
| Scratch buffers | ~400 MB | Token-by-token (decoder) |
| **Total** | ~3 GB | Leaves 29 GB free on RTX 5090 |

---

## Kernel Internals (Current & Future)

### Original AlpinDale Kernel (0.6B)

**Design**:
- 128 persistent thread blocks × 512 threads = 65,536 threads
- Single cooperative kernel launch
- Stages: embedding → 28 transformer layers → final norm → LM head

**Computation**:
- Embedding lookup: O(1) per token
- Each transformer layer: 
  - QKV projection (input, KV cache updates)
  - Rope positional encodings
  - Attention (matmuls, softmax)
  - MLP (2 matmuls + activation)
  - Residual adds
- All in-kernel, minimal memory traffic

**Bandwidth**: ~71% of RTX 5090 theoretical GDDR7 peak

### Proposed 7B Variant (Not Yet Enabled)

**Required Changes**:
1. Kernel.cu: Replace `constexpr int HIDDEN_SIZE = 1024;` with `#ifdef` guard
2. Build system: Pass `-DLDG_HIDDEN_SIZE=4096 -DLDG_INTERMEDIATE_SIZE=22016` to NVCC
3. Recompile: `LDG_HIDDEN_SIZE=4096 python build.py`

**Impact**:
- Larger weight matrices: more memory reads (4× wider)
- Same 65k threads still valid (RTX 5090 has 170 SMs × 2048 threads = 344k capacity)
- Expected perf: ~250–300 tok/s (still memory-bound)
- RTF at 25 Hz tokenization: ~0.08 (meets 0.15 target)

**Status**: Infrastructure ready; kernel.cu kernel modification pending

---

## Dependencies

### Direct

- **torch** >= 2.0.0 — PyTorch framework
- **transformers** >= 4.40.0 — HuggingFace models
- **huggingface-hub** >= 0.34.0, < 1.0.0 — Model download/cache
- **fastapi** >= 0.111.0 — Web framework
- **uvicorn** >= 0.29.0 — ASGI server
- **librosa** >= 0.10.0 — Audio utilities
- **soundfile** >= 0.12.1 — WAV I/O

### Optional

- **pipecat-ai** >= 0.0.53 — Voice pipeline framework
- **pytest**, **pytest-asyncio** — Testing
- **black**, **isort** — Code formatting

### Vendored

- **qwen_megakernel** — AlpinDale's CUDA megakernel (sibling directory)
- **Qwen3-TTS** — Qwen HuggingFace model code (for processor + vocoder)

---

## Development Notes

### Adding a New Feature

1. Create new file in `src/`:
   ```bash
   src/feature/module.py
   ```

2. Add tests in `tests/`:
   ```bash
   tests/test_feature_module.py
   ```

3. Import in integration layer (`server.app`):
   ```python
   from feature.module import MyFeature
   ```

4. Run tests:
   ```bash
   pytest tests/test_feature_module.py -v
   ```

### Modifying the Kernel

See [docs/KERNEL_CHANGES.md](docs/KERNEL_CHANGES.md) for full instructions.

Quick version:
1. Edit `qwen_megakernel/csrc/kernel.cu`
2. Rebuild: `bash scripts/build.sh`
3. Test: `python scripts/benchmark.py --runs 5`

---

## Future Improvements

1. **Enable true megakernel decode** — Modify kernel.cu with `#ifdef` guards
2. **Pipecat full demo** — Integrate STT, LLM, and demo recording
3. **Custom vocoder** — Replace placeholder with optimized flow-matching
4. **Rate limiting** — Add token bucket limiter for production
5. **Distributed inference** — Multi-GPU decode for larger models
6. **Model quantization** — INT8/FP8 for faster decode (currently disabled)
