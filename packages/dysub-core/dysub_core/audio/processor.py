"""Audio extraction and chunking utilities using FFmpeg."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from dysub_core.models import AudioChunk, AudioProcessError, MediaSource

logger = logging.getLogger(__name__)


async def _run_ffmpeg(*args: str) -> None:
    """Run FFmpeg asynchronously and raise on non-zero exit."""
    proc = await asyncio.create_subprocess_exec(
        "ffmpeg",
        *args,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        err = stderr.decode().strip() if stderr else "unknown error"
        raise AudioProcessError(f"FFmpeg failed: {err}")


async def extract_audio(source: MediaSource, output_path: Path) -> Path:
    """Extract audio from *source* into a mono 16kHz WAV file.

    Args:
        source: Resolved media source (local path or URL).
        output_path: Destination path for the WAV file.

    Returns:
        Absolute path to the extracted WAV file.
    """
    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info("Extracting audio from %s -> %s", source.stream_url, output_path)
    ffmpeg_args = ["-y"]
    # -headers only applies to network protocols; skip for local files
    if source.headers and source.stream_url.startswith(("http://", "https://")):
        header_lines = "\r\n".join(f"{k}: {v}" for k, v in source.headers.items()) + "\r\n"
        ffmpeg_args.extend(["-headers", header_lines])
    ffmpeg_args.extend(
        [
            "-i",
            source.stream_url,
            "-vn",
            "-acodec",
            "pcm_s16le",
            "-ar",
            "16000",
            "-ac",
            "1",
            str(output_path),
        ]
    )
    await _run_ffmpeg(*ffmpeg_args)
    return output_path


async def get_audio_duration(path: Path) -> float:
    """Return audio duration in seconds using ffprobe."""
    proc = await asyncio.create_subprocess_exec(
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        err = stderr.decode().strip() if stderr else "unknown error"
        raise AudioProcessError(f"ffprobe failed: {err}")
    try:
        return float(stdout.decode().strip())
    except ValueError as exc:
        raise AudioProcessError(f"Could not parse duration: {stdout!r}") from exc


async def chunk_audio(
    wav_path: Path,
    max_size_mb: int = 25,
    chunk_duration_sec: int = 600,
) -> list[AudioChunk]:
    """Split a WAV file into chunks if it exceeds *max_size_mb*.

    Args:
        wav_path: Path to the input WAV file.
        max_size_mb: Maximum allowed file size in MB before splitting.
        chunk_duration_sec: Duration of each chunk in seconds.

    Returns:
        List of audio chunks.  If the input is small enough, a single
        chunk with zero offset is returned.
    """
    wav_path = wav_path.resolve()
    size_mb = wav_path.stat().st_size / (1024 * 1024)

    duration = await get_audio_duration(wav_path)

    if size_mb <= max_size_mb:
        return [
            AudioChunk(
                file_path=wav_path,
                start_offset_seconds=0.0,
                duration_seconds=duration,
            ),
        ]

    logger.info(
        "Audio size %.1f MB exceeds %d MB threshold; chunking into %d s slices",
        size_mb,
        max_size_mb,
        chunk_duration_sec,
    )

    chunks: list[AudioChunk] = []
    num_chunks = int(duration // chunk_duration_sec) + (
        1 if duration % chunk_duration_sec > 0 else 0
    )

    for i in range(num_chunks):
        start = i * chunk_duration_sec
        seg_duration = min(chunk_duration_sec, duration - start)
        chunk_path = wav_path.parent / f"{wav_path.stem}_chunk_{i}{wav_path.suffix}"

        await _run_ffmpeg(
            "-y",
            "-i",
            str(wav_path),
            "-ss",
            str(start),
            "-t",
            str(seg_duration),
            "-c",
            "copy",
            str(chunk_path),
        )

        chunks.append(
            AudioChunk(
                file_path=chunk_path,
                start_offset_seconds=start,
                duration_seconds=seg_duration,
            ),
        )

    return chunks
