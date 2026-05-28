"""MTGateway — unified orchestrator for machine translation engines."""

from __future__ import annotations

import time

from polydrive.core.models import Glossary
from polydrive.core.models import MTResult
from polydrive.core.models import MTUsageStats
from polydrive.mt_gateway.cache import TranslationCache
from polydrive.mt_gateway.engine_base import MTEngine
from polydrive.mt_gateway.glossary_enforcer import enforce_glossary


class MTGateway:
    """Orchestrate multiple MT engines with caching and glossary enforcement."""

    def __init__(self) -> None:
        self._engines: dict[str, MTEngine] = {}
        self._cache: TranslationCache | None = None
        self._usage = MTUsageStats()

    def register(self, engine: MTEngine) -> None:
        """Register an engine instance. It will be available by ``engine.name``."""
        self._engines[engine.name] = engine

    def enable_cache(self, db_path: str = "polydrive_cache.db") -> None:
        """Enable translation caching backed by SQLite."""
        self._cache = TranslationCache(db_path)

    def translate(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        engine: str | None = None,
        glossary: Glossary | None = None,
        use_cache: bool = True,
    ) -> MTResult:
        """Translate text through the gateway.

        Args:
            text: Source text.
            source_lang: BCP 47 source language code.
            target_lang: BCP 47 target language code.
            engine: Engine name to use. None picks the first registered engine.
            glossary: Optional glossary for term enforcement.
            use_cache: Whether to consult/populate the cache.

        Returns:
            MTResult with translation and metadata.
        """
        # Cache lookup
        if use_cache and self._cache is not None:
            cached = self._cache.lookup(text, source_lang, target_lang)
            if cached is not None:
                return MTResult(
                    translated_text=cached,
                    engine="cache",
                    character_count=len(text),
                    metadata={"cache_hit": "true"},
                )

        # Engine selection
        if engine is not None:
            eng = self._engines.get(engine)
            if eng is None:
                raise ValueError(
                    f"Engine '{engine}' not registered. "
                    f"Available: {list(self._engines)}"
                )
        else:
            if not self._engines:
                raise RuntimeError("No MT engines registered.")
            eng = next(iter(self._engines.values()))

        start = time.monotonic()
        result = eng.translate(text, source_lang, target_lang)
        elapsed = (time.monotonic() - start) * 1000.0
        result.latency_ms = round(elapsed, 2)

        # Glossary enforcement
        if glossary is not None:
            enforced_text, applied = enforce_glossary(
                result.translated_text, glossary, source_lang, target_lang
            )
            result.translated_text = enforced_text
            result.glossary_applied = len(applied) > 0
            result.applied_terms = applied

        # Cache store
        if use_cache and self._cache is not None:
            self._cache.store(
                text, source_lang, target_lang, result.translated_text, result.engine
            )

        # Usage tracking
        pair_key = f"{source_lang}:{target_lang}"
        self._usage.total_requests += 1
        self._usage.total_characters += len(text)
        self._usage.by_engine[result.engine] = (
            self._usage.by_engine.get(result.engine, 0) + 1
        )
        self._usage.by_language_pair[pair_key] = (
            self._usage.by_language_pair.get(pair_key, 0) + 1
        )

        return result

    def translate_batch(
        self,
        texts: list[str],
        source_lang: str,
        target_lang: str,
        engine: str | None = None,
        glossary: Glossary | None = None,
    ) -> list[MTResult]:
        """Translate a list of texts sequentially."""
        return [
            self.translate(
                t, source_lang, target_lang, engine=engine, glossary=glossary
            )
            for t in texts
        ]

    def usage_stats(self) -> MTUsageStats:
        """Return accumulated usage statistics."""
        return self._usage.model_copy(deep=True)

    def close(self) -> None:
        """Close all engines and the cache."""
        for eng in self._engines.values():
            eng.close()
        if self._cache is not None:
            self._cache.close()
