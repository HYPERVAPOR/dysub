"""Tests for settings configuration."""

from __future__ import annotations

from pathlib import Path

from dysub_core.config import Settings


class TestSettings:
    def test_defaults(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        s = Settings.load()
        assert s.asr_api_key == ""
        assert s.asr_base_url is None
        assert s.default_language == "zh"
        assert s.default_format == "srt"

    def test_from_env(self, monkeypatch) -> None:
        monkeypatch.setenv("DYSUB_ASR_API_KEY", "sk-test")
        monkeypatch.setenv("DYSUB_ASR_BASE_URL", "https://example.com/v1")
        s = Settings.load()
        assert s.asr_api_key == "sk-test"
        assert s.asr_base_url == "https://example.com/v1"

    def test_from_env_file(self, tmp_path: Path, monkeypatch) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text("DYSUB_ASR_API_KEY=sk-from-file\n")
        monkeypatch.chdir(tmp_path)
        s = Settings.load()
        assert s.asr_api_key == "sk-from-file"
