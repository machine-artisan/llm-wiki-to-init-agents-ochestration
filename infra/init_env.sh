#!/usr/bin/env bash
# init_env.sh — Detect GPU VRAM and deploy the appropriate Ollama model.
# Run once after `git clone` on each node.
set -euo pipefail

OLLAMA_MIN_VERSION="0.1.30"

# ── VRAM detection ────────────────────────────────────────────────────────────
detect_vram_gb() {
    if command -v nvidia-smi &>/dev/null; then
        nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits 2>/dev/null \
            | head -1 \
            | awk '{printf "%d", $1/1024}'
    else
        echo "0"
    fi
}

# ── Model selection ───────────────────────────────────────────────────────────
select_model() {
    local vram_gb="$1"
    if   (( vram_gb >= 20 )); then echo "gemma2:9b"
    elif (( vram_gb >= 6  )); then echo "gemma2:2b"
    else                           echo "phi3:mini"
    fi
}

select_role() {
    local vram_gb="$1"
    if (( vram_gb >= 20 )); then echo "deputy"
    else                         echo "worker"
    fi
}

# ── Ollama install/upgrade ────────────────────────────────────────────────────
ensure_ollama() {
    if ! command -v ollama &>/dev/null; then
        echo "[init] Installing Ollama..."
        curl -fsSL https://ollama.ai/install.sh | sh
    else
        echo "[init] Ollama already installed: $(ollama --version)"
    fi
}

start_ollama_server() {
    if ! pgrep -x ollama &>/dev/null; then
        echo "[init] Starting Ollama server in background..."
        nohup ollama serve &>/tmp/ollama.log &
        sleep 3
    else
        echo "[init] Ollama server already running."
    fi
}

# ── Python deps ───────────────────────────────────────────────────────────────
install_python_deps() {
    if ! command -v pip &>/dev/null; then
        echo "[init] pip not found — skipping Python deps (install manually)"
        return
    fi
    echo "[init] Installing Python dependencies..."
    pip install --quiet langgraph pydantic httpx gitpython
}

# ── Node config file ──────────────────────────────────────────────────────────
write_node_config() {
    local role="$1" model="$2" vram_gb="$3"
    mkdir -p state
    cat > state/node_config.json <<EOF
{
  "role": "${role}",
  "ollama_model": "${model}",
  "gpu_vram_gb": ${vram_gb},
  "hostname": "$(hostname)",
  "configured_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF
    echo "[init] Node config written to state/node_config.json"
}

# ── Main ──────────────────────────────────────────────────────────────────────
main() {
    echo "======================================================"
    echo "  llm-wiki-to-init-agents-ochestration — Node Init   "
    echo "======================================================"

    VRAM_GB=$(detect_vram_gb)
    MODEL=$(select_model "$VRAM_GB")
    ROLE=$(select_role "$VRAM_GB")

    echo "[init] Detected VRAM : ${VRAM_GB} GB"
    echo "[init] Assigned role : ${ROLE}"
    echo "[init] Selected model: ${MODEL}"
    echo ""

    ensure_ollama
    start_ollama_server
    install_python_deps

    echo "[init] Pulling Ollama model: ${MODEL} ..."
    ollama pull "${MODEL}"

    write_node_config "${ROLE}" "${MODEL}" "${VRAM_GB}"

    echo ""
    echo "[init] Done. Start the polling daemon:"
    echo "       python scripts/git_sync_daemon.py"
}

main "$@"
