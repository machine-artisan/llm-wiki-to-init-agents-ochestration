# OpenCode 모델 분리 — gemma3:27b(daemon) / qwen2.5-coder:32b(opencode)

> **Date:** 2026-04-23
> **Node:** A (RTX A5000, 24GB VRAM)
> **Status:** ✅ Fixed

## 문제

opencode TUI에서 `gemma3:27b`를 사용하면 아래 오류 발생:

```
registry.ollama.ai/library/gemma3:27b does not support tools
```

opencode는 파일 읽기·편집·bash 실행을 모두 **tool call**로 처리한다.
`gemma3:27b`는 Ollama의 OpenAI-compatible API(`/v1/chat/completions`)에서
tool calling 형식을 지원하지 않아 파일시스템 접근 자체가 불가능했다.

## 해결: 용도별 모델 분리

| 용도 | 모델 | 이유 |
|------|------|------|
| `git_sync_daemon` (자율 태스크 처리) | `gemma3:27b` | tool call 불필요, generate API만 사용 |
| `opencode` TUI (대화·파일 작업) | `qwen2.5-coder:32b` | tool calling 검증, 코딩 특화, ~19GB |

## VRAM 여유

RTX A5000 24GB에서 `qwen2.5-coder:32b` Q4 모델은 ~19GB 사용.
두 모델이 동시에 메모리에 상주하지 않으므로 충돌 없음.

## 변경 파일

- `opencode.json`: `model` 및 `agent.deputy.model` → `ollama/qwen2.5-coder:32b`
- `infra/init_env.sh`: Deputy 노드에서 두 모델 모두 pull
