# Implementation Audit (Compared Against Assignment Context)

Date: 2026-05-15
Source of requirements: ../../context.md (left unchanged as requested)
Repository audited: qwen-markel_tts

## 1) What Changed

Recent implementation/fix commits (newest first):
- a9c3111 Bypass HF decode after first CUDA/assert failure
- 8f08baa Handle HF talker decode signature mismatch with deterministic fallback
- 80af966 Always attach loaded HF model for non-kernel decode path
- e3fa87d Auto-fix huggingface-hub compatibility at server startup
- b960c06 Set HF cache/token env defaults for container runtime
- fc22a0b Fix layer prefix construction for Qwen3-TTS state dict
- 2f284c2 Handle Qwen3-TTS models without embed_tokens or final_norm
- 214487e Make weight extraction more flexible for different model structures

Functional components now present:
- Streaming server: src/server/app.py
- Megakernel adapter and fallback decode path: src/megakernel/adapter.py
- Qwen3-TTS loader/decoder/vocoder modules: src/qwen3_tts/
- Pipecat TTS adapter: src/pipecat_adapter/tts.py
- Benchmark script and benchmark artifact: scripts/benchmark.py, docs/benchmark_30_requests.json

## 2) What We Achieved

Observed from live endpoint runs:
- /tts/stream returns chunked NDJSON with chunk_id + base64 PCM and an end metrics event.
- /health previously reported model_loaded=true in deployed environment.
- Throughput exceeded 1000 tok/s target across 30-request benchmark.

30-run summary (from docs/benchmark_30_requests.json):
- decode_tokens_per_sec: mean=13198.40, min=5963.16, max=32833.45
- RTF: mean=0.002312, min=0.000811, max=0.004300
- avg_latency_ms: mean=12.94, min=7.97, max=23.63 (server metric)

Note on TTFC:
- Server-reported TTFC_ms in end-metrics is very low (~0.017-0.027 ms), likely instrumentation scope issue.
- Client-observed first-byte timing in benchmark wrapper was much higher over tunnel.
- Recommendation: keep both server and client TTFC metrics in final report.

## 3) Requirement Comparison vs context.md

### Goal-level requirements

1. Megakernel running as decode backend for Qwen3-TTS talker decoder.
Status: PARTIAL
Evidence: megakernel adapter exists; runtime currently can fall back to deterministic/HF path.
Gap: No confirmed production run proving true CUDA megakernel decode is actively serving all streamed tokens.

2. Streaming real-time speech synthesis into Pipecat voice pipeline.
Status: PARTIAL
Evidence: Pipecat service adapter implemented in src/pipecat_adapter/tts.py.
Gap: Full STT -> LLM -> TTS -> transport pipeline demo evidence not captured in this repo audit.

### Performance targets from context.md

1. TTFC < 60 ms
Status: INCONCLUSIVE
Evidence: server metric shows very low values; client-observed first-byte timings are higher over tunnel.
Gap: Need clear, trusted TTFC methodology (local and remote) and p50/p95 values.

2. RTF < 0.15
Status: PASS
Evidence: 30-run mean RTF 0.002312 (min 0.000811, max 0.004300).

3. Streaming to Pipecat without full buffering
Status: PARTIAL/PASS FOR ADAPTER
Evidence: adapter yields frames incrementally and server yields chunks incrementally.
Gap: end-to-end Pipecat session capture still needed as proof artifact.

### Deliverables from context.md

1. Working repo with build instructions
Status: MOSTLY PASS
Evidence: project structure and scripts present.
Gap: README still includes assumptions that should be validated against actual runtime mode.

2. README with architecture decisions and kernel modifications
Status: PASS
Evidence: README documents architecture and kernel adaptation intent.

3. Performance numbers (decode tok/s, TTFC, RTF, end-to-end latency)
Status: PARTIAL
Evidence: tok/s and RTF logged; latency logged.
Gap: TTFC methodology mismatch needs cleanup; end-to-end voice round-trip numbers not yet finalized.

4. Demo recording of voice agent
Status: MISSING
Gap: No recording artifact in repo.

## 4) 30 Request Logs (Server Metrics)

Source: docs/benchmark_30_requests.json

