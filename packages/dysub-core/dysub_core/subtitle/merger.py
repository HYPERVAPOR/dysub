"""SRT parsing, merging, and VTT export."""

from __future__ import annotations

import logging
import re
from typing import overload

from dysub_core.models import SubtitleSegment

logger = logging.getLogger(__name__)

_SRT_TIME_RE = re.compile(r"(\d{2}):(\d{2}):(\d{2}),(\d{3})")
_VTT_TIME_RE = re.compile(r"(\d{2}):(\d{2}):(\d{2})\.(\d{3})")
_REPEAT_RE = re.compile(r"(.)\1{3,}")


def _srt_time_to_seconds(time_str: str) -> float:
    m = _SRT_TIME_RE.match(time_str.strip())
    if not m:
        raise ValueError(f"Invalid SRT time format: {time_str}")
    h, mi, s, ms = map(int, m.groups())
    return h * 3600 + mi * 60 + s + ms / 1000.0


def _seconds_to_srt_time(seconds: float) -> str:
    ms = int((seconds % 1) * 1000)
    total = int(seconds)
    s = total % 60
    m = (total // 60) % 60
    h = total // 3600
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _seconds_to_vtt_time(seconds: float) -> str:
    ms = int((seconds % 1) * 1000)
    total = int(seconds)
    s = total % 60
    m = (total // 60) % 60
    h = total // 3600
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"


def parse_srt(srt_text: str) -> list[SubtitleSegment]:
    """Parse SRT text into a list of SubtitleSegment."""
    segments: list[SubtitleSegment] = []
    blocks = [b.strip() for b in srt_text.strip().split("\n\n") if b.strip()]

    for block in blocks:
        lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
        if len(lines) < 2:
            continue

        # First line is index
        try:
            index = int(lines[0])
        except ValueError:
            # Some malformed SRTs may have index missing
            continue

        # Second line is timecode
        time_line = lines[1]
        if "-->" not in time_line:
            continue

        start_str, end_str = time_line.split("-->", 1)
        start = _srt_time_to_seconds(start_str)
        end = _srt_time_to_seconds(end_str)
        text = "\n".join(lines[2:])

        segments.append(SubtitleSegment(index=index, start=start, end=end, text=text))

    return segments


def render_srt(segments: list[SubtitleSegment]) -> str:
    """Render segments back to SRT format."""
    lines: list[str] = []
    for seg in segments:
        lines.append(str(seg.index))
        lines.append(f"{_seconds_to_srt_time(seg.start)} --> {_seconds_to_srt_time(seg.end)}")
        lines.append(seg.text)
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def render_vtt(segments: list[SubtitleSegment]) -> str:
    """Render segments to WebVTT format."""
    lines = ["WEBVTT", ""]
    for seg in segments:
        lines.append(str(seg.index))
        lines.append(f"{_seconds_to_vtt_time(seg.start)} --> {_seconds_to_vtt_time(seg.end)}")
        lines.append(seg.text)
        lines.append("")
    return "\n".join(lines).strip() + "\n"


@overload
def merge_chunks(chunks: list[tuple[str, float]]) -> str: ...


def merge_chunks(chunks: list[tuple[str, float]]) -> str:
    """Merge multiple SRT chunks into a single SRT string.

    Args:
        chunks: List of (srt_text, offset_seconds) tuples.

    Returns:
        Combined SRT text with continuous indices and adjusted timestamps.
    """
    all_segments: list[SubtitleSegment] = []
    for srt_text, offset in chunks:
        segments = parse_srt(srt_text)
        for seg in segments:
            all_segments.append(
                SubtitleSegment(
                    index=0,  # will be renumbered
                    start=seg.start + offset,
                    end=seg.end + offset,
                    text=seg.text,
                )
            )

    # Sort by start time just in case
    all_segments.sort(key=lambda s: s.start)

    # Renumber
    for i, seg in enumerate(all_segments, start=1):
        seg.index = i

    return render_srt(all_segments)


def postprocess(srt_text: str) -> str:
    """Light post-processing on SRT text.

    - Collapse runs of 4+ identical characters to a single one.
    - Normalize spaces around CJK punctuation.
    """
    # Collapse repeated chars (e.g. "啊啊啊啊" -> "啊")
    text = _REPEAT_RE.sub(r"\1", srt_text)

    # Normalize CJK punctuation spacing
    text = re.sub(r"([，。！？、；：]) ", r"\1", text)
    text = re.sub(r" ([，。！？、；：])", r"\1", text)

    return text
