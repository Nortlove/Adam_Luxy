# =============================================================================
# ADAM Episodic Memory System
# Location: adam/orchestrator/adaptive/episodic_memory.py
# =============================================================================

"""
EPISODIC MEMORY — Cross-Session Retrieval-Augmented Reasoning

A novel LangGraph extension that gives the reasoning system PERSISTENT MEMORY
across requests. Instead of treating each request as independent (memoryless),
the system remembers past decisions and their outcomes, retrieving relevant
episodes to inform current reasoning.

This is inspired by:
- Tulving (1972) — Episodic vs. Semantic Memory distinction
- Graves et al. (2014) — Neural Turing Machines (differentiable memory)
- Lewis et al. (2020) — Retrieval-Augmented Generation (RAG)
- Blundell et al. (2016) — Model-Free Episodic Control

Architecture:
    Request → Encode as query embedding
           → Retrieve top-K similar past episodes
           → Inject as context into atom reasoning
           → After outcome: store new episode

Episode structure:
    - context_embedding: Dense vector capturing request characteristics
    - archetype: Detected archetype
    - ndf_profile: NDF fingerprint
    - mechanisms_used: Which mechanisms were activated
    - atom_routing: Which atoms ran and with what weights
    - outcome: Success/failure + quality score
    - timestamp: When this episode occurred

The memory has three retrieval modes:
1. SIMILARITY — Find episodes with similar contexts (nearest neighbor)
2. ANALOGY — Find episodes where a similar PROBLEM was solved differently
3. COUNTERFACTUAL — Find episodes where a different approach was tried
   for the same type of context (enables learning from alternatives)
"""

import logging
import time
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from collections import defaultdict
from enum import Enum

import numpy as np

logger = logging.getLogger(__name__)


class RetrievalMode(str, Enum):
    """How to retrieve from episodic memory."""
    SIMILARITY = "similarity"       # Most similar context
    ANALOGY = "analogy"             # Similar problem, different solution
    COUNTERFACTUAL = "counterfactual"  # Same context, different approach


@dataclass
class Episode:
    """A single episode in memory."""
    episode_id: str
    timestamp: float

    # Context
    archetype: str = ""
    category: str = ""
    ndf_profile: Dict[str, float] = field(default_factory=dict)
    expanded_type: Dict[str, Any] = field(default_factory=dict)  # Richer psychological constructs
    context_features: Dict[str, float] = field(default_factory=dict)
    context_hash: str = ""

    # Decision
    strategy_used: str = ""
    mechanisms_selected: List[str] = field(default_factory=list)
    atoms_activated: List[str] = field(default_factory=list)
    routing_weights: Dict[str, float] = field(default_factory=dict)

    # Outcome
    success: bool = False
    quality_score: float = 0.0
    outcome_details: Dict[str, Any] = field(default_factory=dict)

    # Embedding (computed lazily)
    _embedding: Optional[List[float]] = field(default=None, repr=False)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d.pop("_embedding", None)
        return d


@dataclass
class RetrievalResult:
    """Result of retrieving from episodic memory."""
    episodes: List[Episode] = field(default_factory=list)
    similarities: List[float] = field(default_factory=list)
    mode: RetrievalMode = RetrievalMode.SIMILARITY
    retrieval_latency_ms: float = 0.0

    # Aggregated insights from retrieved episodes
    mechanism_success_rates: Dict[str, float] = field(default_factory=dict)
    strategy_recommendations: Dict[str, float] = field(default_factory=dict)
    avg_quality_for_context: float = 0.0
    confidence: float = 0.0


# =============================================================================
# EPISODIC MEMORY STORE
# =============================================================================

