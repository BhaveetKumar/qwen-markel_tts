#!/usr/bin/env bash
# Wrapper to run demo.py with proper SSL certificate configuration

cd "$(dirname "$0")/.."

export PYTHONPATH="/Users/fc20136/Desktop/poc/qwen-markel_tts/src:$PYTHONPATH"

# Fix SSL certificate issues on macOS
export SSL_CERT_FILE=$(python3 -c 'import certifi; print(certifi.where())')
export REQUESTS_CA_BUNDLE=$SSL_CERT_FILE
export CURL_CA_BUNDLE=$SSL_CERT_FILE

echo "🎙️  Starting Qwen3-TTS Pipecat Voice Pipeline"
echo "======================================================="
echo "SSL Certificate: $SSL_CERT_FILE"
echo ""

python3 -u scripts/demo.py "$@"
