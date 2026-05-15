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

# Normalize Hugging Face runtime/cache layout for container hosts (e.g., Vast).
export HF_HOME="${HF_HOME:-/workspace/.hf_home}"
export HF_HUB_CACHE="${HF_HUB_CACHE:-$HF_HOME/hub}"
export HF_ASSETS_CACHE="${HF_ASSETS_CACHE:-$HF_HOME/assets}"
export HF_TOKEN_PATH="${HF_TOKEN_PATH:-$HF_HOME/token}"
export HF_STORED_TOKENS_PATH="${HF_STORED_TOKENS_PATH:-$HF_HOME/stored_tokens}"

# Keep these configurable, but default to stable runtime values.
export HF_HUB_OFFLINE="${HF_HUB_OFFLINE:-False}"
export HF_HUB_DISABLE_TELEMETRY="${HF_HUB_DISABLE_TELEMETRY:-False}"
export HF_HUB_DISABLE_PROGRESS_BARS="${HF_HUB_DISABLE_PROGRESS_BARS:-}"
export HF_HUB_DISABLE_SYMLINKS_WARNING="${HF_HUB_DISABLE_SYMLINKS_WARNING:-False}"
export HF_HUB_DISABLE_EXPERIMENTAL_WARNING="${HF_HUB_DISABLE_EXPERIMENTAL_WARNING:-False}"
export HF_HUB_DISABLE_IMPLICIT_TOKEN="${HF_HUB_DISABLE_IMPLICIT_TOKEN:-False}"
export HF_HUB_DISABLE_XET="${HF_HUB_DISABLE_XET:-False}"
export HF_HUB_ENABLE_HF_TRANSFER="${HF_HUB_ENABLE_HF_TRANSFER:-False}"
export HF_HUB_ETAG_TIMEOUT="${HF_HUB_ETAG_TIMEOUT:-10}"
export HF_HUB_DOWNLOAD_TIMEOUT="${HF_HUB_DOWNLOAD_TIMEOUT:-10}"

mkdir -p "$HF_HOME" "$HF_HUB_CACHE" "$HF_ASSETS_CACHE"

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
