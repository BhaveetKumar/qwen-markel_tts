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

# Prefer a local Qwen3-TTS clone to avoid hub auth issues.
if [[ -z "${QWEN_TTS_MODEL:-}" ]]; then
    if [[ -d "$PROJECT_ROOT/../Qwen3-TTS" ]]; then
        export QWEN_TTS_MODEL="$PROJECT_ROOT/../Qwen3-TTS"
    else
        export QWEN_TTS_MODEL="Qwen/Qwen3-TTS"
    fi
fi
export PORT="${PORT:-8000}"

echo "Starting TTS server on port $PORT (model: $QWEN_TTS_MODEL)"
uvicorn server.app:create_app \
    --factory \
    --host 0.0.0.0 \
    --port "$PORT" \
    --log-level info
