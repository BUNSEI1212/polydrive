"""Amazon Translate engine — lazy-imports boto3."""

from __future__ import annotations

import time

from polydrive.core.models import MTResult
from polydrive.mt_gateway.engine_base import MTEngine


class AmazonTranslateEngine(MTEngine):
    """AWS Amazon Translate engine."""

    def __init__(
        self, region: str = "us-east-1", *, aws_access_key_id: str | None = None, aws_secret_access_key: str | None = None
    ) -> None:
        self._region = region
        self._aws_access_key_id = aws_access_key_id
        self._aws_secret_access_key = aws_secret_access_key
        self._client: object | None = None

    @property
    def name(self) -> str:
        return "amazon"

    def _ensure_client(self) -> None:
        if self._client is not None:
            return
        try:
            import boto3  # type: ignore[import-untyped]
        except ImportError as exc:
            raise ImportError("Install boto3: pip install boto3") from exc
        kwargs: dict[str, str] = {"region_name": self._region}
        if self._aws_access_key_id:
            kwargs["aws_access_key_id"] = self._aws_access_key_id
        if self._aws_secret_access_key:
            kwargs["aws_secret_access_key"] = self._aws_secret_access_key
        self._client = boto3.client("translate", **kwargs)

    def translate(self, text: str, source_lang: str, target_lang: str) -> MTResult:
        self._ensure_client()

        start = time.monotonic()
        response = self._client.translate_text(
            Text=text,
            SourceLanguageCode=source_lang,
            TargetLanguageCode=target_lang,
        )
        elapsed_ms = (time.monotonic() - start) * 1000.0

        return MTResult(
            translated_text=response["TranslatedText"],
            detected_source_lang=response.get("SourceLanguageCode"),
            engine=self.name,
            character_count=len(text),
            latency_ms=round(elapsed_ms, 2),
            metadata={
                "applied_terminologies": str(
                    response.get("AppliedTerminologies", [])
                ),
            },
        )

    def close(self) -> None:
        self._client = None
