"""
deputy_cli.py — Claude Code CLI 없이 Deputy(gemma3:27b)와 직접 대화하는 인터페이스.

두 가지 모드:
  chat     : 대화형 REPL — Deputy와 자유롭게 대화 (기본값)
  task     : 태스크 주입 — global_state.json의 pending_tasks에 태스크를 추가하고 push

사용법:
  python scripts/deputy_cli.py              # chat 모드
  python scripts/deputy_cli.py task         # task 주입 모드
  python scripts/deputy_cli.py chat --plain # 스트리밍 없이 출력
"""

from __future__ import annotations

import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx

OLLAMA_BASE = "http://localhost:11434"
REPO_DIR = Path(__file__).resolve().parent.parent
STATE_FILE = REPO_DIR / "state" / "global_state.json"

DEPUTY_SYSTEM = """\
You are the Deputy Leader of a multi-agent DevOps orchestration system.
The human operator is communicating with you directly (the Leader / Claude API may be offline).

Your capabilities:
- Decompose complex goals into concrete subtasks
- Review and critique code or architecture decisions
- Make operational decisions when the Leader is unavailable
- Supervise Worker agents and interpret their outputs

Be concise, technical, and structured. When asked to produce tasks,
output JSON arrays. When asked for analysis, be direct.\
"""


# ── Ollama helpers ────────────────────────────────────────────────────────────

def get_loaded_model() -> str:
    """Return the model name configured in node_config.json, fallback to gemma3:27b."""
    cfg = REPO_DIR / "state" / "node_config.json"
    if cfg.exists():
        try:
            return json.loads(cfg.read_text()).get("ollama_model", "gemma3:27b")
        except Exception:
            pass
    return "gemma3:27b"


def check_ollama(model: str) -> bool:
    try:
        r = httpx.get(f"{OLLAMA_BASE}/api/tags", timeout=5)
        return any(model in m["name"] for m in r.json().get("models", []))
    except Exception:
        return False


def stream_generate(model: str, messages: list[dict]) -> str:
    """Send a chat request with streaming output. Returns full response text."""
    payload = {"model": model, "messages": messages, "stream": True}
    full = []
    print("\nDeputy: ", end="", flush=True)
    with httpx.stream("POST", f"{OLLAMA_BASE}/api/chat", json=payload, timeout=180) as r:
        for line in r.iter_lines():
            if not line:
                continue
            try:
                chunk = json.loads(line)
                token = chunk.get("message", {}).get("content", "")
                print(token, end="", flush=True)
                full.append(token)
                if chunk.get("done"):
                    break
            except Exception:
                continue
    print()
    return "".join(full)


# ── Chat mode ─────────────────────────────────────────────────────────────────

def run_chat(plain: bool = False) -> None:
    model = get_loaded_model()

    if not check_ollama(model):
        print(f"ERROR: {model} not found in Ollama. Run: ollama pull {model}")
        sys.exit(1)

    print(f"\n{'='*58}")
    print(f"  Deputy CLI — {model}")
    print(f"  Type 'exit' or Ctrl+C to quit")
    print(f"  Type '/task' to switch to task injection mode")
    print(f"{'='*58}\n")

    messages: list[dict] = [{"role": "system", "content": DEPUTY_SYSTEM}]

    while True:
        try:
            user_input = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nBye.")
            break

        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit"):
            break
        if user_input == "/task":
            run_task_inject()
            continue
        if user_input == "/clear":
            messages = [{"role": "system", "content": DEPUTY_SYSTEM}]
            print("[context cleared]\n")
            continue
        if user_input == "/state":
            _print_state_summary()
            continue

        messages.append({"role": "user", "content": user_input})
        response = stream_generate(model, messages)
        messages.append({"role": "assistant", "content": response})
        print()


# ── Task injection mode ───────────────────────────────────────────────────────

def run_task_inject() -> None:
    """Interactive task builder — appends to global_state.json pending_tasks."""
    if not STATE_FILE.exists():
        print("ERROR: state/global_state.json not found.")
        print("Run: python scripts/init_leader_state.py  (on Node A)")
        return

    print("\n── Task Injection ──────────────────────────────────────")
    desc = input("Task description: ").strip()
    if not desc:
        print("Cancelled.\n")
        return

    try:
        score = int(input("Complexity score 0-10 (7-10=Deputy, 0-3=Worker): ").strip())
        score = max(0, min(10, score))
    except ValueError:
        score = 5

    wiki = input("Generate wiki entry on completion? [y/N]: ").strip().lower() == "y"

    state = json.loads(STATE_FILE.read_text())
    task = {
        "task_id": f"manual-{uuid.uuid4().hex[:8]}",
        "description": desc,
        "complexity_score": score,
        "assigned_to": "deputy" if score >= 7 else "worker",
        "status": "pending",
        "result": None,
        "created_at": _now(),
        "updated_at": _now(),
        "wiki_trigger": wiki,
    }
    state.setdefault("pending_tasks", []).append(task)
    state["updated_at"] = _now()
    STATE_FILE.write_text(json.dumps(state, indent=2))

    print(f"\n[task] Added: {task['task_id']} → assigned to {task['assigned_to']}")
    print(f"[task] Saved to state/global_state.json")

    push = input("Git commit & push now? [Y/n]: ").strip().lower()
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
        print("[task] Pushed to origin/main — daemon will pick up on next poll.")
    except Exception as exc:
        print(f"[task] Push failed: {exc}")
        print("[task] Commit manually: git add state/global_state.json && git push")


def _print_state_summary() -> None:
    if not STATE_FILE.exists():
        print("No state file found.\n")
        return
    state = json.loads(STATE_FILE.read_text())
    print(f"\n── State Summary ──────────────────────────────────────")
    print(f"  Session  : {state.get('session_id', 'n/a')}")
    print(f"  Pending  : {len(state.get('pending_tasks', []))}")
    print(f"  In prog  : {len(state.get('in_progress_tasks', []))}")
    print(f"  Completed: {len(state.get('completed_tasks', []))}")
    a = state.get("node_a_status", {})
    b = state.get("node_b_status", {})
    print(f"  Node A   : {a.get('hostname','?')} — {'online' if a.get('is_available') else 'offline'}")
    print(f"  Node B   : {b.get('hostname','?')} — {'online' if b.get('is_available') else 'offline'}\n")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "chat"
    plain = "--plain" in sys.argv

    if mode == "task":
        run_task_inject()
    else:
        run_chat(plain=plain)
