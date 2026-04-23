# llm-wiki-to-init-agents-ochestration

A **Self-Evolving DevOps Pipeline** combining LangGraph orchestration with GitOps (polling-based) communication across heterogeneous hardware nodes. Architectural decisions and troubleshooting records are automatically accumulated as an **LLM-Wiki** inside this repository.

---

## 1. 3-Tier Agent Architecture

```
┌─────────────────────────────────────────────────────────┐
│              LEADER  (Claude API / Claude Code)         │
│         Task decomposition · Routing · Wiki trigger     │
└────────────────────────┬────────────────────────────────┘
                         │  Git push (task assignment)
           ┌─────────────┴──────────────┐
           │                            │
┌──────────▼──────────┐      ┌──────────▼──────────┐
│  NODE A — Deputy    │      │  NODE B — Worker    │
│  (Supervisor)       │      │  (Executor)         │
│                     │      │                     │
│ RTX A5000  24GB VRAM│      │ GTX 1070   8GB VRAM │
│ i7-12700F  64GB RAM │      │ i5-7500   32GB RAM  │
└─────────────────────┘      └─────────────────────┘
```

### 역할과 모델

| Tier | Node | 용도별 모델 | 역할 |
|------|------|-------------|------|
| Leader | Claude API | claude-sonnet-4-6 | 태스크 분해, 라우팅, Wiki 트리거 |
| Deputy | Node A | **gemma3:27b** (daemon) · **qwen2.5-coder:32b** (opencode) | 복잡한 추론, 코드 리뷰, Worker 감독 |
| Worker | Node B | **gemma2:2b** / phi3:mini (daemon) | 스크립트 실행, 로그 분석, 환경 모니터링 |

> **Node A는 두 개의 모델을 사용한다.**
> `gemma3:27b`는 자율 데몬(`git_sync_daemon.py`)용이고,
> `qwen2.5-coder:32b`는 opencode TUI용이다.
> 이유: `gemma3:27b`는 Ollama OpenAI-compatible API에서 tool calling을 지원하지 않아
> opencode의 파일 접근 기능을 사용할 수 없다. 두 모델이 동시에 메모리에 올라오지 않으므로 VRAM 충돌 없음.

---

## 2. Git-Polling 동기화 전략

노드 간 통신은 공유 GitHub 저장소를 통해서만 이루어진다. **Git이 State Bus 역할을 한다.**

```
GitHub Repo
├── state/
│   ├── global_state.json          ← LangGraph 직렬화 상태 (모든 노드가 공유)
│   └── <role>_heartbeat.json      ← 노드별 생존 신호
├── wiki/
│   ├── INDEX.md
│   └── <domain>/<date>_<id>.md    ← 자동 생성 LLM-Wiki 문서
└── (tasks/ 디렉토리는 state 내 pending_tasks 배열로 관리됨)
```

폴링 흐름:
1. **Leader**가 목표 분해 → `state/global_state.json`의 `pending_tasks`에 태스크 추가 → commit + push
2. **Deputy/Worker** 데몬이 30초마다 pull → 자신에게 배정된 태스크 감지
3. 노드가 태스크 수행 → 결과를 `completed_tasks`에 기록 → `global_state.json` 업데이트 → push
4. **Wiki Pipeline**이 `wiki_trigger=true`인 완료 태스크를 Markdown으로 자동 생성

---

## 3. VRAM 기반 라우팅

Leader는 태스크의 `complexity_score`(0–10)로 라우팅을 결정한다.

| Score | 배정 노드 | 근거 |
|-------|-----------|------|
| 7–10 | Deputy only | 대형 모델, 긴 컨텍스트, 코드 생성 필요 |
| 4–6 | Deputy 우선 | 대형 모델이 유리, Worker 폴백 가능 |
| 0–3 | Worker | 단순 실행·분류·모니터링으로 충분 |

---

## 4. 빠른 시작 (모든 노드 공통)

> **전제조건:** `git`, `curl`, NVIDIA 드라이버(`nvidia-smi`) 설치 완료.
> Python3가 없으면 `init_env.sh`가 자동 설치를 시도한다 (apt / dnf / brew).

### Step 0 — Clone

```bash
git clone https://github.com/machine-artisan/llm-wiki-to-init-agents-ochestration
cd llm-wiki-to-init-agents-ochestration
```

### Step 1 — 환경 초기화

```bash
bash infra/init_env.sh
```

