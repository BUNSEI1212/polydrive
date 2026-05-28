"""LibreTranslate engine — self-hosted, always available (requires only httpx)."""

from __future__ import annotations

import time

import httpx

from polydrive.core.models import MTResult
from polydrive.mt_gateway.engine_base import MTEngine


class LibreTranslateEngine(MTEngine):
    """Translate via a LibreTranslate instance using httpx (synchronous)."""

    def __init__(
        self, base_url: str = "http://localhost:5000", api_key: str | None = None
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key

    @property
    def name(self) -> str:
        return "libretranslate"

    def translate(self, text: str, source_lang: str, target_lang: str) -> MTResult:
        payload: dict[str, object] = {
            "q": text,
            "source": source_lang,
            "target": target_lang,
            "format": "text",
        }
        if self._api_key:
            payload["api_key"] = self._api_key

        start = time.monotonic()
        resp = httpx.post(f"{self._base_url}/translate", json=payload, timeout=30.0)
        resp.raise_for_status()
        elapsed_ms = (time.monotonic() - start) * 1000.0

        data = resp.json()
        translated = data.get("translatedText", "")
        detected = data.get("detectedLanguage", {}).get("language")

        return MTResult(
            translated_text=translated,
            detected_source_lang=detected,
            engine=self.name,
            character_count=len(text),
            latency_ms=round(elapsed_ms, 2),
        )

    def supported_languages(self) -> set[str]:
        try:
            resp = httpx.get(f"{self._base_url}/languages", timeout=10.0)
            resp.raise_for_status()
            return {lang["code"] for lang in resp.json()}
        except httpx.HTTPError:
            return set()
