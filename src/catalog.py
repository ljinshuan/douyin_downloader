import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class JsonlCatalog:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, record: dict[str, Any]) -> None:
        line = json.dumps(record, ensure_ascii=False) + "\n"
        try:
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(line)
            logger.info("Recorded video %s to catalog", record.get("aweme_id"))
        except Exception as e:
            logger.error("Failed to write catalog: %s", e)

    @staticmethod
    def build_record(
        aweme_id: str,
        author_nickname: str | None = None,
        author_uid: str | None = None,
        desc: str | None = None,
        cover_url: str | None = None,
        play_url: str | None = None,
        duration_ms: int | None = None,
        create_time: int | None = None,
        file_path: str | None = None,
        hashtags: list[str] | None = None,
    ) -> dict[str, Any]:
        return {
            "aweme_id": aweme_id,
            "author_nickname": author_nickname,
            "author_uid": author_uid,
            "desc": desc,
            "cover_url": cover_url,
            "play_url": play_url,
            "duration_ms": duration_ms,
            "create_time": create_time,
            "download_time": datetime.now(timezone.utc).isoformat(),
            "file_path": file_path,
            "hashtags": hashtags or [],
        }