| 단계 | 내용 |
|------|------|
| Python3 확인 | 없으면 apt/dnf/brew로 자동 설치 |
| `.venv/` 생성 | `python3 -m venv .venv` (시스템 패키지 격리) |
| 의존성 설치 | `.venv/bin/pip install -r requirements.txt` |
| opencode 설치 | Deputy 노드(VRAM ≥ 20GB)에서만 자동 설치 |
| Ollama 설치·시작 | 없으면 자동 설치 |
| 모델 pull | VRAM 감지 → 적합한 모델 자동 선택 및 다운로드 |
| node_config 저장 | `state/node_config.json` (role, model, hostname) |

> **설치 후 PATH 갱신 주의:** opencode 설치 직후 같은 쉘에서 `opencode` 명령이 없다면:
> ```bash
> export PATH="${HOME}/.opencode/bin:${PATH}"
> ```
> 새 터미널을 열면 `.bashrc`가 자동 로드되어 해결된다.

### Step 2 — 가상환경 활성화

```bash
source .venv/bin/activate
```

쉘을 새로 열 때마다 실행해야 한다. 비활성화: `deactivate`

### Step 3 — Node A만: 오케스트레이션 상태 초기화 (최초 1회)

```bash
python scripts/init_leader_state.py
```

`state/global_state.json`을 생성하고 GitHub에 push한다.
Node B는 이 파일이 존재해야 태스크 처리를 시작할 수 있다.

### Step 4 — 데몬 시작

```bash
python scripts/git_sync_daemon.py
```

환경 변수(선택):

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `POLL_INTERVAL_SECONDS` | `30` | 폴링 주기(초) |
| `HEARTBEAT_INTERVAL` | `60` | heartbeat 커밋 주기(초) |
| `GIT_REMOTE` | `origin` | 원격 저장소 이름 |
| `GIT_BRANCH` | `main` | 추적 브랜치 |

---

## 5. Claude 부재 시 Human + Deputy 협업 모드

Claude API / Claude Code CLI가 없을 때 **사람이 Deputy(opencode)와 직접 협업**하여 오케스트레이션을 운영하는 방법.

### 동작 계층

| 상황 | 동작 |
|------|------|
| Claude 정상 | Leader → Deputy → Worker 3단 계층 자동화 |
| **Claude 부재** | **사람 + Deputy(opencode)** → Worker 2단 운영 |
| Node A도 오프라인 | Worker 단독으로 단순 태스크만 처리 |

### opencode로 Deputy와 협업하기

```bash
# 프로젝트 루트에서 실행 (opencode.json + AGENTS.md 자동 로드)
cd ~/llm-wiki-to-init-agents-ochestration
opencode
```

opencode가 시작되면 `qwen2.5-coder:32b` 모델이 Deputy Leader 역할로 활성화된다.
`AGENTS.md`의 시스템 프롬프트가 자동으로 적용되므로 별도 설정 없이 프로젝트 컨텍스트를 인식한다.

**Deputy에게 요청할 수 있는 것:**

| 요청 유형 | 예시 |
|-----------|------|
| 파일 읽기·분석 | "README를 읽고 현재 시스템 상태를 요약해줘" |
| 코드 리뷰 | "core/nodes.py의 deputy_node 함수를 리뷰해줘" |
| 태스크 계획 | "FastAPI 서비스를 Docker로 배포하는 3단계 계획을 짜줘" |
| 아키텍처 결정 | "Worker 노드를 2개로 늘리려면 어떻게 수정해야 해?" |
| Wiki 작성 | "오늘 결정한 내용을 wiki/architecture/ 에 문서화해줘" |

**오케스트레이션 조작 (deputy_cli.py):**

```bash
# 태스크를 global_state.json에 주입하고 push
python scripts/deputy_cli.py task

# 현재 노드 상태 및 태스크 큐 확인
python scripts/deputy_cli.py state
```

### opencode 설정 파일

| 파일 | 역할 |
|------|------|
| `opencode.json` | Ollama provider(localhost:11434), qwen2.5-coder:32b 모델, bash 권한 설정 |
| `AGENTS.md` | Deputy Leader 시스템 프롬프트, 프로젝트 구조, 태스크 라우팅 정책 |

> **Node B에서는 opencode 미지원** — `gemma2:2b`는 tool calling을 지원하지 않는다.

---

## 6. Deputy 모델 검증

### 빠른 상태 확인

