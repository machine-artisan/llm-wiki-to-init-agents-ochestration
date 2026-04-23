#!/usr/bin/env bash
# stop_daemon.sh — Gracefully stop git_sync_daemon.py.
#
# Sends SIGTERM so the daemon finishes its current task, pushes a final
# "node offline" state to Git, then exits. Falls back to SIGKILL after
# GRACE_SECONDS if the process does not exit on its own.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PID_FILE="${REPO_DIR}/state/daemon.pid"
GRACE_SECONDS="${1:-30}"   # optional arg: timeout before force-kill

# ── Locate daemon PID ─────────────────────────────────────────────────────────
if [[ ! -f "$PID_FILE" ]]; then
    echo "[stop] PID file not found at $PID_FILE"
    echo "[stop] Searching for running daemon process..."
    PID=$(pgrep -f "git_sync_daemon.py" || true)
    if [[ -z "$PID" ]]; then
        echo "[stop] No running daemon found. Already stopped."
        exit 0
    fi
else
    PID=$(cat "$PID_FILE")
fi

# ── Verify process is alive ───────────────────────────────────────────────────
if ! kill -0 "$PID" 2>/dev/null; then
    echo "[stop] PID $PID is not running. Cleaning up stale PID file."
    rm -f "$PID_FILE"
    exit 0
fi

# ── Send SIGTERM (graceful) ───────────────────────────────────────────────────
echo "[stop] Sending SIGTERM to daemon PID $PID (grace period: ${GRACE_SECONDS}s)..."
kill -TERM "$PID"

# ── Wait for clean exit ───────────────────────────────────────────────────────
elapsed=0
while kill -0 "$PID" 2>/dev/null; do
    if (( elapsed >= GRACE_SECONDS )); then
        echo "[stop] Grace period expired. Sending SIGKILL to PID $PID..."
        kill -KILL "$PID" 2>/dev/null || true
        break
    fi
    sleep 1
    (( elapsed++ ))
done

# ── Cleanup ───────────────────────────────────────────────────────────────────
rm -f "$PID_FILE"

if kill -0 "$PID" 2>/dev/null; then
    echo "[stop] WARNING: Process $PID still alive after SIGKILL."
    exit 1
fi

echo "[stop] Daemon stopped cleanly (waited ${elapsed}s)."
