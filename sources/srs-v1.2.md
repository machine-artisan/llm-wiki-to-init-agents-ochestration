# Software Requirements Specification v1.2 (원본)

> **소스 유형:** 원본 기획 문서
> **작성일:** 2026-04-23
> **상태:** 불변 원본 — 수정 금지

---

## 프로젝트명

llm-wiki-to-init-agents-ochestration

## 1. 시스템 개요

본 시스템은 이기종 워크스테이션 환경에서 LangGraph와 GitOps(Polling 방식)를 결합하여 다중 에이전트가 아키텍처를 스스로 구축하고, 기술적 의사결정 과정을 LLM-Wiki로 자산화하는 Self-Evolving DevOps Pipeline이다.

## 2. 하드웨어 리소스 및 에이전트 프로파일

### Node A (Workstation - High Performance)

- **Spec:** NVIDIA RTX A5000 (24GB), i7-12700F, 64GB RAM
- **Role:** Deputy Leader (The Supervisor). 복잡한 로직 구현, 코드 리뷰, 고성능 sLLM(Gemma-2-9b 이상 혹은 상위 모델) 구동. Leader(Claude)의 지시를 구체화하고 Worker를 감독함.

### Node B (Desktop - Economy)

- **Spec:** NVIDIA GeForce GTX 1070 (8GB), i5-7500, 32GB RAM
- **Role:** Worker (The Executor). 경량화된 sLLM(Gemma-2-2b, Phi-3-mini 등) 구동. 단위 스크립트 실행, 단순 로그 분석 및 환경 모니터링 수행.

## 3. 에이전틱 워크플로우 (Git-Polling Mechanism)

- **Autonomous Polling:** 각 노드의 에이전트는 중앙 GitHub Repository를 주기적으로 Polling하여 자신의 역할에 할당된 새로운 'Task Ticket'이나 'State Update'가 있는지 확인한다.
- **GitOps State Management:** LangGraph의 전역 상태(State)를 JSON 또는 YAML 형태로 직렬화하여 Git Commit으로 기록함으로써, 물리적으로 떨어진 두 대의 컴퓨터가 동일한 Graph Context를 공유한다.

## 4. 기능적 요구사항 (Functional Requirements)

- **Init Module:** 타 환경에서 git clone 후 실행 시, 각 노드의 GPU 사양을 체크하고 그에 적합한 로컬 LLM(Ollama 등)을 자동으로 배포 및 설정한다.
- **Wiki Pipeline:** 오케스트레이션 중 발생하는 트러블슈팅과 아키텍처 변경점을 llm-wiki-blockchain-devops와 같은 도메인별 마크다운 문서로 자동 생성하여 Push한다.
