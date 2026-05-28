"""DeepL engine — lazy-imports the deepl package."""

from __future__ import annotations

import time

from polydrive.core.models import MTResult
from polydrive.mt_gateway.engine_base import MTEngine


class DeepLEngine(MTEngine):
    """DeepL translation API engine."""

    def __init__(self, auth_key: str, *, server_region: str = "free") -> None:
        self._auth_key = auth_key
        self._server_region = server_region
        self._client: object | None = None

    @property
    def name(self) -> str:
        return "deepl"

    def _ensure_client(self) -> None:
        if self._client is not None:
            return
        try:
            import deepl  # type: ignore[import-untyped]
        except ImportError as exc:
            raise ImportError("Install deepl: pip install deepl") from exc
        self._client = deepl.Translator(self._auth_key)

    def translate(self, text: str, source_lang: str, target_lang: str) -> MTResult:
        self._ensure_client()

        start = time.monotonic()
        result = self._client.translate_text(
            text,
            source_lang=source_lang.upper(),
            target_lang=target_lang.upper(),
        )
        elapsed_ms = (time.monotonic() - start) * 1000.0

        return MTResult(
            translated_text=result.text,
            detected_source_lang=result.detected_source_lang or None,
            engine=self.name,
            character_count=len(text),
            latency_ms=round(elapsed_ms, 2),
        )

    def close(self) -> None:
        self._client = None
