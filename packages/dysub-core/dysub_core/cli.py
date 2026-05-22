"""DySub CLI entry point."""

from __future__ import annotations

import asyncio
import os
import shutil
from pathlib import Path

import typer
from rich.console import Console
from rich.progress import Progress

from dysub_core.config import Settings
from dysub_core.inputs.registry import discover_inputs, get_input_for_source
from dysub_core.models import InvalidAPIKey, TaskConfig
from dysub_core.pipeline import Pipeline

app = typer.Typer(help="DySub - Local subtitle extraction tool")
console = Console()


def _require_key(explicit: str | None) -> str:
    settings = Settings.load()
    key = explicit or settings.asr_api_key or os.getenv("DYSUB_ASR_API_KEY", "")
    if not key:
        console.print(
            "[red]Error:[/red] ASR API key is required.\n"
            "Set it via --api-key, ~/.config/dysub/.env, "
            "or the DYSUB_ASR_API_KEY environment variable."
        )
        raise typer.Exit(1)
    return key


@app.command()
def process(
    source: str = typer.Argument(..., help="Input source (file path or URL)"),
    output: Path = typer.Option(Path("outputs"), "--output", "-o", help="Output directory"),
    lang: str = typer.Option("zh", "--lang", "-l", help="Language code"),
    fmt: str = typer.Option("srt", "--format", "-f", help="Output format: srt or vtt"),
    api_key: str | None = typer.Option(None, "--api-key", help="ASR API key"),
    base_url: str | None = typer.Option(None, "--base-url", help="Custom ASR base URL"),
    temp_dir: Path = typer.Option(Path("/tmp/dysub"), "--temp-dir", help="Temp directory"),
    keep_temp: bool = typer.Option(False, "--keep-temp", help="Keep temporary files"),
) -> None:
    """Transcribe a media source to subtitles."""
    key = _require_key(api_key)

    if fmt not in ("srt", "vtt", "txt"):
        console.print(f"[red]Error:[/red] Unsupported format: {fmt}")
        raise typer.Exit(1)

    output_dir = output.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    settings = Settings.load()
    config = TaskConfig(
        temp_dir=temp_dir,
        output_dir=output_dir,
        api_key=key,
        language=lang or settings.default_language,
        output_format=fmt or settings.default_format,
        base_url=base_url or settings.asr_base_url,
        keep_temp=keep_temp,
    )

    async def _run() -> None:
        adapter = get_input_for_source(source)
        media = adapter.resolve(source)
        pipeline = Pipeline(config)

        with Progress(console=console) as progress:
            task = progress.add_task("[cyan]Working...", total=1.0)

            def _prog(stage: str, value: float) -> None:
                progress.update(task, completed=value, description=f"[cyan]{stage}[/cyan]")

            try:
                result = await pipeline.run(media, progress=_prog)
            except InvalidAPIKey as exc:
                console.print(f"[red]Error:[/red] {exc.message}")
                raise typer.Exit(1) from exc
            except Exception as exc:
                console.print(f"[red]Error:[/red] {exc}")
                raise typer.Exit(1) from exc

        console.print(f"[green]Done![/green] Subtitle saved to: {result}")

    asyncio.run(_run())


@app.command()
def doctor() -> None:
    """Check system configuration and dependencies."""
    issues: list[str] = []

    # FFmpeg
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path:
        console.print(f"[green]✓[/green] FFmpeg found: {ffmpeg_path}")
    else:
        issues.append("FFmpeg not found in PATH. Install it first.")

    # API key
    settings = Settings.load()
    key = settings.asr_api_key or os.getenv("DYSUB_ASR_API_KEY", "")
    if key:
        masked = key[:4] + "****" + key[-4:] if len(key) > 8 else "****"
        console.print(f"[green]✓[/green] ASR API Key is set ({masked})")
    else:
        issues.append(
            "ASR API Key not found. Set it in ~/.config/dysub/.env or DYSUB_ASR_API_KEY env."
        )

    # Plugins
    adapters = discover_inputs()
    if adapters:
        names = ", ".join(sorted(adapters.keys()))
        console.print(f"[green]✓[/green] Input adapters: {names}")
    else:
        issues.append("No input adapters installed.")

    if issues:
        console.print()
        for issue in issues:
            console.print(f"[red]✗[/red] {issue}")
        raise typer.Exit(1)

    console.print("[green]All checks passed![/green]")


@app.command()
def webui(
    host: str = typer.Option("127.0.0.1", "--host", help="Bind address"),
    port: int = typer.Option(7860, "--port", "-p", help="Port"),
) -> None:
    """Launch the local Web UI."""
    try:
        from webui.app import create_ui
    except ImportError:
        console.print(
            "[red]Error:[/red] WebUI dependencies not installed.\nRun: pip install dysub-webui"
        )
        raise typer.Exit(1) from None

    demo = create_ui()
    demo.launch(server_name=host, server_port=port, show_error=True)


def main() -> None:
    app()
