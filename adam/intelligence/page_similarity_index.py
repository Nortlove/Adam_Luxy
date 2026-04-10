# =============================================================================
# Page Similarity Index — Cosine Similarity on 20-Dim Edge Space
# Location: adam/intelligence/page_similarity_index.py
# =============================================================================

"""
Finds pages with similar psychological fields using cosine similarity
on the 20-dimensional bilateral edge space.

When a converting page is scored, this index finds similar pages that
the system should target next. This is the active discovery loop:

    conversion → crawl → score → find_similar → bid-boost similar → more conversions

The index operates on the same 20 edge dimensions used by the bilateral
cascade, so similarity in this space = similarity in mechanism effectiveness.
"""

import logging
import time
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# The 20 edge dimensions (same order as bilateral cascade)
EDGE_DIMENSIONS = [
    "regulatory_fit", "construal_fit", "personality_alignment",
    "emotional_resonance", "value_alignment", "evolutionary_motive",
    "persuasion_confidence",
    # Extended 13
    "persuasion_susceptibility", "cognitive_load_tolerance",
    "narrative_transport", "social_proof_sensitivity",
    "loss_aversion_intensity", "temporal_discounting",
    "brand_relationship_depth", "autonomy_reactance",
    "information_seeking", "mimetic_desire",
    "interoceptive_awareness", "cooperative_framing_fit",
    "decision_entropy",
]


class PageSimilarityIndex:
    """Cosine similarity index over the 20-dim edge space for scored pages.

    Backed by an in-memory numpy matrix. When a converting page is scored,
    find the K nearest pages and add them to the bid-boost whitelist.
    """

    def __init__(self):
        self._vectors: Dict[str, np.ndarray] = {}  # url_pattern → 20-dim vector
        self._matrix: Optional[np.ndarray] = None   # N × 20 matrix
        self._urls: List[str] = []                   # index → URL mapping
        self._built = False

    def add_page(self, url: str, edge_dimensions: Dict[str, float]) -> None:
        """Add a scored page to the index."""
        vec = np.array([edge_dimensions.get(d, 0.5) for d in EDGE_DIMENSIONS])
        self._vectors[url] = vec
        self._built = False  # Matrix needs rebuild

    def rebuild_index(self) -> int:
        """Rebuild the numpy matrix from all stored vectors.

        Call after adding a batch of pages or periodically.
        Returns count of pages indexed.
        """
        if not self._vectors:
            self._matrix = None
            self._urls = []
            self._built = True
            return 0

        self._urls = list(self._vectors.keys())
        self._matrix = np.stack([self._vectors[u] for u in self._urls])

        # Precompute norms for cosine similarity
        norms = np.linalg.norm(self._matrix, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1.0, norms)
        self._normed = self._matrix / norms

        self._built = True
        logger.info("Page similarity index rebuilt: %d pages", len(self._urls))
        return len(self._urls)

    def find_similar(
        self,
        url: str,
        k: int = 20,
        threshold: float = 0.75,
    ) -> List[Tuple[str, float]]:
        """Find k most similar pages by cosine similarity on edge dimensions.

        Args:
            url: URL to find similar pages for (must be in index).
            k: Maximum number of similar pages to return.
            threshold: Minimum cosine similarity (0-1).

        Returns:
            List of (url, similarity_score) tuples, sorted by similarity descending.
        """
        if not self._built:
            self.rebuild_index()

        if url not in self._vectors or self._matrix is None:
            return []

        query = self._vectors[url]
        query_norm = np.linalg.norm(query)
        if query_norm == 0:
            return []

        query_normed = query / query_norm

        # Cosine similarities (dot product of normed vectors)
        similarities = self._normed @ query_normed

        # Sort by similarity, exclude self
        indices = np.argsort(similarities)[::-1]
        results = []
        for idx in indices:
            if self._urls[idx] == url:
                continue
            sim = float(similarities[idx])
            if sim < threshold:
                break
            results.append((self._urls[idx], sim))
            if len(results) >= k:
                break

        return results

    def find_similar_to_vector(
        self,
        edge_dimensions: Dict[str, float],
        k: int = 20,
        threshold: float = 0.75,
    ) -> List[Tuple[str, float]]:
        """Find similar pages to an arbitrary edge dimension vector.

        Useful for finding pages similar to a converting page that
        hasn't been added to the index yet.
        """
        if not self._built:
            self.rebuild_index()

        if self._matrix is None or len(self._urls) == 0:
            return []

        query = np.array([edge_dimensions.get(d, 0.5) for d in EDGE_DIMENSIONS])
        query_norm = np.linalg.norm(query)
        if query_norm == 0:
            return []

        query_normed = query / query_norm
        similarities = self._normed @ query_normed

        indices = np.argsort(similarities)[::-1]
        results = []
        for idx in indices:
            sim = float(similarities[idx])
            if sim < threshold:
                break
            results.append((self._urls[idx], sim))
            if len(results) >= k:
                break

        return results

    def expand_from_conversion(
        self,
        converting_url: str,
        edge_dimensions: Optional[Dict[str, float]] = None,
        k: int = 10,
        threshold: float = 0.80,
    ) -> List[str]:
        """Find pages similar to a converting page.

        Returns URLs that should be added to the bid-boost list.
        If the converting URL is already in the index, uses it.
        Otherwise uses the provided edge_dimensions directly.
        """
        if converting_url in self._vectors:
            similar = self.find_similar(converting_url, k=k, threshold=threshold)
        elif edge_dimensions:
            similar = self.find_similar_to_vector(edge_dimensions, k=k, threshold=threshold)
        else:
            return []

        urls = [url for url, _ in similar]
        if urls:
            logger.info(
                "Expansion from conversion on %s: found %d similar pages (threshold=%.2f)",
                converting_url, len(urls), threshold,
            )
        return urls

    @property
    def size(self) -> int:
        return len(self._vectors)

    @property
    def stats(self) -> Dict[str, Any]:
        return {
            "pages_indexed": len(self._vectors),
            "matrix_built": self._built,
            "dimensions": len(EDGE_DIMENSIONS),
        }


# =============================================================================
# SINGLETON
# =============================================================================

_instance: Optional[PageSimilarityIndex] = None


def get_page_similarity_index() -> PageSimilarityIndex:
    """Get or create the singleton PageSimilarityIndex."""
    global _instance
    if _instance is None:
        _instance = PageSimilarityIndex()
    return _instance
