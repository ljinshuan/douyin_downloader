.PHONY: run stop reset clean test

PORT ?= 8081
DOWNLOAD_DIR ?= downloads

run:
	uv run python -m src.main --port $(PORT)

run-favorites:
	uv run python -m src.main --port $(PORT) --download-favorites

run-no-browser:
	uv run python -m src.main --port $(PORT) --no-browser

stop:
	@PID=$$(lsof -ti:$(PORT) -sTCP:LISTEN 2>/dev/null) && kill $$PID && echo "Stopped proxy on :$(PORT)" || echo "No proxy running on :$(PORT)"

reset:
	uv run python -m src.main --reset-filter

clean:
	rm -rf $(DOWNLOAD_DIR)/*.mp4 $(DOWNLOAD_DIR)/*.jpeg $(DOWNLOAD_DIR)/bloom_filter.bin $(DOWNLOAD_DIR)/videos.jsonl

test:
	uv run pytest tests/ -x -q