- run 01: tok/s=10524.56, TTFC_ms=0.017736, RTF=0.002435, latency_ms=9.021291
- run 02: tok/s=19048.92, TTFC_ms=0.023486, RTF=0.001413, latency_ms=16.310630
- run 03: tok/s=6789.93, TTFC_ms=0.025959, RTF=0.003771, latency_ms=19.354973
- run 04: tok/s=10267.59, TTFC_ms=0.017236, RTF=0.002496, latency_ms=9.290835
- run 05: tok/s=10533.28, TTFC_ms=0.017416, RTF=0.002443, latency_ms=9.198497
- run 06: tok/s=7959.92, TTFC_ms=0.026049, RTF=0.003253, latency_ms=16.554316
- run 07: tok/s=20568.08, TTFC_ms=0.016864, RTF=0.001263, latency_ms=10.610688
- run 08: tok/s=17468.85, TTFC_ms=0.018357, RTF=0.001499, latency_ms=11.836889
- run 09: tok/s=10031.67, TTFC_ms=0.025018, RTF=0.002576, latency_ms=13.139056
- run 10: tok/s=13480.97, TTFC_ms=0.017927, RTF=0.001917, latency_ms=12.324292
- run 11: tok/s=16468.71, TTFC_ms=0.017156, RTF=0.001569, latency_ms=11.857921
- run 12: tok/s=20018.50, TTFC_ms=0.018458, RTF=0.001327, latency_ms=11.740425
- run 13: tok/s=16682.78, TTFC_ms=0.018428, RTF=0.001554, latency_ms=11.617140
- run 14: tok/s=13687.70, TTFC_ms=0.017566, RTF=0.001913, latency_ms=18.150494
- run 15: tok/s=8652.94, TTFC_ms=0.023426, RTF=0.003003, latency_ms=23.629103
- run 16: tok/s=24706.87, TTFC_ms=0.017786, RTF=0.001063, latency_ms=23.074199
- run 17: tok/s=6734.59, TTFC_ms=0.025649, RTF=0.003847, latency_ms=18.052115
- run 18: tok/s=15900.04, TTFC_ms=0.025278, RTF=0.001645, latency_ms=15.427954
- run 19: tok/s=6007.13, TTFC_ms=0.027020, RTF=0.004279, latency_ms=16.508597
- run 20: tok/s=11458.93, TTFC_ms=0.026089, RTF=0.002258, latency_ms=10.832962
- run 21: tok/s=10471.98, TTFC_ms=0.017156, RTF=0.002467, latency_ms=9.091237
- run 22: tok/s=10087.28, TTFC_ms=0.016916, RTF=0.002540, latency_ms=9.387420
- run 23: tok/s=12500.93, TTFC_ms=0.024618, RTF=0.002056, latency_ms=11.531943
- run 24: tok/s=14173.68, TTFC_ms=0.017566, RTF=0.001822, latency_ms=7.974237
- run 25: tok/s=32833.45, TTFC_ms=0.017727, RTF=0.000811, latency_ms=17.584063
- run 26: tok/s=8497.48, TTFC_ms=0.025178, RTF=0.003025, latency_ms=11.225984
- run 27: tok/s=12274.32, TTFC_ms=0.023365, RTF=0.002136, latency_ms=15.490197
- run 28: tok/s=11680.81, TTFC_ms=0.018898, RTF=0.002211, latency_ms=8.143001
- run 29: tok/s=5963.16, TTFC_ms=0.024857, RTF=0.004300, latency_ms=16.557140
- run 30: tok/s=10476.90, TTFC_ms=0.017457, RTF=0.002464, latency_ms=9.056604

## 5) Pipecat UI Integration Check

Question: do we need to integrate with Pipecat UI?

Answer:
- For the assignment requirements in context.md, a dedicated Pipecat UI is not mandatory.
- What is required is pipeline integration (STT -> LLM -> TTS) and streaming behavior.
- Current repo has the Pipecat TTS service adapter needed for pipeline wiring.
- A UI can be added as a demo enhancement, but it is optional compared to proving pipeline correctness and metrics.

## 6) Remaining Missing Pieces (Priority)

1. Verify and demonstrate true CUDA megakernel decode path in production logs.
2. Produce end-to-end Pipecat pipeline proof (STT->LLM->TTS) with run instructions and evidence.
3. Add a trusted TTFC measurement section (server and client definitions, p50/p95).
4. Add final demo recording artifact for deliverable completeness.
