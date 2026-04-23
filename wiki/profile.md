---
title: Project Profile
date: 2026-04-23
tags: [profile, system]
---

# Project Profile

## 정체성

**프로젝트명:** llm-wiki-to-init-agents-ochestration
**유형:** Self-Evolving Multi-Agent DevOps Pipeline + LLM-Wiki Knowledge Base
**저장소:** https://github.com/machine-artisan/llm-wiki-to-init-agents-ochestration
**운영자:** machine-artisan

## 시스템 구성

### 에이전트 계층

| Tier | 정체 | 역할 |
|------|------|------|
| Leader | Claude API (claude-sonnet-4-6) | 목표 분해, 라우팅, Wiki 트리거 |
| Deputy | Node A — gemma3:27b / qwen2.5-coder:32b | 복잡한 추론, 코드 리뷰, Worker 감독 |
| Worker | Node B — gemma2:2b | 스크립트 실행, 모니터링 |

### 하드웨어

| 노드 | GPU | VRAM | CPU | RAM | 역할 |
|------|-----|------|-----|-----|------|
| Node A (워크스테이션) | NVIDIA RTX A5000 | 24 GB | i7-12700F | 64 GB | Deputy Leader |
| Node B (데스크탑) | NVIDIA GeForce GTX 1070 | 8 GB | i5-7500 | 32 GB | Worker |

### 모델 현황

| 모델 | 노드 | 용도 | 상태 |
|------|------|------|------|
| gemma3:27b | Node A | git_sync_daemon 자율 처리 | ✅ 설치됨 |
| qwen2.5-coder:32b | Node A | opencode TUI (tool calling) | 🔄 다운로드 중 |
| gemma2:2b | Node B | git_sync_daemon 자율 처리 | ✅ 설치됨 |

## 통신 아키텍처

- **State Bus:** GitHub 저장소 (Git-Polling)
- **상태 파일:** `state/global_state.json` (LangGraph 직렬화, JSON)
- **폴링 주기:** 30초 (기본값)
- **인증:** GitHub CLI (`gh auth`)

## 현재 구축 상태 (2026-04-23)

| 항목 | 상태 |
|------|------|
| Node A 환경 초기화 | ✅ 완료 |
| Node B 환경 초기화 | ✅ 완료 |
| git_sync_daemon | ⏳ Node A 실행 대기 |
| opencode TUI | 🔄 qwen2.5-coder:32b 다운로드 중 |
| LLM-Wiki 재구조화 | 🔄 진행 중 (이 세션) |

## 관련 페이지

- [Initial System Design](architecture/2026-04-23_initial-system-design.md)
- [Environment Replication Guide](infra/2026-04-23_environment-replication-for-llm.md)
- [Human + Deputy Collaboration](orchestration/2026-04-23_human-deputy-collaboration.md)
