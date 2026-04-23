# LLM-Wiki Index

> Last updated: 2026-04-23
> 아래 항목들은 오케스트레이션 운영 중 자동·수동으로 생성된 기술 결정 및 트러블슈팅 기록이다.

## Architecture

- [2026-04-23 — Initial System Design](architecture/2026-04-23_initial-system-design.md) — 3-tier 에이전트 계층, Git-as-State-Bus 결정, VRAM 라우팅 근거

## Orchestration

- [2026-04-23 — Human + Deputy 협업 모드](orchestration/2026-04-23_human-deputy-collaboration.md) — Claude 부재 시 사람+Deputy 2인 운영 패턴, opencode 인터페이스

## Infra

- [2026-04-23 — Node A Model Correction](infra/2026-04-23_node-a-model-correction.md) — gemma2:9b → gemma3:27b 교체 경위
- [2026-04-23 — OpenCode Model Split](infra/2026-04-23_opencode-model-split.md) — gemma3:27b(daemon) / qwen2.5-coder:32b(opencode) 분리 이유
- [2026-04-23 — Environment Replication Guide](infra/2026-04-23_environment-replication-for-llm.md) — 새 워크스테이션/LLM을 위한 부트스트랩 가이드 및 알려진 함정
