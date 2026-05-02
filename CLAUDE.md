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
make run-favorites          # Start proxy + Chrome with favorite list download enabled
make run-no-browser         # Start proxy only
make stop                   # Stop proxy
make reset                  # Reset bloom filter
make clean                  # Clean downloaded files
uv sync                     # Install dependencies
uv run pytest tests/        # Run tests
```

## Key Design Decisions

- Only downloads videos where `userDigged=true` or `userCollected=true` (like-gated)
- Favorite list API (`/aweme/v1/web/aweme/favorite/`) is ignored by default; use `--download-favorites` to enable
- SSR `aweme_list` is only processed when `modal_id` is present in the URL (prevents batch download when browsing liked tab)
- Video data from SSR `self.__pace_f` chunks (URL-encoded JSON) or API JSON responses
- Supports both camelCase (SSR) and snake_case (API) field names
- playAddr URLs are time-limited; download immediately after intercept
- Must send Referer + User-Agent headers for CDN to allow download
- Bloom filter: capacity=10000, error_rate=1%, persisted to downloads/bloom_filter.bin
- JSONL catalog: one JSON object per line in downloads/videos.jsonl
- Chrome auto-launch with `--proxy-server` and `--user-data-dir` for persistent sessions

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **douyin_downloader** (186 symbols, 290 relationships, 12 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

> If any GitNexus tool warns the index is stale, run `npx gitnexus analyze` in terminal first.

## Always Do

- **MUST run impact analysis before editing any symbol.** Before modifying a function, class, or method, run `gitnexus_impact({target: "symbolName", direction: "upstream"})` and report the blast radius (direct callers, affected processes, risk level) to the user.
- **MUST run `gitnexus_detect_changes()` before committing** to verify your changes only affect expected symbols and execution flows.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before proceeding with edits.
- When exploring unfamiliar code, use `gitnexus_query({query: "concept"})` to find execution flows instead of grepping. It returns process-grouped results ranked by relevance.
- When you need full context on a specific symbol — callers, callees, which execution flows it participates in — use `gitnexus_context({name: "symbolName"})`.

## Never Do

- NEVER edit a function, class, or method without first running `gitnexus_impact` on it.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis.
- NEVER rename symbols with find-and-replace — use `gitnexus_rename` which understands the call graph.
- NEVER commit changes without running `gitnexus_detect_changes()` to check affected scope.

## Resources

| Resource | Use for |
|----------|---------|
| `gitnexus://repo/douyin_downloader/context` | Codebase overview, check index freshness |
| `gitnexus://repo/douyin_downloader/clusters` | All functional areas |
| `gitnexus://repo/douyin_downloader/processes` | All execution flows |
| `gitnexus://repo/douyin_downloader/process/{name}` | Step-by-step execution trace |

## CLI

| Task | Read this skill file |
|------|---------------------|
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` |

<!-- gitnexus:end -->
