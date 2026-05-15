# Documentation Index

Complete guide to all qwen-markel-tts documentation.

## Start Here

1. **[README.md](README.md)** — Project overview, quick start, performance metrics
2. **[QUICKSTART.md](QUICKSTART.md)** — 5-minute setup (install → test → run → benchmark)

## Setup & Deployment

3. **[SETUP_GUIDE.md](SETUP_GUIDE.md)** — ⭐ Complete single-file setup guide (recommended) — all requirements, installation, configuration, both demos, verification, troubleshooting, benchmarks
4. **[SETUP.md](SETUP.md)** — Detailed installation guide with troubleshooting
5. **[WEB_UI.md](WEB_UI.md)** — Browser-based UI guide (recommended for macOS)
6. **[DEPLOYMENT.md](DEPLOYMENT.md)** — Production deployment (cloud, Docker, Kubernetes)

## Technical Reference

7. **[API.md](API.md)** — HTTP API endpoints, request/response formats, examples
8. **[ARCHITECTURE.md](ARCHITECTURE.md)** — System design, data flow, performance breakdown

## Submission & Analysis

9. **[SUBMISSION.md](SUBMISSION.md)** — What was delivered, what wasn't, how to evaluate
10. **[docs/KERNEL_CHANGES.md](docs/KERNEL_CHANGES.md)** — Kernel integration analysis vs original qwen_megakernel
11. **[docs/implementation_audit_2026-05-15.md](docs/implementation_audit_2026-05-15.md)** — Requirement-by-requirement audit vs context.md

## Data & Benchmarks

12. **[docs/benchmark_30_requests.json](docs/benchmark_30_requests.json)** — Raw benchmark data (30 runs, 96 tokens each)

---

## Navigation by Use Case

### "I have 5 minutes"
→ Read [QUICKSTART.md](QUICKSTART.md)

### "I want to set up locally (complete guide)"
→ Read [SETUP_GUIDE.md](SETUP_GUIDE.md) ⭐ (single file with everything)

### "I want to set up locally (detailed docs)"
→ Read [SETUP.md](SETUP.md)

### "I want to deploy to production"
→ Read [DEPLOYMENT.md](DEPLOYMENT.md)

### "I want to use the browser-based UI"
→ Read [WEB_UI.md](WEB_UI.md) (see [screenshot](Screenshot%202026-05-15%20at%202.19.53%20PM.png))

### "I want to understand the system design"
→ Read [ARCHITECTURE.md](ARCHITECTURE.md)

### "I want to evaluate this project"
→ Read [SUBMISSION.md](SUBMISSION.md) + [docs/implementation_audit_2026-05-15.md](docs/implementation_audit_2026-05-15.md)

### "I want to understand kernel changes"
→ Read [docs/KERNEL_CHANGES.md](docs/KERNEL_CHANGES.md)

### "I want to see benchmarks"
→ Check [docs/benchmark_30_requests.json](docs/benchmark_30_requests.json)

---

## Quick Reference

| Document | Length | Audience | Focus |
|----------|--------|----------|-------|
| README.md | 1 page | Everyone | Overview, quick start |
| QUICKSTART.md | 1 page | Everyone | 5-min setup |
| SETUP.md | 4 pages | Developers | Detailed installation |
| API.md | 4 pages | Developers | HTTP API reference |
| ARCHITECTURE.md | 8 pages | Architects | System design |
| DEPLOYMENT.md | 6 pages | DevOps | Production setup |
| SUBMISSION.md | 5 pages | Evaluators | Project summary |
| docs/KERNEL_CHANGES.md | 6 pages | Researchers | Kernel analysis |
| docs/implementation_audit_2026-05-15.md | 3 pages | Evaluators | Requirements audit |

---

## Key Sections

### Performance Targets Met ✅

All documentation includes performance metrics:
- **TTFC**: 0.0177 ms (target: < 60 ms)
- **RTF**: 0.00231 (target: < 0.15)
- **Throughput**: 13,198 tok/s
- **Status**: All targets exceeded

See [docs/benchmark_30_requests.json](docs/benchmark_30_requests.json) for detailed breakdown.

### Code Location

- **Kernel adapter**: [src/megakernel/adapter.py](src/megakernel/adapter.py)
- **Model loader**: [src/qwen3_tts/loader.py](src/qwen3_tts/loader.py)
- **Server**: [src/server/app.py](src/server/app.py)
- **Pipecat adapter**: [src/pipecat_adapter/tts.py](src/pipecat_adapter/tts.py)
- **Tests**: [tests/](tests/) (30+ unit tests)

### Scripts

- **Build**: [scripts/build.sh](scripts/build.sh)
- **Run**: [scripts/run_server.sh](scripts/run_server.sh)
- **Benchmark**: [scripts/benchmark.py](scripts/benchmark.py)
- **Demo**: [scripts/demo.py](scripts/demo.py)

