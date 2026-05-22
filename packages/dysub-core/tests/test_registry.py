"""Tests for input adapter registry."""

import pytest
from dysub_core.inputs.registry import discover_inputs, get_input_for_source
from dysub_core.models import InputNotSupported


def test_discover_inputs_finds_local() -> None:
    """Local adapter should be discoverable once installed."""
    adapters = discover_inputs()
    assert "local" in adapters
    assert adapters["local"].name == "local"


def test_get_input_for_local_file(tmp_path) -> None:
    video = tmp_path / "test.mp4"
    video.write_text("fake")
    adapter = get_input_for_source(str(video))
    assert adapter.name == "local"


def test_get_input_unsupported() -> None:
    with pytest.raises(InputNotSupported):
        get_input_for_source("unknown://whatever")
