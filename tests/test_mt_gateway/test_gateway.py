"""Tests for the MT gateway module."""

from __future__ import annotations

from pathlib import Path

import pytest

from polydrive.core.models import Glossary
from polydrive.core.models import LocalizedTerm
from polydrive.core.models import MTResult
from polydrive.core.models import TermEntry
from polydrive.mt_gateway import MTGateway
from polydrive.mt_gateway.cache import TranslationCache
from polydrive.mt_gateway.engine_base import MTEngine
from polydrive.mt_gateway.engines import AmazonTranslateEngine
from polydrive.mt_gateway.engines import DeepLEngine
from polydrive.mt_gateway.engines import GoogleCloudEngine
from polydrive.mt_gateway.engines import LibreTranslateEngine
from polydrive.mt_gateway.glossary_enforcer import enforce_glossary

# ── Mock engine for testing ─────────────────────────────────────────


class MockEngine(MTEngine):
    """Simple mock engine for testing — no real API calls."""

    @property
    def name(self) -> str:
        return "mock"

    def translate(self, text: str, source_lang: str, target_lang: str) -> MTResult:
        return MTResult(
            translated_text=f"[{target_lang}]{text}",
            engine="mock",
            character_count=len(text),
        )


# ── Gateway tests ───────────────────────────────────────────────────


class TestMTGatewayTranslate:
    def test_translate_with_mock_engine(self) -> None:
        gw = MTGateway()
        gw.register(MockEngine())
        result = gw.translate("hello", "en", "zh")
        assert result.translated_text == "[zh]hello"
        assert result.engine == "mock"
        assert result.character_count == 5
        gw.close()

    def test_translate_with_no_engines_raises(self) -> None:
        gw = MTGateway()
        with pytest.raises(RuntimeError, match="No MT engines registered"):
            gw.translate("hello", "en", "zh")

    def test_translate_with_unknown_engine_raises(self) -> None:
        gw = MTGateway()
        gw.register(MockEngine())
        with pytest.raises(ValueError, match="Engine 'nonexistent' not registered"):
            gw.translate("hello", "en", "zh", engine="nonexistent")
        gw.close()

    def test_translate_uses_first_engine_when_none_specified(self) -> None:
        gw = MTGateway()
        gw.register(MockEngine())
        result = gw.translate("test", "en", "de")
        assert result.engine == "mock"
        gw.close()


class TestMTGatewayCache:
    def test_cache_hit(self, tmp_path: Path) -> None:
        db = tmp_path / "test_cache.db"
        gw = MTGateway()
        gw.register(MockEngine())
        gw.enable_cache(str(db))

        # First call — miss, stores in cache
        r1 = gw.translate("hello", "en", "zh")
        assert r1.engine == "mock"

        # Second call — should hit cache
        r2 = gw.translate("hello", "en", "zh")
        assert r2.engine == "cache"
        assert r2.translated_text == "[zh]hello"
        gw.close()

    def test_cache_miss(self, tmp_path: Path) -> None:
        db = tmp_path / "test_cache.db"
        gw = MTGateway()
        gw.register(MockEngine())
        gw.enable_cache(str(db))

        _r1 = gw.translate("hello", "en", "zh")
        r2 = gw.translate("world", "en", "zh")
        assert r2.engine == "mock"  # different text, cache miss
        gw.close()

    def test_cache_disabled(self) -> None:
        gw = MTGateway()
        gw.register(MockEngine())
        # No enable_cache call
        r1 = gw.translate("hello", "en", "zh")
        r2 = gw.translate("hello", "en", "zh")
        # Both should use the engine since cache is not enabled
        assert r1.engine == "mock"
        assert r2.engine == "mock"
        gw.close()


