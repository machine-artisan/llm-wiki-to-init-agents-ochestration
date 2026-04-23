.PHONY: ingest build lint serve help

VENV_PYTHON := .venv/bin/python
PYTHON := $(shell command -v $(VENV_PYTHON) 2>/dev/null || echo python3)

help:
	@echo "LLM-Wiki Makefile"
	@echo ""
	@echo "  make ingest SRC=sources/<file>  소스 파일을 분석하고 wiki 업데이트 제안"
	@echo "  make build                       wiki/ → index.html 명함 페이지 재생성"
	@echo "  make lint                        wiki/ 건강 상태 점검"
	@echo "  make serve                       index.html 로컬 미리보기 (http://localhost:8000)"

ingest:
ifndef SRC
	$(error SRC 를 지정하세요. 예: make ingest SRC=sources/srs-v1.2.md)
endif
	$(PYTHON) agent/ingest.py $(SRC)

build:
	$(PYTHON) agent/build_card.py

lint:
	@echo "[lint] wiki/ 파일 점검..."
	@test -f wiki/index.md   || (echo "MISSING: wiki/index.md" && exit 1)
	@test -f wiki/log.md     || (echo "MISSING: wiki/log.md" && exit 1)
	@test -f wiki/profile.md || (echo "MISSING: wiki/profile.md" && exit 1)
	@test -f wiki/goals.md   || (echo "MISSING: wiki/goals.md" && exit 1)
	@test -f wiki/schema.md  || (echo "MISSING: wiki/schema.md" && exit 1)
	@echo "[lint] index.md 항목 수: $$(grep -c '^\-' wiki/index.md)"
	@echo "[lint] log.md 항목 수:   $$(grep -c '^## \[' wiki/log.md)"
	@echo "[lint] goals 미완료:      $$(grep -c '\- \[ \]' wiki/goals.md)"
	@echo "[lint] goals 완료:        $$(grep -c '\- \[x\]' wiki/goals.md)"
	@echo "[lint] OK"

serve: build
	@echo "[serve] http://localhost:8000"
	$(PYTHON) -m http.server 8000
