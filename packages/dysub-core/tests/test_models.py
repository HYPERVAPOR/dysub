"""Tests for core data models."""

from pathlib import Path

import pytest
from dysub_core.models import (
    AudioChunk,
    ContentFilterError,
    DySubError,
    InputNotSupported,
    MediaSource,
    SubtitleSegment,
    TaskConfig,
    TranscriptionResult,
)


def test_media_source_defaults() -> None:
    ms = MediaSource(stream_url="/tmp/test.mp4", source_type="local")
    assert ms.stream_url == "/tmp/test.mp4"
    assert ms.metadata == {}
    assert ms.source_type == "local"


def test_audio_chunk() -> None:
    chunk = AudioChunk(
        file_path=Path("/tmp/chunk.wav"),
        start_offset_seconds=600.0,
        duration_seconds=300.0,
    )
    assert chunk.start_offset_seconds == 600.0


def test_subtitle_segment() -> None:
    seg = SubtitleSegment(index=1, start=0.0, end=5.0, text="Hello")
    assert seg.text == "Hello"


def test_transcription_result() -> None:
    tr = TranscriptionResult(raw_srt="1\n00:00:00,000 --> ...", language="zh")
    assert tr.language == "zh"
    assert tr.segments == []


def test_task_config_defaults() -> None:
    cfg = TaskConfig()
    assert cfg.concurrency_limit == 2
    assert cfg.language == "zh"
    assert cfg.output_format == "srt"


def test_task_config_invalid_format() -> None:
    with pytest.raises(ValueError):
        TaskConfig(output_format="ass")


def test_exception_hierarchy() -> None:
    exc = InputNotSupported("test", context={"src": "x"})
    assert isinstance(exc, DySubError)
    assert exc.context == {"src": "x"}

    exc2 = ContentFilterError("blocked")
    assert exc2.context == {}