class TestMTGatewayGlossary:
    def test_glossary_enforcement(self) -> None:
        glossary = Glossary(
            id="test",
            entries=[
                TermEntry(
                    id="t1",
                    translations=[
                        LocalizedTerm(lang="en", term="brake"),
                        LocalizedTerm(lang="zh", term="制动"),
                    ],
                ),
            ],
        )
        gw = MTGateway()
        gw.register(MockEngine())
        result = gw.translate("brake", "en", "zh", glossary=glossary)
        assert (
            result.glossary_applied is False
        )  # mock engine output doesn't contain the term
        gw.close()

    def test_glossary_enforcement_with_variant(self) -> None:
        """When mock produces output matching glossary target term, enforce it."""
        glossary = Glossary(
            id="test",
            entries=[
                TermEntry(
                    id="t1",
                    translations=[
                        LocalizedTerm(lang="en", term="brake"),
                        LocalizedTerm(lang="zh", term="制动"),
                    ],
                ),
            ],
        )

        # Use a custom mock that produces something containing a glossary variant
        class VariantMock(MTEngine):
            @property
            def name(self) -> str:
                return "variant_mock"

            def translate(self, text: str, src: str, tgt: str) -> MTResult:
                return MTResult(
                    translated_text="请检查 制动 系统",
                    engine="variant_mock",
                    character_count=len(text),
                )

        gw = MTGateway()
        gw.register(VariantMock())
        result = gw.translate("check brake system", "en", "zh", glossary=glossary)
        assert result.translated_text == "请检查 制动 系统"
        gw.close()


class TestMTGatewayBatch:
    def test_batch_translation(self) -> None:
        gw = MTGateway()
        gw.register(MockEngine())
        results = gw.translate_batch(["hello", "world"], "en", "zh")
        assert len(results) == 2
        assert results[0].translated_text == "[zh]hello"
        assert results[1].translated_text == "[zh]world"
        gw.close()

    def test_batch_empty_list(self) -> None:
        gw = MTGateway()
        gw.register(MockEngine())
        results = gw.translate_batch([], "en", "zh")
        assert results == []
        gw.close()


class TestMTGatewayUsageStats:
    def test_usage_tracking(self) -> None:
        gw = MTGateway()
        gw.register(MockEngine())
        gw.translate("hello", "en", "zh")
        gw.translate("world", "en", "de")

        stats = gw.usage_stats()
        assert stats.total_requests == 2
        assert stats.total_characters == 10
        assert stats.by_engine.get("mock") == 2
        assert stats.by_language_pair.get("en:zh") == 1
        assert stats.by_language_pair.get("en:de") == 1
        gw.close()

    def test_usage_initial_state(self) -> None:
        gw = MTGateway()
        stats = gw.usage_stats()
        assert stats.total_requests == 0
        assert stats.total_characters == 0
        gw.close()


# ── TranslationCache tests ──────────────────────────────────────────


class TestTranslationCache:
    def test_store_and_lookup(self, tmp_path: Path) -> None:
        cache = TranslationCache(str(tmp_path / "cache.db"))
        cache.store("hello", "en", "zh", "你好", "mock")
        assert cache.lookup("hello", "en", "zh") == "你好"
        cache.close()

    def test_lookup_miss(self, tmp_path: Path) -> None:
        cache = TranslationCache(str(tmp_path / "cache.db"))
        assert cache.lookup("missing", "en", "zh") is None
        cache.close()

    def test_stats(self, tmp_path: Path) -> None:
        cache = TranslationCache(str(tmp_path / "cache.db"))
        cache.store("hello", "en", "zh", "你好", "mock")
        cache.store("world", "en", "zh", "世界", "mock")
        assert cache.stats()["cached_entries"] == 2
        cache.close()

    def test_overwrite_on_store(self, tmp_path: Path) -> None:
        cache = TranslationCache(str(tmp_path / "cache.db"))
        cache.store("hello", "en", "zh", "你好", "mock")
        cache.store("hello", "en", "zh", "您好", "mock")
        assert cache.lookup("hello", "en", "zh") == "您好"
        cache.close()


# ── Glossary enforcer tests ─────────────────────────────────────────


