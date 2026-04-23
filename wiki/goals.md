---
title: Current Goals
date: 2026-04-23
tags: [goals, roadmap]
---

# 현재 목표

## 단기 목표 (이번 주)

- [ ] `qwen2.5-coder:32b` opencode TUI 정상 동작 확인
- [ ] `python scripts/init_leader_state.py` 실행 → `state/global_state.json` 초기화
- [ ] Node A `git_sync_daemon.py` 시작
- [ ] Node B `git_sync_daemon.py` 시작 → 두 노드 동시 폴링 확인
- [ ] LLM-Wiki Karpathy 구조 전환 완료 (이 세션)

## 중기 목표 (이번 달)

- [ ] `agent/ingest.py` 를 통한 자동 위키 업데이트 파이프라인 검증
- [ ] 실제 태스크를 Deputy/Worker에게 라우팅하고 완료까지 자동화
- [ ] `wiki_trigger=true` 태스크 완료 시 위키 자동 생성 동작 확인
- [ ] `make lint` — 위키 건강 점검 자동화
- [ ] opencode + qwen2.5-coder:32b Deputy 역할 검증 (4-item suite)

## 장기 목표

- [ ] 새 소스 투입 → 위키 자동 업데이트 → index.html 재생성 전체 파이프라인 자동화
- [ ] Worker 노드 수평 확장 (Node C 추가) 실증
- [ ] `wiki/log.md` 기반 오케스트레이션 이력 분석 도구
- [ ] 오케스트레이션 결과물을 외부 llm-wiki 저장소로 push하는 파이프라인

## 완료된 목표

- [x] 프로젝트 초기 구조 설계 및 GitHub push
- [x] Node A, Node B `init_env.sh` 정상 동작
- [x] gemma3:27b Node A 설치 완료
- [x] gemma2:2b Node B 설치 완료
- [x] opencode 설치 및 `opencode.json` 설정
- [x] LLM-Wiki 초기 문서 생성 (architecture, infra, orchestration ADR)
- [x] Graceful shutdown 데몬 구현
- [x] LLM-Wiki Karpathy 표준으로 전환
- [x] qwen2.5-coder:32b Node A 설치 완료
