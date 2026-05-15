#!/usr/bin/env bash
# Start the Qwen3-TTS megakernel inference server.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="$SCRIPT_DIR/../src"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

export PYTHONPATH="$SRC:${PYTHONPATH:-}"
# Load project environment variables when available (HF_TOKEN, etc.).
if [[ -f "$PROJECT_ROOT/.env" ]]; then
    set -a
    source "$PROJECT_ROOT/.env"
    set +a
fi

# Fallback: load token from common SSH locations when project .env is absent.
if [[ -z "${HF_TOKEN:-}" ]]; then
    for token_file in \
        "$HOME/.ssh/hf_token.env" \
        "/root/.ssh/hf_token.env" \
        "/root/workspace/qwen-markel_tts/.env"; do
        if [[ -f "$token_file" ]]; then
            set -a
            source "$token_file"
            set +a
            break
        fi
    done
fi

# Hugging Face libraries often accept either env var name.
if [[ -n "${HF_TOKEN:-}" && -z "${HUGGINGFACE_HUB_TOKEN:-}" ]]; then
    export HUGGINGFACE_HUB_TOKEN="$HF_TOKEN"
fi

# Use HuggingFace model ID for weights/config. The local Qwen3-TTS clone,
# when present, is used only for Python package imports by loader.py.
export QWEN_TTS_MODEL="${QWEN_TTS_MODEL:-Qwen/Qwen3-TTS-12Hz-0.6B-Base}"
export PORT="${PORT:-8000}"

echo "Starting TTS server on port $PORT (model: $QWEN_TTS_MODEL)"
uvicorn server.app:create_app \
    --factory \
    --host 0.0.0.0 \
    --port "$PORT" \
    --log-level info
