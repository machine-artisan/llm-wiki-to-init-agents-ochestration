# Initial System Design — 3-Tier Multi-Agent Orchestration

> **Session:** manual (pre-automation)
> **Date:** 2026-04-23
> **Author:** Leader (Claude API)
> **Status:** ✅ Implemented

## Decision

Adopt a **3-tier agent hierarchy** (Leader → Deputy → Worker) over Git-Polling as the communication bus between physically separate machines.

## Context

Two heterogeneous workstations are available:
- **Node A:** RTX A5000 (24GB VRAM) — capable of running large local LLMs
- **Node B:** GTX 1070 (8GB VRAM) — limited to lightweight models

A direct network RPC between nodes was considered but rejected to avoid firewall/VPN complexity and to gain a free audit trail.

## Architecture Choices

### Git as State Bus
LangGraph state is serialized to `state/global_state.json` and committed to GitHub. Nodes poll the repo instead of talking to each other directly.

**Trade-off:** 30–60s latency per task hand-off vs. zero infrastructure beyond GitHub access.

### VRAM-Aware Routing
Tasks carry a `complexity_score` (0–10). The Leader routes:
- Score ≥ 7 → Deputy only (requires gemma3:27b scale)
- Score 4–6 → Deputy preferred, Worker fallback
- Score 0–3 → Worker (gemma2:2b sufficient)

### Model Selection (as of 2026-04-23)

| Node | GPU | Model |
|------|-----|-------|
| A (Deputy) | RTX A5000 24GB | gemma3:27b |
| B (Worker) | GTX 1070 8GB | gemma2:2b |

`gemma3:27b` was chosen over `gemma2:9b` — already installed on Node A and offers a full generation improvement at no additional setup cost.

## Scaling Notes

Multiple Workers can share the same role. They race on the pending task queue; first-poll-wins. No code changes required to add a third Worker node.

Adding a second Deputy requires extending `OrchestratorState` with an additional `node_c_status` field.
