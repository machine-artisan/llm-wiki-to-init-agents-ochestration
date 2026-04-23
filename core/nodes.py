"""
LangGraph node functions for Deputy (Node A) and Worker (Node B).

Deputy:  high-level reasoning, code review, complex generation  — 24GB VRAM
Worker:  execution, monitoring, lightweight classification       —  8GB VRAM
"""

from __future__ import annotations

import json
import subprocess
from typing import Any

import httpx

from core.graph_state import NodeRole, NodeStatus, OrchestratorState, Task, TaskStatus

# ── Ollama endpoints (each node runs its own local Ollama instance) ───────────
OLLAMA_BASE = "http://localhost:11434"
DEPUTY_MODEL = "gemma2:9b"    # fallback: mistral, llama3:8b
WORKER_MODEL = "gemma2:2b"    # fallback: phi3:mini


# ── Shared Ollama client ──────────────────────────────────────────────────────

def _ollama_generate(model: str, prompt: str, system: str = "") -> str:
    payload: dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "stream": False,
    }
    if system:
        payload["system"] = system
    resp = httpx.post(f"{OLLAMA_BASE}/api/generate", json=payload, timeout=120)
    resp.raise_for_status()
    return resp.json()["response"].strip()


# ── Hardware introspection ────────────────────────────────────────────────────

def detect_node_profile() -> NodeStatus:
    """
    Detect local GPU VRAM and select the appropriate Ollama model.
    Returns a NodeStatus populated with real hardware values.
    """
    import socket

    vram_gb = _query_vram_gb()
    role, model = _classify_by_vram(vram_gb)
    return NodeStatus(
        role=role,
        hostname=socket.gethostname(),
        gpu_vram_gb=vram_gb,
        ollama_model=model,
        is_available=True,
    )


def _query_vram_gb() -> float:
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
            text=True,
        )
        return round(int(out.strip().splitlines()[0]) / 1024, 1)
    except Exception:
        return 0.0


def _classify_by_vram(vram_gb: float) -> tuple[NodeRole, str]:
    if vram_gb >= 20:
        return NodeRole.DEPUTY, DEPUTY_MODEL
    if vram_gb >= 6:
        return NodeRole.WORKER, WORKER_MODEL
    # CPU-only fallback — still functional, just slow
    return NodeRole.WORKER, "phi3:mini"


# ── Deputy Node (Node A — 24GB VRAM) ─────────────────────────────────────────

DEPUTY_SYSTEM = """\
You are the Deputy Leader in a multi-agent DevOps orchestration system.
You have access to a high-capability local LLM (gemma2:9b class).
Responsibilities:
- Decompose complex tasks into executable subtasks
- Review code and architecture decisions
- Supervise Worker execution quality
- Escalate blockers to the Leader (Claude API)
Be precise, structured, and always output JSON when asked.\
"""


def deputy_node(state: OrchestratorState) -> dict[str, Any]:
    """
    Processes tasks assigned to DEPUTY role.
    Picks the highest-complexity pending task, runs reasoning via local Ollama,
    and returns updated state fields.
    """
    task = _pick_task(state, NodeRole.DEPUTY)
    if task is None:
        return {"node_a_status": state.node_a_status.model_copy(update={"is_available": True})}

    state.node_a_status.is_available = False
    state.node_a_status.current_task_id = task.task_id

    prompt = (
        f"Task ID: {task.task_id}\n"
        f"Description: {task.description}\n"
        f"Complexity: {task.complexity_score}/10\n\n"
        "Analyze this task, outline a step-by-step solution, and provide the result."
    )
    try:
        result = _ollama_generate(DEPUTY_MODEL, prompt, system=DEPUTY_SYSTEM)
        task.status = TaskStatus.COMPLETED
        task.result = result
    except Exception as exc:
        task.status = TaskStatus.FAILED
        task.result = f"ERROR: {exc}"

    task.updated_at = _now_iso()
    state.node_a_status.is_available = True
    state.node_a_status.current_task_id = None
    _move_task(state, task)

    return {
        "node_a_status": state.node_a_status,
        "in_progress_tasks": state.in_progress_tasks,
        "completed_tasks": state.completed_tasks,
    }


# ── Worker Node (Node B — 8GB VRAM) ──────────────────────────────────────────

WORKER_SYSTEM = """\
You are the Worker agent in a multi-agent DevOps orchestration system.
You have access to a lightweight local LLM (gemma2:2b class).
Responsibilities:
- Execute well-defined unit tasks (scripts, checks, monitoring)
- Report results in structured JSON
- Flag anomalies for Deputy review
Keep responses brief and factual.\
"""


def worker_node(state: OrchestratorState) -> dict[str, Any]:
    """
    Processes tasks assigned to WORKER role (complexity 0–3).
    """
    task = _pick_task(state, NodeRole.WORKER)
    if task is None:
        return {"node_b_status": state.node_b_status.model_copy(update={"is_available": True})}

    state.node_b_status.is_available = False
    state.node_b_status.current_task_id = task.task_id

    prompt = (
        f"Task: {task.description}\n"
        "Execute this task and return a concise JSON result with keys: "
        "'status', 'output', 'anomalies'."
    )
    try:
        result = _ollama_generate(WORKER_MODEL, prompt, system=WORKER_SYSTEM)
        task.status = TaskStatus.COMPLETED
        task.result = result
    except Exception as exc:
        task.status = TaskStatus.FAILED
        task.result = f"ERROR: {exc}"

    task.updated_at = _now_iso()
    state.node_b_status.is_available = True
    state.node_b_status.current_task_id = None
    _move_task(state, task)

    return {
        "node_b_status": state.node_b_status,
        "in_progress_tasks": state.in_progress_tasks,
        "completed_tasks": state.completed_tasks,
    }


# ── Router (used by LangGraph conditional_edges) ─────────────────────────────

def route_next(state: OrchestratorState) -> str:
    """
    Determines next node to execute based on pending task queue.
    Returns node name string consumed by LangGraph.
    """
    for task in state.pending_tasks:
        if task.assigned_to == NodeRole.DEPUTY and state.node_a_status.is_available:
            return "deputy"
        if task.assigned_to == NodeRole.WORKER and state.node_b_status.is_available:
            return "worker"
    return "END"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _pick_task(state: OrchestratorState, role: NodeRole) -> Task | None:
    for i, task in enumerate(state.pending_tasks):
        if task.assigned_to == role:
            task.status = TaskStatus.IN_PROGRESS
            state.pending_tasks.pop(i)
            state.in_progress_tasks.append(task)
            return task
    return None


def _move_task(state: OrchestratorState, task: Task) -> None:
    state.in_progress_tasks = [t for t in state.in_progress_tasks if t.task_id != task.task_id]
    state.completed_tasks.append(task)


def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()