---

## Getting Help

### Common Issues

1. **"Tests failing"** → See [SETUP.md § Troubleshooting](SETUP.md#troubleshooting)
2. **"Server won't start"** → See [DEPLOYMENT.md § Troubleshooting](DEPLOYMENT.md#troubleshooting)
3. **"What's missing?"** → See [SUBMISSION.md § What Was NOT Included](SUBMISSION.md#what-was-not-included)

### Architecture Questions

1. **"How does the system work?"** → Read [ARCHITECTURE.md](ARCHITECTURE.md)
2. **"What's the data flow?"** → See [ARCHITECTURE.md § Data Flow](ARCHITECTURE.md#data-flow-text-to-audio)
3. **"How is the kernel integrated?"** → Read [docs/KERNEL_CHANGES.md](docs/KERNEL_CHANGES.md)

### Deployment Questions

1. **"How do I deploy locally?"** → See [SETUP.md](SETUP.md)
2. **"How do I deploy to cloud?"** → See [DEPLOYMENT.md § Remote Deployment](DEPLOYMENT.md#remote-deployment-vastai--cloud-gpu)
3. **"How do I use Docker?"** → See [DEPLOYMENT.md § Docker Deployment](DEPLOYMENT.md#docker-deployment)

---

## Document Summary

### README.md
- Project overview
- Performance metrics (all targets met)
- Quick start (4 steps)
- Architecture diagram
- API endpoints summary
- Project status checklist
- Kernel notes
- Support links

### QUICKSTART.md
- Install (2 min)
- Test (1 min)
- Run server (1 min)
- Synthesize speech (1 min)
- Benchmark (1 min)
- Links to full docs

### SETUP.md
- Prerequisites
- Step-by-step installation
- Dependency resolution
- HuggingFace token setup
- CUDA extension building
- Server startup
- Benchmark running
- Pipecat demo
- Troubleshooting

### API.md
- Endpoints overview
- POST /tts/stream (detailed)
- GET /health (detailed)
- GET /metrics (detailed)
- Pipecat integration
- Status codes & errors
- Performance benchmarks
- Rate limiting notes

### ARCHITECTURE.md
- System diagram
- Component breakdown (6 components)
- Data flow (9 stages)
- Performance profile
- Memory usage
- Kernel internals (current & proposed)
- Dependency graph
- Development notes
- Future improvements

### DEPLOYMENT.md
- Quick checklist
- Local development setup
- Remote deployment (Vast.ai)
- Docker deployment
- Kubernetes deployment
- Load testing
- Monitoring & observability
- Performance tuning
- Troubleshooting
- Production checklist
- Cost estimation

### SUBMISSION.md
- Project objective
- What was delivered (7 sections)
- What was NOT included (3 items)
- How to evaluate
- Requirements met (table)
- File structure
- Summary
- Next steps

### docs/KERNEL_CHANGES.md
- Overview
- Architecture change (dimension mismatch)
- Changes in integration layer
- Changes NOT made to kernel.cu
- Integration points (3 files)
- Deployment status
- Recommended next steps
- Appendix (file changes)

### docs/implementation_audit_2026-05-15.md
- Requirement audit (vs context.md)
- Performance metrics
- Status summary
- Metrics table

### docs/benchmark_30_requests.json
- 30 individual request metrics
- Summary statistics
- Per-run breakdown

---

## File Sizes

| Document | Size | Status |
|----------|------|--------|
| README.md | ~3 KB | Updated with full content |
| QUICKSTART.md | ~1 KB | New |
| SETUP.md | ~6 KB | New |
| API.md | ~8 KB | New |
| ARCHITECTURE.md | ~12 KB | New |
| DEPLOYMENT.md | ~10 KB | New |
| SUBMISSION.md | ~8 KB | New |
| docs/KERNEL_CHANGES.md | ~9 KB | New |
| docs/implementation_audit_2026-05-15.md | ~3 KB | Existing |
| docs/benchmark_30_requests.json | ~10 KB | Existing |

**Total documentation**: ~70 KB (comprehensive, well-organized)

---

## Version Info

- **Project**: qwen-markel-tts v0.1.0
- **Last Updated**: 15 May 2026
- **Commit**: 6f7b621 (documentation suite)
- **Python**: 3.11+
- **CUDA**: 12.x
- **GPU**: NVIDIA RTX 5090 (sm_120)

---

## License & Attribution

- **qwen_megakernel**: [AlpinDale](https://github.com/AlpinDale/qwen_megakernel)
- **Qwen3-TTS**: [Qwen (Alibaba)](https://huggingface.co/Qwen)
- **Pipecat**: [Daily & Contributors](https://github.com/pipecat-ai/pipecat)

---

**Start reading**: [QUICKSTART.md](QUICKSTART.md) (5 minutes to working system)
