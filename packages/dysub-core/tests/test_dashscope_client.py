"""Tests for DashScope ASR client."""

from __future__ import annotations

import pytest
from dysub_core.asr.dashscope_client import DashScopeClient
from dysub_core.models import InvalidAPIKey


class TestParseText:
    def test_native_format(self) -> None:
        data = {
            "output": {
                "choices": [
                    {
                        "message": {
                            "content": [{"text": "你好世界"}],
                            "role": "assistant",
                        }
                    }
                ]
            }
        }
        assert DashScopeClient._parse_text(data) == "你好世界"

    def test_openai_compatible_format(self) -> None:
        data = {
            "choices": [
                {
                    "message": {
                        "content": "Hello world",
                        "role": "assistant",
                    }
                }
            ]
        }
        assert DashScopeClient._parse_text(data) == "Hello world"

    def test_empty_choices(self) -> None:
        with pytest.raises(ValueError):
            DashScopeClient._parse_text({})

    def test_empty_api_key(self) -> None:
        with pytest.raises(InvalidAPIKey):
            DashScopeClient(api_key="")
