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
│ Model: gemma3:27b   │      │ Model: gemma2:2b    │
│                     │      │        or phi3:mini │
└─────────────────────┘      └─────────────────────┘
```

### Tier Responsibilities

| Tier | Node | Model | Responsibilities |
|------|------|-------|-----------------|
| Leader | Claude API | claude-sonnet-4-6 | Task decomposition, routing, Wiki generation trigger |
| Deputy | Node A | gemma3:27b | Complex reasoning, code review, Worker supervision |
| Worker | Node B | gemma2:2b / phi3:mini | Script execution, log analysis, env monitoring |

## Git-Polling Synchronization Strategy

Nodes communicate exclusively through a shared GitHub repository — **Git acts as the State Bus**.

```
GitHub Repo
├── state/
│   ├── global_state.json          ← LangGraph serialized state
│   └── <role>_heartbeat.json      ← Per-node liveness signal
├── tasks/
│   ├── pending/                   ← Leader pushes new tasks here
│   ├── in_progress/               ← Nodes move tasks here on pickup
│   └── completed/                 ← Nodes push results here
└── wiki/
    ├── INDEX.md                   ← Auto-generated index
    └── <domain>/<date>_<id>.md    ← Decision & troubleshooting records
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
| 7–10  | Deputy only | Requires large model, long context, code generation |
| 4–6   | Deputy preferred | Benefits from larger model, fallback to Worker |
| 0–3   | Worker | Simple classification, monitoring, script execution |

## Quick Start

### Step 1 — Leader initializes state (run once on Node A)

```bash
git clone https://github.com/machine-artisan/llm-wiki-to-init-agents-ochestration
cd llm-wiki-to-init-agents-ochestration
pip install -r requirements.txt
python scripts/init_leader_state.py   # creates state/global_state.json and pushes
```

### Step 2 — Each node runs init and starts daemon

```bash
bash infra/init_env.sh             # detects GPU VRAM → pulls correct Ollama model
python scripts/git_sync_daemon.py  # start polling daemon
```

Environment variables (optional):

| Variable | Default | Description |
|----------|---------|-------------|
| `POLL_INTERVAL_SECONDS` | `30` | How often to pull and check for tasks |
| `HEARTBEAT_INTERVAL` | `60` | How often to push a liveness commit |
| `GIT_REMOTE` | `origin` | Remote name to pull/push |
| `GIT_BRANCH` | `main` | Branch to track |

## Stopping the Daemon (Graceful Shutdown)

The daemon handles `SIGTERM` and `SIGINT` — it **finishes the current task first**, marks the node offline in `state/global_state.json`, pushes a final commit, then exits.

```bash
bash scripts/stop_daemon.sh           # default 30s grace period
bash scripts/stop_daemon.sh 60        # custom grace period in seconds
```

Manual signals:

```bash
kill -TERM $(cat state/daemon.pid)   # graceful
kill -KILL $(cat state/daemon.pid)   # force (skips final Git push)
```

## Scaling to Additional Nodes

The system is designed to grow beyond the initial two nodes. When adding Node C or later:

### VRAM thresholds and auto-assigned roles

| VRAM | Auto Role | Model |
|------|-----------|-------|
| ≥ 20 GB | Deputy | gemma3:27b |
| 6 – 19 GB | Worker | gemma2:2b |
| < 6 GB | Worker (CPU) | phi3:mini |

### How to add a new node

1. `git clone` the repo on the new machine
2. Run `bash infra/init_env.sh` — role and model are assigned automatically based on detected VRAM
3. Start `python scripts/git_sync_daemon.py`
4. The daemon will self-register via a heartbeat commit (`state/<role>_heartbeat.json`)

> **Note:** The current `OrchestratorState` tracks exactly two nodes (`node_a_status`, `node_b_status`).
> For a third node, either reuse the `worker` role (Node B and C both poll for `worker` tasks) or
> extend `OrchestratorState` with a `node_c_status` field and add a new `NodeRole` enum value.

### Recommended expansion path

```
Node C (spare GPU ≥ 6GB) → Worker role — increases parallel Worker capacity
Node D (high VRAM ≥ 20GB) → Deputy role — increases Deputy throughput
```

Multiple Workers with the same role will race to pick up tasks from the pending queue; whichever polls first wins. No additional code is needed for Worker-level horizontal scaling.

## LLM-Wiki

All architectural decisions and troubleshooting events are auto-documented under `wiki/` as Markdown files, committed and pushed by the daemon after each qualifying task completes.

```bash
cat wiki/INDEX.md                          # see all generated entries
find wiki/ -name "*.md" | sort -r | head   # latest entries
```

Domain classification is automatic based on task description keywords:

| Domain folder | Trigger keywords |
|---------------|-----------------|
| `infra/` | docker, ollama, gpu, install |
| `orchestration/` | langgraph, state, routing, agent |
| `devops/` | ci, cd, pipeline, git, deploy |
| `troubleshoot/` | error, fail, fix, debug |
| `architecture/` | design, decision, adr, refactor |
| `general/` | (anything else) |

View on GitHub: `https://github.com/machine-artisan/llm-wiki-to-init-agents-ochestration/tree/main/wiki`
