"""
LangGraph global state — serialized to state/global_state.json and committed to Git
so physically separate nodes share the same graph context.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Annotated, Any

from langgraph.graph import add_messages
from pydantic import BaseModel, Field


STATE_FILE = Path("state/global_state.json")


class NodeRole(str, Enum):
    LEADER = "leader"
    DEPUTY = "deputy"   # Node A — RTX A5000, 24GB VRAM
    WORKER = "worker"   # Node B — GTX 1070, 8GB VRAM


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class NodeStatus(BaseModel):
    role: NodeRole
    hostname: str = ""
    gpu_vram_gb: float = 0.0
    ollama_model: str = ""
    last_heartbeat: str = Field(default_factory=lambda: _now())
    current_task_id: str | None = None
    is_available: bool = True


class Task(BaseModel):
    task_id: str
    description: str
    # 0–3: Worker, 4–6: Deputy preferred, 7–10: Deputy only
    complexity_score: int = Field(ge=0, le=10)
    assigned_to: NodeRole | None = None
    status: TaskStatus = TaskStatus.PENDING
    result: str | None = None
    created_at: str = Field(default_factory=lambda: _now())
    updated_at: str = Field(default_factory=lambda: _now())
    wiki_trigger: bool = False  # if True, wiki pipeline runs on completion


class OrchestratorState(BaseModel):
    """
    Full LangGraph state. Serialized to JSON and committed to Git as the shared
    state bus between nodes.
    """
    session_id: str
    created_at: str = Field(default_factory=lambda: _now())
    updated_at: str = Field(default_factory=lambda: _now())

    node_a_status: NodeStatus = Field(
        default_factory=lambda: NodeStatus(role=NodeRole.DEPUTY)
    )
    node_b_status: NodeStatus = Field(
        default_factory=lambda: NodeStatus(role=NodeRole.WORKER)
    )

    pending_tasks: list[Task] = Field(default_factory=list)
    in_progress_tasks: list[Task] = Field(default_factory=list)
    completed_tasks: list[Task] = Field(default_factory=list)

    # Accumulates LangGraph message history (uses LangGraph reducer)
    messages: Annotated[list[Any], add_messages] = Field(default_factory=list)

    wiki_entries_generated: int = 0
    last_wiki_push: str | None = None

    def route_task(self, task: Task) -> NodeRole:
        """Leader routing logic: assign tasks based on complexity and availability."""
        deputy_available = self.node_a_status.is_available
        worker_available = self.node_b_status.is_available

        if task.complexity_score >= 7:
            return NodeRole.DEPUTY
        if task.complexity_score >= 4:
            return NodeRole.DEPUTY if deputy_available else NodeRole.WORKER
        return NodeRole.WORKER if worker_available else NodeRole.DEPUTY

    def assign_task(self, task: Task) -> Task:
        task.assigned_to = self.route_task(task)
        task.status = TaskStatus.PENDING
        task.updated_at = _now()
        return task

    # ── Serialization ────────────────────────────────────────────────────────

    def save(self, path: Path = STATE_FILE) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.updated_at = _now()
        path.write_text(self.model_dump_json(indent=2))

    @classmethod
    def load(cls, path: Path = STATE_FILE) -> "OrchestratorState":
        return cls.model_validate_json(path.read_text())

    @classmethod
    def load_or_create(cls, session_id: str, path: Path = STATE_FILE) -> "OrchestratorState":
        if path.exists():
            return cls.load(path)
        state = cls(session_id=session_id)
        state.save(path)
        return state


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
