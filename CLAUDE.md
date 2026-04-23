# CLAUDE.md — llm-wiki-to-init-agents-ochestration

Claude Code가 이 프로젝트에서 세션을 시작할 때 자동으로 읽는 에이전트 행동 지침.

## 프로젝트 정체성

이 프로젝트는 두 가지 레이어로 구성된다:
1. **Multi-Agent DevOps Pipeline** — LangGraph + GitOps 기반 이기종 GPU 노드 오케스트레이션
2. **LLM-Wiki** — 오케스트레이션 과정에서 발생하는 결정과 지식을 자동 축적하는 Karpathy 패턴 위키

## 세션 시작 시 필독 순서

```
1. wiki/schema.md      ← 위키 구조와 운영 규칙
2. wiki/index.md       ← 모든 위키 페이지 목록
3. wiki/log.md         ← 최근 5개 항목 (grep "^## \[" wiki/log.md | tail -5)
4. wiki/profile.md     ← 프로젝트 현재 상태
```

## 핵심 파일 맵

| 파일/디렉토리 | 역할 |
|---------------|------|
| `CLAUDE.md` | Claude Code 행동 지침 (이 파일) |
| `AGENTS.md` | opencode TUI 행동 지침 |
| `opencode.json` | opencode provider/model 설정 |
| `wiki/schema.md` | 위키 운영 규칙 (반드시 준수) |
| `wiki/index.md` | 콘텐츠 카탈로그 (ingest마다 업데이트) |
| `wiki/log.md` | 작업 이력 (append-only) |
| `sources/` | 불변 원본 자료 (LLM이 수정하지 않음) |
| `agent/ingest.py` | 소스 → 위키 업데이트 |
| `agent/build_card.py` | 위키 → index.html 생성 |
| `state/global_state.json` | LangGraph 직렬화 상태 |
| `core/graph_state.py` | OrchestratorState 스키마 |
| `scripts/git_sync_daemon.py` | Git-Polling 데몬 |

## LLM-Wiki 운영 워크플로

### Ingest (새 소스 추가)
1. `sources/`에 원본 파일 추가 (LLM은 sources/를 수정하지 않음)
2. `python agent/ingest.py sources/<파일명>` 실행
3. 또는 수동: 소스 읽기 → 핵심 추출 → 관련 `wiki/` 페이지 업데이트 → `wiki/index.md` 업데이트 → `wiki/log.md`에 항목 추가

### Query (위키 기반 질의응답)
1. `wiki/index.md` 읽기 → 관련 페이지 식별
2. 관련 페이지 읽기 → 답변 합성
3. 가치 있는 분석은 새 위키 페이지로 저장 (지식이 채팅 히스토리로 사라지지 않게)

### Lint (위키 건강 점검)
```bash
make lint
```
확인 항목: 모순된 클레임, 오래된 정보, 고아 페이지, 누락된 크로스-레퍼런스

## 오케스트레이션 운영 규칙

- `state/global_state.json` 수정 후에는 반드시 `git add + commit + push`
- `sources/` 파일은 절대 수정하지 않음 (불변 원본)
- 새로운 아키텍처 결정은 `wiki/architecture/` 또는 `wiki/orchestration/`에 페이지 생성
- 트러블슈팅 해결 후에는 `wiki/troubleshoot/`에 기록

## 모델 사용 규칙

| 모델 | 사용처 |
|------|--------|
| `gemma3:27b` | `git_sync_daemon.py` 자율 태스크 처리 |
| `qwen2.5-coder:32b` | opencode TUI 대화·파일 작업 |
| `gemma2:2b` | Node B 데몬 |
| `claude-sonnet-4-6` | Leader (이 CLI) |
