"""End-to-end transcription pipeline."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from pathlib import Path

from dysub_core.asr.client import ASRClient
from dysub_core.asr.dashscope_client import DashScopeClient
from dysub_core.audio.processor import chunk_audio, extract_audio
from dysub_core.models import (
    AudioChunk,
    DySubError,
    MediaSource,
    TaskConfig,
)
from dysub_core.subtitle.merger import merge_chunks, parse_srt, render_vtt

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[str, float], None]


class Pipeline:
    """Orchestrates the full local transcription workflow."""

    def __init__(self, config: TaskConfig) -> None:
        self.config = config
        self._semaphore = asyncio.Semaphore(config.concurrency_limit)

    async def run(
        self,
        source: MediaSource,
        progress: ProgressCallback | None = None,
    ) -> Path:
        """Run the full pipeline for a single media source.

        Args:
            source: Resolved media source.
            progress: Optional callback(stage_name, progress_0_to_1).

        Returns:
            Path to the generated subtitle file.

        Raises:
            DySubError: On any processing failure.
        """
        temp_dir = self.config.temp_dir.resolve()
        temp_dir.mkdir(parents=True, exist_ok=True)
        temp_files: list[Path] = []

        def _report(stage: str, value: float) -> None:
            if progress:
                progress(stage, value)

        try:
            # -----------------------------------------------------------------
            # 1. Audio extraction
            # -----------------------------------------------------------------
            _report("extracting", 0.1)
            wav_path = temp_dir / f"{self._safe_name(source)}.wav"
            await extract_audio(source, wav_path)
            temp_files.append(wav_path)

            # -----------------------------------------------------------------
            # 2. Chunking
            # -----------------------------------------------------------------
            _report("chunking", 0.2)
            chunks = await chunk_audio(
                wav_path,
                max_size_mb=25,
                chunk_duration_sec=600,
            )
            for ch in chunks:
                if ch.file_path.resolve() != wav_path.resolve():
                    temp_files.append(ch.file_path.resolve())

            # -----------------------------------------------------------------
            # 3. Transcription (with concurrency limit)
            # -----------------------------------------------------------------
            _report("transcribing", 0.3)
            client = self._create_asr_client()

            text_chunks: list[tuple[str, float]] = []
            for idx, chunk in enumerate(chunks):
                text = await self._transcribe_chunk(client, chunk)
                text_chunks.append((text, chunk.start_offset_seconds))
                progress_value = 0.3 + 0.5 * (idx + 1) / len(chunks)
                _report("transcribing", progress_value)

            # -----------------------------------------------------------------
            # 4. Merge & export
            # -----------------------------------------------------------------
            _report("merging", 0.9)
            output_path = self._output_path(source)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            result_text = self._merge_output(text_chunks)

            output_path.write_text(result_text, encoding="utf-8")
            _report("done", 1.0)
            return output_path

        except DySubError:
            raise
        except Exception as exc:
            logger.exception("Pipeline failed")
            raise DySubError(f"Pipeline failed: {exc}") from exc
        finally:
            if not self.config.keep_temp:
                for f in temp_files:
                    try:
                        if f.exists():
                            f.unlink()
                    except OSError:
                        logger.warning("Failed to delete temp file: %s", f)

    def _create_asr_client(self) -> ASRClient | DashScopeClient:
        if self.config.base_url and "dashscope" in self.config.base_url:
            return DashScopeClient(
                api_key=self.config.api_key,
                base_url=self.config.base_url,
            )
        return ASRClient(
            api_key=self.config.api_key,
            base_url=self.config.base_url,
        )

    async def _transcribe_chunk(
        self, client: ASRClient | DashScopeClient, chunk: AudioChunk
    ) -> str:
        async with self._semaphore:
            if isinstance(client, DashScopeClient):
                return await client.transcribe(
                    chunk.file_path,
                    language=self.config.language,
                )
            return await client.transcribe(
                chunk.file_path,
                language=self.config.language,
                response_format="srt",
            )

    def _merge_output(self, chunks: list[tuple[str, float]]) -> str:
        fmt = self.config.output_format

        # Detect whether ASR returned SRT (has timecodes) or plain text
        has_timecodes = any("-->" in text for text, _ in chunks)

        if fmt == "txt":
            return "\n".join(text.strip() for text, _ in chunks)

        if has_timecodes:
            if fmt == "srt":
                return merge_chunks(chunks)
            return self._merge_vtt(chunks)

        # Plain text: wrap into a single pseudo subtitle block
        full_text = "\n".join(text.strip() for text, _ in chunks)
        if fmt == "srt":
            return f"1\n00:00:00,000 --> 99:59:59,999\n{full_text}\n"
        return f"WEBVTT\n\n00:00:00.000 --> 99:59:59.999\n{full_text}\n"

    def _safe_name(self, source: MediaSource) -> str:
        raw = source.metadata.get("filename", "output")
        name = Path(raw).stem
        # Sanitize
        return "".join(c if c.isalnum() or c in "_-" else "_" for c in name) or "output"

    def _output_path(self, source: MediaSource) -> Path:
        name = self._safe_name(source)
        ext = self.config.output_format
        return (self.config.output_dir / f"{name}.{ext}").resolve()

    @staticmethod
    def _merge_vtt(srt_chunks: list[tuple[str, float]]) -> str:
        segments = []
        for srt_text, offset in srt_chunks:
            for seg in parse_srt(srt_text):
                seg.start += offset
                seg.end += offset
                segments.append(seg)
        segments.sort(key=lambda s: s.start)
        for i, seg in enumerate(segments, start=1):
            seg.index = i
        return render_vtt(segments)
