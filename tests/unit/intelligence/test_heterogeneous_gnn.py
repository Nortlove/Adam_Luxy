"""Pin the M5 GNN substrate.

Discipline anchors:
    - GNNLibsMissingError raised cleanly when torch_geometric isn't
      installed. Same discipline as M2/M3: no silent None on missing
      libs.
    - The cosine-similarity helper for cold-start lookup is the
      cascade-side surface (a brand without conversion history matches
      against existing brand embeddings via 65-dim seller features).
      Tests pin the formula behavior so a refactor can't silently
      change cold-start scoring.
    - Redis read on hot path is sync + soft-fail. The cascade can call
      lookup_embedding_from_redis at <5ms; failure modes return None.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from adam.intelligence.heterogeneous_gnn import (
    GNNEmbedding,
    GNNLibsMissingError,
    _cosine_similarity,
    build_hetero_data_from_neo4j,
    build_hgt_link_predictor,
    cold_start_brand_similarity,
    export_embedding_to_redis,
    lookup_embedding_from_redis,
)


# -----------------------------------------------------------------------------
# Soft-import gate
# -----------------------------------------------------------------------------


def test_build_hetero_data_raises_libs_missing_when_pyg_unavailable():
    with patch(
        "adam.intelligence.heterogeneous_gnn._try_import_torch_geometric",
        return_value=None,
    ):
        with pytest.raises(GNNLibsMissingError):
            build_hetero_data_from_neo4j(driver=MagicMock())


def test_build_hgt_raises_libs_missing_when_pyg_unavailable():
    with patch(
        "adam.intelligence.heterogeneous_gnn._try_import_torch_geometric",
        return_value=None,
    ):
        with pytest.raises(GNNLibsMissingError):
            build_hgt_link_predictor(metadata=None)


# -----------------------------------------------------------------------------
# Cosine similarity — cold-start surface
# -----------------------------------------------------------------------------


def test_cosine_identical_vectors_is_one():
    a = [1.0, 0.0, 1.0, 0.5]
    assert _cosine_similarity(a, a) == pytest.approx(1.0)


def test_cosine_orthogonal_vectors_is_zero():
    assert _cosine_similarity([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)


def test_cosine_opposite_is_negative_one():
    assert _cosine_similarity([1.0, 0.0], [-1.0, 0.0]) == pytest.approx(-1.0)


def test_cosine_zero_vector_is_zero():
    """Empty / zero vector cannot have a cosine; return 0 rather than
    NaN to avoid downstream propagation."""
    assert _cosine_similarity([0.0, 0.0], [1.0, 0.0]) == 0.0
    assert _cosine_similarity([], [1.0]) == 0.0


# -----------------------------------------------------------------------------
# Cold-start brand lookup
# -----------------------------------------------------------------------------


def test_cold_start_returns_top_k_by_similarity():
    """A new brand whose features match brand_a closely should rank
    brand_a first in cold-start similarity."""
    new_features = [1.0, 1.0, 0.0]
    candidates = {
        "brand_a": [1.0, 1.0, 0.0],   # identical
        "brand_b": [0.0, 1.0, 1.0],   # different
        "brand_c": [-1.0, -1.0, 0.0],  # opposite
    }
    result = cold_start_brand_similarity(new_features, candidates, top_k=2)

    assert result[0][0] == "brand_a"
    assert result[0][1] == pytest.approx(1.0)
    # brand_b ranks above brand_c (positive vs negative)
    assert result[1][0] == "brand_b"


def test_cold_start_handles_empty_inputs():
    assert cold_start_brand_similarity([], {"a": [1.0]}) == []
    assert cold_start_brand_similarity([1.0], {}) == []


def test_cold_start_skips_dimension_mismatched_candidates():
    """Candidates with wrong dimensionality silently skipped — the GNN
    re-train fixes this on next refresh, but lookup must not crash."""
    new_features = [1.0, 1.0, 0.0]
    candidates = {
        "valid": [0.5, 0.5, 0.5],
        "wrong_dim": [1.0, 0.0],          # 2-d (mismatched)
        "also_valid": [0.0, 1.0, 0.0],
    }
    result = cold_start_brand_similarity(new_features, candidates)
    brand_ids = [r[0] for r in result]
    assert "wrong_dim" not in brand_ids
    assert "valid" in brand_ids
    assert "also_valid" in brand_ids


# -----------------------------------------------------------------------------
# Redis embedding export / lookup
# -----------------------------------------------------------------------------


def test_export_writes_under_canonical_key():
    redis_mock = MagicMock()
    embedding = GNNEmbedding(
        node_type="brand", node_id="lux_luxy_ride",
        vector=[0.1, 0.2, 0.3],
    )
    with patch(
        "adam.infrastructure.redis_client.get_redis",
        return_value=redis_mock,
    ):
        ok = export_embedding_to_redis(embedding)
    assert ok is True

    key = redis_mock.set.call_args.args[0]
    assert key == "informativ:gnn:emb:v1:brand:lux_luxy_ride"


def test_export_writes_ttl():
    redis_mock = MagicMock()
    embedding = GNNEmbedding(
        node_type="user", node_id="u1", vector=[0.0],
    )
    with patch(
        "adam.infrastructure.redis_client.get_redis",
        return_value=redis_mock,
    ):
        export_embedding_to_redis(embedding)
    kwargs = redis_mock.set.call_args.kwargs
    assert kwargs.get("ex") == 7 * 24 * 3600


def test_export_soft_fails_when_redis_unavailable():
    embedding = GNNEmbedding(node_type="brand", node_id="x", vector=[0.0])
    with patch(
        "adam.infrastructure.redis_client.get_redis",
        return_value=None,
    ):
        ok = export_embedding_to_redis(embedding)
    assert ok is False


def test_lookup_returns_none_on_miss():
    redis_mock = MagicMock()
    redis_mock.get = MagicMock(return_value=None)
    with patch(
        "adam.infrastructure.redis_client.get_redis",
        return_value=redis_mock,
    ):
        result = lookup_embedding_from_redis("brand", "x")
    assert result is None


def test_lookup_returns_floats_on_hit():
    redis_mock = MagicMock()
    redis_mock.get = MagicMock(return_value="0.1,0.2,0.3,-0.4")
    with patch(
        "adam.infrastructure.redis_client.get_redis",
        return_value=redis_mock,
    ):
        result = lookup_embedding_from_redis("brand", "lux_luxy_ride")
    assert result == [0.1, 0.2, 0.3, -0.4]


def test_lookup_handles_malformed_payload():
    """Malformed Redis payload → None, don't crash."""
    redis_mock = MagicMock()
    redis_mock.get = MagicMock(return_value="not,floats,at,all")
    with patch(
        "adam.infrastructure.redis_client.get_redis",
        return_value=redis_mock,
    ):
        result = lookup_embedding_from_redis("brand", "x")
    assert result is None


def test_lookup_handles_redis_exception_silently():
    redis_mock = MagicMock()
    redis_mock.get = MagicMock(side_effect=ConnectionError("redis"))
    with patch(
        "adam.infrastructure.redis_client.get_redis",
        return_value=redis_mock,
    ):
        result = lookup_embedding_from_redis("brand", "x")
    assert result is None
