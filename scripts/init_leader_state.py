"""
init_leader_state.py — Leader(워크스테이션)가 한 번만 실행하는 초기화 스크립트.

state/global_state.json 을 생성하고 GitHub에 push한다.
Node B 데몬은 이 파일이 존재해야 태스크 처리를 시작할 수 있다.
"""

from __future__ import annotations

import socket
import sys
import uuid
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_DIR))

from core.graph_state import NodeRole, NodeStatus, OrchestratorState

STATE_FILE = REPO_DIR / "state" / "global_state.json"


def main() -> None:
    if STATE_FILE.exists():
        print(f"[init_leader] {STATE_FILE} already exists — skipping creation.")
        print("[init_leader] Delete the file manually if you want to reset.")
        return

    session_id = f"session-{uuid.uuid4().hex[:8]}"
    state = OrchestratorState(
        session_id=session_id,
        node_a_status=NodeStatus(
            role=NodeRole.DEPUTY,
            hostname="(pending — Node A not yet connected)",
            gpu_vram_gb=24.0,
            ollama_model="gemma2:9b",
            is_available=False,
        ),
        node_b_status=NodeStatus(
            role=NodeRole.WORKER,
            hostname="(pending — Node B not yet connected)",
            gpu_vram_gb=8.0,
            ollama_model="gemma2:2b",
            is_available=False,
        ),
    )
    state.save(STATE_FILE)
    print(f"[init_leader] Created {STATE_FILE}  (session: {session_id})")

    # Git commit + push
    try:
        import git
        repo = git.Repo(REPO_DIR)
        repo.index.add(["state/global_state.json"])
        repo.index.commit(
            f"[leader/{socket.gethostname()}] initialize global state\n\n"
            f"session_id: {session_id}"
        )
        repo.remote("origin").push("main")
        print("[init_leader] Pushed to origin/main — Node B can now start its daemon.")
    except Exception as exc:
        print(f"[init_leader] WARNING: Git push failed ({exc})")
        print("[init_leader] Commit and push state/global_state.json manually.")


if __name__ == "__main__":
    main()
