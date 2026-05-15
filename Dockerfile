FROM nvidia/cuda:12.4.1-runtime-ubuntu22.04

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3.11 python3.11-venv python3.11-dev \
    git curl ca-certificates ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy project
COPY . /app

# Create venv and install dependencies
RUN python3.11 -m venv venv && \
    . venv/bin/activate && \
    pip install --upgrade pip && \
    pip install -e ".[dev]"

# Create cache directories
RUN mkdir -p /cache/huggingface /cache/torch

# Set environment variables
ENV HF_HOME=/cache/huggingface
ENV TORCH_HOME=/cache/torch
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python3.11 -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Expose port
EXPOSE 8000

# Run server
ENTRYPOINT ["bash", "scripts/run_server.sh"]
