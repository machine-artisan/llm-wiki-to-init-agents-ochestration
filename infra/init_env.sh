#!/usr/bin/env bash
# init_env.sh — Detect GPU VRAM, set up Python venv, and deploy Ollama model.
# Run once after `git clone` on each node.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
VENV_DIR="${REPO_DIR}/.venv"

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
    if   (( vram_gb >= 20 )); then echo "gemma3:27b"
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

# ── Python 설치 확인 ──────────────────────────────────────────────────────────
ensure_python3() {
    if command -v python3 &>/dev/null; then
        echo "[init] Python3 found: $(python3 --version)"
        return
    fi
    echo "[init] python3 not found. Installing..."
    if command -v apt-get &>/dev/null; then
        sudo apt-get update -qq
        sudo apt-get install -y python3 python3-venv python3-full
    elif command -v dnf &>/dev/null; then
        sudo dnf install -y python3 python3-virtualenv
    elif command -v brew &>/dev/null; then
        brew install python3
    else
        echo "[init] ERROR: Cannot auto-install python3. Install it manually and re-run."
        exit 1
    fi
}

# ── Python venv 생성 및 의존성 설치 ──────────────────────────────────────────
setup_venv() {
    if [[ ! -d "${VENV_DIR}" ]]; then
        echo "[init] Creating virtual environment at .venv/ ..."
        python3 -m venv "${VENV_DIR}"
    else
        echo "[init] Virtual environment already exists at .venv/"
    fi

    echo "[init] Installing Python dependencies into .venv/ ..."
    "${VENV_DIR}/bin/pip" install --quiet --upgrade pip
    "${VENV_DIR}/bin/pip" install --quiet -r "${REPO_DIR}/requirements.txt"
    echo "[init] Python deps installed."
}

# ── OpenCode 설치 (Deputy 노드 전용 — VRAM >= 20GB) ──────────────────────────
ensure_opencode() {
    local role="$1"
    if [[ "${role}" != "deputy" ]]; then
        echo "[init] Worker node — skipping opencode install."
        return
    fi
    if command -v opencode &>/dev/null; then
        echo "[init] opencode already installed: $(opencode --version 2>/dev/null || echo 'unknown version')"
        return
    fi
    echo "[init] Installing opencode..."
    if curl -fsSL https://opencode.ai/install | bash; then
        # 설치 후 현재 쉘 세션 PATH에도 즉시 반영
        export PATH="${HOME}/.opencode/bin:${PATH}"
        echo "[init] opencode installed."
    else
        echo "[init] WARNING: opencode install failed. Install manually:"
        echo "       curl -fsSL https://opencode.ai/install | bash"
    fi
}

# ── Ollama install ────────────────────────────────────────────────────────────
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

# ── Node config file ──────────────────────────────────────────────────────────
write_node_config() {
    local role="$1" model="$2" vram_gb="$3"
    mkdir -p "${REPO_DIR}/state"
    cat > "${REPO_DIR}/state/node_config.json" <<EOF
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
    cd "${REPO_DIR}"

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

    ensure_python3
    setup_venv
    ensure_opencode "${ROLE}"
    ensure_ollama
    start_ollama_server

    echo "[init] Pulling Ollama model: ${MODEL} ..."
    ollama pull "${MODEL}"

    write_node_config "${ROLE}" "${MODEL}" "${VRAM_GB}"

    echo ""
    echo "======================================================"
    echo "  Init complete. Next steps:"
    echo ""
    echo "  # 가상환경 활성화 (새 터미널이면 아래 두 줄 모두 실행)"
    echo "  export PATH=\"\${HOME}/.opencode/bin:\${PATH}\""
    echo "  source .venv/bin/activate"
    echo ""
    if [[ "${ROLE}" == "deputy" ]]; then
    echo "  # (Node A only) 전체 상태 초기화 — 최초 1회만"
    echo "  python scripts/init_leader_state.py"
    echo ""
    echo "  # Deputy 검증"
    echo "  python scripts/verify_deputy.py"
    echo ""
    echo "  # Deputy 대화 인터페이스 (opencode TUI)"
    echo "  opencode"
    echo ""
    echo "  # 태스크 주입 전용 CLI"
    echo "  python scripts/deputy_cli.py task"
    echo ""
    fi
    echo "  # 데몬 시작"
    echo "  python scripts/git_sync_daemon.py"
    echo "======================================================"
}

main "$@"
