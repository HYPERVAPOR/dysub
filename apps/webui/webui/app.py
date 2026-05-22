"""Local WebUI for DySub using Gradio."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any

import gradio as gr
from dysub_core.inputs.registry import discover_inputs, get_input_for_source
from dysub_core.models import InputNotSupported, TaskConfig
from dysub_core.pipeline import Pipeline


def _get_source(file_obj: Any, url: str) -> str | None:
    if file_obj is not None:
        return str(file_obj)
    if url and url.strip():
        return url.strip()
    return None


async def _do_transcribe(
    file_obj: Any,
    url: str,
    lang: str,
    fmt: str,
    api_key: str,
    base_url: str,
    keep_temp: bool,
) -> tuple[str, str, str | None]:
    key = api_key or os.getenv("DYSUB_ASR_API_KEY", "")
    if not key:
        return "Error: API Key is required", "", None

    source_str = _get_source(file_obj, url)
    if source_str is None:
        return "Error: Please upload a file or enter a URL", "", None

    try:
        adapter = get_input_for_source(source_str)
        media = adapter.resolve(source_str)
    except InputNotSupported as exc:
        adapters = discover_inputs()
        avail = ", ".join(sorted(adapters.keys())) or "none"
        hint = ""
        if "douyin" in source_str.lower() and "douyin" not in adapters:
            hint = " (hint: pip install dysub-input-douyin)"
        return f"Error: {exc.message}. Available: {avail}{hint}", "", None
    except Exception as exc:
        return f"Error: {exc}", "", None

    out_dir = Path("/tmp/dysub/output")
    out_dir.mkdir(parents=True, exist_ok=True)
    config = TaskConfig(
        temp_dir=Path("/tmp/dysub"),
        output_dir=out_dir,
        api_key=key,
        language=lang,
        output_format=fmt,
        base_url=base_url or None,
        keep_temp=keep_temp,
    )

    pipeline = Pipeline(config)
    status_updates: list[str] = []

    def progress(stage: str, value: float) -> None:
        pct = int(value * 100)
        status_updates.append(f"**{stage}** … {pct}%")

    try:
        result_path = await pipeline.run(media, progress=progress)
    except Exception as exc:
        return f"Error: {exc}", "", None

    preview = result_path.read_text(encoding="utf-8")[:2000]
    status = status_updates[-1] if status_updates else "Done"
    return status, preview, str(result_path)


def _transcribe_sync(*args: Any) -> tuple[str, str, str | None]:
    return asyncio.run(_do_transcribe(*args))


def _batch_process(
    files: list[Any] | None,
    lang: str,
    fmt: str,
    api_key: str,
) -> list[list[str]]:
    if not files:
        return []
    rows: list[list[str]] = []
    for f in files:
        status, _preview, path = _transcribe_sync(f, "", lang, fmt, api_key, "", False)
        name = Path(str(f)).name if f else "unknown"
        rows.append([name, status, path or ""])
    return rows


def create_ui() -> gr.Blocks:
    with gr.Blocks(title="DySub") as demo:
        gr.Markdown("# 🎬 DySub — 本地字幕提取工具")
        gr.Markdown("所有处理均在本地完成。音频数据直接发送至您配置的 ASR 服务商。")

        with gr.Tab("单文件"):
            with gr.Row():
                with gr.Column(scale=1):
                    file_input = gr.File(
                        label="上传音视频文件",
                        file_types=["video", "audio"],
                    )
                    url_input = gr.Textbox(
                        label="或粘贴链接",
                        placeholder="https://...",
                    )
                    lang = gr.Dropdown(
                        choices=["zh", "en", "ja", "ko", "auto"],
                        value="zh",
                        label="语言",
                    )
                    fmt = gr.Radio(
                        choices=["srt", "vtt"],
                        value="srt",
                        label="输出格式",
                    )
                    api_key_input = gr.Textbox(
                        label="API Key (留空则使用环境变量 DYSUB_ASR_API_KEY)",
                        type="password",
                    )
                    base_url_input = gr.Textbox(
                        label="Base URL (可选)",
                        placeholder="https://api.openai.com/v1",
                    )
                    keep_temp = gr.Checkbox(
                        label="保留临时文件",
                        value=False,
                    )
                    run_btn = gr.Button("提取字幕", variant="primary")

                with gr.Column(scale=1):
                    status_md = gr.Markdown("等待开始…")
                    preview_box = gr.Textbox(
                        label="字幕预览",
                        lines=12,
                        interactive=False,
                    )
                    download_file = gr.File(
                        label="下载字幕文件",
                        interactive=False,
                    )

            run_btn.click(
                fn=_transcribe_sync,
                inputs=[
                    file_input,
                    url_input,
                    lang,
                    fmt,
                    api_key_input,
                    base_url_input,
                    keep_temp,
                ],
                outputs=[status_md, preview_box, download_file],
            )

        with gr.Tab("批量文件"):
            files_input = gr.File(
                label="上传多个文件",
                file_count="multiple",
                file_types=["video", "audio"],
            )
            batch_lang = gr.Dropdown(
                choices=["zh", "en", "ja", "ko", "auto"],
                value="zh",
                label="语言",
            )
            batch_fmt = gr.Radio(
                choices=["srt", "vtt"],
                value="srt",
                label="输出格式",
            )
            batch_api = gr.Textbox(
                label="API Key",
                type="password",
            )
            batch_run = gr.Button("批量提取", variant="primary")
            batch_results = gr.Dataframe(
                headers=["文件", "状态", "输出路径"],
                label="结果",
            )

            batch_run.click(
                fn=_batch_process,
                inputs=[files_input, batch_lang, batch_fmt, batch_api],
                outputs=[batch_results],
            )

        gr.Markdown("---")
        gr.Markdown(
            "**DySub** — 本地运行，数据不经过开发者服务器。使用本工具须遵守相关平台服务条款。"
        )

    return demo


if __name__ == "__main__":
    ui = create_ui()
    ui.launch(server_name="127.0.0.1", server_port=7860)
