"""Abstract base class for MT engine backends."""

from __future__ import annotations

from abc import ABC, abstractmethod

from polydrive.core.models import MTResult


class MTEngine(ABC):
    """Abstract base for machine translation engine backends."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Engine identifier used for routing and logging."""

    @abstractmethod
    def translate(self, text: str, source_lang: str, target_lang: str) -> MTResult:
        """Translate a single text string."""

    def translate_batch(
        self, texts: list[str], source_lang: str, target_lang: str
    ) -> list[MTResult]:
        """Translate a batch of texts. Default: sequential per-item."""
        return [self.translate(t, source_lang, target_lang) for t in texts]

    def supported_languages(self) -> set[str]:
        """Return set of supported language codes. Empty set means 'unknown'."""
        return set()

    def close(self) -> None:
        """Release resources held by this engine."""
