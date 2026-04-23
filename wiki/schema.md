# Wiki Schema — 운영 규칙

이 파일은 이 위키의 구조, 규칙, LLM 워크플로를 정의한다.
Karpathy LLM-Wiki 패턴을 따른다. (https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)

## 3-Layer Architecture

```
sources/          ← Raw layer: 불변 원본 자료. LLM이 읽기만 함.
wiki/             ← Wiki layer: LLM이 생성·유지하는 마크다운 파일들.
CLAUDE.md         ← Schema layer: LLM에게 위키 구조와 워크플로를 알려주는 설정.
```

## 위키 디렉토리 구조

```
wiki/
├── schema.md          ← 이 파일. 위키 운영 규칙.
├── profile.md         ← 프로젝트/시스템 정체성
├── interests.md       ← 기술 관심사 및 집중 영역
├── goals.md           ← 현재 목표 (단기·중기·장기)
├── index.md           ← 콘텐츠 카탈로그 (모든 페이지 목록)
├── log.md             ← append-only 작업 이력
├── architecture/      ← 아키텍처 결정 기록 (ADR)
├── infra/             ← 인프라 설정·트러블슈팅 기록
├── orchestration/     ← 오케스트레이션 패턴 기록
└── troubleshoot/      ← 문제 해결 기록
```

## 페이지 규칙

### 파일명 규칙
- 날짜 포함: `YYYY-MM-DD_<slug>.md`
- slug는 소문자, 하이픈 구분
- 예: `2026-04-23_human-deputy-collaboration.md`

### 페이지 헤더 (YAML frontmatter 권장)
```yaml
---
title: 페이지 제목
date: YYYY-MM-DD
sources: [source-file-1.md, source-file-2.md]
tags: [architecture, infra, orchestration]
---
```

### 크로스-레퍼런스
- 관련 페이지는 `[페이지명](../category/filename.md)` 형식으로 링크
- 새 페이지 생성 시 관련 기존 페이지에 역방향 링크 추가

## index.md 규칙

모든 위키 페이지는 `wiki/index.md`에 등록되어야 한다.
형식: `- [제목](path/file.md) — 한 줄 요약 | sources: N | date: YYYY-MM-DD`

LLM은 매 ingest 또는 새 페이지 생성 시 index.md를 업데이트한다.

## log.md 규칙

append-only. 절대 삭제·수정하지 않는다.

항목 형식:
```
## [YYYY-MM-DD] <operation> | <title>
<한 줄 설명>
```

operation 종류:
- `ingest` — 새 소스 처리
- `create` — 새 위키 페이지 생성
- `update` — 기존 페이지 수정
- `query` — 중요한 질의응답 (가치 있는 분석은 페이지로 저장)
- `lint` — 위키 건강 점검
- `build` — index.html 생성

파싱 예시:
```bash
grep "^## \[" wiki/log.md | tail -5   # 최근 5개 항목
grep "ingest" wiki/log.md              # 모든 ingest 이력
```

## Ingest 워크플로

1. `sources/`에 원본 파일 추가 (LLM 수정 금지)
2. `python agent/ingest.py sources/<파일명>` 실행
3. agent가 수행:
   - 소스 읽기 → 핵심 정보 추출
   - 관련 위키 페이지 업데이트 (보통 5–15개 페이지 영향)
   - 새 페이지 필요시 생성
   - `wiki/index.md` 업데이트
   - `wiki/log.md`에 항목 추가

## Query 워크플로

1. `wiki/index.md` 읽기 → 관련 페이지 식별
2. 관련 페이지 읽기 → 합성
3. 답변이 가치 있으면 새 위키 페이지로 저장
4. `wiki/log.md`에 query 항목 추가

## Lint 워크플로

`make lint` 실행. 점검 항목:
- 페이지 간 모순된 클레임
- 새 소스가 무효화한 오래된 주장
- 인바운드 링크 없는 고아 페이지
- 언급됐지만 페이지가 없는 개념
- 누락된 크로스-레퍼런스
- 웹 검색으로 채울 수 있는 데이터 공백
