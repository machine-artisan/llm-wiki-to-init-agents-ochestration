# Wiki Log

append-only. 수정·삭제 금지.
파싱: `grep "^## \[" wiki/log.md | tail -10`

---

## [2026-04-23] create | Initial system design ADR
3-tier 에이전트 아키텍처, Git-as-State-Bus, VRAM 라우팅 근거 문서화.

## [2026-04-23] create | Node A model correction
gemma2:9b → gemma3:27b 교체 경위 기록. 이미 설치된 모델과 코드 불일치 수정.

## [2026-04-23] create | OpenCode model split
gemma3:27b(daemon) / qwen2.5-coder:32b(opencode) 분리 결정. tool calling 미지원 문제 해결.

## [2026-04-23] create | Environment replication guide
새 워크스테이션/LLM을 위한 부트스트랩 가이드. 알려진 5가지 함정 포함.

## [2026-04-23] create | Human-Deputy collaboration pattern
Claude 부재 시 사람+Deputy 2인 운영 패턴. opencode 인터페이스 문서화.

## [2026-04-23] build | LLM-Wiki Karpathy 표준 전환
자체 양식 → Karpathy LLM-Wiki 패턴으로 전환.
CLAUDE.md, wiki/schema.md, wiki/profile.md, wiki/interests.md, wiki/goals.md 생성.
sources/, agent/, Makefile, index.html 추가.

## [2026-04-23] build | index.html
wiki/profile.md, goals.md, interests.md로부터 명함 페이지 재생성.

## [2026-04-23] install | qwen2.5-coder:32b
Node A에 qwen2.5-coder:32b 다운로드 완료. gemma3:27b와 함께 두 모델 모두 가동 확인. opencode TUI tool-calling 준비 완료.
