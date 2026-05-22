"""Core data models for DySub."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class MediaSource(BaseModel):
    """Resolved media source ready for audio extraction."""

    stream_url: str = Field(description="URL or local path readable by FFmpeg")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Optional metadata from parser"
    )
    source_type: str = Field(description="Discriminator, e.g. 'local', 'douyin'")
    headers: dict[str, str] | None = Field(
        default=None, description="HTTP headers FFmpeg should send when fetching URL"
    )


class AudioChunk(BaseModel):
    """A single audio chunk with temporal offset info."""

    file_path: Path
    start_offset_seconds: float = Field(description="Offset of this chunk in the original media")
    duration_seconds: float


class SubtitleSegment(BaseModel):
    """A single subtitle segment."""

    index: int
    start: float
    end: float
    text: str


class TranscriptionResult(BaseModel):
    """Result from ASR service."""

    raw_srt: str
    language: str
    segments: list[SubtitleSegment] = Field(default_factory=list)


class TaskConfig(BaseModel):
    """Configuration for a single transcription task."""

    temp_dir: Path = Field(default=Path("/tmp/dysub"))
    output_dir: Path = Field(default=Path("."))
    api_key: str = Field(default="", description="ASR API key")
    base_url: str | None = Field(default=None, description="Custom ASR base URL")
    concurrency_limit: int = Field(default=2, ge=1)
    keep_temp: bool = Field(default=False)
    language: str = Field(default="zh")
    output_format: str = Field(default="srt", pattern=r"^(srt|vtt|txt)$")


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------


class DySubError(Exception):
    """Base exception for all DySub errors."""

    def __init__(self, message: str, *, context: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.context = context or {}


class InputNotSupported(DySubError):
    """No installed adapter can handle the given input source."""


class ParserError(DySubError):
    """Failed to parse or resolve the input source."""


class AudioProcessError(DySubError):
    """FFmpeg or audio processing failure."""


class APIQuotaExceeded(DySubError):
    """ASR API rate limit or quota exceeded."""


class InvalidAPIKey(DySubError):
    """ASR API key is missing or invalid."""


class ContentFilterError(DySubError):
    """ASR service refused to process due to content policy."""
