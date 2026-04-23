"""
agent/ingest.py — 소스 파일을 읽고 위키를 업데이트한다.

사용법:
  python agent/ingest.py sources/<파일명>
  python agent/ingest.py sources/srs-v1.2.md

흐름:
  1. 소스 읽기
  2. Ollama(qwen2.5-coder:32b)로 핵심 정보 추출
  3. 관련 wiki/ 페이지 업데이트 제안
  4. wiki/index.md 업데이트
  5. wiki/log.md에 항목 추가
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx

REPO_DIR = Path(__file__).resolve().parent.parent
OLLAMA_BASE = "http://localhost:11434"
INGEST_MODEL = "qwen2.5-coder:32b"  # tool calling 지원 모델 우선
FALLBACK_MODEL = "gemma3:27b"

WIKI_DIR = REPO_DIR / "wiki"
INDEX_FILE = WIKI_DIR / "index.md"
LOG_FILE = WIKI_DIR / "log.md"


def get_available_model() -> str:
    try:
        r = httpx.get(f"{OLLAMA_BASE}/api/tags", timeout=5)
        models = [m["name"] for m in r.json().get("models", [])]
        if any(INGEST_MODEL in m for m in models):
            return INGEST_MODEL
        if any(FALLBACK_MODEL in m for m in models):
            return FALLBACK_MODEL
    except Exception:
        pass
    return FALLBACK_MODEL


def analyze_source(source_text: str, model: str) -> str:
    """소스에서 위키 업데이트에 필요한 핵심 정보를 추출한다."""
    prompt = f"""You are a wiki maintainer. Analyze this source document and produce:

1. A one-paragraph summary
2. Key entities/concepts that need wiki pages
3. Which existing wiki categories this affects (architecture/infra/orchestration/troubleshoot)
4. Specific claims or facts to record

Source:
---
{source_text[:4000]}
---

Respond in Korean. Be concise and structured."""

    payload = {"model": model, "prompt": prompt, "stream": False}
    resp = httpx.post(f"{OLLAMA_BASE}/api/generate", json=payload, timeout=180)
    resp.raise_for_status()
    return resp.json()["response"].strip()


def append_log(operation: str, title: str, description: str) -> None:
    entry = (
        f"\n## [{_now_date()}] {operation} | {title}\n"
        f"{description}\n"
    )
    with LOG_FILE.open("a") as f:
        f.write(entry)
    print(f"[ingest] log 추가: {operation} | {title}")


def _now_date() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def main() -> None:
    if len(sys.argv) < 2:
        print("사용법: python agent/ingest.py sources/<파일명>")
        sys.exit(1)

    source_path = Path(sys.argv[1])
    if not source_path.exists():
        print(f"ERROR: 파일을 찾을 수 없음 — {source_path}")
        sys.exit(1)

    # sources/ 외부 파일 수정 방지
    if "sources" not in str(source_path.resolve()):
        print("WARNING: sources/ 디렉토리 외부 파일은 원본 소스로 취급되지 않습니다.")

    print(f"[ingest] 소스 읽기: {source_path}")
    source_text = source_path.read_text()

    model = get_available_model()
    print(f"[ingest] 분석 모델: {model}")

    print("[ingest] 핵심 정보 추출 중...")
    analysis = analyze_source(source_text, model)

    print("\n" + "="*60)
    print("분석 결과:")
    print("="*60)
    print(analysis)
    print("="*60 + "\n")

    print("[ingest] 위키 업데이트 방법:")
    print("  1. 위 분석을 바탕으로 관련 wiki/ 페이지를 직접 수정하거나")
    print("  2. opencode를 실행해 Deputy에게 위키 업데이트를 요청하세요:")
    print(f"     opencode  # 그 후: '{source_path.name} 소스를 분석해서 위키를 업데이트해줘'")

    # log.md에 ingest 기록
    append_log(
        "ingest",
        source_path.name,
        f"소스 분석 완료. 모델: {model}. 위키 수동 업데이트 필요."
    )


if __name__ == "__main__":
    main()
