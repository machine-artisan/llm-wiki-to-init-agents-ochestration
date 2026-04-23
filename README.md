# llm-wiki-to-init-agents-ochestration

A **Self-Evolving DevOps Pipeline** combining LangGraph orchestration with GitOps (polling-based) communication across heterogeneous hardware nodes.

## 3-Tier Agent Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   LEADER (Claude API)                   │
│            Orchestrates via GitHub State Files          │
└────────────────────────┬────────────────────────────────┘
                         │ Git Push (Task Assignment)
           ┌─────────────┴──────────────┐
           │                            │
┌──────────▼──────────┐      ┌──────────▼──────────┐
│   NODE A — Deputy   │      │   NODE B — Worker   │
│   Leader (Supervisor│      │   (Executor)        │
│                     │      │                     │
│ RTX A5000  24GB VRAM│      │ GTX 1070   8GB VRAM │
│ i7-12700F  64GB RAM │      │ i5-7500   32GB RAM  │
│                     │      │                     │
│ Model: gemma2:9b+   │      │ Model: gemma2:2b    │
│        or mistral   │      │        or phi3:mini │
└─────────────────────┘      └─────────────────────┘
```

### Tier Responsibilities

| Tier | Node | Model | Responsibilities |
|------|------|-------|-----------------|
| Leader | Claude API | claude-sonnet-4-6 | Task decomposition, routing, Wiki generation trigger |
| Deputy | Node A | gemma2:9b / mistral | Complex reasoning, code review, Worker supervision |
| Worker | Node B | gemma2:2b / phi3:mini | Script execution, log analysis, env monitoring |

## Git-Polling Synchronization Strategy

Nodes communicate exclusively through a shared GitHub repository — **Git acts as the State Bus**.

```
GitHub Repo
├── state/
│   ├── global_state.json     ← LangGraph serialized state
│   ├── node_a_heartbeat.json
│   └── node_b_heartbeat.json
├── tasks/
│   ├── pending/              ← Leader pushes new tasks here
│   ├── in_progress/          ← Nodes move tasks here on pickup
│   └── completed/            ← Nodes push results here
└── wiki/
    └── *.md                  ← Auto-generated LLM-Wiki documents
```

### Polling Flow

1. **Leader** decomposes a goal → creates task files in `tasks/pending/` → commits + pushes
2. **Deputy/Worker** daemons poll every N seconds → detect new tasks matching their role
3. Node picks up task → moves to `in_progress/` → executes via local Ollama
4. On completion → writes result → moves to `completed/` → updates `state/global_state.json`
5. **Wiki Pipeline** triggers on state changes → auto-generates Markdown documentation

## VRAM-Aware Routing

The Leader assigns tasks based on `complexity_score` (0–10):

| Score | Assigned To | Rationale |
|-------|-------------|-----------|
| 7–10  | Node A only | Requires ≥9B model, long context, code gen |
| 4–6   | Node A preferred | Benefits from larger model, fallback to B |
| 0–3   | Node B | Simple classification, monitoring, execution |

## Quick Start

```bash
git clone <repo-url>
cd llm-wiki-to-init-agents-ochestration
bash infra/init_env.sh             # Auto-detects GPU, pulls correct Ollama model
python scripts/git_sync_daemon.py  # Start polling daemon
```

## Stopping the Daemon (Graceful Shutdown)

The daemon handles `SIGTERM` and `SIGINT` — it **finishes the current task first**, then marks the node offline in `state/global_state.json`, pushes a final commit to Git, and exits.

### Recommended: use the stop script

```bash
bash scripts/stop_daemon.sh           # default 30s grace period
bash scripts/stop_daemon.sh 60        # custom grace period in seconds
```

### Manual signals

```bash
# Graceful (waits for current task to finish, then pushes final state)
kill -TERM $(cat state/daemon.pid)

# Immediate keyboard interrupt (same graceful handler)
Ctrl+C

# Force kill — skips final Git push (last resort only)
kill -KILL $(cat state/daemon.pid)
```

### What happens on graceful stop

1. `_shutdown_requested` flag is set — no new tasks are picked up
2. Current in-progress task runs to completion
3. `node_X_status.is_available = False` is written to `state/global_state.json`
4. Final state is committed and pushed to the shared repo
5. `state/daemon.pid` is removed
6. Process exits 0

## LLM-Wiki

All architectural decisions and troubleshooting are auto-documented in `wiki/` as Markdown, pushed to this repo. See `wiki_generator/pipeline.py` for generation logic.
