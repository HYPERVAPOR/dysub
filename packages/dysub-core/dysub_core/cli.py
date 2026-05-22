"""DySub CLI entry point."""

from __future__ import annotations

import asyncio
import os
import shutil
from pathlib import Path

import typer
from rich.console import Console
from rich.progress import Progress

from dysub_core.config import DEFAULT_ENV_PATH, Settings, ensure_config_dir
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
            "[red bold]Error:[/red bold] ASR API Key 未配置\n"
            "\n"
            "DySub 需要调用第三方 ASR 服务（语音转文字）。\n"
            "推荐阿里百炼（DashScope），新用户有免费额度：\n"
            "  [blue]https://bailian.console.aliyun.com/[/blue]\n"
            "\n"
            "获取 API Key 后，选择以下任一方式配置：\n"
            "\n"
            "[cyan]1. 命令行参数（临时）[/cyan]\n"
            "   dysub process ./video.mp4 --api-key sk-xxxxx\n"
            "\n"
            "[cyan]2. 环境变量[/cyan]\n"
            "   export DYSUB_ASR_API_KEY=sk-xxxxx\n"
            "   export DYSUB_ASR_BASE_URL=https://dashscope.aliyuncs.com/api/v1\n"
            "\n"
            "[cyan]3. 配置文件（推荐）[/cyan]\n"
            "   mkdir -p ~/.config/dysub\n"
            "   echo 'DYSUB_ASR_API_KEY=sk-xxxxx' > ~/.config/dysub/.env\n"
            "\n"
            "你也可以运行 [green]dysub doctor --init[/green] 交互式创建配置文件。"
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
def doctor(
    init: bool = typer.Option(
        False, "--init", help="Interactive setup: create ~/.config/dysub/.env"
    ),
) -> None:
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

    # Interactive init mode
    if init:
        console.print()
        _interactive_init(settings)
        return

    if issues:
        console.print()
        console.print("Run [green]dysub doctor --init[/green] to create config file interactively.")
        raise typer.Exit(1)

    console.print("[green]All checks passed![/green]")


def _interactive_init(settings: Settings) -> None:
    """Interactively create ~/.config/dysub/.env."""
    ensure_config_dir()

    console.print("[bold cyan]DySub 配置向导[/bold cyan]")
    console.print()

    if DEFAULT_ENV_PATH.exists():
        console.print(f"[yellow]⚠[/yellow] Config file already exists: {DEFAULT_ENV_PATH}")
        overwrite = typer.confirm("Overwrite?", default=False)
        if not overwrite:
            console.print("Aborted.")
            raise typer.Exit(0)

    # API Key
    console.print(
        "[bold]1. API Key[/bold]\n"
        "   推荐阿里百炼（DashScope），新用户有免费额度：\n"
        "   [blue]https://bailian.console.aliyun.com/[/blue]"
    )
    api_key = typer.prompt("Enter your ASR API Key", default=settings.asr_api_key or "")

    # Base URL
    console.print()
    console.print("[bold]2. ASR Base URL[/bold]")
    base_url_default = settings.asr_base_url or "https://dashscope.aliyuncs.com/api/v1"
    base_url = typer.prompt("Base URL", default=base_url_default)

    # Language
    console.print()
    console.print("[bold]3. Default Language[/bold]")
    lang = typer.prompt("Default language", default=settings.default_language or "zh")

    # Format
    console.print()
    console.print("[bold]4. Default Output Format[/bold]")
    fmt = typer.prompt("Default format (srt/vtt/txt)", default=settings.default_format or "srt")

    # Write file
    content = f"""# DySub 配置文件
DYSUB_ASR_API_KEY={api_key}
DYSUB_ASR_BASE_URL={base_url}
DYSUB_DEFAULT_LANGUAGE={lang}
DYSUB_DEFAULT_FORMAT={fmt}
"""
    DEFAULT_ENV_PATH.write_text(content, encoding="utf-8")
    DEFAULT_ENV_PATH.chmod(0o600)

    console.print()
    console.print(f"[green]✓[/green] Config saved to: {DEFAULT_ENV_PATH}")
    console.print("[dim]Permissions set to 600 (owner read/write only).[/dim]")
    console.print()
    console.print("You can now run: [bold]dysub process ./video.mp4 --lang zh[/bold]")


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
