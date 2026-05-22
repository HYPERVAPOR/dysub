"""Plugin discovery and registry for input adapters."""

from __future__ import annotations

import importlib.metadata

from dysub_core.inputs.base import BaseInputAdapter
from dysub_core.models import InputNotSupported


def discover_inputs() -> dict[str, BaseInputAdapter]:
    """Discover all installed input adapters via entry points.

    Returns:
        Mapping from adapter name to adapter instance.
    """
    adapters: dict[str, BaseInputAdapter] = {}
    eps = importlib.metadata.entry_points(group="dysub.inputs")
    for ep in eps:
        cls = ep.load()
        instance = cls()
        adapters[ep.name] = instance
    return adapters


def get_input_for_source(source: str) -> BaseInputAdapter:
    """Find the first adapter that can handle the given source.

    Args:
        source: Raw input string.

    Raises:
        InputNotSupported: If no adapter claims the source.
    """
    adapters = discover_inputs()
    for _name, adapter in adapters.items():
        if adapter.can_handle(source):
            return adapter
    raise InputNotSupported(
        f"No input adapter found for source: {source}",
        context={"source": source, "available_adapters": list(adapters.keys())},
    )
