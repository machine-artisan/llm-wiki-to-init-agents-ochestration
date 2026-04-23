# Node A Model Correction — gemma2:9b → gemma3:27b

> **Date:** 2026-04-23
> **Node:** A (RTX A5000, 24GB VRAM)
> **Status:** ✅ Fixed

## Issue

Initial scaffold hardcoded `gemma2:9b` as the Deputy model, but Node A already had `gemma3:27b` installed and running via Ollama.

Running the daemon in this state would have caused an immediate `httpx` error: Ollama would reject requests for a model that doesn't exist locally.

## Fix

Updated two files:
- `core/nodes.py`: `DEPUTY_MODEL = "gemma3:27b"`
- `infra/init_env.sh`: `select_model()` now returns `gemma3:27b` for VRAM ≥ 20GB

## Why gemma3:27b over gemma2:9b

`gemma3:27b` is a full generation newer and 3× the parameter count. It fits within the 24GB VRAM budget (uses ~17GB loaded). No quantization required.

## Remaining Setup (Node A)

```bash
pip install -r requirements.txt
python scripts/init_leader_state.py
python scripts/git_sync_daemon.py
```
