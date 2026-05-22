"""OpenAI-compatible ASR client with retry logic."""

from __future__ import annotations

import logging
from pathlib import Path

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from dysub_core.models import (
    APIQuotaExceeded,
    ContentFilterError,
    InvalidAPIKey,
)

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://api.openai.com/v1"


class ASRClient:
    """Client for OpenAI-compatible audio transcription APIs."""

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str | None = None,
        timeout: float = 300.0,
    ) -> None:
        if not api_key:
            raise InvalidAPIKey("ASR API key is empty")
        self.api_key = api_key
        self.base_url = (base_url or DEFAULT_BASE_URL).rstrip("/")
        self.client = httpx.AsyncClient(timeout=timeout)

    async def transcribe(
        self,
        file_path: Path,
        language: str,
        response_format: str = "srt",
        model: str = "whisper-1",
    ) -> str:
        """Transcribe an audio file to text/SRT.

        Args:
            file_path: Path to the audio file.
            language: Language code (e.g. "zh", "en").
            response_format: "srt" or "vtt".
            model: ASR model identifier.

        Returns:
            Raw SRT/VTT text from the API.

        Raises:
            InvalidAPIKey: On 401.
            APIQuotaExceeded: On 429 (with automatic retry).
            ContentFilterError: On content policy violations.
        """
        return await self._transcribe_with_retry(
            file_path=file_path,
            language=language,
            response_format=response_format,
            model=model,
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=4),
        retry=retry_if_exception_type(APIQuotaExceeded),
        reraise=True,
    )
    async def _transcribe_with_retry(
        self,
        file_path: Path,
        language: str,
        response_format: str,
        model: str,
    ) -> str:
        url = f"{self.base_url}/audio/transcriptions"
        headers = {"Authorization": f"Bearer {self.api_key}"}

        with file_path.open("rb") as fh:
            files = {"file": (file_path.name, fh, "audio/wav")}
            data = {
                "model": model,
                "language": language,
                "response_format": response_format,
            }
            logger.debug("POST %s (file=%s, lang=%s)", url, file_path.name, language)
            response = await self.client.post(url, headers=headers, files=files, data=data)

        if response.status_code == 401:
            raise InvalidAPIKey("Invalid ASR API key (401)")

        if response.status_code == 429:
            raise APIQuotaExceeded(
                "ASR rate limit exceeded (429)",
                context={"retry_after": response.headers.get("retry-after")},
            )

        if response.status_code == 400:
            body = response.text.lower()
            if "content" in body or "filter" in body or "policy" in body:
                raise ContentFilterError("ASR content filter triggered (400)")

        response.raise_for_status()
        return response.text
