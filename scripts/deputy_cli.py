"""
deputy_cli.py — 오케스트레이션 태스크 주입 및 상태 확인 CLI.

대화 인터페이스는 opencode(TUI)가 담당한다.
이 스크립트는 오케스트레이션 고유 작업만 처리한다:
  - global_state.json 에 태스크 주입 후 Git push
  - 현재 상태 요약 출력

사용법:
  python scripts/deputy_cli.py task    # 태스크 주입
  python scripts/deputy_cli.py state   # 상태 요약
"""

from __future__ import annotations

import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

REPO_DIR = Path(__file__).resolve().parent.parent
STATE_FILE = REPO_DIR / "state" / "global_state.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── 태스크 주입 ───────────────────────────────────────────────────────────────

def run_task_inject() -> None:
    if not STATE_FILE.exists():
        print("ERROR: state/global_state.json not found.")
        print("Run: python scripts/init_leader_state.py  (Node A에서 최초 1회)")
        sys.exit(1)

    print("\n── Task Injection ──────────────────────────────────────")
    desc = input("Task description: ").strip()
    if not desc:
        print("Cancelled.")
        return

    try:
        score_raw = input("Complexity score 0-10  (7-10=Deputy / 0-3=Worker) [5]: ").strip()
        score = int(score_raw) if score_raw else 5
        score = max(0, min(10, score))
    except ValueError:
        score = 5

    assigned = "deputy" if score >= 4 else "worker"
    wiki = input("Wiki 문서 자동 생성? [y/N]: ").strip().lower() == "y"

    state = json.loads(STATE_FILE.read_text())
    task = {
        "task_id": f"manual-{uuid.uuid4().hex[:8]}",
        "description": desc,
        "complexity_score": score,
        "assigned_to": assigned,
        "status": "pending",
        "result": None,
        "created_at": _now(),
        "updated_at": _now(),
        "wiki_trigger": wiki,
    }
    state.setdefault("pending_tasks", []).append(task)
    state["updated_at"] = _now()
    STATE_FILE.write_text(json.dumps(state, indent=2))

    print(f"\n[task] 추가됨: {task['task_id']}  →  {assigned}  (score={score})")

    push = input("Git commit & push? [Y/n]: ").strip().lower()
    if push != "n":
        _git_push_state(task["task_id"])
    print()


def _git_push_state(task_id: str) -> None:
    try:
        import git as gitlib
        repo = gitlib.Repo(REPO_DIR)
        repo.index.add(["state/global_state.json"])
        repo.index.commit(f"[deputy_cli] inject task {task_id}")
        repo.remote("origin").push("main")
        print("[task] Pushed — 데몬이 다음 폴링에서 태스크를 감지합니다.")
    except Exception as exc:
        print(f"[task] Push 실패: {exc}")
        print("[task] 수동으로 실행: git add state/global_state.json && git push")


# ── 상태 요약 ─────────────────────────────────────────────────────────────────

def run_state_summary() -> None:
    if not STATE_FILE.exists():
        print("state/global_state.json 없음 — init_leader_state.py를 먼저 실행하세요.")
        return

    state = json.loads(STATE_FILE.read_text())
    a = state.get("node_a_status", {})
    b = state.get("node_b_status", {})

    print(f"\n── Orchestration State ─────────────────────────────────")
    print(f"  Session    : {state.get('session_id', 'n/a')}")
    print(f"  Updated    : {state.get('updated_at', 'n/a')}")
    print(f"  Pending    : {len(state.get('pending_tasks', []))}")
    print(f"  In progress: {len(state.get('in_progress_tasks', []))}")
    print(f"  Completed  : {len(state.get('completed_tasks', []))}")
    print(f"  Wiki entries: {state.get('wiki_entries_generated', 0)}")
    print(f"  Node A     : {a.get('hostname', '?')}  "
          f"{'● online' if a.get('is_available') else '○ offline'}  "
          f"model={a.get('ollama_model', '?')}")
    print(f"  Node B     : {b.get('hostname', '?')}  "
          f"{'● online' if b.get('is_available') else '○ offline'}  "
          f"model={b.get('ollama_model', '?')}")

    pending = state.get("pending_tasks", [])
    if pending:
        print(f"\n  Pending tasks:")
        for t in pending:
            print(f"    [{t['assigned_to']:7}] {t['task_id']}  {t['description'][:55]}")
    print()


# ── Entry point ───────────────────────────────────────────────────────────────

HELP = """
deputy_cli.py — 오케스트레이션 CLI (대화는 opencode 사용)

  python scripts/deputy_cli.py task    태스크 주입
  python scripts/deputy_cli.py state   상태 요약

Deputy와 대화하려면:
  opencode                             TUI 실행 (프로젝트 루트에서)
"""

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode == "task":
        run_task_inject()
    elif mode == "state":
        run_state_summary()
    else:
        print(HELP)
