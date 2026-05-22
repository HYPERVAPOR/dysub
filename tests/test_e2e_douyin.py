"""End-to-end test: Douyin URL → subtitle file."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest
from dysub_core.models import TaskConfig
from dysub_core.pipeline import Pipeline
from dysub_input_douyin.adapter import DouyinAdapter

ASSETS = Path(__file__).parent / "assets"
SAMPLE_MP4 = ASSETS / "sample.mp4"


def _make_share_page_html(
    stream_url: str = "https://example.com/video.mp4",
    aweme_id: str = "1234567890",
    title: str = "Test Douyin Video",
    uploader: str = "test_user",
    duration: int = 5000,
) -> str:
    data = {
        "loaderData": {
            "video_(id)/page": {
                "videoInfoRes": {
                    "item_list": [
                        {
                            "aweme_id": aweme_id,
                            "desc": title,
                            "author": {"nickname": uploader},
                            "video": {
                                "duration": duration,
                                "play_addr": {
                                    "uri": "v0test",
                                    "url_list": [stream_url],
                                },
                            },
                        }
                    ]
                }
            }
        }
    }
    return f"<script>window._ROUTER_DATA = {json.dumps(data, ensure_ascii=False)};</script>"


class TestDouyinE2E:
    async def test_douyin_url_to_srt(self, httpx_mock, tmp_path: Path) -> None:
        """Full flow: Douyin URL → resolve → extract audio → transcribe → SRT."""
        httpx_mock.add_response(
            url="https://api.openai.com/v1/audio/transcriptions",
            text="1\n00:00:00,000 --> 00:00:05,000\n抖音测试字幕\n",
            status_code=200,
        )

        # Mock the Douyin share-page fetch
        page_html = _make_share_page_html(stream_url=str(SAMPLE_MP4))
        mock_resp = MagicMock()
        mock_resp.text = page_html
        mock_resp.raise_for_status = MagicMock()

        with patch("dysub_input_douyin.adapter.httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get.return_value = mock_resp
            mock_client_cls.return_value = mock_client

            adapter = DouyinAdapter()
            source = adapter.resolve("https://v.douyin.com/xxxxx")

        assert source.source_type == "douyin"
        assert source.stream_url == str(SAMPLE_MP4)
        assert source.headers is not None
        assert source.metadata["title"] == "Test Douyin Video"
        assert source.metadata["filename"] == "1234567890.mp4"

        config = TaskConfig(
            temp_dir=tmp_path / "temp",
            output_dir=tmp_path / "out",
            api_key="sk-test",
            output_format="srt",
        )
        pipeline = Pipeline(config)
        result = await pipeline.run(source)

        assert result.exists()
        assert result.name == "1234567890.srt"
        content = result.read_text()
        assert "抖音测试字幕" in content

    async def test_douyin_url_to_txt(self, httpx_mock, tmp_path: Path) -> None:
        """Full flow: Douyin URL → resolve → extract audio → transcribe → TXT."""
        httpx_mock.add_response(
            url="https://api.openai.com/v1/audio/transcriptions",
            text="抖音纯文本输出测试",
            status_code=200,
        )

        page_html = _make_share_page_html(stream_url=str(SAMPLE_MP4))
        mock_resp = MagicMock()
        mock_resp.text = page_html
        mock_resp.raise_for_status = MagicMock()

        with patch("dysub_input_douyin.adapter.httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get.return_value = mock_resp
            mock_client_cls.return_value = mock_client

            adapter = DouyinAdapter()
            source = adapter.resolve("https://v.douyin.com/xxxxx")

        config = TaskConfig(
            temp_dir=tmp_path / "temp",
            output_dir=tmp_path / "out",
            api_key="sk-test",
            output_format="txt",
        )
        pipeline = Pipeline(config)
        result = await pipeline.run(source)

        assert result.name == "1234567890.txt"
        assert result.read_text() == "抖音纯文本输出测试"

    async def test_douyin_url_progress_callback(self, httpx_mock, tmp_path: Path) -> None:
        """Verify progress stages are reported correctly for Douyin source."""
        httpx_mock.add_response(
            url="https://api.openai.com/v1/audio/transcriptions",
            text="1\n00:00:00,000 --> 00:00:05,000\nHello\n",
            status_code=200,
        )

        stages = []

        def progress(stage: str, value: float) -> None:
            stages.append((stage, value))

        page_html = _make_share_page_html(stream_url=str(SAMPLE_MP4))
        mock_resp = MagicMock()
        mock_resp.text = page_html
        mock_resp.raise_for_status = MagicMock()

        with patch("dysub_input_douyin.adapter.httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get.return_value = mock_resp
            mock_client_cls.return_value = mock_client

            adapter = DouyinAdapter()
            source = adapter.resolve("https://v.douyin.com/xxxxx")

        config = TaskConfig(
            temp_dir=tmp_path / "temp",
            output_dir=tmp_path / "out",
            api_key="sk-test",
        )
        pipeline = Pipeline(config)
        await pipeline.run(source, progress=progress)

        assert len(stages) > 0
        assert stages[0][0] == "extracting"
        assert stages[-1][0] == "done"
        assert stages[-1][1] == 1.0


@pytest.mark.network
class TestRealDouyinParsing:
    """Tests that hit the real Douyin network. Marked with 'network' so they
    can be skipped in CI or sandboxed environments.
    """

    def test_resolve_real_douyin_url(self) -> None:
        """Verify we can parse a real Douyin short link and get a working stream URL."""
        adapter = DouyinAdapter()
        source = adapter.resolve("https://v.douyin.com/LtQTEmgLs58/")

        assert source.source_type == "douyin"
        assert source.stream_url.startswith("https://")
        assert "aweme" in source.stream_url or "douyinvod" in source.stream_url
        assert source.headers is not None
        assert "User-Agent" in source.headers
        assert "Referer" in source.headers
        assert source.metadata.get("title")
        assert source.metadata.get("uploader")
        assert source.metadata.get("duration", 0) > 0

    def test_real_stream_url_is_reachable(self) -> None:
        """The resolved stream URL should return a 302 or 200 with video content."""
        adapter = DouyinAdapter()
        source = adapter.resolve("https://v.douyin.com/LtQTEmgLs58/")

        with httpx.Client(follow_redirects=False, timeout=15) as client:
            resp = client.get(source.stream_url, headers=source.headers)

        # The playwm endpoint typically 302-redirects to a CDN URL
        assert resp.status_code in (200, 302)
        if resp.status_code == 302:
            location = resp.headers.get("location", "")
            assert "douyinvod.com" in location or "snssdk.com" in location

    def test_ffmpeg_can_extract_audio_from_real_url(self, tmp_path: Path) -> None:
        """FFmpeg must be able to extract audio using the resolved URL + headers."""
        import subprocess

        adapter = DouyinAdapter()
        source = adapter.resolve("https://v.douyin.com/LtQTEmgLs58/")

        wav_path = tmp_path / "douyin_test.wav"
        header_lines = "\r\n".join(f"{k}: {v}" for k, v in source.headers.items()) + "\r\n"

        result = subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-headers",
                header_lines,
                "-i",
                source.stream_url,
                "-vn",
                "-acodec",
                "pcm_s16le",
                "-ar",
                "16000",
                "-ac",
                "1",
                "-t",
                "3",
                str(wav_path),
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, f"FFmpeg failed: {result.stderr}"
        assert wav_path.exists()
        assert wav_path.stat().st_size > 0
