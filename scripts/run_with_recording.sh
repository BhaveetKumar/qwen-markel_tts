#!/usr/bin/env bash
# Example usage of demo.py with audio recording
# Set the following environment variables before running:
#   TTS_URL - URL of the TTS server
#   DEEPGRAM_KEY - Deepgram API key for STT
#   OPENAI_KEY - OpenAI API key for LLM

TTS_URL="${TTS_URL:-https://collectibles-wrapped-studied-hazards.trycloudflare.com}"
DEEPGRAM_KEY="${DEEPGRAM_KEY:-}"
OPENAI_KEY="${OPENAI_KEY:-}"
AUDIO_OUTPUT_DIR="./responses"

echo "🎙️  Starting voice pipeline with audio recording..."
echo "Audio files will be saved to: $AUDIO_OUTPUT_DIR"
echo ""

python3 -u scripts/demo.py \
  --tts-url "$TTS_URL" \
  --deepgram-key "$DEEPGRAM_KEY" \
  --openai-key "$OPENAI_KEY" \
  --audio-output-dir "$AUDIO_OUTPUT_DIR"
