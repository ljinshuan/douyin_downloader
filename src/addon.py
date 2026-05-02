import asyncio
import json
import logging
import re
import urllib.parse
from typing import Any

from mitmproxy import http

from src.catalog import JsonlCatalog
from src.dedup import BloomDedup
from src.downloader import VideoDownloader

logger = logging.getLogger(__name__)

# URL patterns for video data
AWEME_DETAIL_PATTERN = re.compile(r"/aweme/v1/web/aweme/detail/")
FAVORITE_LIST_PATTERN = re.compile(r"/aweme/v1/web/aweme/favorite/")
DOUYIN_SSR_PATTERN = re.compile(r"https://www\.douyin\.com/user/self")


class DouyinAddon:
    def __init__(
        self,
        downloader: VideoDownloader,
        dedup: BloomDedup,
        catalog: JsonlCatalog,
        download_favorites: bool = False,
    ):
        self.downloader = downloader
        self.dedup = dedup
        self.catalog = catalog
        self.download_favorites = download_favorites

    def response(self, flow: http.HTTPFlow) -> None:
        url = flow.request.pretty_url
        if not self._is_douyin(flow):
            return

        content_type = flow.response.headers.get("content-type", "")

        # Aweme detail API
        if AWEME_DETAIL_PATTERN.search(url) and "json" in content_type:
            logger.info("Matched aweme detail API: %s", url[:120])
            self._handle_api_response(flow)
            return

        # Favorite list API (only when --download-favorites is enabled)
        if self.download_favorites and FAVORITE_LIST_PATTERN.search(url) and "json" in content_type:
            logger.info("Matched favorite list API: %s", url[:120])
            self._handle_favorite_list_response(flow)
            return

        # SSR page with embedded video data
        if DOUYIN_SSR_PATTERN.search(url) and "html" in content_type:
            logger.info("Matched SSR page: %s", url[:120])
            self._handle_ssr_page(flow)
            return

    def _is_douyin(self, flow: http.HTTPFlow) -> bool:
        return "douyin.com" in flow.request.pretty_host

    def _handle_api_response(self, flow: http.HTTPFlow) -> None:
        """Handle /aweme/v1/web/aweme/detail/ - single video detail."""
        try:
            body = flow.response.get_text(strict=False)
            if not body:
                return
            data = json.loads(body)
            video_detail = self._find_video_detail_in_json(data)
            if video_detail:
                self._process_aweme_item(video_detail)
        except Exception as e:
            logger.error("API response parse error: %s", e)

    def _handle_favorite_list_response(self, flow: http.HTTPFlow) -> None:
        """Handle /aweme/v1/web/aweme/favorite/ - liked video list."""
        try:
            body = flow.response.get_text(strict=False)
            if not body:
                return
            data = json.loads(body)
            aweme_list = data.get("aweme_list")
            if not aweme_list:
                return
            for item in aweme_list:
                self._process_aweme_item(item)
        except Exception as e:
            logger.error("Favorite list response parse error: %s", e)

    def _handle_ssr_page(self, flow: http.HTTPFlow) -> None:
        """Handle SSR page with embedded videoDetail in __pace_f or <script> tags."""
        try:
            body = flow.response.get_text(strict=False)
            if not body:
                return

            # Check both play_addr (snake_case) and playAddr (camelCase)
            if "play_addr" not in body and "playAddr" not in body:
                return

            # Only process aweme_list when viewing a specific video (modal_id in URL)
            allow_aweme_list = "modal_id" in flow.request.pretty_url

            # Pattern 1: self.__pace_f chunks (URL-encoded JSON)
            pace_f_matches = re.findall(
                r'self\.__pace_f\.push\(\[\d+,"(.*?)"\]\)', body, re.DOTALL
            )
            for chunk_text in pace_f_matches:
                try:
                    decoded = urllib.parse.unquote(chunk_text)
                    result = self._extract_from_decoded_text(decoded, allow_aweme_list)
                    if result:
                        return
                except Exception:
                    continue

            # Pattern 2: <script> tags with inline data
            script_matches = re.findall(
                r'<script[^>]*>(.*?)</script>', body, re.DOTALL
            )
            for script_text in script_matches:
                try:
                    decoded = urllib.parse.unquote(script_text)
                    result = self._extract_from_decoded_text(decoded, allow_aweme_list)
                    if result:
                        return
                except Exception:
                    continue

        except Exception as e:
            logger.error("SSR page parse error: %s", e)

    def _extract_from_decoded_text(self, text: str, allow_aweme_list: bool = True) -> bool:
        """Extract video details from decoded SSR text. Returns True if found."""
        # Try videoDetail block (camelCase from SSR) — always allowed
        detail = self._extract_video_detail_from_text(text)
        if detail:
            self._process_aweme_item(detail)
            return True

        # Try aweme_list block (snake_case from API-like SSR data) — gated by modal_id
        if allow_aweme_list and "aweme_list" in text:
            idx = text.find('"aweme_list"')
            if idx != -1:
                start = text.index("[", idx)
                depth = 0
                for i in range(start, min(start + 500000, len(text))):
                    if text[i] == "[":
                        depth += 1
                    elif text[i] == "]":
                        depth -= 1
                        if depth == 0:
                            try:
                                items = json.loads(text[start:i + 1])
                                for item in items:
                                    aweme_id = str(item.get("aweme_id", ""))
                                    if aweme_id and not self.dedup.is_seen(aweme_id):
                                        self._process_aweme_item(item)
                                return True
                            except json.JSONDecodeError:
                                break
        return False

    def _find_video_detail_in_json(self, data: Any) -> dict[str, Any] | None:
        if isinstance(data, dict):
            # camelCase (SSR videoDetail)
            if "awemeId" in data:
                return data
            # snake_case (API response)
            if "aweme_id" in data and "video" in data:
                return data
            if "aweme_detail" in data:
                return data["aweme_detail"]
            for v in data.values():
                result = self._find_video_detail_in_json(v)
                if result:
                    return result
        elif isinstance(data, list):
            for item in data:
                result = self._find_video_detail_in_json(item)
                if result:
                    return result
        return None

    def _extract_video_detail_from_text(self, text: str) -> dict[str, Any] | None:
        if "videoDetail" not in text or "playAddr" not in text:
            return None

        idx = text.find('"videoDetail"')
        if idx == -1:
            return None

        start = text.index("{", idx)
        depth = 0
        for i in range(start, min(start + 50000, len(text))):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start:i + 1])
                    except json.JSONDecodeError:
                        return None
        return None

    def _process_aweme_item(self, item: dict[str, Any]) -> None:
        """Process a single aweme item (supports both camelCase and snake_case)."""
        aweme_id = str(item.get("awemeId", item.get("aweme_id", "")))
        if not aweme_id:
            return

        if self.dedup.is_seen(aweme_id):
            return

        user_digged = item.get("userDigged", item.get("user_digged", 0))
        user_collected = item.get("userCollected", item.get("user_collected", 0))
        if not user_digged and not user_collected:
            logger.info("Skipped (not liked/collected): %s", aweme_id)
            return

        self.dedup.mark_seen(aweme_id)

        # Author info (camelCase or snake_case)
        author = item.get("authorInfo", item.get("author", {}))
        author_nickname = author.get("nickname", "")
        author_uid = str(author.get("uid", ""))

        # Description
        desc = item.get("desc", "")

        # Hashtags
        text_extra = item.get("textExtra", item.get("text_extra", []))
        hashtags = []
        for t in text_extra:
            name = t.get("hashtagName", t.get("hashtag_name", ""))
            if name:
                hashtags.append(name)

        # Video info
        video = item.get("video", {})
        duration = video.get("duration")

        # Play URL
        play_url = self._extract_play_url(video)

        # Cover URL
        cover_url = self._extract_cover_url(video)

        # Create time
        create_time = item.get("createTime", item.get("create_time"))

        record = JsonlCatalog.build_record(
            aweme_id=aweme_id,
            author_nickname=author_nickname,
            author_uid=author_uid,
            desc=desc,
            cover_url=cover_url,
            play_url=play_url,
            duration_ms=duration,
            create_time=create_time,
            file_path=str(self.downloader.dir / f"{aweme_id}.mp4"),
            hashtags=hashtags,
        )

        logger.info("New video: %s - %s (%s)", aweme_id, desc[:50], author_nickname)
        self.catalog.append(record)

        if play_url:
            logger.info("Downloading: %s", aweme_id)
            asyncio.ensure_future(self._download(aweme_id, play_url, cover_url))

    def _extract_play_url(self, video: dict[str, Any]) -> str:
        """Extract play URL from video object (camelCase or snake_case)."""
        # camelCase: playAddr[].src
        play_addrs = video.get("playAddr", video.get("play_addr", []))
        if isinstance(play_addrs, list) and play_addrs:
            first = play_addrs[0]
            if isinstance(first, dict):
                # Try src field
                src = first.get("src", "")
                if src:
                    return src
                # Try url_list
                url_list = first.get("url_list", first.get("urlList", []))
                if url_list:
                    return url_list[0]
        elif isinstance(play_addrs, dict):
            # Sometimes play_addr is a dict with url_list directly
            url_list = play_addrs.get("url_list", play_addrs.get("urlList", []))
            if url_list:
                return url_list[0]
        return ""

    def _extract_cover_url(self, video: dict[str, Any]) -> str:
        """Extract cover URL from video object."""
        # Direct string
        cover = video.get("cover", "")
        if isinstance(cover, str) and cover:
            return cover
        # Object with url_list
        if isinstance(cover, dict):
            url_list = cover.get("url_list", cover.get("urlList", []))
            if url_list:
                return url_list[0]
        # Fallback to originCover / origin_cover
        origin = video.get("originCover", video.get("origin_cover", ""))
        if isinstance(origin, str) and origin:
            return origin
        if isinstance(origin, dict):
            url_list = origin.get("url_list", origin.get("urlList", []))
            if url_list:
                return url_list[0]
        # Fallback to coverUrlList
        cover_list = video.get("coverUrlList", video.get("cover_url_list", []))
        if cover_list:
            return cover_list[0]
        return ""

    async def _download(self, aweme_id: str, play_url: str, cover_url: str) -> None:
        await self.downloader.download_video(play_url, aweme_id)
        if cover_url:
            await self.downloader.download_cover(cover_url, aweme_id)
