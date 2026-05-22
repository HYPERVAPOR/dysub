"""Local file input adapter."""

from __future__ import annotations

from pathlib import Path

from dysub_core.inputs.base import BaseInputAdapter
from dysub_core.models import MediaSource


class LocalFileAdapter(BaseInputAdapter):
    """Adapter for local audio/video files."""

    name = "local"
    SUPPORTED_EXTS: set[str] = {
        ".mp4",
        ".mkv",
        ".mov",
        ".mp3",
        ".wav",
        ".m4a",
        ".flac",
    }

    def can_handle(self, source: str) -> bool:
        p = Path(source)
        return p.exists() and p.suffix.lower() in self.SUPPORTED_EXTS

    def resolve(self, source: str) -> MediaSource:
        p = Path(source).resolve()
        if not p.exists():
            raise FileNotFoundError(f"File not found: {source}")
        if p.suffix.lower() not in self.SUPPORTED_EXTS:
            raise ValueError(
                f"Unsupported file format: {p.suffix}. "
                f"Supported: {', '.join(sorted(self.SUPPORTED_EXTS))}"
            )
        return MediaSource(
            stream_url=str(p),
            metadata={"filename": p.name, "absolute_path": str(p)},
            source_type="local",
        )
