# Human + Deputy 협업 모드 — Claude 부재 시 운영 패턴

> **Date:** 2026-04-23
> **Status:** ✅ 검증 완료 (opencode + qwen2.5-coder:32b)
> **관련 파일:** `opencode.json`, `AGENTS.md`, `scripts/deputy_cli.py`

## 배경

이 시스템의 원래 Leader는 **Claude API (claude-sonnet-4-6)** 이다.
그러나 Claude Code CLI가 없는 환경, 또는 API 미접속 상태에서도 오케스트레이션을 운영해야 하는 상황이 발생한다.

이 문서는 **사람 오퍼레이터 + Deputy LLM(opencode)** 이 2인 체제로 Leader 역할을 대행하는 패턴을 기술한다.

## 계층 변화

```
[정상]                          [Claude 부재]
Leader (Claude)                 사람 오퍼레이터
    ↓                               ↓
Deputy (Node A)        →        Deputy (opencode, Node A)
    ↓                               ↓
Worker (Node B)                 Worker (Node B)
```

## 협업 인터페이스

### opencode TUI — 대화·파일 작업

Deputy와의 주 인터페이스. 프로젝트 루트에서 `opencode` 실행 시:
- `opencode.json`이 Ollama 백엔드와 `qwen2.5-coder:32b` 모델을 자동 설정
- `AGENTS.md`가 Deputy Leader 시스템 프롬프트와 프로젝트 컨텍스트를 자동 주입
- 파일 읽기·편집·bash 실행이 tool calling으로 처리됨

**사용 가능한 인터랙션 패턴:**

```
사람: "현재 pending 태스크가 몇 개야?"
Deputy: [cat state/global_state.json 실행 후] "pending 2개, assigned_to=deputy 1개..."

사람: "core/nodes.py deputy_node 함수 리뷰해줘"
Deputy: [파일 직접 읽기 후 분석 결과 제시]

사람: "Node B 8GB VRAM에서 실행할 수 있는 모델 중 tool calling 지원하는 거 뭐가 있어?"
Deputy: [추론 후 답변]
```

### deputy_cli.py — 오케스트레이션 조작

opencode는 대화·코딩에 특화. 오케스트레이션 상태 조작은 별도 CLI 사용.

```bash
# 태스크 주입 (pending_tasks에 추가 후 git push)
python scripts/deputy_cli.py task

# 현재 노드 상태 요약
python scripts/deputy_cli.py state
```

## 역할 분담 지침

| 작업 유형 | 담당 |
|-----------|------|
| 아키텍처 결정, 코드 리뷰, 복잡한 분석 | Deputy (opencode) |
| 태스크 생성·주입, 우선순위 결정 | 사람 오퍼레이터 |
| 단위 스크립트 실행, 모니터링 | Worker 데몬 자동 처리 |
| Wiki 문서화 | Deputy 또는 자동 파이프라인 |

## opencode 설정 파일 역할

### `opencode.json`

```json
{
  "model": "ollama/qwen2.5-coder:32b",
  "agent": {
    "deputy": {
      "model": "ollama/qwen2.5-coder:32b",
      "prompt": "AGENTS.md",
      "permission": { "edit": "ask", "bash": { ... } }
    }
  }
}
```

- `model`: opencode 기본 모델 (`gemma3:27b`는 tool calling 미지원으로 교체됨)
- `permission.bash`: 허용된 명령은 자동 실행, `"*": "ask"`는 매번 확인

### `AGENTS.md`

Deputy의 역할, 프로젝트 구조, 태스크 라우팅 정책, 파일 위치를 기술한 시스템 프롬프트.
opencode 실행 시 자동 로드되며 Deputy가 컨텍스트 없이도 프로젝트를 이해하게 한다.

## 검증된 작동 조건

| 항목 | 요구사항 |
|------|----------|
| VRAM | ≥ 20GB (qwen2.5-coder:32b ~19GB) |
| Ollama | 서버 실행 중 (`pgrep -a ollama`) |
| opencode | 설치됨 (`~/.opencode/bin/opencode`) |
| 모델 | `qwen2.5-coder:32b` pull 완료 |
| PATH | `~/.opencode/bin` 포함 |
