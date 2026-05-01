# Douyin Downloader

Mitmproxy-based Douyin video auto-downloader. Intercepts HTTPS traffic when browsing Douyin in Chrome, extracts video metadata, and downloads liked/collected videos + covers with bloom filter deduplication.

## Project Structure

```
src/
├── __init__.py
├── main.py          # CLI entry point, mitmproxy startup, Chrome auto-launch
├── addon.py         # Mitmproxy addon: response interception, like-gate, URL matching
├── downloader.py    # Async video/cover downloader (aiohttp)
├── dedup.py         # Bloom filter dedup (pybloom_live)
└── catalog.py       # JSONL metadata catalog
```

## Tech Stack

- Python 3.13+, managed by uv
- mitmproxy: HTTPS proxy with addon system
- aiohttp: async HTTP downloads
- pybloom_live: bloom filter for dedup

## Commands

```bash
make run                    # Start proxy + Chrome
make run-no-browser         # Start proxy only
make stop                   # Stop proxy
make reset                  # Reset bloom filter
make clean                  # Clean downloaded files
uv sync                     # Install dependencies
uv run pytest tests/        # Run tests
```

## Key Design Decisions

- Only downloads videos where `userDigged=true` or `userCollected=true` (like-gated)
- Favorite list API (`/aweme/v1/web/aweme/favorite/`) is ignored to prevent batch downloads
- Video data from SSR `self.__pace_f` chunks (URL-encoded JSON) or API JSON responses
- Supports both camelCase (SSR) and snake_case (API) field names
- playAddr URLs are time-limited; download immediately after intercept
- Must send Referer + User-Agent headers for CDN to allow download
- Bloom filter: capacity=10000, error_rate=1%, persisted to downloads/bloom_filter.bin
- JSONL catalog: one JSON object per line in downloads/videos.jsonl
- Chrome auto-launch with `--proxy-server` and `--user-data-dir` for persistent sessions
