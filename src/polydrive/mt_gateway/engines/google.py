"""Google Cloud Translation engine — lazy-imports google-cloud-translate."""

from __future__ import annotations

import time

from polydrive.core.models import MTResult
from polydrive.mt_gateway.engine_base import MTEngine


class GoogleCloudEngine(MTEngine):
    """Google Cloud Translation API v3 engine."""

    def __init__(self, project_id: str, location: str = "us-central1") -> None:
        self._project_id = project_id
        self._location = location
        self._client: object | None = None

    @property
    def name(self) -> str:
        return "google_cloud"

    def _ensure_client(self) -> None:
        if self._client is not None:
            return
        try:
            from google.cloud import translate_v3
        except ImportError as exc:
            raise ImportError(
                "Install google-cloud-translate: pip install google-cloud-translate"
            ) from exc
        self._client = translate_v3.TranslationServiceClient()

    def translate(self, text: str, source_lang: str, target_lang: str) -> MTResult:
        self._ensure_client()
        from google.cloud import translate_v3  # type: ignore[import-untyped]

        assert isinstance(self._client, translate_v3.TranslationServiceClient)
        parent = f"projects/{self._project_id}/locations/{self._location}"

        start = time.monotonic()
        response = self._client.translate_text(
            request={
                "parent": parent,
                "contents": [text],
                "mime_type": "text/plain",
                "source_language_code": source_lang,
                "target_language_code": target_lang,
            }
        )
        elapsed_ms = (time.monotonic() - start) * 1000.0

        translation = response.translations[0]
        return MTResult(
            translated_text=translation.translated_text,
            detected_source_lang=translation.detected_language_code or None,
            engine=self.name,
            character_count=len(text),
            latency_ms=round(elapsed_ms, 2),
        )

    def close(self) -> None:
        self._client = None
