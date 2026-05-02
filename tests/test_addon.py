import json
import urllib.parse
from unittest.mock import MagicMock, patch

from mitmproxy import http as mitm_http

from src.addon import DouyinAddon


def _make_flow(url: str, response_body: str, content_type: str = "application/json") -> mitm_http.HTTPFlow:
    """Create a minimal HTTPFlow for testing."""
    req = MagicMock()
    req.pretty_url = url
    req.pretty_host = "www.douyin.com"

    resp = MagicMock()
    resp.headers = {"content-type": content_type}
    resp.get_text.return_value = response_body

    flow = MagicMock(spec=mitm_http.HTTPFlow)
    flow.request = req
    flow.response = resp
    return flow


def _make_addon(download_favorites: bool = False) -> DouyinAddon:
    return DouyinAddon(
        downloader=MagicMock(),
        dedup=MagicMock(),
        catalog=MagicMock(),
        download_favorites=download_favorites,
    )


class TestHandleFavoriteListResponse:
    """Tests for _handle_favorite_list_response (task 3.1)."""

    def test_normal_list_processes_items(self):
        addon = _make_addon(download_favorites=True)
        addon.dedup.is_seen.return_value = False

        items = [
            {
                "aweme_id": "111",
                "user_digged": 1,
                "video": {"play_addr": {"url_list": ["http://cdn/111.mp4"]}},
                "desc": "video 1",
                "author": {"nickname": "user1", "uid": "u1"},
            },
            {
                "aweme_id": "222",
                "user_digged": 1,
                "video": {"play_addr": {"url_list": ["http://cdn/222.mp4"]}},
                "desc": "video 2",
                "author": {"nickname": "user2", "uid": "u2"},
            },
        ]
        body = json.dumps({"aweme_list": items})
        flow = _make_flow(
            "https://www.douyin.com/aweme/v1/web/aweme/favorite/?count=20",
            body,
        )

        addon._handle_favorite_list_response(flow)
        assert addon.dedup.is_seen.call_count == 2
        assert addon.dedup.mark_seen.call_count == 2
        assert addon.catalog.append.call_count == 2

    def test_empty_list_no_processing(self):
        addon = _make_addon(download_favorites=True)

        body = json.dumps({"aweme_list": []})
        flow = _make_flow(
            "https://www.douyin.com/aweme/v1/web/aweme/favorite/?count=20",
            body,
        )

        addon._handle_favorite_list_response(flow)
        addon.dedup.is_seen.assert_not_called()
        addon.catalog.append.assert_not_called()

    def test_no_aweme_list_field(self):
        addon = _make_addon(download_favorites=True)

        body = json.dumps({"status_code": 0})
        flow = _make_flow(
            "https://www.douyin.com/aweme/v1/web/aweme/favorite/?count=20",
            body,
        )

        addon._handle_favorite_list_response(flow)
        addon.dedup.is_seen.assert_not_called()
        addon.catalog.append.assert_not_called()

    def test_dedup_skips_seen_items(self):
        addon = _make_addon(download_favorites=True)
        addon.dedup.is_seen.side_effect = lambda aid: aid == "111"

        items = [
            {
                "aweme_id": "111",
                "user_digged": 1,
                "video": {"play_addr": {"url_list": ["http://cdn/111.mp4"]}},
                "desc": "old",
                "author": {"nickname": "u", "uid": "1"},
            },
            {
                "aweme_id": "222",
                "user_digged": 1,
                "video": {"play_addr": {"url_list": ["http://cdn/222.mp4"]}},
                "desc": "new",
                "author": {"nickname": "u", "uid": "2"},
            },
        ]
        body = json.dumps({"aweme_list": items})
        flow = _make_flow(
            "https://www.douyin.com/aweme/v1/web/aweme/favorite/?count=20",
            body,
        )

        addon._handle_favorite_list_response(flow)
        # Only item 222 should be processed (111 is already seen)
        addon.dedup.mark_seen.assert_called_once_with("222")
        addon.catalog.append.assert_called_once()


class TestFavoriteListIgnoredByDefault:
    """Tests that favorite API is ignored without --download-favorites (task 3.2)."""

    def test_favorite_api_ignored_without_flag(self):
        addon = _make_addon(download_favorites=False)

        items = [
            {
                "aweme_id": "111",
                "user_digged": 1,
                "video": {"play_addr": {"url_list": ["http://cdn/111.mp4"]}},
                "desc": "video",
                "author": {"nickname": "u", "uid": "1"},
            },
        ]
        body = json.dumps({"aweme_list": items})
        flow = _make_flow(
            "https://www.douyin.com/aweme/v1/web/aweme/favorite/?count=20",
            body,
        )

        addon.response(flow)
        addon.dedup.is_seen.assert_not_called()
        addon.catalog.append.assert_not_called()

    def test_favorite_api_processed_with_flag(self):
        addon = _make_addon(download_favorites=True)
        addon.dedup.is_seen.return_value = False

        items = [
            {
                "aweme_id": "111",
                "user_digged": 1,
                "video": {"play_addr": {"url_list": ["http://cdn/111.mp4"]}},
                "desc": "video",
                "author": {"nickname": "u", "uid": "1"},
            },
        ]
        body = json.dumps({"aweme_list": items})
        flow = _make_flow(
            "https://www.douyin.com/aweme/v1/web/aweme/favorite/?count=20",
            body,
        )

        addon.response(flow)
        addon.dedup.mark_seen.assert_called_once_with("111")
        addon.catalog.append.assert_called_once()


class TestSsrAwemeListModalIdGuard:
    """Tests that aweme_list from SSR is only processed when modal_id is in URL."""

    def _make_ssr_body_with_aweme_list(self, items: list[dict]) -> str:
        """Build a minimal SSR HTML body containing aweme_list in a script tag."""
        data_json = json.dumps({"aweme_list": items})
        encoded = urllib.parse.quote(data_json)
        return f'<html><script>self.__pace_f.push([1,"{encoded}"])</script></html>'

    def test_aweme_list_ignored_without_modal_id(self):
        addon = _make_addon()
        addon.dedup.is_seen.return_value = False

        items = [
            {
                "aweme_id": "111",
                "user_digged": 1,
                "video": {"play_addr": {"url_list": ["http://cdn/111.mp4"]}},
                "desc": "video",
                "author": {"nickname": "u", "uid": "1"},
            },
        ]
        body = self._make_ssr_body_with_aweme_list(items)
        flow = _make_flow(
            "https://www.douyin.com/user/self?showTab=like",
            body,
            content_type="text/html",
        )

        addon.response(flow)
        addon.dedup.is_seen.assert_not_called()
        addon.catalog.append.assert_not_called()

    def test_aweme_list_processed_with_modal_id(self):
        addon = _make_addon()
        addon.dedup.is_seen.return_value = False

        items = [
            {
                "aweme_id": "111",
                "user_digged": 1,
                "video": {"play_addr": {"url_list": ["http://cdn/111.mp4"]}},
                "desc": "video",
                "author": {"nickname": "u", "uid": "1"},
            },
        ]
        body = self._make_ssr_body_with_aweme_list(items)
        flow = _make_flow(
            "https://www.douyin.com/user/self?showTab=like&modal_id=111",
            body,
            content_type="text/html",
        )

        addon.response(flow)
        addon.dedup.mark_seen.assert_called_once_with("111")
        addon.catalog.append.assert_called_once()
