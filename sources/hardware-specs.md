# Hardware Specifications (원본)

> **소스 유형:** 실측 하드웨어 스펙
> **측정일:** 2026-04-23
> **상태:** 불변 원본 — 수정 금지

---

## Node A — 워크스테이션 (Deputy Leader)

### GPU
- **모델:** NVIDIA RTX A5000
- **VRAM:** 24,564 MiB (≈ 24 GB)
- **측정 명령:** `nvidia-smi --query-gpu=name,memory.total --format=csv,noheader`
- **측정값:** `NVIDIA RTX A5000, 24564 MiB`

### CPU / RAM
- CPU: Intel Core i7-12700F
- RAM: 64 GB

### OS / 환경
- OS: Ubuntu 24.04 LTS (WSL2 on Windows)
- Hostname: DESKTOP-6D3K9QC (WSL2)
- Shell: bash

### 설치된 소프트웨어 (2026-04-23)
- Python: 3.12.3
- Ollama: 0.20.7
- opencode: 1.14.21
- Models: gemma3:27b (17 GB), qwen2.5-coder:32b (다운로드 중)

---

## Node B — 데스크탑 (Worker)

### GPU
- **모델:** NVIDIA GeForce GTX 1070
- **VRAM:** 8 GB (명목)

### CPU / RAM
- CPU: Intel Core i5-7500
- RAM: 32 GB

### 설치된 소프트웨어 (2026-04-23)
- Python: 3.12.x (Ubuntu 24.04)
- Ollama: 설치됨
- Models: gemma2:2b

---

## VRAM 라우팅 기준

이 스펙에 기반하여 `infra/init_env.sh`가 자동으로 역할과 모델을 배정한다:

| VRAM | 역할 | Daemon 모델 | opencode 모델 |
|------|------|-------------|----------------|
| ≥ 20 GB | Deputy | gemma3:27b | qwen2.5-coder:32b |
| 6–19 GB | Worker | gemma2:2b | 미지원 |
| < 6 GB | Worker(CPU) | phi3:mini | 미지원 |
