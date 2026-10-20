#!/bin/bash
set -e

# Always run from the folder this script lives in
cd "$(dirname "$0")"

echo "🚀 Initializing NEXUS-COVE..."

if ! command -v ollama &> /dev/null; then
    echo "❌ Ollama not found. Please install it from https://ollama.com"
    exit 1
fi

if ! curl -s http://127.0.0.1:11434/api/tags > /dev/null; then
    echo "⏳ Starting Ollama in the background..."
    nohup ollama serve > /dev/null 2>&1 &
    sleep 3
fi

echo "📥 Ensuring qwen2.5:0.5b model is downloaded..."
ollama pull qwen2.5:0.5b

# Use python3 if python isn't available (common on Termux/Ubuntu)
PY=python
command -v python &> /dev/null || PY=python3

echo "📦 Installing Python dependencies..."
$PY -m pip install -q -e ".[dev]"

echo "🧠 Running the verification test..."
$PY tests/termux_ollama_test.py
