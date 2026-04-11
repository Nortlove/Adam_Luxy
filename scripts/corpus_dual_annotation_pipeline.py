"""
ADAM Corpus Dual-Annotation Pipeline — 8-Phase Processing.

Processes the 937M+ review corpus with dual annotation and constructs
the three edge types (BRAND_CONVERTED, PEER_INFLUENCED, ECOSYSTEM_CONVERTED).

AUTHORITATIVE SOURCE: taxonomy/ADAM_Corpus_Architecture_Addendum_Dual_Annotation.md

8 Phases:
  Phase 1: AD-SIDE — Product Descriptions (Domains 29-33)
  Phase 2: USER-SIDE — Reviews as Author Expression (Domains 1-22)
  Phase 3: PEER-AD-SIDE — Reviews as Persuasion Content (Domains 29-33 + 34) [NEW]
  Phase 4: ECOSYSTEM CONSTRUCTION per product (Domain 35) [NEW]
  Phase 5: EDGE TYPE 1 — Brand-to-Buyer (BRAND_CONVERTED)
  Phase 6: EDGE TYPE 2 — Peer-to-Buyer (PEER_INFLUENCED) [NEW]
  Phase 7: EDGE TYPE 3 — Ecosystem-to-Buyer (ECOSYSTEM_CONVERTED) [NEW]
  Phase 8: BAYESIAN PRIOR GENERATION from all three edge types

Tiered annotation priority for Phase 3 (peer-ad-side):
  - Must (50M): Top 5% helpful votes — highest peer influence signal
  - Should (200M): 5-20% helpful votes — moderate signal
  - Could (remaining): Random 10M sample — baseline coverage

Usage:
    python scripts/corpus_dual_annotation_pipeline.py --phase 1 --data-dir /Volumes/Sped/Nocera\\ Models/Review\\ Data/Amazon
    python scripts/corpus_dual_annotation_pipeline.py --phase all --data-dir /path/to/data
    python scripts/corpus_dual_annotation_pipeline.py --dry-run --phase 1
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from adam.intelligence.construct_taxonomy import (
    ALL_DOMAINS,
    Construct,
    Domain,
    EdgeType,
    InferenceTier,
    ScoringSwitch,
    get_all_constructs,
    get_constructs_by_side,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


# =============================================================================
# CONFIG
# =============================================================================

@dataclass
class PipelineConfig:
    """Configuration for the dual-annotation pipeline."""
    data_dir: str = ""
    output_dir: str = "data/corpus_annotations"
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = ""
    batch_size: int = 1000
    dry_run: bool = False

    # Phase 3 tiering thresholds
    peer_must_threshold: float = 0.95   # Top 5% by helpful votes
    peer_should_threshold: float = 0.80  # Next 15%
    peer_sample_size: int = 10_000_000   # Random sample for "could" tier

    # Parallelism
    num_workers: int = 4


# =============================================================================
# PHASE DEFINITIONS
# =============================================================================

@dataclass
class PhaseResult:
    """Result of a pipeline phase."""
    phase: int
    phase_name: str
    items_processed: int = 0
    items_skipped: int = 0
    errors: int = 0
    elapsed_seconds: float = 0.0
    output_path: str = ""

    @property
    def throughput(self) -> float:
        """Items per second."""
        return self.items_processed / max(0.001, self.elapsed_seconds)


class DualAnnotationPipeline:
    """
    The 8-phase corpus processing pipeline.

    Each phase reads from the appropriate data source, applies construct
    annotations, and writes results for the next phase.
    """

    def __init__(self, config: PipelineConfig):
        self.config = config
        self._all_constructs = get_all_constructs()
        self._user_constructs = get_constructs_by_side(ScoringSwitch.USER_SIDE)
        self._ad_constructs = get_constructs_by_side(ScoringSwitch.AD_SIDE)
        self._shared_constructs = get_constructs_by_side(ScoringSwitch.BOTH)
        self._ecosystem_constructs = get_constructs_by_side(ScoringSwitch.ECOSYSTEM)

        # Ensure output directory exists
        os.makedirs(config.output_dir, exist_ok=True)

    def run_phase(self, phase: int) -> PhaseResult:
        """Run a specific phase."""
        phases = {
            1: self._phase_1_ad_side_product_descriptions,
            2: self._phase_2_user_side_reviews,
            3: self._phase_3_peer_ad_side_reviews,
            4: self._phase_4_ecosystem_construction,
            5: self._phase_5_brand_to_buyer_edges,
            6: self._phase_6_peer_to_buyer_edges,
            7: self._phase_7_ecosystem_to_buyer_edges,
            8: self._phase_8_bayesian_prior_generation,
        }
        if phase not in phases:
            raise ValueError(f"Unknown phase: {phase}. Valid: 1-8")
        return phases[phase]()

    def run_all(self) -> list[PhaseResult]:
        """Run all 8 phases sequentially."""
        results = []
        for phase in range(1, 9):
            logger.info(f"Starting Phase {phase}...")
            result = self.run_phase(phase)
            results.append(result)
            logger.info(
                f"Phase {phase} complete: {result.items_processed} items "
                f"in {result.elapsed_seconds:.1f}s "
                f"({result.throughput:.0f} items/s)"
            )
        return results

    # =========================================================================
    # PHASE 1: AD-SIDE — Product Descriptions (Domains 29-33)
    # =========================================================================

    def _phase_1_ad_side_product_descriptions(self) -> PhaseResult:
        """
        Score product descriptions with ad-side constructs (Domains 29-33).

        Input: Product metadata files ({Category}.jsonl with 'description', 'title', etc.)
        Output: {asin: {construct_id: score}} for each product
        """
        result = PhaseResult(phase=1, phase_name="AD-SIDE Product Descriptions")
        start = time.monotonic()

        # Ad-side constructs for product descriptions
        ad_constructs = {
            cid: c for cid, c in self._all_constructs.items()
            if c.scoring_side in (ScoringSwitch.AD_SIDE, ScoringSwitch.BOTH)
            and c.domain_id in ("ad_style", "persuasion_techniques", "value_propositions",
                                "brand_personality", "linguistic_style",
                                "emotion", "values", "trust_credibility")
        }

        output_path = os.path.join(self.config.output_dir, "phase1_ad_side.jsonl")
        result.output_path = output_path

        if self.config.dry_run:
            logger.info(f"  [DRY RUN] Phase 1 would score {len(ad_constructs)} constructs per product")
            logger.info(f"  [DRY RUN] Output: {output_path}")
            result.elapsed_seconds = time.monotonic() - start
            return result

        # Process product metadata files
        for product in self._iter_product_metadata():
            try:
                scores = self._score_text_ad_side(
                    product.get("description", ""),
                    product.get("title", ""),
                    ad_constructs,
                )
                self._write_annotation(output_path, {
                    "asin": product.get("asin", ""),
                    "type": "product_description",
                    "constructs": scores,
                })
                result.items_processed += 1
            except Exception as e:
                result.errors += 1
                if result.errors <= 10:
                    logger.error(f"Phase 1 error: {e}")

        result.elapsed_seconds = time.monotonic() - start
        return result

    # =========================================================================
    # PHASE 2: USER-SIDE — Reviews as Author Expression (Domains 1-22)
    # =========================================================================

    def _phase_2_user_side_reviews(self) -> PhaseResult:
        """
        Score reviews for what they reveal about the AUTHOR's psychology.

        "What does this review tell us about the person who wrote it?"

        Input: Review files ({Category}.jsonl with 'reviewText', 'reviewerID', etc.)
        Output: {review_id: {construct_id: score}} for user-side constructs
        """
        result = PhaseResult(phase=2, phase_name="USER-SIDE Reviews as Author Expression")
        start = time.monotonic()

        user_constructs = {
            cid: c for cid, c in self._all_constructs.items()
            if c.scoring_side in (ScoringSwitch.USER_SIDE, ScoringSwitch.BOTH)
        }

        output_path = os.path.join(self.config.output_dir, "phase2_user_side.jsonl")
        result.output_path = output_path

        if self.config.dry_run:
            logger.info(f"  [DRY RUN] Phase 2 would score {len(user_constructs)} constructs per review")
            logger.info(f"  [DRY RUN] Output: {output_path}")
            result.elapsed_seconds = time.monotonic() - start
            return result

        for review in self._iter_reviews():
            try:
                scores = self._score_review_user_side(
                    review.get("reviewText", ""),
                    review.get("summary", ""),
                    review.get("overall", 3.0),
                    user_constructs,
                )
                self._write_annotation(output_path, {
                    "review_id": review.get("reviewerID", "") + "_" + review.get("asin", ""),
                    "reviewer_id": review.get("reviewerID", ""),
                    "asin": review.get("asin", ""),
                    "type": "user_expression",
                    "constructs": scores,
                })
                result.items_processed += 1
            except Exception as e:
                result.errors += 1
                if result.errors <= 10:
                    logger.error(f"Phase 2 error: {e}")

        result.elapsed_seconds = time.monotonic() - start
        return result

    # =========================================================================
    # PHASE 3: PEER-AD-SIDE — Reviews as Persuasion Content (Domains 29-33 + 34)
    # =========================================================================

    def _phase_3_peer_ad_side_reviews(self) -> PhaseResult:
        """
        Score reviews for their PERSUASIVE CONTENT for subsequent readers.

        "What persuasion does this review deliver to someone reading it?"

        This is the dual annotation: same review text, different question.

        Tiered priority:
          Must (50M): Top 5% helpful votes
          Should (200M): 5-20% helpful votes
          Could (remaining): Random 10M sample

        Input: Review files + helpful vote data
        Output: {review_id: {construct_id: score}} for ad-side + peer-persuasion constructs
        """
        result = PhaseResult(phase=3, phase_name="PEER-AD-SIDE Reviews as Persuasion Content")
        start = time.monotonic()

        # Peer-ad constructs = standard ad-side + Domain 34 peer persuasion
        peer_ad_constructs = {
            cid: c for cid, c in self._all_constructs.items()
            if c.scoring_side == ScoringSwitch.AD_SIDE
            and c.domain_id in ("ad_style", "persuasion_techniques", "value_propositions",
                                "brand_personality", "linguistic_style", "peer_persuasion")
        }

        output_path = os.path.join(self.config.output_dir, "phase3_peer_ad_side.jsonl")
        result.output_path = output_path

        if self.config.dry_run:
            logger.info(f"  [DRY RUN] Phase 3 would score {len(peer_ad_constructs)} constructs per review")
            logger.info(f"  [DRY RUN] Tiered: Must=top 5%, Should=5-20%, Could=10M sample")
            logger.info(f"  [DRY RUN] Output: {output_path}")
            result.elapsed_seconds = time.monotonic() - start
            return result

        for review in self._iter_reviews_tiered():
            try:
                scores = self._score_review_peer_ad_side(
                    review.get("reviewText", ""),
                    review.get("summary", ""),
                    review.get("overall", 3.0),
                    review.get("helpful_votes", 0),
                    peer_ad_constructs,
                )
                self._write_annotation(output_path, {
                    "review_id": review.get("reviewerID", "") + "_" + review.get("asin", ""),
                    "reviewer_id": review.get("reviewerID", ""),
                    "asin": review.get("asin", ""),
                    "type": "peer_persuasion",
                    "tier": review.get("_tier", "could"),
                    "constructs": scores,
                })
                result.items_processed += 1
            except Exception as e:
                result.errors += 1
                if result.errors <= 10:
                    logger.error(f"Phase 3 error: {e}")

        result.elapsed_seconds = time.monotonic() - start
        return result

    # =========================================================================
    # PHASE 4: ECOSYSTEM CONSTRUCTION per product (Domain 35)
    # =========================================================================

    def _phase_4_ecosystem_construction(self) -> PhaseResult:
        """
        Build ProductEcosystem nodes by aggregating all persuasion content per ASIN.

        Input: Phase 1 output (brand annotations) + Phase 3 output (peer annotations)
        Output: {asin: {eco_construct_id: score}} for Domain 35 constructs
        """
        result = PhaseResult(phase=4, phase_name="ECOSYSTEM CONSTRUCTION")
        start = time.monotonic()

        eco_constructs = {
            cid: c for cid, c in self._all_constructs.items()
            if c.scoring_side == ScoringSwitch.ECOSYSTEM
        }

        output_path = os.path.join(self.config.output_dir, "phase4_ecosystem.jsonl")
        result.output_path = output_path

        if self.config.dry_run:
            logger.info(f"  [DRY RUN] Phase 4 would compute {len(eco_constructs)} ecosystem constructs per product")
            logger.info(f"  [DRY RUN] Output: {output_path}")
            result.elapsed_seconds = time.monotonic() - start
            return result

        # Aggregate by ASIN
        for asin, brand_scores, peer_scores_list in self._iter_product_ecosystems():
            try:
                eco_scores = self._compute_ecosystem_constructs(
                    asin, brand_scores, peer_scores_list, eco_constructs
                )
                self._write_annotation(output_path, {
                    "asin": asin,
                    "type": "ecosystem",
                    "review_count": len(peer_scores_list),
                    "constructs": eco_scores,
                })
                result.items_processed += 1
            except Exception as e:
                result.errors += 1
                if result.errors <= 10:
                    logger.error(f"Phase 4 error: {e}")

        result.elapsed_seconds = time.monotonic() - start
        return result

    # =========================================================================
    # PHASE 5: BRAND_CONVERTED edges
    # =========================================================================

    def _phase_5_brand_to_buyer_edges(self) -> PhaseResult:
        """
        Create BRAND_CONVERTED edges: ProductDescription -> Review.

        For each review, compute the alignment between the product's brand
        constructs (Phase 1) and the reviewer's user constructs (Phase 2).
        """
        result = PhaseResult(phase=5, phase_name="BRAND_CONVERTED Edges")
        start = time.monotonic()
        output_path = os.path.join(self.config.output_dir, "phase5_brand_edges.jsonl")
        result.output_path = output_path

        if self.config.dry_run:
            logger.info(f"  [DRY RUN] Phase 5 would create BRAND_CONVERTED edges")
            logger.info(f"  [DRY RUN] Output: {output_path}")
            result.elapsed_seconds = time.monotonic() - start
            return result

        for asin, brand_ann, review_ann in self._iter_brand_review_pairs():
            try:
                edge_data = self._compute_brand_edge(asin, brand_ann, review_ann)
                self._write_annotation(output_path, edge_data)
                result.items_processed += 1
            except Exception as e:
                result.errors += 1

        result.elapsed_seconds = time.monotonic() - start
        return result

    # =========================================================================
    # PHASE 6: PEER_INFLUENCED edges
    # =========================================================================

    def _phase_6_peer_to_buyer_edges(self) -> PhaseResult:
        """
        Create PEER_INFLUENCED edges: Influential Review -> Subsequent Review.

        For reviews with helpful votes, compute influence on subsequent reviewers.
        """
        result = PhaseResult(phase=6, phase_name="PEER_INFLUENCED Edges")
        start = time.monotonic()
        output_path = os.path.join(self.config.output_dir, "phase6_peer_edges.jsonl")
        result.output_path = output_path

        if self.config.dry_run:
            logger.info(f"  [DRY RUN] Phase 6 would create PEER_INFLUENCED edges")
            logger.info(f"  [DRY RUN] Output: {output_path}")
            result.elapsed_seconds = time.monotonic() - start
            return result

        for influencer_ann, buyer_ann in self._iter_peer_influence_pairs():
            try:
                edge_data = self._compute_peer_edge(influencer_ann, buyer_ann)
                self._write_annotation(output_path, edge_data)
                result.items_processed += 1
            except Exception as e:
                result.errors += 1

        result.elapsed_seconds = time.monotonic() - start
        return result

    # =========================================================================
    # PHASE 7: ECOSYSTEM_CONVERTED edges
    # =========================================================================

    def _phase_7_ecosystem_to_buyer_edges(self) -> PhaseResult:
        """
        Create ECOSYSTEM_CONVERTED edges: ProductEcosystem -> Review.

        Links the product's overall persuasion ecosystem to each buyer.
        """
        result = PhaseResult(phase=7, phase_name="ECOSYSTEM_CONVERTED Edges")
        start = time.monotonic()
        output_path = os.path.join(self.config.output_dir, "phase7_eco_edges.jsonl")
        result.output_path = output_path

        if self.config.dry_run:
            logger.info(f"  [DRY RUN] Phase 7 would create ECOSYSTEM_CONVERTED edges")
            logger.info(f"  [DRY RUN] Output: {output_path}")
            result.elapsed_seconds = time.monotonic() - start
            return result

        for asin, eco_ann, review_ann in self._iter_ecosystem_review_pairs():
            try:
                edge_data = self._compute_ecosystem_edge(asin, eco_ann, review_ann)
                self._write_annotation(output_path, edge_data)
                result.items_processed += 1
            except Exception as e:
                result.errors += 1

        result.elapsed_seconds = time.monotonic() - start
        return result

    # =========================================================================
    # PHASE 8: BAYESIAN PRIOR GENERATION
    # =========================================================================

    def _phase_8_bayesian_prior_generation(self) -> PhaseResult:
        """
        Generate Bayesian priors from all three edge types.

        Aggregates across all edges to compute empirical priors for each
        (user_construct, ad_construct) pair, stratified by edge type.
        """
        result = PhaseResult(phase=8, phase_name="BAYESIAN PRIOR GENERATION")
        start = time.monotonic()
        output_path = os.path.join(self.config.output_dir, "phase8_priors.jsonl")
        result.output_path = output_path

        if self.config.dry_run:
            logger.info(f"  [DRY RUN] Phase 8 would generate Bayesian priors from all edges")
            logger.info(f"  [DRY RUN] Output: {output_path}")
            result.elapsed_seconds = time.monotonic() - start
            return result

        from adam.intelligence.bayesian_fusion import (
            BayesianFusionEngine, CampaignOutcome, EdgeType as BET, OutcomeType
        )
        engine = BayesianFusionEngine()

        # Process each edge type's output
        for edge_file, edge_type in [
            ("phase5_brand_edges.jsonl", BET.BRAND_CONVERTED),
            ("phase6_peer_edges.jsonl", BET.PEER_INFLUENCED),
            ("phase7_eco_edges.jsonl", BET.ECOSYSTEM_CONVERTED),
        ]:
            filepath = os.path.join(self.config.output_dir, edge_file)
            if not os.path.exists(filepath):
                logger.warning(f"Phase 8: {filepath} not found, skipping")
                continue

            for edge_data in self._iter_jsonl(filepath):
                try:
                    outcome = CampaignOutcome(
                        campaign_id=edge_data.get("review_id", ""),
                        user_id=edge_data.get("reviewer_id", ""),
                        asin=edge_data.get("asin", ""),
                        outcome_type=OutcomeType.PURCHASE,
                        outcome_value=edge_data.get("outcome", 0.5),
                        user_construct_scores=edge_data.get("user_constructs", {}),
                        ad_construct_scores=edge_data.get("ad_constructs", {}),
                        peer_construct_scores=edge_data.get("peer_constructs", {}),
                        ecosystem_construct_scores=edge_data.get("eco_constructs", {}),
                        edge_types=[edge_type],
                    )
                    engine.process_outcome(outcome)
                    result.items_processed += 1
                except Exception as e:
                    result.errors += 1

        # Persist final priors
        persisted = engine.persist_to_neo4j()
        logger.info(f"Phase 8: Persisted {persisted} Bayesian priors to Neo4j")

        # Write metrics
        metrics = engine.get_flywheel_metrics()
        self._write_annotation(output_path, {
            "type": "prior_generation_metrics",
            "metrics": metrics,
        })

        result.elapsed_seconds = time.monotonic() - start
        return result

    # =========================================================================
    # DATA ITERATORS (stubs — to be implemented with actual data access)
    # =========================================================================

    def _iter_product_metadata(self) -> Iterator[dict]:
        """Iterate over product metadata files."""
        data_dir = self.config.data_dir
        if not data_dir or not os.path.exists(data_dir):
            logger.warning(f"Data dir not found: {data_dir}")
            return

        for filename in sorted(os.listdir(data_dir)):
            if filename.endswith("_meta.jsonl") or filename.startswith("meta_"):
                filepath = os.path.join(data_dir, filename)
                yield from self._iter_jsonl(filepath)

    def _iter_reviews(self) -> Iterator[dict]:
        """Iterate over all reviews."""
        data_dir = self.config.data_dir
        if not data_dir or not os.path.exists(data_dir):
            return

        for filename in sorted(os.listdir(data_dir)):
            if filename.endswith(".jsonl") and not filename.startswith("meta_"):
                filepath = os.path.join(data_dir, filename)
                yield from self._iter_jsonl(filepath)

    def _iter_reviews_tiered(self) -> Iterator[dict]:
        """Iterate over reviews with tiered priority annotation."""
        # In production, this would sort by helpful votes and assign tiers
        for review in self._iter_reviews():
            helpful = review.get("helpful", [0, 0])
            if isinstance(helpful, list) and len(helpful) >= 2:
                helpful_votes = helpful[0]
            elif isinstance(helpful, (int, float)):
                helpful_votes = helpful
            else:
                helpful_votes = 0
            review["helpful_votes"] = helpful_votes

            # Assign tier (in production, use precomputed percentiles)
            if helpful_votes >= 50:
                review["_tier"] = "must"
            elif helpful_votes >= 5:
                review["_tier"] = "should"
            else:
                review["_tier"] = "could"

            yield review

    def _iter_product_ecosystems(self) -> Iterator[tuple]:
        """Iterate over product ecosystems (aggregated by ASIN)."""
        # Stub: reads Phase 1 + Phase 3 outputs and groups by ASIN
        return iter([])

    def _iter_brand_review_pairs(self) -> Iterator[tuple]:
        """Iterate over (asin, brand_annotation, review_annotation) triples."""
        return iter([])

    def _iter_peer_influence_pairs(self) -> Iterator[tuple]:
        """Iterate over (influencer_annotation, buyer_annotation) pairs."""
        return iter([])

    def _iter_ecosystem_review_pairs(self) -> Iterator[tuple]:
        """Iterate over (asin, ecosystem_annotation, review_annotation) triples."""
        return iter([])

    def _iter_jsonl(self, filepath: str) -> Iterator[dict]:
        """Iterate over a JSONL file."""
        try:
            with open(filepath, "r") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            yield json.loads(line)
                        except json.JSONDecodeError:
                            continue
        except FileNotFoundError:
            logger.warning(f"File not found: {filepath}")

    # =========================================================================
    # SCORING STUBS (to be implemented with Claude/NLP)
    # =========================================================================

    def _score_text_ad_side(
        self, description: str, title: str, constructs: dict[str, Construct]
    ) -> dict[str, float]:
        """Score product description text for ad-side constructs."""
        # TODO: Implement with Claude API or NLP pipeline
        # For now, return prior means
        return {cid: c.prior.alpha / (c.prior.alpha + c.prior.beta) for cid, c in constructs.items()}

    def _score_review_user_side(
        self, text: str, summary: str, rating: float, constructs: dict[str, Construct]
    ) -> dict[str, float]:
        """Score review text for user-side constructs (author expression)."""
        # TODO: Implement with Claude API or NLP pipeline
        return {cid: c.prior.alpha / (c.prior.alpha + c.prior.beta) for cid, c in constructs.items()}

    def _score_review_peer_ad_side(
        self, text: str, summary: str, rating: float, helpful_votes: int,
        constructs: dict[str, Construct]
    ) -> dict[str, float]:
        """Score review text for peer-ad-side constructs (persuasion content)."""
        # TODO: Implement with Claude API or NLP pipeline
        return {cid: c.prior.alpha / (c.prior.alpha + c.prior.beta) for cid, c in constructs.items()}

    def _compute_ecosystem_constructs(
        self, asin: str, brand_scores: dict, peer_scores_list: list[dict],
        constructs: dict[str, Construct]
    ) -> dict[str, float]:
        """Compute Domain 35 ecosystem constructs from brand + peer data."""
        # TODO: Implement ecosystem aggregation logic
        return {cid: 0.5 for cid in constructs}

    def _compute_brand_edge(
        self, asin: str, brand_ann: dict, review_ann: dict
    ) -> dict:
        """Compute BRAND_CONVERTED edge data."""
        return {
            "asin": asin,
            "review_id": review_ann.get("review_id", ""),
            "reviewer_id": review_ann.get("reviewer_id", ""),
            "edge_type": "BRAND_CONVERTED",
            "outcome": review_ann.get("rating", 3.0) / 5.0,
            "user_constructs": review_ann.get("constructs", {}),
            "ad_constructs": brand_ann.get("constructs", {}),
        }

    def _compute_peer_edge(self, influencer_ann: dict, buyer_ann: dict) -> dict:
        """Compute PEER_INFLUENCED edge data."""
        return {
            "influencer_review_id": influencer_ann.get("review_id", ""),
            "buyer_review_id": buyer_ann.get("review_id", ""),
            "edge_type": "PEER_INFLUENCED",
            "outcome": buyer_ann.get("rating", 3.0) / 5.0,
            "user_constructs": buyer_ann.get("constructs", {}),
            "peer_constructs": influencer_ann.get("constructs", {}),
        }

    def _compute_ecosystem_edge(
        self, asin: str, eco_ann: dict, review_ann: dict
    ) -> dict:
        """Compute ECOSYSTEM_CONVERTED edge data."""
        return {
            "asin": asin,
            "review_id": review_ann.get("review_id", ""),
            "reviewer_id": review_ann.get("reviewer_id", ""),
            "edge_type": "ECOSYSTEM_CONVERTED",
            "outcome": review_ann.get("rating", 3.0) / 5.0,
            "user_constructs": review_ann.get("constructs", {}),
            "eco_constructs": eco_ann.get("constructs", {}),
        }

    # =========================================================================
    # UTILITY
    # =========================================================================

    def _write_annotation(self, filepath: str, data: dict) -> None:
        """Write a single annotation to a JSONL file."""
        with open(filepath, "a") as f:
            f.write(json.dumps(data) + "\n")


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="ADAM Corpus Dual-Annotation Pipeline")
    parser.add_argument(
        "--phase", default="all",
        help="Phase to run: 1-8 or 'all' (default: all)"
    )
    parser.add_argument(
        "--data-dir",
        help="Path to review data directory"
    )
    parser.add_argument("--output-dir", default="data/corpus_annotations")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--batch-size", type=int, default=1000)
    args = parser.parse_args()

    config = PipelineConfig(
        data_dir=args.data_dir or "",
        output_dir=args.output_dir,
        dry_run=args.dry_run,
        batch_size=args.batch_size,
    )

    pipeline = DualAnnotationPipeline(config)

    if args.phase == "all":
        results = pipeline.run_all()
    else:
        result = pipeline.run_phase(int(args.phase))
        results = [result]

    # Print summary
    print("\n" + "=" * 70)
    print("PIPELINE SUMMARY")
    print("=" * 70)
    for r in results:
        print(f"  Phase {r.phase} ({r.phase_name}):")
        print(f"    Processed: {r.items_processed}")
        print(f"    Errors: {r.errors}")
        print(f"    Time: {r.elapsed_seconds:.1f}s")
        print(f"    Output: {r.output_path}")


if __name__ == "__main__":
    main()
