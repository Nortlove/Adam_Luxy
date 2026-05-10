"""Q.2.A — endpoint correctness tests for /analytics/per-cohort-outcome-correlation."""

from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from adam.api.dashboard.router import router
from adam.intelligence.cohort_discovery import UserCohort


@pytest.fixture
def client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def _cohort(
    cid: str,
    doms: list,
    size: int = 100,
    flag: bool = False,
    confidence: float = 0.5,
) -> UserCohort:
    return UserCohort(
        cohort_id=cid,
        size=size,
        sample_members=[],
        dominant_mechanisms=doms,
        compensatory_consumption_pattern=flag,
        compensatory_detection_confidence=confidence,
    )


def test_route_registered(client: TestClient):
    response = client.get("/api/dashboard/analytics/per-cohort-outcome-correlation")
    assert response.status_code == 200
    body = response.json()
    assert "cohorts" in body
    assert "data_source_state" in body


def test_empty_state_when_no_cohorts(client: TestClient):
    with patch(
        "adam.api.dashboard.cell_aggregation_service._fetch_user_cohorts",
        return_value=[],
    ):
        response = client.get(
            "/api/dashboard/analytics/per-cohort-outcome-correlation"
        )
        body = response.json()
    assert body["cohorts"] == []
    assert body["data_source_state"] == "empty"


def test_affiliative_cohort_classified(client: TestClient):
    cohorts = [
        _cohort(
            "c_aff",
            ["social_proof", "liking", "unity"],
            size=300,
            flag=True,
            confidence=0.85,
        )
    ]
    with patch(
        "adam.api.dashboard.cell_aggregation_service._fetch_user_cohorts",
        return_value=cohorts,
    ):
        response = client.get(
            "/api/dashboard/analytics/per-cohort-outcome-correlation"
        )
        body = response.json()
    assert body["data_source_state"] == "partial"  # rates not wired pre-pilot
    by_id = {c["cohort_id"]: c for c in body["cohorts"]}
    assert by_id["c_aff"]["mechanism_orientation"] == "affiliative"
    assert by_id["c_aff"]["compensatory_flag"] is True
    assert by_id["c_aff"]["confidence_label"] == "high_confidence"


def test_transactional_cohort_classified(client: TestClient):
    cohorts = [
        _cohort(
            "c_tr",
            ["anchoring", "scarcity", "loss_aversion"],
            size=80,
            flag=False,
            confidence=0.55,
        )
    ]
    with patch(
        "adam.api.dashboard.cell_aggregation_service._fetch_user_cohorts",
        return_value=cohorts,
    ):
        response = client.get(
            "/api/dashboard/analytics/per-cohort-outcome-correlation"
        )
        body = response.json()
    by_id = {c["cohort_id"]: c for c in body["cohorts"]}
    assert by_id["c_tr"]["mechanism_orientation"] == "transactional"
    assert by_id["c_tr"]["confidence_label"] == "partial_evidence"


def test_mixed_cohort_classified(client: TestClient):
    cohorts = [
        _cohort(
            "c_mix",
            ["social_proof", "anchoring", "authority", "reciprocity"],
            size=50,
            confidence=0.30,
        )
    ]
    with patch(
        "adam.api.dashboard.cell_aggregation_service._fetch_user_cohorts",
        return_value=cohorts,
    ):
        response = client.get(
            "/api/dashboard/analytics/per-cohort-outcome-correlation"
        )
        body = response.json()
    by_id = {c["cohort_id"]: c for c in body["cohorts"]}
    assert by_id["c_mix"]["mechanism_orientation"] == "mixed"
    assert by_id["c_mix"]["confidence_label"] == "uninformative"


def test_compensatory_flag_propagated(client: TestClient):
    cohorts = [
        _cohort("c_with_flag", ["social_proof"], flag=True),
        _cohort("c_no_flag", ["anchoring"], flag=False),
    ]
    with patch(
        "adam.api.dashboard.cell_aggregation_service._fetch_user_cohorts",
        return_value=cohorts,
    ):
        response = client.get(
            "/api/dashboard/analytics/per-cohort-outcome-correlation"
        )
        body = response.json()
    by_id = {c["cohort_id"]: c for c in body["cohorts"]}
    assert by_id["c_with_flag"]["compensatory_flag"] is True
    assert by_id["c_no_flag"]["compensatory_flag"] is False


def test_sample_size_propagated(client: TestClient):
    cohorts = [_cohort("c1", ["social_proof"], size=523)]
    with patch(
        "adam.api.dashboard.cell_aggregation_service._fetch_user_cohorts",
        return_value=cohorts,
    ):
        response = client.get(
            "/api/dashboard/analytics/per-cohort-outcome-correlation"
        )
        body = response.json()
    assert body["cohorts"][0]["sample_size"] == 523


def test_window_bounds_present(client: TestClient):
    response = client.get(
        "/api/dashboard/analytics/per-cohort-outcome-correlation?days=14"
    )
    body = response.json()
    assert "window_start" in body
    assert "window_end" in body


def test_no_raw_member_ids_in_response(client: TestClient):
    """Privacy: cohort sample_members must NOT leak into response."""
    cohorts = [
        UserCohort(
            cohort_id="c1",
            size=100,
            sample_members=["secret_user_alpha", "secret_user_beta"],
            dominant_mechanisms=["social_proof"],
        )
    ]
    with patch(
        "adam.api.dashboard.cell_aggregation_service._fetch_user_cohorts",
        return_value=cohorts,
    ):
        response = client.get(
            "/api/dashboard/analytics/per-cohort-outcome-correlation"
        )
        body_text = response.text
    assert "secret_user_alpha" not in body_text
    assert "secret_user_beta" not in body_text
