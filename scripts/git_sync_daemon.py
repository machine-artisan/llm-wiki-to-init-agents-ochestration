"""
git_sync_daemon.py — Agentic Git-Polling daemon.

Each node runs this daemon to:
  1. Periodically pull the shared GitHub repo
  2. Detect tasks assigned to this node in state/global_state.json
  3. Execute via local Ollama (through core/nodes.py)
  4. Commit results and push back to the repo
"""

from __future__ import annotations

import json
import logging
import os
import signal
import socket
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# repo root를 sys.path에 추가 (scripts/ 하위에서 실행 시 core/ 를 찾기 위해)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import git  # gitpython

from core.graph_state import NodeRole, OrchestratorState, Task, TaskStatus
from core.nodes import deputy_node, detect_node_profile, worker_node

# ── Config ────────────────────────────────────────────────────────────────────
REPO_DIR = Path(__file__).resolve().parent.parent
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL_SECONDS", "30"))
GIT_REMOTE = os.getenv("GIT_REMOTE", "origin")
GIT_BRANCH = os.getenv("GIT_BRANCH", "main")
STATE_FILE = REPO_DIR / "state" / "global_state.json"
HEARTBEAT_INTERVAL = int(os.getenv("HEARTBEAT_INTERVAL", "60"))  # seconds
PID_FILE = REPO_DIR / "state" / "daemon.pid"

# Set by signal handler; main loop checks this before starting each iteration.
_shutdown_requested = False

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(REPO_DIR / "logs" / f"daemon_{socket.gethostname()}.log"),
    ],
)
log = logging.getLogger("git_sync_daemon")


# ── Signal handling ───────────────────────────────────────────────────────────

def _handle_shutdown(signum: int, frame: object) -> None:
    global _shutdown_requested
    sig_name = signal.Signals(signum).name
    log.info("Received %s — finishing current task then shutting down...", sig_name)
    _shutdown_requested = True


# ── Git helpers ───────────────────────────────────────────────────────────────

class GitSyncer:
    def __init__(self, repo_path: Path) -> None:
        self.repo = git.Repo(repo_path)
        self.remote = self.repo.remote(GIT_REMOTE)

    def pull(self) -> bool:
        """Pull latest from remote. Returns True if new commits arrived."""
        before = self.repo.head.commit.hexsha
        self.remote.pull(GIT_BRANCH)
        after = self.repo.head.commit.hexsha
        changed = before != after
        if changed:
            log.info("Pull: new commits detected (%s → %s)", before[:7], after[:7])
        return changed

    def commit_and_push(self, message: str, paths: list[Path]) -> None:
        str_paths = [str(p.relative_to(REPO_DIR)) for p in paths]
        self.repo.index.add(str_paths)
        if not self.repo.index.diff("HEAD"):
            log.debug("Nothing to commit.")
            return
        self.repo.index.commit(
            f"[{socket.gethostname()}] {message}\n\n"
            f"timestamp: {_now()}"
        )
        self.remote.push(GIT_BRANCH)
        log.info("Pushed: %s", message)


# ── Heartbeat ─────────────────────────────────────────────────────────────────

def write_heartbeat(profile: dict, syncer: GitSyncer) -> None:
    hb_file = REPO_DIR / "state" / f"{profile['role']}_heartbeat.json"
    hb_file.parent.mkdir(parents=True, exist_ok=True)
    data = {**profile, "last_heartbeat": _now(), "hostname": socket.gethostname()}
    hb_file.write_text(json.dumps(data, indent=2))
    try:
        syncer.commit_and_push(f"heartbeat from {profile['role']}", [hb_file])
    except Exception as exc:
        log.warning("Heartbeat push failed: %s", exc)


# ── Task dispatch ─────────────────────────────────────────────────────────────

def process_pending_tasks(state: OrchestratorState, role: NodeRole) -> bool:
    """Run all pending tasks assigned to this node's role. Returns True if any ran."""
    eligible = [t for t in state.pending_tasks if t.assigned_to == role]
    if not eligible:
        return False

    for task in eligible:
        log.info("Executing task %s (complexity=%d)", task.task_id, task.complexity_score)
        if role == NodeRole.DEPUTY:
            updates = deputy_node(state)
        else:
            updates = worker_node(state)
        # Apply returned field updates back to state
        for key, val in updates.items():
            setattr(state, key, val)

    return True


# ── Main loop ─────────────────────────────────────────────────────────────────

