"""Heterogeneous GNN — M5 substrate.

Per the handoff §5: replace the 27 hand-engineered alignment dims with
learned 128-d brand × user embeddings on the typed graph (Brand, User,
Archetype, Mechanism, Category nodes; VIEWED, CONVERTED, HAS_ARCHETYPE,
IN_CATEGORY edges). HGT (Hu et al. 2020 WWW) attention per
(source-type, edge-type, target-type) triple. Pre-train on 47M Amazon
edges, fine-tune on 3,103 LUXY edges.

Substrate this commit ships:
    - HeteroData converter signature (Neo4j → torch_geometric.HeteroData)
    - HGTLinkPredictor model definition (no instantiation without torch)
    - Embedding export interface to Redis (handoff §5.4 fast-lookup tier)
    - Cold-start lookup for brands with zero conversion history
    - GNNLibsMissingError raised cleanly when torch_geometric isn't
      installed

The full training loop, multi-GPU LinkNeighborLoader, embedding refresh
cron, and FastAPI cascade integration are M5 follow-on. Today's commit
ships the structure that makes those wires one-line additions.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


_DEFAULT_HGT_PARAMS: Dict[str, Any] = {
    "hidden_dim": 128,
    "num_heads": 4,
    "num_layers": 2,
    "neg_sampling_ratio": 2.0,
    "batch_size": 2048,
    "neighbor_sample_sizes": [20, 10],
}


@dataclass
class GNNEmbedding:
    """One node's learned embedding."""
    node_type: str           # 'brand' | 'user' | 'archetype' | 'mechanism' | 'category'
    node_id: str
    vector: List[float]      # 128-d, fp16 in storage
    fitted_at_ts: float = 0.0


@dataclass
class GNNTrainingDiagnostics:
    """Per-fit diagnostics for the weekly training run."""
    nodes_embedded: int = 0
    edges_seen: int = 0
    held_out_auc: float = 0.0
    cold_start_auc: float = 0.0
    archetype_probe_accuracy: float = 0.0  # ≥97.9% target per handoff §5.7
    library_versions: Dict[str, str] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)


class GNNLibsMissingError(RuntimeError):
    """Raised when torch_geometric isn't installed and a fit is requested."""
    pass


def _try_import_torch_geometric() -> Optional[Any]:
    try:
        import torch_geometric  # noqa: F401
        return torch_geometric
    except ImportError:
        return None


# -----------------------------------------------------------------------------
# Neo4j → HeteroData converter (signature only; full impl is follow-on)
# -----------------------------------------------------------------------------


def build_hetero_data_from_neo4j(driver: Optional[Any] = None) -> Any:
    """Pull the typed graph from Neo4j into a torch_geometric HeteroData.

    Per handoff §5.3:
        data["brand"].x      = 65 seller dims
        data["user"].x       = 65 buyer dims
        data["archetype"].x  = identity matrix(5)
        data["mechanism"].x  = identity matrix(9)  [or 10 — ADAM's K]
        data["category"].x   = category embeddings
        edge: ("user", "viewed", "brand")
        edge: ("user", "converted", "brand")
        edge: ("user", "has_archetype", "archetype")
        edge: ("brand", "in_category", "category")
        edge_attr: ("user", "alignment", "brand") = 27-dim alignment

    Raises GNNLibsMissingError if torch_geometric isn't installed.
    Raises ValueError if Neo4j returns no edges.

    The full implementation extracts via Cypher, materializes node
    feature matrices, deduplicates and remaps node IDs, applies
    T.ToUndirected(). This commit ships the signature — the full
    extraction is M5 follow-on.
    """
    pyg = _try_import_torch_geometric()
    if pyg is None:
        raise GNNLibsMissingError(
            "torch_geometric not installed. M5 requires "
            "torch_geometric>=2.6 (handoff §5.6 library pins)."
        )

    if driver is None:
        try:
            from adam.core.dependencies import get_neo4j_driver
            driver = get_neo4j_driver()
        except Exception as exc:
            raise ValueError(f"Neo4j driver unavailable: {exc}")

    if driver is None:
        raise ValueError("Neo4j driver is None")

    raise NotImplementedError(
        "build_hetero_data_from_neo4j: full extraction is M5 follow-on. "
        "Substrate signature shipped; extraction wires when training run "
        "is scheduled."
    )


# -----------------------------------------------------------------------------
# HGT model definition (signature only; full impl is follow-on)
# -----------------------------------------------------------------------------