class TestGlossaryEnforcer:
    def test_no_matching_terms(self) -> None:
        glossary = Glossary(
            id="test",
            entries=[
                TermEntry(
                    id="t1",
                    translations=[
                        LocalizedTerm(lang="en", term="brake"),
                        LocalizedTerm(lang="de", term="Bremse"),
                    ],
                ),
            ],
        )
        text, applied = enforce_glossary("制动系统", glossary, "en", "zh")
        assert applied == []
        assert text == "制动系统"

    def test_enforce_matching_term(self) -> None:
        glossary = Glossary(
            id="test",
            entries=[
                TermEntry(
                    id="t1",
                    translations=[
                        LocalizedTerm(lang="en", term="brake"),
                        LocalizedTerm(lang="zh", term="制动"),
                    ],
                ),
            ],
        )
        # Simulate an MT engine outputting a wrong casing variant
        text, applied = enforce_glossary("检查 制动 系统", glossary, "en", "zh")
        # "制动" matches exactly, so no change needed
        assert applied == []
        assert text == "检查 制动 系统"

        # Now test with case-insensitive enforcement on Latin text
        glossary2 = Glossary(
            id="test2",
            entries=[
                TermEntry(
                    id="t1",
                    translations=[
                        LocalizedTerm(lang="en", term="brake"),
                        LocalizedTerm(lang="de", term="Bremse"),
                    ],
                ),
            ],
        )
        # The approved term is "Bremse", but MT produced "bremse" (wrong case)
        text2, applied2 = enforce_glossary("Prüfe bremse System", glossary2, "en", "de")
        assert applied2 == [("bremse", "Bremse")]
        assert text2 == "Prüfe Bremse System"

    def test_enforce_exact_match_no_change(self) -> None:
        glossary = Glossary(
            id="test",
            entries=[
                TermEntry(
                    id="t1",
                    translations=[
                        LocalizedTerm(lang="en", term="brake"),
                        LocalizedTerm(lang="zh", term="制动"),
                    ],
                ),
            ],
        )
        text, applied = enforce_glossary("检查制动系统", glossary, "en", "zh")
        assert applied == []  # "制动" already matches exactly
        assert text == "检查制动系统"


# ── Engine lazy-import tests ────────────────────────────────────────


class TestEngineLazyImport:
    def test_google_engine_raises_on_missing_package(self) -> None:
        engine = GoogleCloudEngine(project_id="test-project")
        with pytest.raises(ImportError, match="google-cloud-translate"):
            engine.translate("hello", "en", "zh")

    def test_deepl_engine_raises_on_missing_package(self) -> None:
        engine = DeepLEngine(auth_key="fake-key")
        with pytest.raises(ImportError, match="deepl"):
            engine.translate("hello", "en", "zh")

    def test_amazon_engine_raises_on_missing_package(self) -> None:
        import importlib.util

        if importlib.util.find_spec("boto3") is not None:
            pytest.skip("boto3 is installed; cannot test ImportError path")

        engine = AmazonTranslateEngine()
        with pytest.raises(ImportError, match="boto3"):
            engine.translate("hello", "en", "zh")


# ── Engine base tests ───────────────────────────────────────────────


class TestEngineBase:
    def test_default_batch_uses_translate(self) -> None:
        engine = MockEngine()
        results = engine.translate_batch(["a", "b"], "en", "zh")
        assert len(results) == 2
        assert results[0].translated_text == "[zh]a"
        assert results[1].translated_text == "[zh]b"

    def test_supported_languages_default_empty(self) -> None:
        engine = MockEngine()
        assert engine.supported_languages() == set()

    def test_close_default_noop(self) -> None:
        engine = MockEngine()
        engine.close()  # should not raise


# ── Engine exports test ─────────────────────────────────────────────


class TestEngineExports:
    def test_all_engines_importable(self) -> None:
        assert LibreTranslateEngine is not None
        assert GoogleCloudEngine is not None
        assert DeepLEngine is not None
        assert AmazonTranslateEngine is not None

    def test_libretranslate_engine_name(self) -> None:
        engine = LibreTranslateEngine()
        assert engine.name == "libretranslate"

    def test_google_engine_name(self) -> None:
        engine = GoogleCloudEngine(project_id="test")
        assert engine.name == "google_cloud"

    def test_deepl_engine_name(self) -> None:
        engine = DeepLEngine(auth_key="test")
        assert engine.name == "deepl"

    def test_amazon_engine_name(self) -> None:
        engine = AmazonTranslateEngine()
        assert engine.name == "amazon"
