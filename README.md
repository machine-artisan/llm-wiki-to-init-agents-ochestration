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

## Verifying Deputy Model (Node A)

Before running the daemon, confirm that `gemma3:27b` is operational and capable of fulfilling the Deputy role.

### Quick health check

```bash
# 1. Ollama 서버 실행 중인지 확인
pgrep -a ollama

# 2. 모델 디스크 설치 확인
ollama list

# 3. VRAM 로드 상태 확인 (idle이면 정상 — 첫 요청 시 자동 로드)
ollama ps

# 4. 단순 응답 테스트 (모델 로드 포함 ~30–60초)
curl -s http://localhost:11434/api/generate \
  -d '{"model":"gemma3:27b","prompt":"Reply with one word: ready","stream":false}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['response'])"
```

### Deputy 역할 적합성 검증 (4-item suite)

```bash
pip install httpx          # 아직 없는 경우
python scripts/verify_deputy.py
```

테스트 항목:

| # | 항목 | 검증 내용 |
|---|------|-----------|
| 1 | Structured JSON output | Worker 태스크 생성을 위한 구조화 응답 |
| 2 | Task decomposition | Leader 부재 시 자체 계획 수립 |
| 3 | Code review | Worker 결과물 품질 검증 |
| 4 | Anomaly decision-making | Worker 실패 시 대응 판단 |

전체 PASS 시 출력: `Deputy READY — gemma3:27b can operate without Claude API.`

---

## Offline / Claude-less Operation

Claude API(`LEADER`)가 없을 때 Deputy(Node A)는 **단독 최상위 의사결정자**로 동작한다.

| 상황 | 동작 |
|------|------|
| Claude API 정상 | Leader → Deputy → Worker 3단 계층 |
| Claude API 미접속 | Deputy가 직접 태스크 분해 + 라우팅 담당 |
| Node A도 오프라인 | Worker만 단순 실행 태스크 처리, 복잡 태스크 대기 |

Deputy 단독 모드에서도 `complexity_score` 기반 라우팅과 Wiki Pipeline은 그대로 동작한다.
Leader 없이 태스크를 직접 주입하려면 `state/global_state.json`의 `pending_tasks` 배열에
태스크를 수동 추가 후 커밋·푸시하면 된다.

---

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
