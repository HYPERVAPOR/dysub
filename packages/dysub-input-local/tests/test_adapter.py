"""Tests for local file input adapter."""

from pathlib import Path

import pytest
from dysub_input_local.adapter import LocalFileAdapter


class TestLocalFileAdapter:
    @pytest.fixture
    def adapter(self):
        return LocalFileAdapter()

    def test_can_handle_existing_video(self, tmp_path: Path, adapter: LocalFileAdapter) -> None:
        video = tmp_path / "test.mp4"
        video.write_text("fake")
        assert adapter.can_handle(str(video)) is True

    def test_can_handle_missing_file(self, tmp_path: Path, adapter: LocalFileAdapter) -> None:
        missing = tmp_path / "missing.mp4"
        assert adapter.can_handle(str(missing)) is False

    def test_can_handle_unsupported_ext(self, tmp_path: Path, adapter: LocalFileAdapter) -> None:
        txt = tmp_path / "test.txt"
        txt.write_text("fake")
        assert adapter.can_handle(str(txt)) is False

    def test_resolve_success(self, tmp_path: Path, adapter: LocalFileAdapter) -> None:
        video = tmp_path / "test.mp4"
        video.write_text("fake")
        result = adapter.resolve(str(video))
        assert result.source_type == "local"
        assert result.metadata["filename"] == "test.mp4"

    def test_resolve_not_found(self, tmp_path: Path, adapter: LocalFileAdapter) -> None:
        missing = tmp_path / "missing.mp4"
        with pytest.raises(FileNotFoundError):
            adapter.resolve(str(missing))

    def test_resolve_unsupported_ext(self, tmp_path: Path, adapter: LocalFileAdapter) -> None:
        txt = tmp_path / "test.txt"
        txt.write_text("fake")
        with pytest.raises(ValueError, match="Unsupported file format"):
            adapter.resolve(str(txt))
