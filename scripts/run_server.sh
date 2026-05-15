#!/usr/bin/env bash
# Start the Qwen3-TTS megakernel inference server.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="$SCRIPT_DIR/../src"

export PYTHONPATH="$SRC:${PYTHONPATH:-}"
export QWEN_TTS_MODEL="${QWEN_TTS_MODEL:-Qwen/Qwen3-TTS}"
export PORT="${PORT:-8000}"

echo "Starting TTS server on port $PORT (model: $QWEN_TTS_MODEL)"
uvicorn server.app:create_app \
    --factory \
    --host 0.0.0.0 \
    --port "$PORT" \
    --log-level info
