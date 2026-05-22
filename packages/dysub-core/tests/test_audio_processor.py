"""Tests for audio extraction and chunking."""

from __future__ import annotations

from pathlib import Path

import pytest
from dysub_core.audio.processor import chunk_audio, extract_audio, get_audio_duration
from dysub_core.models import AudioProcessError, MediaSource

ASSETS = Path(__file__).parents[3] / "tests" / "assets"
SAMPLE_MP4 = ASSETS / "sample.mp4"


@pytest.fixture
def temp_wav(tmp_path: Path) -> Path:
    return tmp_path / "out.wav"


class TestExtractAudio:
    async def test_extracts_wav_from_mp4(self, temp_wav: Path) -> None:
        source = MediaSource(stream_url=str(SAMPLE_MP4), source_type="local")
        result = await extract_audio(source, temp_wav)
        assert result.exists()
        assert result.suffix == ".wav"

    async def test_output_is_mono_16khz(self, temp_wav: Path) -> None:
        source = MediaSource(stream_url=str(SAMPLE_MP4), source_type="local")
        await extract_audio(source, temp_wav)

        import asyncio

        proc = await asyncio.create_subprocess_exec(
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "a:0",
            "-show_entries",
            "stream=sample_rate,channels",
            "-of",
            "csv=s=x:p=0",
            str(temp_wav),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        assert proc.returncode == 0
        sample_rate, channels = stdout.decode().strip().split("x")
        assert sample_rate == "16000"
        assert channels == "1"

    async def test_invalid_source_raises(self, temp_wav: Path) -> None:
        source = MediaSource(stream_url="/tmp/nonexistent.mp4", source_type="local")
        with pytest.raises(AudioProcessError):
            await extract_audio(source, temp_wav)


class TestGetAudioDuration:
    async def test_duration_approx_10s(self, temp_wav: Path) -> None:
        source = MediaSource(stream_url=str(SAMPLE_MP4), source_type="local")
        await extract_audio(source, temp_wav)
        duration = await get_audio_duration(temp_wav)
        assert 9.5 <= duration <= 10.5

    async def test_missing_file_raises(self) -> None:
        with pytest.raises(AudioProcessError):
            await get_audio_duration(Path("/tmp/nonexistent.wav"))


class TestChunkAudio:
    async def test_small_file_not_chunked(self, temp_wav: Path) -> None:
        source = MediaSource(stream_url=str(SAMPLE_MP4), source_type="local")
        await extract_audio(source, temp_wav)
        chunks = await chunk_audio(temp_wav, max_size_mb=25)
        assert len(chunks) == 1
        assert chunks[0].start_offset_seconds == 0.0
        assert chunks[0].file_path == temp_wav.resolve()

    async def test_large_file_chunked(self, tmp_path: Path) -> None:
        # Create a ~30s silent WAV to force chunking with low threshold
        big_wav = tmp_path / "big.wav"
        proc = await __import__("asyncio").create_subprocess_exec(
            "ffmpeg",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=r=16000:cl=mono",
            "-t",
            "30",
            "-acodec",
            "pcm_s16le",
            str(big_wav),
            stdout=__import__("asyncio").subprocess.DEVNULL,
            stderr=__import__("asyncio").subprocess.PIPE,
        )
        await proc.communicate()
        assert proc.returncode == 0

        chunks = await chunk_audio(big_wav, max_size_mb=0.5, chunk_duration_sec=10)
        assert len(chunks) == 3
        assert chunks[0].start_offset_seconds == 0.0
        assert chunks[1].start_offset_seconds == 10.0
        assert chunks[2].start_offset_seconds == 20.0

        # Each chunk file should exist and be independent
        for ch in chunks:
            assert ch.file_path.exists()
