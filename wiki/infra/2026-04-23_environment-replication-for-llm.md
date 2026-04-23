# 환경 재현 가이드 — 다른 LLM/워크스테이션을 위한 부트스트랩

> **Date:** 2026-04-23
> **대상:** 이 환경을 새 워크스테이션에 구축하려는 LLM 에이전트 또는 사람
> **전제:** Ubuntu 24.04 LTS / WSL2, NVIDIA GPU 탑재

이 문서는 이 프로젝트를 처음 접하는 LLM이 README만으로 놓칠 수 있는 **구축 과정의 함정과 정확한 순서**를 기술한다.

---

## 전체 순서 (검증된 최단 경로)

```
1. 전제조건 확인
2. git clone
3. bash infra/init_env.sh   ← 이 단계가 Python venv, Ollama, 모델, opencode를 모두 처리
4. PATH 반영 (opencode)
5. source .venv/bin/activate
6. [Node A만] python scripts/init_leader_state.py
7. [Node A만] python scripts/verify_deputy.py
8. python scripts/git_sync_daemon.py
```

---

## 단계별 상세

### 1. 전제조건 확인

```bash
git --version           # git 필요
curl --version          # curl 필요 (Ollama, opencode 설치용)
nvidia-smi              # NVIDIA 드라이버 필요
python3 --version       # 없어도 init_env.sh가 설치
```

### 2. Clone

```bash
git clone https://github.com/machine-artisan/llm-wiki-to-init-agents-ochestration
cd llm-wiki-to-init-agents-ochestration
```

### 3. 환경 초기화

```bash
bash infra/init_env.sh
```

이 명령 하나로 아래가 모두 처리된다:
- Python3 없으면 `apt-get install python3 python3-venv python3-full`
- `.venv/` 생성 및 `requirements.txt` 설치 (시스템 Python 오염 방지)
- VRAM ≥ 20GB → Deputy 역할, `gemma3:27b` + `qwen2.5-coder:32b` pull
- VRAM 6–19GB → Worker 역할, `gemma2:2b` pull
- VRAM < 6GB → Worker 역할, `phi3:mini` pull
- Ollama 없으면 자동 설치 후 서버 시작
- opencode 없으면 Deputy 노드에서만 자동 설치
- `state/node_config.json` 생성

### 4. PATH 반영 (opencode, 현재 쉘)

```bash
# init_env.sh 실행 후 같은 터미널에서 opencode가 없다고 나오면:
export PATH="${HOME}/.opencode/bin:${PATH}"

# 새 터미널을 열면 .bashrc가 자동 로드되어 불필요
```

### 5. 가상환경 활성화

```bash
source .venv/bin/activate
# 프롬프트에 (.venv) 표시되면 성공
```

### 6. 오케스트레이션 상태 초기화 (Node A만, 최초 1회)

```bash
python scripts/init_leader_state.py
```

`state/global_state.json`이 생성되고 GitHub에 push된다.
Node B는 이 파일이 있어야 데몬이 태스크를 처리하기 시작한다.

### 7. Deputy 검증 (Node A만)

```bash
python scripts/verify_deputy.py
```

4개 항목 모두 `✅ PASS`이면 준비 완료.

### 8. 데몬 시작

```bash
python scripts/git_sync_daemon.py
# 또는 백그라운드로:
nohup python scripts/git_sync_daemon.py > logs/daemon.log 2>&1 &
```

---

## 알려진 함정 (이전 구축에서 발생한 오류)

### ❌ pip install이 거부되는 경우

```
error: externally-managed-environment
```

**원인:** Ubuntu 24.04는 시스템 Python에 직접 pip 설치를 막는다.
**해결:** `bash infra/init_env.sh`를 사용한다. `.venv/`에 격리 설치한다.
직접 설치가 꼭 필요하면: `pip install --break-system-packages` (비권장)

### ❌ ModuleNotFoundError: No module named 'core'

```
python scripts/git_sync_daemon.py
→ ModuleNotFoundError: No module named 'core'
```

**원인:** `scripts/` 하위 실행 시 Python이 repo root를 path에 추가하지 않는다.
**해결:** 프로젝트 루트에서 실행한다. 모든 스크립트에 `sys.path.insert(0, repo_root)`가 이미 추가되어 있다.

### ❌ opencode: command not found (설치 직후)

**원인:** `~/.opencode/bin`이 현재 쉘 PATH에 없음. `.bashrc`에는 추가됐지만 현재 세션에 미반영.
**해결:** `export PATH="${HOME}/.opencode/bin:${PATH}"` 또는 새 터미널.

### ❌ gemma3:27b does not support tools (opencode 실행 시)

**원인:** `gemma3:27b`는 Ollama OpenAI-compatible API(`/v1/chat/completions`)에서 tool calling 포맷을 지원하지 않는다.
**해결:** `opencode.json`의 모델을 `qwen2.5-coder:32b`로 설정한다 (이미 적용됨).
`gemma3:27b`는 데몬의 generate API 호출에만 사용한다.

### ❌ state/global_state.json not found (Node B 데몬 시작 시)

**원인:** Node A에서 `init_leader_state.py`를 아직 실행하지 않았다.
**해결:** Node A에서 먼저 실행 후 Node B 데몬을 시작한다.

---

## 모델 용도 요약

| 모델 | 용도 | 설치 노드 |
|------|------|-----------|
| `gemma3:27b` | `git_sync_daemon.py` 자율 처리 (generate API) | Node A |
| `qwen2.5-coder:32b` | `opencode` TUI 대화·파일 작업 (tool calling) | Node A |
| `gemma2:2b` | Node B `git_sync_daemon.py` 자율 처리 | Node B |
| `phi3:mini` | VRAM < 6GB 폴백 | 해당 노드 |

---

## 검증 체크리스트

이 환경이 정상 구축됐는지 확인하는 명령들:

```bash
# 1. venv 활성화 확인
which python | grep ".venv"

# 2. Ollama 동작 확인
ollama list

# 3. Deputy 검증
python scripts/verify_deputy.py

# 4. opencode 동작 확인 (Node A)
opencode --version 2>/dev/null || echo "opencode not in PATH"

# 5. 데몬 시작 테스트 (Ctrl+C로 중단 가능)
python scripts/git_sync_daemon.py
```
