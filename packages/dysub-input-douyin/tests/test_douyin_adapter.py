"""Tests for Douyin input adapter."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from dysub_core.models import ParserError
from dysub_input_douyin.adapter import DouyinAdapter


def _make_router_data(
    aweme_id: str = "12345",
    desc: str = "Test Video",
    nickname: str = "Creator",
    duration: int = 120000,
    urls: list[str] | None = None,
) -> str:
    """Return a minimal Douyin share-page HTML with _ROUTER_DATA."""
    url_list = urls if urls is not None else ["https://example.com/video.mp4"]
    data = {
        "loaderData": {
            "video_(id)/page": {
                "videoInfoRes": {
                    "item_list": [
                        {
                            "aweme_id": aweme_id,
                            "desc": desc,
                            "author": {"nickname": nickname},
                            "video": {
                                "duration": duration,
                                "play_addr": {
                                    "uri": "v0test",
                                    "url_list": url_list,
                                },
                            },
                        }
                    ]
                }
            }
        }
    }
    import json

    return f"<script>window._ROUTER_DATA = {json.dumps(data, ensure_ascii=False)};</script>"


class TestDouyinAdapter:
    @pytest.fixture
    def adapter(self) -> DouyinAdapter:
        return DouyinAdapter()

    # ------------------------------------------------------------------
    # can_handle
    # ------------------------------------------------------------------

    @pytest.mark.parametrize(
        "url,expected",
        [
            ("https://v.douyin.com/xxxxx", True),
            ("https://www.douyin.com/video/12345", True),
            ("https://www.iesdouyin.com/share/video/12345", True),
            ("https://www.youtube.com/watch?v=abc", False),
            ("/tmp/video.mp4", False),
        ],
    )
    def test_can_handle(self, adapter: DouyinAdapter, url: str, expected: bool) -> None:
        assert adapter.can_handle(url) is expected

    # ------------------------------------------------------------------
    # resolve — success path
    # ------------------------------------------------------------------

    def test_resolve_success(self, adapter: DouyinAdapter) -> None:
        html = _make_router_data()
        mock_resp = MagicMock()
        mock_resp.text = html
        mock_resp.raise_for_status = MagicMock()

        with patch("dysub_input_douyin.adapter.httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get.return_value = mock_resp
            mock_client_cls.return_value = mock_client

            result = adapter.resolve("https://v.douyin.com/xxxxx")

        assert result.source_type == "douyin"
        assert result.stream_url == "https://example.com/video.mp4"
        assert result.headers is not None
        assert "User-Agent" in result.headers
        assert "Referer" in result.headers
        assert result.metadata["title"] == "Test Video"
        assert result.metadata["uploader"] == "Creator"
        assert result.metadata["duration"] == 120.0  # 120000 ms → 120 s
        assert result.metadata["filename"] == "12345.mp4"

    def test_resolve_duration_none(self, adapter: DouyinAdapter) -> None:
        """Handle videos where duration field is missing."""
        html = _make_router_data(duration=0)
        mock_resp = MagicMock()
        mock_resp.text = html
        mock_resp.raise_for_status = MagicMock()

        with patch("dysub_input_douyin.adapter.httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get.return_value = mock_resp
            mock_client_cls.return_value = mock_client

            result = adapter.resolve("https://v.douyin.com/xxxxx")
            assert result.metadata["duration"] == 0.0

    # ------------------------------------------------------------------
    # resolve — error paths
    # ------------------------------------------------------------------

    def test_resolve_http_error(self, adapter: DouyinAdapter) -> None:
        import httpx

        with patch("dysub_input_douyin.adapter.httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get.side_effect = httpx.HTTPError("Connection refused")
            mock_client_cls.return_value = mock_client

            with pytest.raises(ParserError, match="Failed to fetch Douyin share page"):
                adapter.resolve("https://v.douyin.com/xxxxx")

    def test_resolve_no_router_data(self, adapter: DouyinAdapter) -> None:
        mock_resp = MagicMock()
        mock_resp.text = "<html><body>no data</body></html>"
        mock_resp.raise_for_status = MagicMock()

        with patch("dysub_input_douyin.adapter.httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get.return_value = mock_resp
            mock_client_cls.return_value = mock_client

            with pytest.raises(ParserError, match="does not contain window._ROUTER_DATA"):
                adapter.resolve("https://v.douyin.com/xxxxx")

    def test_resolve_no_video_info(self, adapter: DouyinAdapter) -> None:
        mock_resp = MagicMock()
        mock_resp.text = '<script>window._ROUTER_DATA = {"loaderData": {}};</script>'
        mock_resp.raise_for_status = MagicMock()

        with patch("dysub_input_douyin.adapter.httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get.return_value = mock_resp
            mock_client_cls.return_value = mock_client

            with pytest.raises(ParserError, match="missing video info"):
                adapter.resolve("https://v.douyin.com/xxxxx")

    def test_resolve_empty_url_list(self, adapter: DouyinAdapter) -> None:
        html = _make_router_data(urls=[])
        mock_resp = MagicMock()
        mock_resp.text = html
        mock_resp.raise_for_status = MagicMock()

        with patch("dysub_input_douyin.adapter.httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get.return_value = mock_resp
            mock_client_cls.return_value = mock_client

            with pytest.raises(ParserError, match="has no play_addr URLs"):
                adapter.resolve("https://v.douyin.com/xxxxx")
