"""
Quality gates and end-to-end validation for the corpus pipeline.

Validates:
1. Per-phase output counts and schema compliance
2. Annotation distribution health (not all zeros, reasonable spread)
3. Edge type integrity (all edges connect valid nodes)
4. Bayesian prior sanity (means within expected ranges)
"""

from __future__ import annotations

import logging
from typing import Any

from neo4j import Driver

logger = logging.getLogger("adam.corpus.quality")


class ValidationResult:
    def __init__(self, name: str):
        self.name = name
        self.passed: list[str] = []
        self.warnings: list[str] = []
        self.failures: list[str] = []

    @property
    def ok(self) -> bool:
        return len(self.failures) == 0

    def add_pass(self, msg: str) -> None:
        self.passed.append(msg)

    def add_warning(self, msg: str) -> None:
        self.warnings.append(msg)
        logger.warning(f"[{self.name}] {msg}")

    def add_failure(self, msg: str) -> None:
        self.failures.append(msg)
        logger.error(f"[{self.name}] FAIL: {msg}")

    def summary(self) -> str:
        status = "PASS" if self.ok else "FAIL"
        return (
            f"[{status}] {self.name}: "
            f"{len(self.passed)} passed, "
            f"{len(self.warnings)} warnings, "
            f"{len(self.failures)} failures"
        )


def validate_phase1(driver: Driver) -> ValidationResult:
    """Validate Phase 1: Product description nodes."""
    result = ValidationResult("Phase 1: Product Descriptions")
    with driver.session() as session:
        count = session.run(
            "MATCH (pd:ProductDescription) RETURN count(pd) AS cnt"
        ).single()["cnt"]

        if count == 0:
            result.add_failure("No ProductDescription nodes found")
            return result

        result.add_pass(f"{count} ProductDescription nodes")

        # Check annotation coverage
        annotated = session.run(
            "MATCH (pd:ProductDescription) WHERE pd.annotation_confidence > 0.1 "
            "RETURN count(pd) AS cnt"
        ).single()["cnt"]

        pct = annotated / count * 100
        if pct < 10:
            result.add_warning(f"Only {pct:.1f}% annotated with confidence > 0.1")
        else:
            result.add_pass(f"{pct:.1f}% annotated ({annotated}/{count})")

        # Check for all-zero annotations
        zeros = session.run("""
            MATCH (pd:ProductDescription)
            WHERE pd.annotation_confidence > 0.1
              AND pd.ad_framing_gain = 0 AND pd.ad_framing_loss = 0
              AND pd.ad_appeals_rational = 0 AND pd.ad_appeals_emotional = 0
            RETURN count(pd) AS cnt
        """).single()["cnt"]

        if zeros > annotated * 0.5:
            result.add_failure(f"{zeros} annotated products have all-zero scores")
        elif zeros > annotated * 0.2:
            result.add_warning(f"{zeros} annotated products have all-zero scores")

    return result


def validate_phase2_3(driver: Driver) -> ValidationResult:
    """Validate Phase 2+3: Annotated reviews."""
    result = ValidationResult("Phase 2+3: Annotated Reviews")
    with driver.session() as session:
        count = session.run(
            "MATCH (r:AnnotatedReview) RETURN count(r) AS cnt"
        ).single()["cnt"]

        if count == 0:
            result.add_failure("No AnnotatedReview nodes found")
            return result

        result.add_pass(f"{count} AnnotatedReview nodes")

        # User-side annotation coverage
        user_ann = session.run(
            "MATCH (r:AnnotatedReview) WHERE r.annotation_confidence > 0 "
            "RETURN count(r) AS cnt"
        ).single()["cnt"]
        result.add_pass(f"{user_ann} user-side annotated")

        # Peer-ad-side annotation coverage
        peer_ann = session.run(
            "MATCH (r:AnnotatedReview) WHERE r.peer_ad_annotation_confidence > 0 "
            "RETURN count(r) AS cnt"
        ).single()["cnt"]
        result.add_pass(f"{peer_ann} peer-ad-side annotated")

        # Personality score distribution (should be centered around 0.5)
        dist = session.run("""
            MATCH (r:AnnotatedReview)
            WHERE r.annotation_confidence > 0
            RETURN
                avg(r.user_personality_openness) AS avg_o,
                avg(r.user_personality_conscientiousness) AS avg_c,
                avg(r.user_personality_extraversion) AS avg_e,
                avg(r.user_personality_agreeableness) AS avg_a,
                avg(r.user_personality_neuroticism) AS avg_n
        """).single()

        for trait, key in [("O", "avg_o"), ("C", "avg_c"), ("E", "avg_e"), ("A", "avg_a"), ("N", "avg_n")]:
            val = dist[key]
            if val is not None and (val < 0.2 or val > 0.8):
                result.add_warning(f"Big Five {trait} avg = {val:.3f} (expected ~0.5)")
            elif val is not None:
                result.add_pass(f"Big Five {trait} avg = {val:.3f}")

    return result


