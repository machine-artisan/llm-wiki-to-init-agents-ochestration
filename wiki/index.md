# LLM-Wiki Index

Content catalog — one line per page. Parseable: `grep "^\-" wiki/index.md`

---

## sources/ (immutable originals)

- [srs-v1.2.md](../sources/srs-v1.2.md) — SRS v1.2: 시스템 개요, 에이전트 프로파일, Git-Polling 메커니즘 | sources: 1 | date: 2026-04-23
- [hardware-specs.md](../sources/hardware-specs.md) — 실측 하드웨어 스펙: Node A RTX A5000 24GB / Node B GTX 1070 8GB, VRAM 라우팅 기준표 | sources: 1 | date: 2026-04-23

## wiki/ (LLM-maintained)

- [profile.md](profile.md) — 프로젝트 정체성: 하드웨어 구성, 에이전트 계층, 빌드 상태 | sources: 2 | date: 2026-04-23
- [interests.md](interests.md) — 기술 관심사 5개 영역: Multi-Agent Orchestration, GitOps, Local LLM, Self-Documenting, Human-AI Workflow | sources: 1 | date: 2026-04-23
- [goals.md](goals.md) — 단기/중기/장기 목표 체크리스트: qwen 다운로드 완료, 데몬 가동, Wiki 자동화 | sources: 1 | date: 2026-04-23
- [schema.md](schema.md) — Wiki 운영 규칙: 3-레이어 아키텍처, Ingest/Query/Lint 워크플로우 | sources: 0 | date: 2026-04-23
- [architecture/2026-04-23_initial-system-design.md](architecture/2026-04-23_initial-system-design.md) — 3-tier 에이전트 계층, Git-as-State-Bus 결정, VRAM 라우팅 근거 | sources: 2 | date: 2026-04-23
- [orchestration/2026-04-23_human-deputy-collaboration.md](orchestration/2026-04-23_human-deputy-collaboration.md) — Claude 부재 시 사람+Deputy 2인 운영 패턴, opencode 인터페이스 | sources: 1 | date: 2026-04-23
- [infra/2026-04-23_node-a-model-correction.md](infra/2026-04-23_node-a-model-correction.md) — gemma2:9b → gemma3:27b 교체 경위 | sources: 1 | date: 2026-04-23
- [infra/2026-04-23_opencode-model-split.md](infra/2026-04-23_opencode-model-split.md) — gemma3:27b(daemon) / qwen2.5-coder:32b(opencode) 분리 이유 | sources: 1 | date: 2026-04-23
- [infra/2026-04-23_environment-replication-for-llm.md](infra/2026-04-23_environment-replication-for-llm.md) — 새 워크스테이션/LLM 부트스트랩 가이드, 알려진 함정 5가지 | sources: 1 | date: 2026-04-23
- [log.md](log.md) — append-only 운영 로그 | date: 2026-04-23
