---
title: Technical Interests
date: 2026-04-23
tags: [interests, focus-areas]
---

# 기술 관심사

이 시스템이 탐구하고 발전시키는 기술 영역.

## 핵심 관심사

### 1. Multi-Agent Orchestration
- LangGraph 기반 상태 머신 설계
- 에이전트 역할 계층화 (Leader / Deputy / Worker)
- VRAM-aware 태스크 라우팅
- 에이전트 간 신뢰·권한 모델

### 2. GitOps as Communication Bus
- Git 저장소를 네트워크 대신 State Bus로 활용
- LangGraph State → JSON 직렬화 → Git Commit 패턴
- 물리적으로 분리된 노드의 컨텍스트 공유
- Polling vs Webhook 트레이드오프

### 3. Local LLM Deployment
- Ollama 기반 이기종 GPU 환경 모델 배포
- VRAM별 최적 모델 선택 (gemma3:27b / gemma2:2b / phi3:mini)
- Tool calling 지원 여부에 따른 모델 분리
- 모델 교체 시 영향 범위 관리

### 4. Self-Documenting Systems (LLM-Wiki)
- Karpathy 패턴: 원본 소스 → 위키 → 영속적 지식 축적
- LLM이 유지보수하는 위키 (인간이 직접 작성하지 않음)
- 크로스-레퍼런스 자동 관리
- 지식이 채팅 히스토리로 사라지지 않게 하는 패턴

### 5. Human-AI Collaborative Workflow
- Claude API 부재 시 Human + Deputy 2인 운영 패턴
- opencode TUI를 통한 Deputy LLM 인터페이스
- 오케스트레이션 조작 CLI (task injection, state query)

## 탐구 중인 질문

- Git-Polling 레이턴시(30–60초)를 허용 가능한 유스케이스는?
- Deputy(27B)와 Worker(2B) 사이의 태스크 경계를 어떻게 정밀하게 정의할까?
- LLM-Wiki가 얼마나 커지면 embedding-based RAG가 필요해질까?
- 자율 오케스트레이션이 안전하게 실행할 수 있는 작업의 경계는?

## 관련 외부 자료

- [Karpathy LLM-Wiki Pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [Ollama Model Library](https://ollama.ai/library)
- [opencode Documentation](https://opencode.ai/docs)
