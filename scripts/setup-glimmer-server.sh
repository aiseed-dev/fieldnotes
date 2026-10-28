#!/usr/bin/env bash
# Set up Muse Glimmer as an OpenAI-compatible HTTP server on the MS-S1 MAX
# (Ryzen AI Max+ 395, 128 GB unified memory, Linux).
#
# Run this ON the MS-S1 MAX. Afterwards, debpc reaches it at
#   http://192.168.100.6:11434/v1   (Ollama's OpenAI-compatible endpoint)
#
# Usage:  bash setup-glimmer-server.sh [model-tag]
set -euo pipefail

MODEL="${1:-muse-glimmer}"   # TODO: confirm the exact tag on https://ollama.com/library

# 1. Ollama (single binary, ships its own llama.cpp with Vulkan/ROCm support).
if ! command -v ollama >/dev/null 2>&1; then
  curl -fsSL https://ollama.com/install.sh | sh
fi

# 2. Listen on the LAN, not only on localhost, so debpc can call it.
sudo mkdir -p /etc/systemd/system/ollama.service.d
sudo tee /etc/systemd/system/ollama.service.d/override.conf >/dev/null <<'EOF'
[Service]
Environment="OLLAMA_HOST=0.0.0.0:11434"
Environment="OLLAMA_KEEP_ALIVE=24h"
EOF
sudo systemctl daemon-reload
sudo systemctl enable --now ollama
sudo systemctl restart ollama

# 3. Pull the model (30B; expect ~20 GB at Q4, ~32 GB at Q8).
ollama pull "$MODEL"

# 4. Smoke test.
curl -s http://localhost:11434/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d "{\"model\":\"$MODEL\",\"messages\":[{\"role\":\"user\",\"content\":\"Reply with the single word: ready\"}]}" \
  | head -c 600
echo
echo "Done. From debpc:  curl http://192.168.100.6:11434/v1/models"
