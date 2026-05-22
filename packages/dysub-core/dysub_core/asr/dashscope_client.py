"""DashScope Qwen-ASR client (sync mode, returns plain text)."""

from __future__ import annotations

import base64
import logging
from pathlib import Path

import httpx

from dysub_core.models import InvalidAPIKey

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com/api/v1"


class DashScopeClient:
    """Client for DashScope Qwen-ASR synchronous API.

    Supports local files via base64 encoding.
    Returns plain text (no timestamps).
    """

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str | None = None,
        timeout: float = 300.0,
    ) -> None:
        if not api_key:
            raise InvalidAPIKey("DashScope API key is empty")
        self.api_key = api_key
        self.base_url = (base_url or DEFAULT_BASE_URL).rstrip("/")
        self.client = httpx.AsyncClient(timeout=timeout)

    async def transcribe(
        self,
        file_path: Path,
        language: str,
    ) -> str:
        """Transcribe a local audio file to plain text.

        Args:
            file_path: Path to the local audio file.
            language: Language code (e.g. "zh", "en").

        Returns:
            Recognized plain text.
        """
        url = f"{self.base_url}/services/aigc/multimodal-generation/generation"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        # Base64 encode the local file into a Data URI
        file_path = file_path.resolve()
        with file_path.open("rb") as fh:
            audio_b64 = base64.b64encode(fh.read()).decode()

        # DashScope requires data URI format for base64 audio
        data_uri = f"data:audio/wav;base64,{audio_b64}"

        payload = {
            "model": "qwen3-asr-flash",
            "input": {
                "messages": [
                    {
                        "role": "user",
                        "content": [{"audio": data_uri}],
                    },
                ],
            },
            "asr_options": {
                "language": language,
                "enable_itn": False,
            },
        }

        logger.debug("POST %s (file=%s, lang=%s)", url, file_path.name, language)
        response = await self.client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()

        return self._parse_text(data)

    @staticmethod
    def _parse_text(data: dict) -> str:
        """Extract text from DashScope sync response."""
        choices = data.get("output", {}).get("choices", [])
        if not choices:
            # Fallback: try OpenAI-compatible shape
            choices = data.get("choices", [])

        if not choices:
            raise ValueError("No choices in DashScope response")

        message = choices[0].get("message", {})
        content = message.get("content", "")

        # DashScope native: content = [{"text": "..."}]
        if isinstance(content, list) and content:
            return content[0].get("text", "")

        # OpenAI-compatible: content = "..."
        if isinstance(content, str):
            return content

        return ""
