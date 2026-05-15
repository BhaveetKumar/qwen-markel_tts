#!/usr/bin/env bash
# Build the qwen_megakernel CUDA extension (requires RTX 5090 / sm_120, CUDA 12.x).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
MEGAKERNEL_ROOT="$(cd "$REPO_ROOT/../qwen_megakernel" && pwd)"

echo "=== Building qwen_megakernel CUDA extension ==="
echo "Megakernel root: $MEGAKERNEL_ROOT"

# Install megakernel Python deps
pip install -r "$MEGAKERNEL_ROOT/requirements.txt"

# Trigger JIT compilation by importing the package
# Dimension overrides for Qwen3-TTS talker (7B-class)
export LDG_HIDDEN_SIZE=4096
export LDG_INTERMEDIATE_SIZE=22016
export LDG_NUM_Q_HEADS=32
export LDG_NUM_KV_HEADS=8
export LDG_NUM_LAYERS=32
# Keep block/thread counts tuned for RTX 5090
export LDG_NUM_BLOCKS=128
export LDG_BLOCK_SIZE=512

pushd "$MEGAKERNEL_ROOT" > /dev/null
python -c "
import sys; sys.path.insert(0, '.')
from qwen_megakernel.build import get_extension
get_extension()
print('Extension compiled successfully.')
"
popd > /dev/null

# Install qwen-markel-tts package
pip install -e "$REPO_ROOT[dev]"

echo "=== Build complete ==="
