#!/bin/bash
set -e
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
echo "📦 Installing Python dependencies..."
pip install -e ".[dev]" > /dev/null 2>&1
echo "🧠 Running the verification test..."
python tests/termux_ollama_test.py
