"""Tests for subtitle parsing, merging, and export."""

from __future__ import annotations

from dysub_core.models import SubtitleSegment
from dysub_core.subtitle.merger import (
    merge_chunks,
    parse_srt,
    postprocess,
    render_srt,
    render_vtt,
)

SAMPLE_A = """1
00:00:00,000 --> 00:00:05,000
First segment

2
00:00:05,000 --> 00:00:08,000
Second segment
"""

SAMPLE_B = """1
00:00:00,000 --> 00:00:03,000
Third segment
"""


class TestParseSrt:
    def test_basic(self) -> None:
        segs = parse_srt(SAMPLE_A)
        assert len(segs) == 2
        assert segs[0].index == 1
        assert segs[0].start == 0.0
        assert segs[0].end == 5.0
        assert segs[0].text == "First segment"

    def test_multiline_text(self) -> None:
        text = """1
00:00:01,000 --> 00:00:04,000
Line one
Line two
"""
        segs = parse_srt(text)
        assert segs[0].text == "Line one\nLine two"


class TestRenderSrt:
    def test_roundtrip(self) -> None:
        segs = parse_srt(SAMPLE_A)
        output = render_srt(segs)
        assert "00:00:00,000 --> 00:00:05,000" in output
        assert output.endswith("\n")


class TestMergeChunks:
    def test_two_chunks(self) -> None:
        result = merge_chunks([(SAMPLE_A, 0.0), (SAMPLE_B, 10.0)])
        segs = parse_srt(result)
        assert len(segs) == 3
        # Indices renumbered
        assert segs[0].index == 1
        assert segs[1].index == 2
        assert segs[2].index == 3
        # Timestamps shifted
        assert segs[2].start == 10.0
        assert segs[2].end == 13.0

    def test_no_gap(self) -> None:
        # Ensure continuous timestamps without overlap
        chunk1 = """1
00:00:00,000 --> 00:00:05,000
A
"""
        chunk2 = """1
00:00:00,000 --> 00:00:03,000
B
"""
        result = merge_chunks([(chunk1, 0.0), (chunk2, 5.0)])
        segs = parse_srt(result)
        assert segs[0].end == 5.0
        assert segs[1].start == 5.0


class TestRenderVtt:
    def test_header_and_format(self) -> None:
        segs = [
            SubtitleSegment(index=1, start=0.0, end=5.0, text="Hello"),
        ]
        vtt = render_vtt(segs)
        assert vtt.startswith("WEBVTT\n")
        assert "00:00:00.000 --> 00:00:05.000" in vtt


class TestPostprocess:
    def test_collapse_repeats(self) -> None:
        raw = "啊啊啊啊啊，你好"
        assert postprocess(raw) == "啊，你好"

    def test_punctuation_spacing(self) -> None:
        raw = "Hello ， world 。"
        assert postprocess(raw) == "Hello，world。"
