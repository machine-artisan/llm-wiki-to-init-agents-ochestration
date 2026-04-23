"""
agent/build_card.py — wiki/ 콘텐츠로 index.html 명함 페이지를 생성한다.

사용법:
  python agent/build_card.py
  make build
"""

from __future__ import annotations

import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent.parent
WIKI_DIR = REPO_DIR / "wiki"
OUTPUT = REPO_DIR / "index.html"


def read_md(filename: str) -> str:
    path = WIKI_DIR / filename
    return path.read_text() if path.exists() else ""


def extract_section(md: str, heading: str) -> str:
    """마크다운에서 특정 헤딩 아래 내용을 추출한다."""
    pattern = rf"#{1,3}\s+{re.escape(heading)}\n(.*?)(?=\n#{1,3}\s|\Z)"
    m = re.search(pattern, md, re.DOTALL)
    return m.group(1).strip() if m else ""


def md_table_to_html(md: str) -> str:
    """간단한 마크다운 테이블을 HTML로 변환한다."""
    lines = [l for l in md.splitlines() if l.strip().startswith("|")]
    if not lines:
        return ""
    rows = []
    for i, line in enumerate(lines):
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if i == 0:
            rows.append("<tr>" + "".join(f"<th>{c}</th>" for c in cells) + "</tr>")
        elif set(line.replace("|", "").replace("-", "").replace(" ", "")) == set():
            continue
        else:
            rows.append("<tr>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>")
    return "<table>" + "".join(rows) + "</table>"


def parse_goals(goals_md: str) -> tuple[list[str], list[str]]:
    """goals.md에서 미완료/완료 목표를 파싱한다."""
    pending, done = [], []
    for line in goals_md.splitlines():
        if line.strip().startswith("- [ ]"):
            pending.append(line.strip()[6:])
        elif line.strip().startswith("- [x]"):
            done.append(line.strip()[6:])
    return pending, done


def parse_interests(interests_md: str) -> list[tuple[str, str]]:
    """interests.md에서 (제목, 설명) 리스트를 파싱한다."""
    items = []
    current_title = ""
    current_desc = []
    for line in interests_md.splitlines():
        if line.startswith("### "):
            if current_title:
                items.append((current_title, " ".join(current_desc[:2])))
            current_title = line[4:].strip()
            current_desc = []
        elif line.startswith("- ") and current_title:
            current_desc.append(line[2:].strip())
    if current_title:
        items.append((current_title, " ".join(current_desc[:2])))
    return items


def build_html() -> str:
    profile = read_md("profile.md")
    goals_md = read_md("goals.md")
    interests_md = read_md("interests.md")
    index_md = read_md("index.md")

    project_name = "llm-wiki-to-init-agents-ochestration"
    repo_url = "https://github.com/machine-artisan/llm-wiki-to-init-agents-ochestration"

    pending_goals, done_goals = parse_goals(goals_md)
    interests = parse_interests(interests_md)
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    interests_html = "".join(
        f'<div class="interest-card"><strong>{title}</strong><p>{desc}</p></div>'
        for title, desc in interests[:4]
    )
    goals_html = "".join(f"<li>{g}</li>" for g in pending_goals[:5])
    done_html = "".join(f"<li class='done'>{g}</li>" for g in done_goals[-3:])

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{project_name}</title>
  <style>
    :root {{
      --bg: #0d1117; --surface: #161b22; --border: #30363d;
      --text: #c9d1d9; --muted: #8b949e; --accent: #58a6ff;
      --green: #3fb950; --orange: #d29922;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ background: var(--bg); color: var(--text); font-family: -apple-system, sans-serif; padding: 2rem; }}
    .container {{ max-width: 900px; margin: 0 auto; }}
    header {{ border-bottom: 1px solid var(--border); padding-bottom: 1.5rem; margin-bottom: 2rem; }}
    h1 {{ font-size: 1.5rem; color: var(--accent); }}
    .subtitle {{ color: var(--muted); margin-top: 0.4rem; font-size: 0.9rem; }}
    .badge {{ display: inline-block; padding: 0.2rem 0.6rem; border-radius: 999px;
              font-size: 0.75rem; margin-right: 0.4rem; margin-top: 0.5rem; }}
    .badge-blue {{ background: #1f3352; color: var(--accent); }}
    .badge-green {{ background: #1a2e1a; color: var(--green); }}
    section {{ margin-bottom: 2rem; }}
    h2 {{ font-size: 1rem; color: var(--muted); text-transform: uppercase;
          letter-spacing: 0.08em; margin-bottom: 1rem; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; }}
    .interest-card {{ background: var(--surface); border: 1px solid var(--border);
                      border-radius: 8px; padding: 1rem; }}
    .interest-card strong {{ color: var(--accent); display: block; margin-bottom: 0.4rem; }}
    .interest-card p {{ color: var(--muted); font-size: 0.85rem; line-height: 1.4; }}
    ul {{ list-style: none; }}
    ul li {{ padding: 0.3rem 0; padding-left: 1.2rem; position: relative; color: var(--text); font-size: 0.9rem; }}
    ul li::before {{ content: "○"; position: absolute; left: 0; color: var(--orange); }}
    ul li.done::before {{ content: "●"; color: var(--green); }}
    ul li.done {{ color: var(--muted); }}
    .footer {{ text-align: center; color: var(--muted); font-size: 0.8rem;
               margin-top: 3rem; padding-top: 1rem; border-top: 1px solid var(--border); }}
    a {{ color: var(--accent); text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
  </style>
</head>
<body>
<div class="container">
  <header>
    <h1>{project_name}</h1>
    <p class="subtitle">Self-Evolving Multi-Agent DevOps Pipeline + LLM-Wiki</p>
    <span class="badge badge-blue">LangGraph</span>
    <span class="badge badge-blue">GitOps</span>
    <span class="badge badge-blue">Ollama</span>
    <span class="badge badge-green">Node A: RTX A5000 24GB</span>
    <span class="badge badge-green">Node B: GTX 1070 8GB</span>
  </header>

  <section>
    <h2>기술 관심사</h2>
    <div class="grid">{interests_html}</div>
  </section>

  <section>
    <h2>현재 목표</h2>
    <ul>{goals_html}</ul>
  </section>

  <section>
    <h2>완료된 목표</h2>
    <ul>{done_html}</ul>
  </section>

  <section>
    <h2>리소스</h2>
    <p>
      <a href="{repo_url}" target="_blank">GitHub 저장소</a> ·
      <a href="wiki/index.md" target="_blank">LLM-Wiki Index</a> ·
      <a href="wiki/log.md" target="_blank">운영 로그</a>
    </p>
  </section>

  <div class="footer">
    Generated by agent/build_card.py · {generated}
  </div>
</div>
</body>
</html>"""


def main() -> None:
    html = build_html()
    OUTPUT.write_text(html)
    print(f"[build] index.html 생성 완료: {OUTPUT}")

    # log 기록
    log_path = REPO_DIR / "wiki" / "log.md"
    if log_path.exists():
        from datetime import datetime, timezone
        entry = f"\n## [{datetime.now(timezone.utc).strftime('%Y-%m-%d')}] build | index.html\nwiki/profile.md, goals.md, interests.md로부터 명함 페이지 재생성.\n"
        with log_path.open("a") as f:
            f.write(entry)


if __name__ == "__main__":
    main()