class EpisodicMemoryStore:
    """
    Persistent episodic memory for the ADAM reasoning system.

    Stores and retrieves past decision episodes to inform current
    reasoning. Uses vector similarity for efficient retrieval.

    Memory management:
    - Fixed capacity with LRU eviction
    - High-quality episodes have longer retention
    - Periodic consolidation merges similar episodes
    """

    def __init__(
        self,
        capacity: int = 50000,
        embedding_dim: int = 64,
        persistence_path: Optional[str] = None,
    ):
        self.capacity = capacity
        self.embedding_dim = embedding_dim
        self.persistence_path = persistence_path

        # Episode storage
        self._episodes: Dict[str, Episode] = {}
        self._embeddings: Dict[str, np.ndarray] = {}

        # Index for fast retrieval
        self._archetype_index: Dict[str, List[str]] = defaultdict(list)
        self._category_index: Dict[str, List[str]] = defaultdict(list)
        self._context_hash_index: Dict[str, List[str]] = defaultdict(list)

        # Statistics
        self._total_stored = 0
        self._total_retrieved = 0
        self._hit_rate_window: List[bool] = []

        # Load from disk if available
        if persistence_path:
            self._load_from_disk()

    def store(self, episode: Episode) -> str:
        """
        Store a new episode in memory.

        Returns the episode_id.
        """
        # Compute embedding
        embedding = self._compute_embedding(episode)
        episode._embedding = embedding.tolist()

        # Compute context hash for exact-match retrieval
        episode.context_hash = self._compute_context_hash(episode)

        # Evict if at capacity
        if len(self._episodes) >= self.capacity:
            self._evict_oldest()

        # Store
        self._episodes[episode.episode_id] = episode
        self._embeddings[episode.episode_id] = embedding

        # Update indices
        if episode.archetype:
            self._archetype_index[episode.archetype].append(episode.episode_id)
        if episode.category:
            self._category_index[episode.category].append(episode.episode_id)
        if episode.context_hash:
            self._context_hash_index[episode.context_hash].append(episode.episode_id)

        self._total_stored += 1

        # Periodic persistence
        if self._total_stored % 100 == 0 and self.persistence_path:
            self._save_to_disk()

        return episode.episode_id

    def retrieve(
        self,
        query_ndf: Dict[str, float],
        query_context: Dict[str, Any],
        mode: RetrievalMode = RetrievalMode.SIMILARITY,
        top_k: int = 5,
        archetype_filter: Optional[str] = None,
        category_filter: Optional[str] = None,
    ) -> RetrievalResult:
        """
        Retrieve relevant episodes from memory.

        Args:
            query_ndf: Current request's NDF profile
            query_context: Current request's context features
            mode: Retrieval mode (similarity, analogy, counterfactual)
            top_k: Number of episodes to retrieve
            archetype_filter: Optional archetype to filter by
            category_filter: Optional category to filter by

        Returns:
            RetrievalResult with episodes and aggregated insights
        """
        start_time = time.time()
        result = RetrievalResult(mode=mode)

        if not self._episodes:
            return result

        # Compute query embedding
        query_embedding = self._compute_query_embedding(query_ndf, query_context)

        # Filter candidates
        candidate_ids = self._get_candidates(
            archetype_filter, category_filter, query_context
        )

        if not candidate_ids:
            return result

        # Compute similarities
        similarities = []
        for ep_id in candidate_ids:
            if ep_id not in self._embeddings:
                continue
            sim = self._cosine_similarity(query_embedding, self._embeddings[ep_id])
            similarities.append((ep_id, sim))

        # Mode-specific sorting
        if mode == RetrievalMode.SIMILARITY:
            # Standard: most similar first
            similarities.sort(key=lambda x: x[1], reverse=True)

        elif mode == RetrievalMode.ANALOGY:
            # Analogy: similar context but different strategy
            query_strategy = query_context.get("strategy", "")
            analogies = [
                (ep_id, sim) for ep_id, sim in similarities
                if self._episodes[ep_id].strategy_used != query_strategy
            ]
            analogies.sort(key=lambda x: x[1], reverse=True)
            similarities = analogies

        elif mode == RetrievalMode.COUNTERFACTUAL:
            # Counterfactual: same context hash, different approach
            query_hash = self._compute_context_hash_from_features(
                query_ndf, query_context
            )
            counterfactuals = []
            for ep_id in self._context_hash_index.get(query_hash, []):
                if ep_id in self._embeddings:
                    sim = self._cosine_similarity(
                        query_embedding, self._embeddings[ep_id]
                    )
                    counterfactuals.append((ep_id, sim))
            # Sort by quality (want to see what worked/failed)
            counterfactuals.sort(
                key=lambda x: self._episodes[x[0]].quality_score,
                reverse=True,
            )
            similarities = counterfactuals

        # Take top-K
        top_episodes = similarities[:top_k]

        for ep_id, sim in top_episodes:
            result.episodes.append(self._episodes[ep_id])
            result.similarities.append(sim)

        # Compute aggregated insights
        if result.episodes:
            result.mechanism_success_rates = self._aggregate_mechanism_rates(
                result.episodes
            )
            result.strategy_recommendations = self._aggregate_strategy_rates(
                result.episodes
            )
            result.avg_quality_for_context = np.mean([
                ep.quality_score for ep in result.episodes
            ])
            result.confidence = self._compute_retrieval_confidence(
                result.similarities, len(self._episodes)
            )

        result.retrieval_latency_ms = (time.time() - start_time) * 1000
        self._total_retrieved += 1
        self._hit_rate_window.append(len(result.episodes) > 0)
        if len(self._hit_rate_window) > 1000:
            self._hit_rate_window = self._hit_rate_window[-1000:]

        logger.info(
            f"Episodic memory retrieval ({mode.value}): "
            f"{len(result.episodes)} episodes, "
            f"confidence={result.confidence:.2f}, "
            f"latency={result.retrieval_latency_ms:.1f}ms"
        )

        return result

    def create_episode(
        self,
        archetype: str,
        category: str,
        ndf_profile: Dict[str, float],
        context_features: Dict[str, float],
        strategy_used: str,
        mechanisms_selected: List[str],
        atoms_activated: List[str],
        routing_weights: Dict[str, float],
        success: bool,
        quality_score: float,
        outcome_details: Optional[Dict[str, Any]] = None,
        expanded_type: Optional[Dict[str, Any]] = None,
    ) -> Episode:
        """Create and store a new episode.

        Args:
            expanded_type: Optional richer psychological construct data from
                PsychologicalConstructResolver.  Includes expanded type dimensions
                (motivation, decision_style, etc.) and continuous scores.
                Stored alongside ndf_profile for richer episode fingerprinting.
        """
        episode_id = hashlib.md5(
            f"{time.time()}_{archetype}_{category}".encode()
        ).hexdigest()[:16]

        episode = Episode(
            episode_id=episode_id,
            timestamp=time.time(),
            archetype=archetype,
            category=category,
            ndf_profile=ndf_profile,
            expanded_type=expanded_type or {},
            context_features=context_features,
            strategy_used=strategy_used,
            mechanisms_selected=mechanisms_selected,
            atoms_activated=atoms_activated,
            routing_weights=routing_weights,
            success=success,
            quality_score=quality_score,
            outcome_details=outcome_details or {},
        )

        self.store(episode)
        return episode

    def get_statistics(self) -> Dict[str, Any]:
        """Get memory statistics."""
        hit_rate = (
            sum(self._hit_rate_window) / len(self._hit_rate_window)
            if self._hit_rate_window else 0.0
        )

        success_episodes = [
            ep for ep in self._episodes.values() if ep.success
        ]

        return {
            "total_episodes": len(self._episodes),
            "capacity_used_pct": len(self._episodes) / self.capacity * 100,
            "total_stored": self._total_stored,
            "total_retrieved": self._total_retrieved,
            "hit_rate": hit_rate,
            "success_rate": (
                len(success_episodes) / len(self._episodes)
                if self._episodes else 0.0
            ),
            "unique_archetypes": len(self._archetype_index),
            "unique_categories": len(self._category_index),
            "unique_contexts": len(self._context_hash_index),
        }

    def consolidate(self, similarity_threshold: float = 0.95) -> int:
        """
        Consolidate memory by merging very similar episodes.
        Keeps the highest-quality episode from each cluster.

        Returns number of episodes removed.
        """
        if len(self._episodes) < 100:
            return 0

        removed = 0
        episode_ids = list(self._episodes.keys())
        to_remove = set()

        for i in range(len(episode_ids)):
            if episode_ids[i] in to_remove:
                continue
            for j in range(i + 1, len(episode_ids)):
                if episode_ids[j] in to_remove:
                    continue

                sim = self._cosine_similarity(
                    self._embeddings[episode_ids[i]],
                    self._embeddings[episode_ids[j]],
                )

                if sim > similarity_threshold:
                    # Keep the higher-quality episode
                    ep_i = self._episodes[episode_ids[i]]
                    ep_j = self._episodes[episode_ids[j]]
                    if ep_i.quality_score >= ep_j.quality_score:
                        to_remove.add(episode_ids[j])
                    else:
                        to_remove.add(episode_ids[i])

        for ep_id in to_remove:
            del self._episodes[ep_id]
            del self._embeddings[ep_id]
            removed += 1

        # Rebuild indices
        self._rebuild_indices()

        logger.info(f"Consolidated memory: removed {removed} redundant episodes")
        return removed

    # =========================================================================
    # PRIVATE HELPERS
    # =========================================================================

    def _compute_embedding(self, episode: Episode) -> np.ndarray:
        """Compute a dense embedding for an episode.

        Uses expanded type dimensions when available for richer fingerprinting,
        falling back to NDF dimensions.
        """
        features = []

        # Psychological construct dimensions (7) — prefer expanded type over NDF
        psy_dims = [
            "approach_avoidance", "temporal_horizon", "social_calibration",
            "uncertainty_tolerance", "status_sensitivity",
            "cognitive_engagement", "arousal_seeking",
        ]
        expanded = episode.expanded_type or {}
        for dim in psy_dims:
            # Expanded type may contain resolver-derived continuous scores
            val = expanded.get(dim)
            if val is None:
                val = episode.ndf_profile.get(dim, 0.5)
            features.append(float(val) if isinstance(val, (int, float)) else 0.5)

        # Expanded type discrete dimensions — encode as ordinal features
        # These provide richer fingerprinting when available
        discrete_dims = {
            "motivation": 42, "decision_style": 12, "regulatory_focus": 8,
            "emotional_intensity": 9, "cognitive_load": 3,
            "temporal_orientation": 4, "social_influence": 5,
        }
        for dim, cardinality in discrete_dims.items():
            val = expanded.get(dim)
            # Simple hash-based encoding to [0,1] range
            if val and isinstance(val, str):
                features.append((hash(val) % cardinality) / max(1, cardinality - 1))
            else:
                features.append(0.5)

        # Context features (normalized)
        context_keys = [
            "brand_awareness", "product_complexity", "decision_value",
            "user_history_depth", "price_level", "urgency",
        ]
        for key in context_keys:
            features.append(episode.context_features.get(key, 0.5))

        # Mechanism one-hot (sparse)
        all_mechanisms = [
            "social_proof", "scarcity", "authority", "commitment",
            "reciprocity", "identity_construction", "mimetic_desire",
            "attention_dynamics", "embodied_cognition",
        ]
        for mech in all_mechanisms:
            features.append(1.0 if mech in episode.mechanisms_selected else 0.0)

        # Quality signal
        features.append(episode.quality_score)

        # Pad or truncate to embedding_dim
        embedding = np.zeros(self.embedding_dim)
        for i, f in enumerate(features[:self.embedding_dim]):
            embedding[i] = f

        # L2 normalize
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm

        return embedding

    def _compute_query_embedding(
        self,
        ndf: Dict[str, float],
        context: Dict[str, Any],
    ) -> np.ndarray:
        """Compute query embedding from NDF and context."""
        dummy_episode = Episode(
            episode_id="query",
            timestamp=time.time(),
            ndf_profile=ndf,
            context_features={
                k: float(v) for k, v in context.items()
                if isinstance(v, (int, float))
            },
        )
        return self._compute_embedding(dummy_episode)

    def _compute_context_hash(self, episode: Episode) -> str:
        """Compute a coarse hash for exact-context matching."""
        return self._compute_context_hash_from_features(
            episode.ndf_profile, episode.context_features
        )

    def _compute_context_hash_from_features(
        self,
        ndf: Dict[str, float],
        context: Dict[str, Any],
    ) -> str:
        """Compute context hash from features."""
        # Discretize NDF to create coarse buckets
        ndf_bucket = "_".join(
            f"{k}:{round(v * 4) / 4:.2f}"
            for k, v in sorted(ndf.items())
        )
        # Add category and archetype if available
        category = str(context.get("category", ""))
        return hashlib.md5(f"{ndf_bucket}_{category}".encode()).hexdigest()[:8]

    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Compute cosine similarity between two vectors."""
        dot = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(dot / (norm_a * norm_b))

    def _get_candidates(
        self,
        archetype_filter: Optional[str],
        category_filter: Optional[str],
        context: Dict[str, Any],
    ) -> List[str]:
        """Get candidate episode IDs based on filters."""
        if archetype_filter and category_filter:
            arch_set = set(self._archetype_index.get(archetype_filter, []))
            cat_set = set(self._category_index.get(category_filter, []))
            candidates = list(arch_set & cat_set)
            if not candidates:
                candidates = list(arch_set | cat_set)
        elif archetype_filter:
            candidates = self._archetype_index.get(archetype_filter, [])
        elif category_filter:
            candidates = self._category_index.get(category_filter, [])
        else:
            candidates = list(self._episodes.keys())

        return candidates

    def _aggregate_mechanism_rates(
        self,
        episodes: List[Episode],
    ) -> Dict[str, float]:
        """Aggregate mechanism success rates from episodes."""
        mech_success = defaultdict(list)
        for ep in episodes:
            for mech in ep.mechanisms_selected:
                mech_success[mech].append(1.0 if ep.success else 0.0)

        return {
            mech: np.mean(outcomes) for mech, outcomes in mech_success.items()
        }

    def _aggregate_strategy_rates(
        self,
        episodes: List[Episode],
    ) -> Dict[str, float]:
        """Aggregate strategy success rates."""
        strat_success = defaultdict(list)
        for ep in episodes:
            if ep.strategy_used:
                strat_success[ep.strategy_used].append(
                    ep.quality_score if ep.success else 0.0
                )

        return {
            strat: np.mean(scores) for strat, scores in strat_success.items()
        }

    def _compute_retrieval_confidence(
        self,
        similarities: List[float],
        total_episodes: int,
    ) -> float:
        """Compute confidence in the retrieval results."""
        if not similarities:
            return 0.0

        avg_sim = np.mean(similarities)
        coverage = min(1.0, total_episodes / 1000)  # More episodes = more confidence
        return min(0.95, avg_sim * 0.6 + coverage * 0.4)

    def _evict_oldest(self) -> None:
        """Evict the oldest, lowest-quality episode."""
        if not self._episodes:
            return

        # Score: quality * recency_weight
        now = time.time()
        worst_id = None
        worst_score = float("inf")

        for ep_id, ep in self._episodes.items():
            age_hours = (now - ep.timestamp) / 3600
            recency = 1.0 / (1.0 + age_hours / 24)  # Decay over days
            score = ep.quality_score * recency
            if score < worst_score:
                worst_score = score
                worst_id = ep_id

        if worst_id:
            del self._episodes[worst_id]
            self._embeddings.pop(worst_id, None)

    def _rebuild_indices(self) -> None:
        """Rebuild all indices from scratch."""
        self._archetype_index.clear()
        self._category_index.clear()
        self._context_hash_index.clear()

        for ep_id, ep in self._episodes.items():
            if ep.archetype:
                self._archetype_index[ep.archetype].append(ep_id)
            if ep.category:
                self._category_index[ep.category].append(ep_id)
            if ep.context_hash:
                self._context_hash_index[ep.context_hash].append(ep_id)

    def _save_to_disk(self) -> None:
        """Persist episodes to disk."""
        if not self.persistence_path:
            return

        path = Path(self.persistence_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "episodes": {
                ep_id: ep.to_dict()
                for ep_id, ep in self._episodes.items()
            },
            "embeddings": {
                ep_id: emb.tolist()
                for ep_id, emb in self._embeddings.items()
            },
            "metadata": {
                "total_stored": self._total_stored,
                "total_retrieved": self._total_retrieved,
            },
        }

        with open(path, "w") as f:
            json.dump(data, f)

        logger.debug(f"Saved {len(self._episodes)} episodes to {path}")

    def _load_from_disk(self) -> None:
        """Load episodes from disk."""
        if not self.persistence_path:
            return

        path = Path(self.persistence_path)
        if not path.exists():
            return

        try:
            with open(path) as f:
                data = json.load(f)

            for ep_id, ep_data in data.get("episodes", {}).items():
                ep_data.pop("_embedding", None)
                episode = Episode(**{
                    k: v for k, v in ep_data.items()
                    if k in Episode.__dataclass_fields__
                })
                self._episodes[ep_id] = episode

            for ep_id, emb_list in data.get("embeddings", {}).items():
                self._embeddings[ep_id] = np.array(emb_list)

            metadata = data.get("metadata", {})
            self._total_stored = metadata.get("total_stored", 0)
            self._total_retrieved = metadata.get("total_retrieved", 0)

            self._rebuild_indices()

            logger.info(
                f"Loaded {len(self._episodes)} episodes from {path}"
            )
        except Exception as e:
            logger.warning(f"Failed to load episodic memory: {e}")
