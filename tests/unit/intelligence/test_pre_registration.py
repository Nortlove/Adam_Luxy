"""Unit tests for pre-registration file convention and round-trip serialization."""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import pytest

from adam.intelligence.recommendation_class import (
    AudienceScope,
    AudienceSummary,
    CompetingActivations,
    GoalFulfillmentOutcome,
    PrimingCondition,
    ProjectedImpact,
    SpiesDistribution,
    pre_registration_path,
    pre_registration_root,
    read_pre_registration,
    write_pre_registration,
)


def _valid_claim(claim_id: str = "test_claim") -> ProjectedImpact:
    return ProjectedImpact(
        claim_id=claim_id,
        recommendation_class_id="rec_class:abc123def456",
        priming_condition=PrimingCondition(
            page_activation_vector=[0.5] * 20,
            ad_mechanism="regulatory_fit",
            attentional_posture=-0.3,
            attentional_posture_confidence=0.7,
            register_match=0.6,
        ),
        audience_scope=AudienceScope(
            advertiser_id="luxy_ride",
            archetype_id="status_seeker",
            vertical="luxury_transportation",
            context_posture_band="autopilot_low",
            horizon_band="short",
        ),
        goal_fulfillment_outcome=GoalFulfillmentOutcome(
            outcome_metric="durable_conversion_rate",
            projected_distribution=SpiesDistribution(
                metric_name="durable_conversion_rate",
                bin_edges=[0.0, 0.02, 0.05, 0.10, 1.0],
                bin_weights=[0.40, 0.35, 0.20, 0.05],
            ),
            autopilot_route_fraction=0.7,
            attention_route_fraction=0.2,
        ),
        competing_activations=CompetingActivations(
            counter_regulation_untracked=True,
            attention_route_residual=True,
            winners_curse_portion=True,
            publication_bias_residual=True,
            baseline_rate=0.01,
        ),
        audience_summary=AudienceSummary(
            observation_count=150,
            coverage_estimate=0.8,
            expected_signal_strength=0.6,
        ),
        horizon_days=14,
    )


# -----------------------------------------------------------------------------
# to_dict / from_dict round-trip
# -----------------------------------------------------------------------------

class TestToDictFromDict:
    def test_roundtrip_preserves_hash(self):
        claim = _valid_claim()
        original_hash = claim.compute_content_hash()

        data = claim.to_dict()
        reconstructed = ProjectedImpact.from_dict(data)

        assert reconstructed.compute_content_hash() == original_hash

    def test_roundtrip_equality(self):
        claim = _valid_claim()
        data = claim.to_dict()
        reconstructed = ProjectedImpact.from_dict(data)

        # Reconstruct should match on all substantive fields
        assert reconstructed.claim_id == claim.claim_id
        assert reconstructed.recommendation_class_id == claim.recommendation_class_id
        assert reconstructed.horizon_days == claim.horizon_days
        assert reconstructed.priming_condition == claim.priming_condition
        assert reconstructed.audience_scope == claim.audience_scope
        assert reconstructed.competing_activations == claim.competing_activations
        assert reconstructed.audience_summary == claim.audience_summary
        # goal_fulfillment_outcome nests SpiesDistribution; equality holds
        # because dataclasses compare structurally.
        assert reconstructed.goal_fulfillment_outcome == claim.goal_fulfillment_outcome

    def test_to_dict_fills_metadata(self):
        claim = _valid_claim()
        data = claim.to_dict()
        assert "created_at" in data
        assert "content_hash" in data
        assert data["content_hash"] == claim.compute_content_hash()

    def test_to_dict_preserves_existing_metadata(self):
        claim = dataclasses.replace(
            _valid_claim(),
            created_at="2026-04-24T12:00:00+00:00",
            content_hash="a" * 64,
        )
        data = claim.to_dict()
        assert data["created_at"] == "2026-04-24T12:00:00+00:00"
        assert data["content_hash"] == "a" * 64


# -----------------------------------------------------------------------------
# Path convention
# -----------------------------------------------------------------------------

