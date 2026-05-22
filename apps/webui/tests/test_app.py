"""Basic tests for WebUI app."""

from __future__ import annotations

import gradio as gr
from webui.app import create_ui


def test_create_ui_returns_blocks() -> None:
    ui = create_ui()
    assert isinstance(ui, gr.Blocks)