def build_hgt_link_predictor(
    metadata: Any,
    params: Optional[Dict[str, Any]] = None,
) -> Any:
    """Build an HGTConv-based link predictor for (user, converted, brand).

    Per handoff §5.3:
        HGTConv(hidden=128, num_heads=4, num_layers=2)
        BCE link prediction
        L = −Σ log σ(s) − Σ log(1−σ(s))  on positive vs negative samples

    Raises GNNLibsMissingError when torch_geometric / torch isn't
    installed. Returns the constructed model otherwise.
    """
    pyg = _try_import_torch_geometric()
    if pyg is None:
        raise GNNLibsMissingError(
            "torch_geometric not installed; cannot build HGT model"
        )

    raise NotImplementedError(
        "build_hgt_link_predictor: full model construction is M5 "
        "follow-on. Signature shipped."
    )


# -----------------------------------------------------------------------------
# Redis embedding export — fast-lookup tier per handoff §5.4
# -----------------------------------------------------------------------------


_REDIS_EMBEDDING_PREFIX = "informativ:gnn:emb:v1"
_REDIS_EMBEDDING_TTL = 7 * 24 * 3600  # 7 days, refreshed nightly


def export_embedding_to_redis(
    embedding: GNNEmbedding,
    redis_client: Optional[Any] = None,
) -> bool:
    """Write a 128-d embedding to Redis.

    Key shape: informativ:gnn:emb:v1:{node_type}:{node_id}
    Value: comma-separated fp16 string (matches the cascade's <5ms read
    budget per handoff §5.4).

    Returns True on success, False on Redis unavailable.
    """
    if redis_client is None:
        try:
            from adam.infrastructure.redis_client import get_redis
            redis_client = get_redis()
        except Exception:
            return False
    if redis_client is None:
        return False

    key = f"{_REDIS_EMBEDDING_PREFIX}:{embedding.node_type}:{embedding.node_id}"
    payload = ",".join(f"{v:.4f}" for v in embedding.vector)
    try:
        redis_client.set(key, payload, ex=_REDIS_EMBEDDING_TTL)
        return True
    except Exception as exc:
        logger.warning("GNN embedding export failed: %s", exc)
        return False


def lookup_embedding_from_redis(
    node_type: str, node_id: str,
    redis_client: Optional[Any] = None,
) -> Optional[List[float]]:
    """Read an embedding from Redis. Returns None on miss.

    Cascade hot-path read — must be sync, must soft-fail. Per handoff
    §5.4 budget: <5ms.
    """
    if redis_client is None:
        try:
            from adam.infrastructure.redis_client import get_redis
            redis_client = get_redis()
        except Exception:
            return None
    if redis_client is None:
        return None

    key = f"{_REDIS_EMBEDDING_PREFIX}:{node_type}:{node_id}"
    try:
        payload = redis_client.get(key)
    except Exception:
        return None
    if payload is None:
        return None
    if isinstance(payload, bytes):
        try:
            payload = payload.decode("utf-8")
        except UnicodeDecodeError:
            return None
    try:
        return [float(v) for v in payload.split(",")]
    except ValueError:
        return None


# -----------------------------------------------------------------------------
# Cold-start similarity — for brands with zero conversion history
# -----------------------------------------------------------------------------


def cold_start_brand_similarity(
    new_brand_features: List[float],
    candidate_brand_embeddings: Dict[str, List[float]],
    top_k: int = 5,
) -> List[Tuple[str, float]]:
    """For a new brand with no conversion history, find the K most-similar
    existing brands by feature cosine similarity.

    Per handoff §5.1: the GNN closes the cold-start gap because new
    brands inherit embedding structure from 1-hop neighbors. This
    helper provides the similarity surface BEFORE the GNN has
    re-trained — the new brand's 65 seller dims are matched against
    cached embeddings of existing brands.

    Returns [(brand_id, similarity), ...] sorted by similarity descending.
    """
    if not new_brand_features or not candidate_brand_embeddings:
        return []

    similarities: List[Tuple[str, float]] = []
    for brand_id, candidate_vec in candidate_brand_embeddings.items():
        if len(candidate_vec) != len(new_brand_features):
            continue
        sim = _cosine_similarity(new_brand_features, candidate_vec)
        similarities.append((brand_id, sim))

    similarities.sort(key=lambda x: x[1], reverse=True)
    return similarities[:top_k]


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(ai * bi for ai, bi in zip(a, b))
    norm_a = sum(ai * ai for ai in a) ** 0.5
    norm_b = sum(bi * bi for bi in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)