```bash
pgrep -a ollama          # Ollama 서버 실행 중인지 확인
ollama list              # 설치된 모델 목록
ollama ps                # VRAM에 로드된 모델 (idle이면 정상)

# gemma3:27b 응답 테스트 (데몬용)
curl -s http://localhost:11434/api/generate \
  -d '{"model":"gemma3:27b","prompt":"Reply with one word: ready","stream":false}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['response'])"
```

### Deputy 역할 적합성 4-item 검증

```bash
# venv 활성화 상태에서 실행
python scripts/verify_deputy.py
```

| # | 검증 항목 | 내용 |
|---|-----------|------|
| 1 | Structured JSON output | Worker 태스크 생성용 구조화 응답 |
| 2 | Task decomposition | Leader 부재 시 자체 계획 수립 |
| 3 | Code review | Worker 결과물 품질 검증 |
| 4 | Anomaly decision-making | Worker 실패 시 대응 판단 |

전체 PASS → `Deputy READY — gemma3:27b can operate without Claude API.`

---

## 7. 데몬 종료 (Graceful Shutdown)

데몬은 `SIGTERM` / `SIGINT`를 받으면 현재 태스크를 완료한 뒤, 노드 상태를 offline으로 갱신하고 push한 후 종료한다.

```bash
bash scripts/stop_daemon.sh        # 기본 30초 grace period
bash scripts/stop_daemon.sh 60     # grace period 조정
kill -TERM $(cat state/daemon.pid) # 수동 graceful
kill -KILL $(cat state/daemon.pid) # 강제 종료 (push 생략)
```

---

## 8. 노드 확장

### VRAM별 자동 역할 배정

| VRAM | 자동 역할 | Daemon 모델 | opencode 모델 |
|------|-----------|-------------|----------------|
| ≥ 20 GB | Deputy | gemma3:27b | qwen2.5-coder:32b |
| 6–19 GB | Worker | gemma2:2b | 미지원 |
| < 6 GB | Worker(CPU) | phi3:mini | 미지원 |

### 새 노드 추가 절차

1. 새 머신에서 `git clone` + `bash infra/init_env.sh`
2. `source .venv/bin/activate`
3. `python scripts/git_sync_daemon.py` 시작
4. 데몬이 heartbeat 커밋으로 자동 자기 등록

Worker 노드 추가는 코드 수정 없이 가능하다(선착순 태스크 경쟁).
Deputy 노드 추가는 `core/graph_state.py`의 `OrchestratorState`에 `node_c_status` 필드 확장 필요.

---

## 9. LLM-Wiki

오케스트레이션 중 발생하는 아키텍처 결정·트러블슈팅이 `wiki/` 아래 Markdown으로 자동 기록된다.

```bash
cat wiki/INDEX.md                           # 전체 목록
find wiki/ -name "*.md" | sort -r | head    # 최신 항목
```

| Domain 폴더 | 트리거 키워드 |
|-------------|---------------|
| `infra/` | docker, ollama, gpu, install |
| `orchestration/` | langgraph, state, routing, agent |
| `devops/` | ci, cd, pipeline, git, deploy |
| `troubleshoot/` | error, fail, fix, debug |
| `architecture/` | design, decision, adr, refactor |
| `general/` | (기타) |

GitHub에서 보기: `https://github.com/machine-artisan/llm-wiki-to-init-agents-ochestration/tree/main/wiki`

---

## 10. 알려진 문제 및 해결법

다른 워크스테이션에서 이 환경을 구축할 때 마주칠 수 있는 문제들.

| 증상 | 원인 | 해결 |
|------|------|------|
| `error: externally-managed-environment` | Debian/Ubuntu 시스템 Python에 직접 pip 설치 시도 | `bash infra/init_env.sh` 사용 — `.venv/` 자동 생성 |
| `ModuleNotFoundError: No module named 'core'` | `scripts/` 하위에서 실행 시 repo root가 Python path에 없음 | 프로젝트 루트에서 실행: `python scripts/git_sync_daemon.py` |
| `opencode: command not found` (설치 직후) | `.bashrc`에 PATH 추가됐지만 현재 쉘에 미반영 | `export PATH="${HOME}/.opencode/bin:${PATH}"` 또는 새 터미널 |
| `gemma3:27b does not support tools` | gemma3:27b는 Ollama OpenAI-compatible API에서 tool calling 미지원 | opencode용 모델은 `qwen2.5-coder:32b` 사용 (이미 설정됨) |
| `state/global_state.json not found` | Node A에서 초기화 미실행 | Node A에서 `python scripts/init_leader_state.py` 실행 |
