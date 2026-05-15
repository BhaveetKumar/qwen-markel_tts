.PHONY: help install test build run benchmark demo clean

# Default target
help:
	@echo "qwen-markel-tts development commands"
	@echo ""
	@echo "Setup:"
	@echo "  make install      Install dependencies"
	@echo "  make test         Run unit tests"
	@echo "  make build        Build CUDA extension"
	@echo ""
	@echo "Development:"
	@echo "  make run          Start server"
	@echo "  make benchmark    Run benchmark"
	@echo "  make demo         Run Pipecat demo"
	@echo "  make cli TEXT=... Run CLI tool"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-build Build Docker image"
	@echo "  make docker-run   Run in Docker"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean        Remove cache/artifacts"
	@echo "  make clean-cache  Remove HF cache"

# Installation
install:
	pip install -e ".[dev]"

install-pipecat:
	pip install "pipecat-ai[deepgram,openai]>=0.0.53"

# Testing
test:
	pytest tests/ -v

test-quick:
	pytest tests/ -q --tb=short

# Build
build:
	bash scripts/build.sh

# Running
run:
	bash scripts/run_server.sh

run-port:
	PORT=8001 bash scripts/run_server.sh

# Benchmarking
benchmark:
	python scripts/benchmark.py --runs 10

benchmark-long:
	python scripts/benchmark.py --runs 30 --text "This is a comprehensive test of the streaming TTS system."

# CLI tool
cli:
	python scripts/cli.py $(TEXT)

cli-interactive:
	python scripts/cli.py --interactive

cli-check:
	python scripts/cli.py --check-health

cli-samples:
	python scripts/generate_samples.py --output audio_samples

# Pipecat demo
demo:
	python scripts/demo.py

# Docker
docker-build:
	docker build -t qwen-markel-tts:latest .

docker-run:
	docker run --gpus all -p 8000:8000 -v ./cache:/cache qwen-markel-tts:latest

docker-compose-up:
	docker-compose up -d

docker-compose-down:
	docker-compose down

# Code quality
format:
	black src/ tests/ scripts/ --line-length 100
	isort src/ tests/ scripts/

lint:
	black --check src/ tests/ scripts/ --line-length 100
	isort --check src/ tests/ scripts/

# Development workflow
dev: install test
	@echo "✓ Development environment ready"

full: install test build run
	@echo "✓ Full setup complete"

# Cleanup
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache build dist *.egg-info
	rm -f /tmp/out.wav /tmp/output.wav

clean-cache:
	rm -rf cache/ ~/.cache/huggingface ~/.cache/torch

clean-all: clean clean-cache

# Information
info:
	@echo "qwen-markel-tts v0.1.0"
	@echo ""
	@echo "Python version:"
	@python3 --version
	@echo ""
	@echo "CUDA/GPU:"
	@nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null || echo "No GPU detected"
	@echo ""
	@echo "Installed packages:"
	@pip list | grep -E "torch|transformers|pipecat" || echo "Core packages not installed"

# Quick development cycle
watch-test:
	@echo "Watching tests (requires pytest-watch)..."
	ptw -- tests/

# Development convenience targets
repl:
	python3 -i -c "from src.server.app import create_app; app = create_app()"

# CI/CD simulation
ci: lint test
	@echo "✓ CI checks passed"
