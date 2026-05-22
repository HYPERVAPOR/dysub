"""Integration tests for the full transcription pipeline."""

from __future__ import annotations

from pathlib import Path

from dysub_core.models import AudioChunk, MediaSource, TaskConfig
from dysub_core.pipeline import Pipeline

ASSETS = Path(__file__).parents[3] / "tests" / "assets"
SAMPLE_MP4 = ASSETS / "sample.mp4"


class TestFullPipeline:
    async def test_srt_output(self, httpx_mock, tmp_path: Path) -> None:
        httpx_mock.add_response(
            url="https://api.openai.com/v1/audio/transcriptions",
            text="1\n00:00:00,000 --> 00:00:05,000\nTest subtitle\n",
            status_code=200,
        )

        config = TaskConfig(
            temp_dir=tmp_path / "temp",
            output_dir=tmp_path / "out",
            api_key="sk-test",
            output_format="srt",
        )
        pipeline = Pipeline(config)
        source = MediaSource(
            stream_url=str(SAMPLE_MP4),
            source_type="local",
            metadata={"filename": "sample.mp4"},
        )
        result = await pipeline.run(source)

        assert result.exists()
        assert result.name == "sample.srt"
        content = result.read_text()
        assert "Test subtitle" in content

    async def test_vtt_output(self, httpx_mock, tmp_path: Path) -> None:
        httpx_mock.add_response(
            url="https://api.openai.com/v1/audio/transcriptions",
            text="1\n00:00:00,000 --> 00:00:05,000\nHello\n",
            status_code=200,
        )

        config = TaskConfig(
            temp_dir=tmp_path / "temp",
            output_dir=tmp_path / "out",
            api_key="sk-test",
            output_format="vtt",
        )
        pipeline = Pipeline(config)
        source = MediaSource(
            stream_url=str(SAMPLE_MP4),
            source_type="local",
            metadata={"filename": "sample.mp4"},
        )
        result = await pipeline.run(source)

        assert result.name == "sample.vtt"
        content = result.read_text()
        assert content.startswith("WEBVTT")

    async def test_temp_files_cleaned(self, httpx_mock, tmp_path: Path) -> None:
        httpx_mock.add_response(
            url="https://api.openai.com/v1/audio/transcriptions",
            text="1\n00:00:00,000 --> 00:00:05,000\nHello\n",
            status_code=200,
        )

        temp_dir = tmp_path / "temp"
        config = TaskConfig(
            temp_dir=temp_dir,
            output_dir=tmp_path / "out",
            api_key="sk-test",
            keep_temp=False,
        )
        pipeline = Pipeline(config)
        source = MediaSource(
            stream_url=str(SAMPLE_MP4),
            source_type="local",
            metadata={"filename": "sample.mp4"},
        )
        await pipeline.run(source)

        # After run, temp dir should contain no WAV files
        wav_files = list(temp_dir.glob("*.wav"))
        assert len(wav_files) == 0

    async def test_keep_temp(self, httpx_mock, tmp_path: Path) -> None:
        httpx_mock.add_response(
            url="https://api.openai.com/v1/audio/transcriptions",
            text="1\n00:00:00,000 --> 00:00:05,000\nHello\n",
            status_code=200,
        )

        temp_dir = tmp_path / "temp"
        config = TaskConfig(
            temp_dir=temp_dir,
            output_dir=tmp_path / "out",
            api_key="sk-test",
            keep_temp=True,
        )
        pipeline = Pipeline(config)
        source = MediaSource(
            stream_url=str(SAMPLE_MP4),
            source_type="local",
            metadata={"filename": "sample.mp4"},
        )
        await pipeline.run(source)

        wav_files = list(temp_dir.glob("*.wav"))
        assert len(wav_files) >= 1

    async def test_progress_callback(self, httpx_mock, tmp_path: Path) -> None:
        httpx_mock.add_response(
            url="https://api.openai.com/v1/audio/transcriptions",
            text="1\n00:00:00,000 --> 00:00:05,000\nHello\n",
            status_code=200,
        )

        stages = []

        def progress(stage: str, value: float) -> None:
            stages.append((stage, value))

        config = TaskConfig(
            temp_dir=tmp_path / "temp",
            output_dir=tmp_path / "out",
            api_key="sk-test",
        )
        pipeline = Pipeline(config)
        source = MediaSource(
            stream_url=str(SAMPLE_MP4),
            source_type="local",
            metadata={"filename": "sample.mp4"},
        )
        await pipeline.run(source, progress=progress)

        assert len(stages) > 0
        assert stages[0][0] == "extracting"
        assert stages[-1][0] == "done"
        assert stages[-1][1] == 1.0

    async def test_multiple_chunks_merge(self, httpx_mock, tmp_path: Path, monkeypatch) -> None:
        """Simulate chunked audio by monkeypatching chunk_audio."""
        httpx_mock.add_response(text="1\n00:00:00,000 --> 00:00:05,000\nFirst chunk\n")
        httpx_mock.add_response(text="1\n00:00:00,000 --> 00:00:05,000\nSecond chunk\n")

        # Create fake chunk files
        chunk0 = tmp_path / "temp" / "chunk0.wav"
        chunk1 = tmp_path / "temp" / "chunk1.wav"
        chunk0.parent.mkdir(parents=True, exist_ok=True)
        chunk0.write_bytes(b"fake")
        chunk1.write_bytes(b"fake")

        import dysub_core.pipeline as pipeline_mod

        async def fake_chunk(*args, **kwargs):
            return [
                AudioChunk(file_path=chunk0, start_offset_seconds=0.0, duration_seconds=10.0),
                AudioChunk(file_path=chunk1, start_offset_seconds=10.0, duration_seconds=10.0),
            ]

        monkeypatch.setattr(pipeline_mod, "chunk_audio", fake_chunk)

        config = TaskConfig(
            temp_dir=tmp_path / "temp",
            output_dir=tmp_path / "out",
            api_key="sk-test",
            concurrency_limit=1,  # force serial
        )
        pipeline = Pipeline(config)
        source = MediaSource(
            stream_url=str(SAMPLE_MP4),
            source_type="local",
            metadata={"filename": "sample.mp4"},
        )
        result = await pipeline.run(source)

        content = result.read_text()
        assert "First chunk" in content
        assert "Second chunk" in content
        # Verify timestamps are shifted
        assert "00:00:10,000 --> 00:00:15,000" in content

    async def test_txt_output(self, httpx_mock, tmp_path: Path) -> None:
        httpx_mock.add_response(
            url="https://api.openai.com/v1/audio/transcriptions",
            text="Hello world",
            status_code=200,
        )
        config = TaskConfig(
            temp_dir=tmp_path / "temp",
            output_dir=tmp_path / "out",
            api_key="sk-test",
            output_format="txt",
        )
        pipeline = Pipeline(config)
        source = MediaSource(
            stream_url=str(SAMPLE_MP4),
            source_type="local",
            metadata={"filename": "sample.mp4"},
        )
        result = await pipeline.run(source)
        assert result.name == "sample.txt"
        assert result.read_text() == "Hello world"
