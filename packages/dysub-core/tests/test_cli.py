"""Tests for CLI commands."""

from __future__ import annotations

from pathlib import Path

from dysub_core.cli import app
from typer.testing import CliRunner

ASSETS = Path(__file__).parents[3] / "tests" / "assets"
SAMPLE_MP4 = ASSETS / "sample.mp4"

runner = CliRunner()


class TestDoctor:
    def test_all_ok(self, monkeypatch) -> None:
        monkeypatch.setenv("DYSUB_ASR_API_KEY", "sk-test")
        result = runner.invoke(app, ["doctor"])
        assert result.exit_code == 0
        assert "All checks passed" in result.output

    def test_missing_ffmpeg(self, monkeypatch) -> None:
        monkeypatch.setenv("PATH", "/nonexistent")
        monkeypatch.setenv("DYSUB_ASR_API_KEY", "sk-test")
        result = runner.invoke(app, ["doctor"])
        assert result.exit_code == 1
        assert "FFmpeg not found" in result.output

    def test_missing_api_key(self, monkeypatch, tmp_path: Path) -> None:
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("DYSUB_ASR_API_KEY", raising=False)
        monkeypatch.setattr("dysub_core.config.DEFAULT_ENV_PATH", tmp_path / "nonexistent")
        result = runner.invoke(app, ["doctor"])
        assert result.exit_code == 1
        assert "api key" in result.output.lower()


class TestProcess:
    def test_missing_api_key(self, monkeypatch, tmp_path: Path) -> None:
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr("dysub_core.config.DEFAULT_ENV_PATH", tmp_path / "nonexistent")
        result = runner.invoke(app, ["process", str(SAMPLE_MP4)])
        assert result.exit_code == 1
        assert "ASR API Key" in result.output

    def test_invalid_format(self) -> None:
        result = runner.invoke(
            app,
            ["process", str(SAMPLE_MP4), "--api-key", "sk-test", "--format", "ass"],
        )
        assert result.exit_code == 1
        assert "Unsupported format" in result.output

    def test_success(self, httpx_mock, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr("dysub_core.config.DEFAULT_ENV_PATH", tmp_path / "nonexistent")
        httpx_mock.add_response(
            url="https://api.openai.com/v1/audio/transcriptions",
            text="1\n00:00:00,000 --> 00:00:05,000\nHello\n",
            status_code=200,
        )
        out_dir = tmp_path / "subs"
        result = runner.invoke(
            app,
            [
                "process",
                str(SAMPLE_MP4),
                "--api-key",
                "sk-test",
                "--output",
                str(out_dir),
                "--temp-dir",
                str(tmp_path / "temp"),
            ],
        )
        assert result.exit_code == 0, result.output
        assert "Done!" in result.output
        assert (out_dir / "sample.srt").exists()


class TestWebui:
    def test_launches(self, monkeypatch) -> None:
        pytest = __import__("pytest")
        webui = pytest.importorskip("webui.app", reason="dysub-webui not installed")
        import types

        mock_demo = types.SimpleNamespace(launch=lambda **kw: None)
        monkeypatch.setattr(webui, "create_ui", lambda: mock_demo)
        result = runner.invoke(app, ["webui"])
        assert result.exit_code == 0