class TestPathConvention:
    def test_pre_registration_root(self, tmp_path):
        root = pre_registration_root(tmp_path)
        assert root == tmp_path / "pre_registrations"

    def test_pre_registration_path_shape(self, tmp_path):
        claim = _valid_claim()
        path = pre_registration_path(claim, tmp_path)

        # Structure: {tmp_path}/pre_registrations/{advertiser_id}/{claim_id}_{hash_prefix}.json
        parts = path.relative_to(tmp_path).parts
        assert parts[0] == "pre_registrations"
        assert parts[1] == "luxy_ride"
        assert parts[2].startswith("test_claim_")
        assert parts[2].endswith(".json")

    def test_pre_registration_path_is_content_addressed(self, tmp_path):
        """Different substantive content → different filenames."""
        claim_a = _valid_claim()
        claim_b = dataclasses.replace(claim_a, horizon_days=30)  # substantive change

        path_a = pre_registration_path(claim_a, tmp_path)
        path_b = pre_registration_path(claim_b, tmp_path)
        assert path_a != path_b

    def test_hash_prefix_length(self, tmp_path):
        """Filename hash suffix is 12 hex chars."""
        claim = _valid_claim()
        path = pre_registration_path(claim, tmp_path)
        stem = path.stem  # "test_claim_{12 hex}"
        hash_part = stem.rsplit("_", 1)[-1]
        assert len(hash_part) == 12
        assert all(c in "0123456789abcdef" for c in hash_part)


# -----------------------------------------------------------------------------
# write_pre_registration / read_pre_registration
# -----------------------------------------------------------------------------

class TestWriteRead:
    def test_write_creates_file(self, tmp_path):
        claim = _valid_claim()
        path = write_pre_registration(claim, tmp_path)
        assert path.exists()
        assert path.is_file()

    def test_write_creates_parent_dirs(self, tmp_path):
        claim = _valid_claim()
        path = write_pre_registration(claim, tmp_path)
        # Confirms pre_registrations/luxy_ride/ was created
        assert path.parent.exists()
        assert path.parent.name == "luxy_ride"

    def test_write_content_is_canonical_json(self, tmp_path):
        claim = _valid_claim()
        path = write_pre_registration(claim, tmp_path)
        raw = path.read_text(encoding="utf-8")
        # Canonical JSON has no whitespace between tokens
        assert ": " not in raw
        assert ", " not in raw
        # And it's valid JSON
        data = json.loads(raw)
        assert data["claim_id"] == claim.claim_id

    def test_write_then_read_roundtrip(self, tmp_path):
        claim = _valid_claim()
        path = write_pre_registration(claim, tmp_path)
        loaded = read_pre_registration(path)

        assert loaded.claim_id == claim.claim_id
        assert loaded.compute_content_hash() == claim.compute_content_hash()

    def test_write_rejects_existing_file(self, tmp_path):
        claim = _valid_claim()
        write_pre_registration(claim, tmp_path)

        with pytest.raises(FileExistsError, match="append-only"):
            write_pre_registration(claim, tmp_path)

    def test_different_claim_ids_do_not_collide(self, tmp_path):
        """Distinct claim_ids produce distinct files with the same advertiser."""
        claim_a = _valid_claim(claim_id="claim_a")
        claim_b = _valid_claim(claim_id="claim_b")

        path_a = write_pre_registration(claim_a, tmp_path)
        path_b = write_pre_registration(claim_b, tmp_path)
        assert path_a != path_b
        assert path_a.exists()
        assert path_b.exists()

    def test_read_detects_content_tampering(self, tmp_path):
        """If someone modifies the file after writing, read() should fail."""
        claim = _valid_claim()
        path = write_pre_registration(claim, tmp_path)

        # Tamper: load, modify, write back with the ORIGINAL content_hash preserved
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
        data["horizon_days"] = 60  # substantive change, but keep stored hash
        path.write_text(
            json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False),
            encoding="utf-8",
        )

        with pytest.raises(ValueError, match="Content hash mismatch"):
            read_pre_registration(path)


# -----------------------------------------------------------------------------
# current_git_head — smoke only (returns a hex or None depending on env)
# -----------------------------------------------------------------------------

class TestCurrentGitHead:
    def test_returns_hex_or_none(self, tmp_path):
        from adam.intelligence.recommendation_class import current_git_head
        # In a non-git tmp dir, returns None
        assert current_git_head(tmp_path) is None

    def test_returns_hex_in_this_repo(self):
        """In the actual repo, returns a hex string."""
        from adam.intelligence.recommendation_class import current_git_head
        # This test repo is under git
        repo_root = Path(__file__).resolve().parent.parent.parent.parent
        result = current_git_head(repo_root)
        # Either None (CI may not have git context) or a valid hex hash
        if result is not None:
            assert len(result) == 40
            assert all(c in "0123456789abcdef" for c in result)
