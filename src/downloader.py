import logging
from pathlib import Path

import aiohttp

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36",
    "Referer": "https://www.douyin.com/",
}


class VideoDownloader:
    def __init__(self, download_dir: str | Path):
        self.dir = Path(download_dir)
        self.dir.mkdir(parents=True, exist_ok=True)

    async def download_video(self, url: str, aweme_id: str) -> str | None:
        dest = self.dir / f"{aweme_id}.mp4"
        if dest.exists() and dest.stat().st_size > 0:
            logger.info("Video already exists: %s", dest)
            return str(dest)
        try:
            async with aiohttp.ClientSession(headers=HEADERS) as session:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        logger.error("Video download failed %s: HTTP %s", aweme_id, resp.status)
                        return None
                    with open(dest, "wb") as f:
                        async for chunk in resp.content.iter_chunked(64 * 1024):
                            f.write(chunk)
            logger.info("Downloaded video: %s (%s bytes)", aweme_id, dest.stat().st_size)
            return str(dest)
        except Exception as e:
            logger.error("Video download error for %s: %s", aweme_id, e)
            return None

    async def download_cover(self, url: str, aweme_id: str) -> str | None:
        dest = self.dir / f"{aweme_id}_cover.jpeg"
        if dest.exists() and dest.stat().st_size > 0:
            logger.info("Cover already exists: %s", dest)
            return str(dest)
        try:
            async with aiohttp.ClientSession(headers=HEADERS) as session:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        logger.warning("Cover download failed %s: HTTP %s", aweme_id, resp.status)
                        return None
                    with open(dest, "wb") as f:
                        async for chunk in resp.content.iter_chunked(64 * 1024):
                            f.write(chunk)
            logger.info("Downloaded cover: %s", dest)
            return str(dest)
        except Exception as e:
            logger.warning("Cover download error for %s: %s", aweme_id, e)
            return None
