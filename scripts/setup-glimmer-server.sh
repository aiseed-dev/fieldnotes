#!/usr/bin/env bash
# Muse Glimmer as an OpenAI-compatible server on the house machine
# (MS-S1 MAX: Ryzen AI Max+ 395, 128 GB unified memory, Debian, ROCm 7.14).
# Run as an ordinary user that is in the render and video groups and has
# lingering on (sudo usermod -aG render,video $USER; sudo loginctl enable-linger $USER).
# Afterwards the farm machine reaches it at http://<host>:11434/v1:
#   fieldnotes reader glimmer --url http://<host>:11434/v1 --check
set -euo pipefail

# 1. llama.cpp built for the iGPU (gfx1151). Glimmer needs build b10353 or newer.
[ -d ~/llama.cpp ] || git clone --depth 1 https://github.com/ggml-org/llama.cpp ~/llama.cpp
cd ~/llama.cpp
HIPCXX="$(hipconfig -l)/clang" HIP_PATH="$(hipconfig -R)" \
  cmake -B build -DGGML_HIP=ON -DAMDGPU_TARGETS=gfx1151 -DCMAKE_BUILD_TYPE=Release -DLLAMA_CURL=OFF
cmake --build build --config Release -j "$(nproc)" --target llama-server

# 2. The official GGUF (Apache 2.0): the Q4_K_M model and the mmproj that lets it see photos (~18 GB).
mkdir -p ~/models/glimmer && cd ~/models/glimmer
for f in Muse-Glimmer-30B-KQuant-17GB-Q4_K_M.gguf mmproj-Muse-Glimmer-30B-Q4_K_M.gguf; do
  curl -fL -C - --retry 20 -o "$f" "https://huggingface.co/meta-models/Muse-Glimmer-30B-GGUF/resolve/main/$f"
done

# 3. A user service on port 11434 (open it in the firewall for the farm machine only).
mkdir -p ~/.config/systemd/user
cat > ~/.config/systemd/user/glimmer.service <<'UNIT'
[Unit]
Description=llama-server (Muse Glimmer 30B Q4_K_M + mmproj) for fieldnotes

[Service]
ExecStart=%h/llama.cpp/build/bin/llama-server -m %h/models/glimmer/Muse-Glimmer-30B-KQuant-17GB-Q4_K_M.gguf --mmproj %h/models/glimmer/mmproj-Muse-Glimmer-30B-Q4_K_M.gguf -a muse-glimmer-30B -ngl 99 -c 32768 -np 2 --host 0.0.0.0 --port 11434 --jinja --temp 1.0 --top-p 0.95 --top-k 64
Restart=on-failure

[Install]
WantedBy=default.target
UNIT
systemctl --user daemon-reload
systemctl --user enable --now glimmer.service
until curl -s localhost:11434/health | grep -q ok; do sleep 5; done
echo "ready: http://$(hostname -I | awk '{print $1}'):11434/v1"
