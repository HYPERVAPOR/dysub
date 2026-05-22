"""Tests for ASR client."""

from __future__ import annotations

from pathlib import Path

import pytest
from dysub_core.asr.client import ASRClient
from dysub_core.models import APIQuotaExceeded, ContentFilterError, InvalidAPIKey


class TestTranscribe:
    async def test_success(self, httpx_mock, tmp_path: Path) -> None:
        wav = tmp_path / "test.wav"
        wav.write_bytes(b"RIFF\x00\x00\x00\x00WAVE")

        httpx_mock.add_response(
            url="https://api.openai.com/v1/audio/transcriptions",
            text="1\n00:00:00,000 --> 00:00:05,000\nHello world\n",
            status_code=200,
        )

        client = ASRClient(api_key="sk-test")
        result = await client.transcribe(wav, language="zh")
        assert "Hello world" in result

    async def test_invalid_key_raises_immediately(self, httpx_mock, tmp_path: Path) -> None:
        wav = tmp_path / "test.wav"
        wav.write_bytes(b"RIFF\x00\x00\x00\x00WAVE")

        httpx_mock.add_response(
            url="https://api.openai.com/v1/audio/transcriptions",
            status_code=401,
            text="Unauthorized",
        )

        client = ASRClient(api_key="sk-bad")
        with pytest.raises(InvalidAPIKey):
            await client.transcribe(wav, language="zh")

        # Should NOT retry on 401
        assert len(httpx_mock.get_requests()) == 1

    async def test_429_retries_then_succeeds(self, httpx_mock, tmp_path: Path) -> None:
        wav = tmp_path / "test.wav"
        wav.write_bytes(b"RIFF\x00\x00\x00\x00WAVE")

        httpx_mock.add_response(status_code=429, text="Rate limited")
        httpx_mock.add_response(status_code=429, text="Rate limited")
        httpx_mock.add_response(
            status_code=200,
            text="1\n00:00:00,000 --> 00:00:05,000\nSuccess\n",
        )

        client = ASRClient(api_key="sk-test")
        result = await client.transcribe(wav, language="zh")
        assert "Success" in result
        assert len(httpx_mock.get_requests()) == 3

    async def test_429_all_retries_exhausted(self, httpx_mock, tmp_path: Path) -> None:
        wav = tmp_path / "test.wav"
        wav.write_bytes(b"RIFF\x00\x00\x00\x00WAVE")

        for _ in range(3):
            httpx_mock.add_response(status_code=429, text="Rate limited")

        client = ASRClient(api_key="sk-test")
        with pytest.raises(APIQuotaExceeded):
            await client.transcribe(wav, language="zh")

        assert len(httpx_mock.get_requests()) == 3

    async def test_content_filter(self, httpx_mock, tmp_path: Path) -> None:
        wav = tmp_path / "test.wav"
        wav.write_bytes(b"RIFF\x00\x00\x00\x00WAVE")

        httpx_mock.add_response(
            status_code=400,
            text='{"error": "content_policy_violation"}',
        )

        client = ASRClient(api_key="sk-test")
        with pytest.raises(ContentFilterError):
            await client.transcribe(wav, language="zh")

    async def test_empty_api_key(self) -> None:
        with pytest.raises(InvalidAPIKey):
            ASRClient(api_key="")
