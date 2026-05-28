"""Semantic matching for cross-language scenario names."""

from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

_TRANSFORMERS_AVAILABLE: bool | None = None
_model = None


def _is_available() -> bool:
    global _TRANSFORMERS_AVAILABLE
    if _TRANSFORMERS_AVAILABLE is None:
        try:
            import sentence_transformers  # noqa: F401

            _TRANSFORMERS_AVAILABLE = True
        except ImportError:
            _TRANSFORMERS_AVAILABLE = False
            logger.info(
                "sentence-transformers not installed; using position-based matching"
            )
    return _TRANSFORMERS_AVAILABLE


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
    return _model


@dataclass
class SemanticMatch:
    """A semantic match result between two scenario names."""

    base_name: str
    compare_name: str
    similarity: float
    method: str  # "semantic" or "position"


def match_scenarios(
    base_names: list[str],
    compare_names: list[str],
    threshold: float = 0.5,
) -> list[SemanticMatch]:
    """Match base scenario names to compare names using semantic similarity.

    Falls back to position-based matching when sentence-transformers is not
    available.
    """
    if not _is_available() or not base_names or not compare_names:
        return _position_match(base_names, compare_names)

    return _semantic_match(base_names, compare_names, threshold)


def _semantic_match(
    base_names: list[str],
    compare_names: list[str],
    threshold: float,
) -> list[SemanticMatch]:
    model = _get_model()
    all_names = base_names + compare_names
    embeddings = model.encode(all_names, normalize_embeddings=True)

    base_emb = embeddings[: len(base_names)]
    comp_emb = embeddings[len(base_names) :]

    matches: list[SemanticMatch] = []
    used_compare: set[int] = set()

    # Greedy matching: for each base name, find best unmatched compare name
    similarities = base_emb @ comp_emb.T  # (n_base, n_compare)

    for i in range(len(base_names)):
        best_j = -1
        best_sim = -1.0
        for j in range(len(compare_names)):
            if j in used_compare:
                continue
            sim = float(similarities[i][j])
            if sim > best_sim:
                best_sim = sim
                best_j = j

        if best_j >= 0 and best_sim >= threshold:
            matches.append(
                SemanticMatch(
                    base_name=base_names[i],
                    compare_name=compare_names[best_j],
                    similarity=best_sim,
                    method="semantic",
                )
            )
            used_compare.add(best_j)

    # Fallback unmatched base names to position
    matched_base = {m.base_name for m in matches}
    unmatched_base = [(i, n) for i, n in enumerate(base_names) if n not in matched_base]
    unmatched_compare = [
        (j, n) for j, n in enumerate(compare_names) if j not in used_compare
    ]
    for (_, bn), (_, cn) in zip(unmatched_base, unmatched_compare, strict=False):
        matches.append(
            SemanticMatch(
                base_name=bn, compare_name=cn, similarity=0.0, method="position"
            )
        )

    return matches


def _position_match(
    base_names: list[str],
    compare_names: list[str],
) -> list[SemanticMatch]:
    matches: list[SemanticMatch] = []
    for bn, cn in zip(base_names, compare_names, strict=False):
        matches.append(
            SemanticMatch(
                base_name=bn, compare_name=cn, similarity=0.0, method="position"
            )
        )
    return matches
