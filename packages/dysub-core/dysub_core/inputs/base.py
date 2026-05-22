"""Base input adapter interface."""

from __future__ import annotations

from abc import ABC, abstractmethod

from dysub_core.models import MediaSource


class BaseInputAdapter(ABC):
    """Abstract base class for all input source adapters."""

    name: str = ""

    @abstractmethod
    def resolve(self, source: str) -> MediaSource:
        """Resolve a user-provided source string into a MediaSource.

        Args:
            source: Raw input string (URL, local path, etc.)

        Returns:
            MediaSource ready for audio extraction.
        """
        ...

    @abstractmethod
    def can_handle(self, source: str) -> bool:
        """Return True if this adapter can handle the given source string."""
        ...
