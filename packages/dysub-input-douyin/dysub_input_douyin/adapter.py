"""Douyin input adapter.

Extracts video stream URLs from Douyin share pages via the embedded
``window._ROUTER_DATA`` JSON — no yt-dlp or browser automation required.
"""

from __future__ import annotations

import json
import logging
import re

import httpx
from dysub_core.inputs.base import BaseInputAdapter
from dysub_core.models import MediaSource, ParserError

logger = logging.getLogger(__name__)

# Mobile UA is required; desktop UA triggers an obfuscated JS challenge page.
_MOBILE_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 "
    "Mobile/15E148 Safari/604.1"
)

_SHARE_HEADERS = {
    "User-Agent": _MOBILE_UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9",
}

# Headers FFmpeg must send when fetching the CDN redirect URL.
_CDN_HEADERS = {
    "User-Agent": _MOBILE_UA,
    "Referer": "https://www.iesdouyin.com/",
}


class DouyinAdapter(BaseInputAdapter):
    """Adapter for Douyin video links."""

    name = "douyin"

    # Domains that indicate a Douyin source.
    _DOUYIN_DOMAINS = ("douyin.com", "iesdouyin.com")

    def can_handle(self, source: str) -> bool:
        return any(d in source for d in self._DOUYIN_DOMAINS)

    def resolve(self, source: str) -> MediaSource:
        """Resolve a Douyin URL into a MediaSource with a direct stream URL.

        Args:
            source: A Douyin video URL (short link or direct link).

        Returns:
            MediaSource containing the video stream URL readable by FFmpeg.

        Raises:
            ParserError: If the page cannot be fetched or video data is missing.
        """
        try:
            page_text = self._fetch_share_page(source)
        except httpx.HTTPError as exc:
            raise ParserError(
                f"Failed to fetch Douyin share page: {exc}",
                context={"source": source},
            ) from exc

        info = self._extract_video_info(page_text, source)

        stream_url = info.get("stream_url")
        if not stream_url:
            raise ParserError(
                "Could not extract video stream URL from Douyin page",
                context={"source": source},
            )

        return MediaSource(
            stream_url=stream_url,
            source_type="douyin",
            headers=_CDN_HEADERS,
            metadata={
                "title": info.get("title", ""),
                "uploader": info.get("uploader", ""),
                "duration": info.get("duration"),
                "webpage_url": info.get("webpage_url", source),
                "filename": f"{info.get('id', 'douyin_video')}.mp4",
            },
        )

    def _fetch_share_page(self, url: str) -> str:
        """Download the share page HTML (mobile UA)."""
        with httpx.Client(follow_redirects=True, timeout=20) as client:
            response = client.get(url, headers=_SHARE_HEADERS)
            response.raise_for_status()
            return response.text

    def _extract_video_info(self, html: str, source_url: str) -> dict[str, object]:
        """Parse ``window._ROUTER_DATA`` from the share page HTML."""
        match = re.search(
            r"window\._ROUTER_DATA\s*=\s*(\{.*?\});?</script>",
            html,
            re.DOTALL,
        )
        if not match:
            raise ParserError(
                "Douyin share page does not contain window._ROUTER_DATA",
                context={"source": source_url},
            )

        try:
            router_data = json.loads(match.group(1))
        except json.JSONDecodeError as exc:
            raise ParserError(
                "Failed to parse Douyin _ROUTER_DATA JSON",
                context={"source": source_url},
            ) from exc

        try:
            video_page = router_data["loaderData"]["video_(id)/page"]
            item = video_page["videoInfoRes"]["item_list"][0]
        except (KeyError, IndexError) as exc:
            raise ParserError(
                "Douyin _ROUTER_DATA missing video info",
                context={"source": source_url},
            ) from exc

        video = item.get("video", {})
        play_addr = video.get("play_addr", {})
        url_list = play_addr.get("url_list", [])

        if not url_list:
            raise ParserError(
                "Douyin video has no play_addr URLs",
                context={"source": source_url},
            )

        # Convert duration from microseconds (API returns 281915 for ~281s)
        raw_duration = video.get("duration")
        duration_sec = raw_duration / 1000.0 if isinstance(raw_duration, (int, float)) else None

        return {
            "stream_url": url_list[0],
            "id": item.get("aweme_id", ""),
            "title": item.get("desc", ""),
            "uploader": item.get("author", {}).get("nickname", ""),
            "duration": duration_sec,
            "webpage_url": source_url,
        }
