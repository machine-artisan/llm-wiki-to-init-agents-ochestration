"""
verify_deputy.py — Deputy(gemma3:27b) 역할 적합성 검증 스크립트.

Claude API 없이 Deputy가 단독으로 아래 4가지 역할을 수행할 수 있는지 확인한다:
  1. 구조화 출력 (JSON)       — Worker 태스크 생성에 필요
  2. 태스크 분해               — Leader 부재 시 스스로 계획
  3. 코드 리뷰                 — Worker 결과물 품질 검증
  4. 이상 감지 / 의사결정      — Worker 실패 시 대응 판단
"""

from __future__ import annotations

import json
import sys
import textwrap
import time
from pathlib import Path

import httpx

OLLAMA_BASE = "http://localhost:11434"
MODEL = "gemma3:27b"
TIMEOUT = 180  # 초 (첫 로드 시 VRAM 적재 시간 포함)

PASS = "✅ PASS"
FAIL = "❌ FAIL"
WARN = "⚠️  WARN"


def generate(prompt: str, system: str = "") -> str:
    payload: dict = {"model": MODEL, "prompt": prompt, "stream": False}
    if system:
        payload["system"] = system
    resp = httpx.post(f"{OLLAMA_BASE}/api/generate", json=payload, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()["response"].strip()


# ── 검증 항목 ─────────────────────────────────────────────────────────────────

def test_json_output() -> tuple[str, str]:
    """구조화 JSON 출력 — Worker 태스크 생성 및 상태 관리에 필수."""
    prompt = (
        "You are a DevOps orchestrator. Decompose this goal into exactly 3 subtasks.\n"
        "Goal: Set up a Python FastAPI service in a Docker container.\n\n"
        'Return ONLY a JSON array with objects having keys "task_id", '
        '"description", "complexity_score" (0-10). No extra text.'
    )
    raw = generate(prompt)
    # JSON 블록 추출 (```json ... ``` 감싸는 경우 처리)
    clean = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        parsed = json.loads(clean)
        assert isinstance(parsed, list) and len(parsed) >= 1
        assert all("task_id" in t and "complexity_score" in t for t in parsed)
        return PASS, f"{len(parsed)} tasks parsed — first: {parsed[0]['description'][:60]}"
    except Exception as exc:
        return FAIL, f"JSON parse failed: {exc}\nRaw output:\n{textwrap.indent(raw[:300], '  ')}"


def test_task_decomposition() -> tuple[str, str]:
    """태스크 분해 — Leader 부재 시 Deputy가 자체적으로 계획 수립."""
    prompt = (
        "You are the Deputy Leader of a multi-agent DevOps system. "
        "The Leader (Claude API) is currently unavailable.\n\n"
        "Goal: Migrate a PostgreSQL 13 database to PostgreSQL 16 with zero downtime.\n\n"
        "List the key phases in order, each with a one-sentence description. "
        "Be concise and technical."
    )
    raw = generate(prompt)
    lines = [l.strip() for l in raw.splitlines() if l.strip()]
    if len(lines) >= 3 and any(
        kw in raw.lower() for kw in ["backup", "replicate", "cutover", "migration", "upgrade"]
    ):
        return PASS, f"{len(lines)} lines — snippet: {lines[0][:80]}"
    return WARN, f"Output lacks expected migration keywords.\nSnippet: {raw[:200]}"


def test_code_review() -> tuple[str, str]:
    """코드 리뷰 — Worker가 생성한 스크립트의 품질 검증."""
    code = textwrap.dedent("""\
        import subprocess, os

        def run_backup(db_name, out_dir):
            cmd = f"pg_dump {db_name} > {out_dir}/{db_name}.sql"
            os.system(cmd)
            print("done")
    """)
    prompt = (
        f"Review this Python script for bugs, security issues, and best practices:\n\n"
        f"```python\n{code}```\n\n"
        "List specific issues found. Be direct."
    )
    raw = generate(prompt)
    issues_found = any(
        kw in raw.lower()
        for kw in ["injection", "shell", "subprocess", "error", "exception", "return"]
    )
    if issues_found:
        return PASS, f"Issues identified — snippet: {raw[:120]}"
    return WARN, f"Review seems shallow.\nSnippet: {raw[:200]}"


def test_anomaly_decision() -> tuple[str, str]:
    """이상 감지 및 의사결정 — Worker 실패 시 Deputy의 판단."""
    prompt = (
        "You are the Deputy Leader. A Worker node reported this error:\n\n"
        "  ERROR: disk usage at 94%, Docker build failed with 'no space left on device'\n\n"
        "Decide: (1) what immediate action to take, (2) whether to escalate to Leader, "
        "(3) what to tell the Worker to do next. Reply in 3 short numbered points."
    )
    raw = generate(prompt)
    has_action = any(
        kw in raw.lower()
        for kw in ["clean", "prune", "space", "disk", "escalat", "leader", "worker"]
    )
    numbered = sum(1 for line in raw.splitlines() if line.strip().startswith(("1", "2", "3")))
    if has_action and numbered >= 2:
        return PASS, f"Actionable response — snippet: {raw[:120]}"
    return WARN, f"Response may lack clarity.\nSnippet: {raw[:200]}"


# ── Runner ────────────────────────────────────────────────────────────────────

TESTS = [
    ("Structured JSON output",      test_json_output),
    ("Task decomposition (no Leader)", test_task_decomposition),
    ("Code review",                 test_code_review),
    ("Anomaly decision-making",     test_anomaly_decision),
]


def main() -> None:
    print(f"\n{'='*60}")
    print(f"  Deputy Capability Verification — {MODEL}")
    print(f"{'='*60}\n")

    # Check Ollama reachable
    try:
        r = httpx.get(f"{OLLAMA_BASE}/api/tags", timeout=5)
        models = [m["name"] for m in r.json().get("models", [])]
        if not any(MODEL in m for m in models):
            print(f"ABORT: {MODEL} not found in Ollama. Run: ollama pull {MODEL}")
            sys.exit(1)
        print(f"Ollama reachable. {MODEL} present. Starting tests...\n")
    except Exception as exc:
        print(f"ABORT: Cannot reach Ollama at {OLLAMA_BASE} — {exc}")
        sys.exit(1)

    results = []
    for name, fn in TESTS:
        print(f"[{name}]")
        t0 = time.time()
        try:
            status, detail = fn()
        except Exception as exc:
            status, detail = FAIL, str(exc)
        elapsed = time.time() - t0
        print(f"  {status}  ({elapsed:.1f}s)")
        print(f"  {detail}\n")
        results.append(status)

    passed  = sum(1 for r in results if r == PASS)
    warned  = sum(1 for r in results if r == WARN)
    failed  = sum(1 for r in results if r == FAIL)

    print(f"{'='*60}")
    print(f"  Result: {passed} passed  {warned} warned  {failed} failed  / {len(TESTS)} total")
    if failed == 0:
        verdict = "Deputy READY — gemma3:27b can operate without Claude API."
    elif passed + warned == len(TESTS):
        verdict = "Deputy MARGINAL — functional but some responses need review."
    else:
        verdict = "Deputy NOT READY — check FAIL items above."
    print(f"  {verdict}")
    print(f"{'='*60}\n")

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
