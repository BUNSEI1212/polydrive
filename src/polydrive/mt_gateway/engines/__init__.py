"""MT engine backends."""

from __future__ import annotations

from polydrive.mt_gateway.engines.amazon import AmazonTranslateEngine
from polydrive.mt_gateway.engines.deepl_engine import DeepLEngine
from polydrive.mt_gateway.engines.google import GoogleCloudEngine
from polydrive.mt_gateway.engines.libretranslate import LibreTranslateEngine

__all__ = [
    "AmazonTranslateEngine",
    "DeepLEngine",
    "GoogleCloudEngine",
    "LibreTranslateEngine",
]