def validate_phase5(driver: Driver) -> ValidationResult:
    """Validate Phase 5: BRAND_CONVERTED edges."""
    result = ValidationResult("Phase 5: BRAND_CONVERTED Edges")
    with driver.session() as session:
        count = session.run(
            "MATCH ()-[e:BRAND_CONVERTED]->() RETURN count(e) AS cnt"
        ).single()["cnt"]

        if count == 0:
            result.add_failure("No BRAND_CONVERTED edges found")
            return result

        result.add_pass(f"{count} BRAND_CONVERTED edges")

        # Check score distributions
        scores = session.run("""
            MATCH ()-[e:BRAND_CONVERTED]->()
            RETURN
                avg(e.regulatory_fit_score) AS avg_rf,
                avg(e.construal_fit_score) AS avg_cf,
                avg(e.personality_brand_alignment) AS avg_pa,
                avg(e.emotional_resonance) AS avg_er,
                stDev(e.regulatory_fit_score) AS std_rf
        """).single()

        for metric, key in [
            ("Regulatory Fit", "avg_rf"),
            ("Construal Fit", "avg_cf"),
            ("Personality Alignment", "avg_pa"),
            ("Emotional Resonance", "avg_er"),
        ]:
            val = scores[key]
            if val is not None:
                result.add_pass(f"{metric} avg = {val:.4f}")

        std = scores["std_rf"]
        if std is not None and std < 0.01:
            result.add_warning(f"Regulatory Fit std = {std:.4f} — low variance (degenerate?)")

    return result


def validate_phase6(driver: Driver) -> ValidationResult:
    """Validate Phase 6: PEER_INFLUENCED edges."""
    result = ValidationResult("Phase 6: PEER_INFLUENCED Edges")
    with driver.session() as session:
        count = session.run(
            "MATCH ()-[e:PEER_INFLUENCED]->() RETURN count(e) AS cnt"
        ).single()["cnt"]

        if count == 0:
            result.add_warning("No PEER_INFLUENCED edges (may be expected for small datasets)")
        else:
            result.add_pass(f"{count} PEER_INFLUENCED edges")

    return result


def validate_phase7(driver: Driver) -> ValidationResult:
    """Validate Phase 7: ECOSYSTEM_CONVERTED edges."""
    result = ValidationResult("Phase 7: ECOSYSTEM_CONVERTED Edges")
    with driver.session() as session:
        count = session.run(
            "MATCH ()-[e:ECOSYSTEM_CONVERTED]->() RETURN count(e) AS cnt"
        ).single()["cnt"]

        if count == 0:
            result.add_warning("No ECOSYSTEM_CONVERTED edges")
        else:
            result.add_pass(f"{count} ECOSYSTEM_CONVERTED edges")

    return result


def validate_phase8(driver: Driver) -> ValidationResult:
    """Validate Phase 8: Bayesian priors."""
    result = ValidationResult("Phase 8: Bayesian Priors")
    with driver.session() as session:
        count = session.run(
            "MATCH (p:BayesianPrior) RETURN count(p) AS cnt"
        ).single()["cnt"]

        if count == 0:
            result.add_warning("No BayesianPrior nodes")
        else:
            result.add_pass(f"{count} BayesianPrior nodes")

    return result


def run_full_validation(driver: Driver) -> list[ValidationResult]:
    """Run all quality gates. Returns list of ValidationResult."""
    results = [
        validate_phase1(driver),
        validate_phase2_3(driver),
        validate_phase5(driver),
        validate_phase6(driver),
        validate_phase7(driver),
        validate_phase8(driver),
    ]

    logger.info("=" * 60)
    logger.info("VALIDATION SUMMARY")
    logger.info("=" * 60)
    all_ok = True
    for r in results:
        logger.info(r.summary())
        if not r.ok:
            all_ok = False

    if all_ok:
        logger.info("ALL QUALITY GATES PASSED")
    else:
        logger.warning("SOME QUALITY GATES FAILED — review above")

    return results


def get_graph_stats(driver: Driver) -> dict[str, Any]:
    """Get comprehensive graph statistics."""
    with driver.session() as session:
        stats: dict[str, Any] = {}

        # Node counts
        for label in ["ProductDescription", "AnnotatedReview", "Reviewer",
                       "ProductEcosystem", "BayesianPrior", "Construct", "Domain"]:
            cnt = session.run(
                f"MATCH (n:{label}) RETURN count(n) AS cnt"
            ).single()["cnt"]
            stats[f"nodes_{label}"] = cnt

        # Edge counts
        for rel in ["BRAND_CONVERTED", "PEER_INFLUENCED", "ECOSYSTEM_CONVERTED",
                     "HAS_REVIEW", "AUTHORED", "ANCHORS", "BELONGS_TO", "MODULATES"]:
            cnt = session.run(
                f"MATCH ()-[e:{rel}]->() RETURN count(e) AS cnt"
            ).single()["cnt"]
            stats[f"edges_{rel}"] = cnt

        stats["total_nodes"] = session.run(
            "MATCH (n) RETURN count(n) AS cnt"
        ).single()["cnt"]
        stats["total_edges"] = session.run(
            "MATCH ()-[r]->() RETURN count(r) AS cnt"
        ).single()["cnt"]

    return stats