def _mark_node_offline(
    state: OrchestratorState,
    role: NodeRole,
    syncer: GitSyncer,
) -> None:
    """Set this node's status to unavailable and push the final state."""
    update = {"is_available": False, "current_task_id": None}
    if role == NodeRole.DEPUTY:
        state.node_a_status = state.node_a_status.model_copy(update=update)
    else:
        state.node_b_status = state.node_b_status.model_copy(update=update)
    state.save(STATE_FILE)
    try:
        syncer.commit_and_push(f"graceful shutdown — {role.value} offline", [STATE_FILE])
    except Exception as exc:
        log.warning("Could not push shutdown state: %s", exc)


def main() -> None:
    global _shutdown_requested
    log.info("=== git_sync_daemon starting ===")
    (REPO_DIR / "logs").mkdir(exist_ok=True)

    # Register signal handlers before anything else
    signal.signal(signal.SIGTERM, _handle_shutdown)
    signal.signal(signal.SIGINT, _handle_shutdown)

    # Write PID file so stop_daemon.sh can find us
    PID_FILE.parent.mkdir(parents=True, exist_ok=True)
    PID_FILE.write_text(str(os.getpid()))
    log.info("PID %d written to %s", os.getpid(), PID_FILE)

    syncer = GitSyncer(REPO_DIR)

    # Detect this node's hardware profile
    node_profile = detect_node_profile()
    role = node_profile.role
    log.info("Node role: %s | VRAM: %.1fGB | Model: %s",
             role.value, node_profile.gpu_vram_gb, node_profile.ollama_model)

    last_heartbeat = 0.0
    last_state: OrchestratorState | None = None

    while not _shutdown_requested:
        loop_start = time.time()

        # ── 1. Pull latest state from remote ──
        try:
            syncer.pull()
        except Exception as exc:
            log.error("Pull failed: %s", exc)
            time.sleep(POLL_INTERVAL)
            continue

        # ── 2. Load global state ──
        if not STATE_FILE.exists():
            log.info("No global_state.json yet — waiting for Leader to initialize.")
            time.sleep(POLL_INTERVAL)
            continue

        try:
            state = OrchestratorState.load(STATE_FILE)
            last_state = state
        except Exception as exc:
            log.error("Failed to parse state file: %s", exc)
            time.sleep(POLL_INTERVAL)
            continue

        # ── 3. Update this node's status in state ──
        if role == NodeRole.DEPUTY:
            state.node_a_status = node_profile
        else:
            state.node_b_status = node_profile

        # ── 4. Heartbeat ──
        now = time.time()
        if now - last_heartbeat >= HEARTBEAT_INTERVAL:
            profile_dict = node_profile.model_dump()
            write_heartbeat(profile_dict, syncer)
            last_heartbeat = now

        # ── 5. Process tasks ──
        ran = process_pending_tasks(state, role)

        if ran:
            state.save(STATE_FILE)
            changed_files = [STATE_FILE]

            # Trigger wiki pipeline if any completed task requested it
            wiki_tasks = [
                t for t in state.completed_tasks if t.wiki_trigger and t.result
            ]
            if wiki_tasks:
                from wiki_generator.pipeline import generate_wiki_entries
                new_wiki_files = generate_wiki_entries(wiki_tasks, state)
                changed_files.extend(new_wiki_files)
                state.wiki_entries_generated += len(new_wiki_files)
                state.last_wiki_push = _now()
                state.save(STATE_FILE)

            try:
                syncer.commit_and_push(f"task results from {role.value}", changed_files)
            except Exception as exc:
                log.error("Push failed: %s", exc)

        elapsed = time.time() - loop_start
        sleep_for = max(0, POLL_INTERVAL - elapsed)
        log.debug("Loop done in %.1fs, sleeping %.1fs", elapsed, sleep_for)

        # Interruptible sleep: wake early if shutdown is requested
        deadline = time.time() + sleep_for
        while time.time() < deadline and not _shutdown_requested:
            time.sleep(min(1.0, deadline - time.time()))

    # ── Graceful shutdown sequence ────────────────────────────────────────────
    log.info("Shutdown: marking node offline and pushing final state...")
    if last_state is not None:
        _mark_node_offline(last_state, role, syncer)
    if PID_FILE.exists():
        PID_FILE.unlink()
    log.info("=== git_sync_daemon stopped cleanly ===")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


if __name__ == "__main__":
    main()
