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

> **전제조건:** `git`, `curl`, NVIDIA 드라이버(`nvidia-smi`) 설치 완료.
> Python3가 없어도 `init_env.sh`가 자동 설치를 시도한다 (apt / dnf / brew 감지).

### Step 0 — Clone

```bash
git clone https://github.com/machine-artisan/llm-wiki-to-init-agents-ochestration
cd llm-wiki-to-init-agents-ochestration
```

### Step 1 — 환경 초기화 (모든 노드 공통)

```bash
bash infra/init_env.sh
```

이 스크립트가 한 번에 수행하는 것:

| 단계 | 내용 |
|------|------|
| Python3 확인 | 없으면 apt/dnf/brew로 자동 설치 |
| `.venv/` 생성 | `python3 -m venv .venv` |
| 의존성 설치 | `.venv/bin/pip install -r requirements.txt` |
| Ollama 확인 | 없으면 자동 설치 후 서버 시작 |
| 모델 pull | VRAM 감지 → `gemma3:27b` / `gemma2:2b` / `phi3:mini` 자동 선택 |
| node_config 저장 | `state/node_config.json` (role, model, hostname 기록) |

### Step 2 — 가상환경 활성화

```bash
source .venv/bin/activate
```

> 이후 모든 `python` 명령은 `.venv` 안에서 실행된다.
> 쉘을 새로 열 때마다 이 명령을 다시 실행해야 한다.
> 비활성화: `deactivate`

### Step 3 — Node A만: 상태 초기화 (최초 1회)

```bash
# Node A (Deputy / 워크스테이션)에서만 실행
python scripts/init_leader_state.py
```

`state/global_state.json`을 생성하고 GitHub에 push한다.
Node B는 이 파일이 있어야 태스크 처리를 시작한다.

### Step 4 — 데몬 시작

```bash
python scripts/git_sync_daemon.py
```

환경 변수 (선택):

| Variable | Default | Description |
|----------|---------|-------------|
| `POLL_INTERVAL_SECONDS` | `30` | 폴링 주기 (초) |
| `HEARTBEAT_INTERVAL` | `60` | heartbeat 커밋 주기 (초) |
| `GIT_REMOTE` | `origin` | 원격 저장소 이름 |
| `GIT_BRANCH` | `main` | 추적 브랜치 |

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
# init_env.sh 실행 후 venv가 활성화된 상태에서
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

## Interacting with Deputy Without Claude Code CLI

Claude Code CLI가 없을 때 Deputy(gemma3:27b)에게 요청을 전달하는 방법은 3가지다.

### 방법 1 — deputy_cli.py (권장)

프로젝트 내장 CLI. 대화 기록 유지, 태스크 주입, 상태 확인이 모두 가능하다.

```bash
# 대화 모드 (기본)
python scripts/deputy_cli.py

# 태스크 직접 주입 모드
python scripts/deputy_cli.py task
```

대화 중 사용할 수 있는 명령어:

| 입력 | 동작 |
|------|------|
| `/task` | 태스크 주입 모드로 전환 |
| `/state` | global_state.json 요약 출력 |
| `/clear` | 대화 컨텍스트 초기화 |
| `exit` | 종료 |

### 방법 2 — Ollama CLI (간단한 단발 질문)

```bash
ollama run gemma3:27b
# 또는 단발 질문:
echo "List 3 subtasks to deploy a FastAPI service" | ollama run gemma3:27b
```

### 방법 3 — Ollama REST API (스크립트/자동화)

```bash
curl -s http://localhost:11434/api/generate \
  -d '{"model":"gemma3:27b","prompt":"Your prompt here","stream":false}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['response'])"
```

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
