"""
INFORMATIV Audience Taxonomy Generator for StackAdapt
======================================================

Batch process that transforms ADAM's graph intelligence and 937M-review
empirical priors into StackAdapt-compatible audience segments.

Segment tiers:
    Tier 1 — Archetype Segments (6):        informativ_{archetype}
    Tier 2 — Mechanism-Optimized (~36):      informativ_{archetype}_{mechanism}
    Tier 3 — Category-Specific (~200+):      informativ_{category}_{archetype}

Each segment carries:
    - NDF profile (7+1 dimensions)
    - Top mechanisms with empirical success rates
    - Optimal creative parameters
    - Expected lift from 937M-review corpus
    - Graph-backed confidence from BayesianPrior nodes + BRAND_CONVERTED edges
    - Mechanism synergy/antagonism data

Intelligence sources (priority order):
    1. Graph intelligence export (BRAND_CONVERTED edge aggregates, BayesianPriors)
    2. Graph cache (live Neo4j queries, BayesianPrior nodes, mechanism synergies)
    3. JSON priors (ingestion_merged_priors.json)
    4. Fast lookup tables
    5. Research-grounded defaults

Output: JSON taxonomy file + ready for Data Taxonomy API push.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent


@dataclass
class SegmentDefinition:
    """A single INFORMATIV audience segment ready for StackAdapt."""

    segment_id: str
    name: str
    tier: int
    archetype: str
    category: str = ""
    mechanism_focus: str = ""

    ndf_profile: Dict[str, float] = field(default_factory=dict)
    top_mechanisms: List[Dict[str, Any]] = field(default_factory=list)
    creative_parameters: Dict[str, str] = field(default_factory=dict)

    expected_ctr_lift_pct: float = 0.0
    expected_conv_lift_pct: float = 0.0
    confidence_level: str = "ingestion_derived"
    evidence_sample_size: int = 0

    description: str = ""
    internal_cpm: float = 2.50

    created_at: str = ""


_ARCHETYPE_DESCRIPTIONS = {
    # 6 empirically-validated archetypes covering 99.2% of 937M-review corpus
    "achiever": "Goal-oriented, promotion-focused (44.5% of corpus). High status sensitivity and cognitive engagement. Responds to aspiration framing and authority signals. 4.4M+ mechanism observations.",
    "guardian": "Prevention-focused, risk-averse (21.5% of corpus). Low uncertainty tolerance. Responds to authority, trust signals, and loss-framing. 5.0M+ mechanism observations.",
    "connector": "Socially-calibrated, community-oriented (14.0% of corpus). High social calibration. Responds to social proof, unity, and belonging appeals. 2.8M+ mechanism observations.",
    "explorer": "Novelty-seeking, open to new experiences (11.4% of corpus). High uncertainty tolerance, arousal seeking. Responds to discovery framing and curiosity gaps. 4.0M+ mechanism observations.",
    "analyst": "Detail-oriented, high cognitive engagement (5.2% of corpus). Seeks specifications and evidence. Responds to central-route persuasion and authority. 2.6M+ mechanism observations.",
    "pragmatist": "Balanced decision-maker, value-oriented (2.6% of corpus). Moderate on all dimensions. Responds to practical evidence and clear ROI framing. 238K+ mechanism observations.",
}

_ARCHETYPE_NDF_PROFILES = {
    # 6 empirically-validated archetypes aligned with priors data
    "achiever": {
        "approach_avoidance": 0.80, "temporal_horizon": 0.60,
        "social_calibration": 0.50, "uncertainty_tolerance": 0.42,
        "status_sensitivity": 0.75, "cognitive_engagement": 0.70,
        "arousal_seeking": 0.55, "cognitive_velocity": 0.72,
    },
    "guardian": {
        "approach_avoidance": -0.20, "temporal_horizon": 0.70,
        "social_calibration": 0.55, "uncertainty_tolerance": 0.22,
        "status_sensitivity": 0.35, "cognitive_engagement": 0.65,
        "arousal_seeking": 0.25, "cognitive_velocity": 0.48,
    },
    "connector": {
        "approach_avoidance": 0.55, "temporal_horizon": 0.50,
        "social_calibration": 0.82, "uncertainty_tolerance": 0.45,
        "status_sensitivity": 0.40, "cognitive_engagement": 0.45,
        "arousal_seeking": 0.42, "cognitive_velocity": 0.55,
    },
    "explorer": {
        "approach_avoidance": 0.72, "temporal_horizon": 0.35,
        "social_calibration": 0.40, "uncertainty_tolerance": 0.78,
        "status_sensitivity": 0.45, "cognitive_engagement": 0.55,
        "arousal_seeking": 0.80, "cognitive_velocity": 0.65,
    },
    "analyst": {
        "approach_avoidance": 0.30, "temporal_horizon": 0.65,
        "social_calibration": 0.30, "uncertainty_tolerance": 0.60,
        "status_sensitivity": 0.50, "cognitive_engagement": 0.88,
        "arousal_seeking": 0.30, "cognitive_velocity": 0.80,
    },
    "pragmatist": {
        "approach_avoidance": 0.50, "temporal_horizon": 0.55,
        "social_calibration": 0.45, "uncertainty_tolerance": 0.50,
        "status_sensitivity": 0.42, "cognitive_engagement": 0.72,
        "arousal_seeking": 0.38, "cognitive_velocity": 0.62,
    },
}

_MECHANISM_LABELS = {
    "social_proof": "Social Proof",
    "authority": "Authority",
    "scarcity": "Scarcity",
    "reciprocity": "Reciprocity",
    "commitment": "Commitment & Consistency",
    "liking": "Liking & Similarity",
    "fomo": "Fear of Missing Out",
    "unity": "Unity & Belonging",
}


class TaxonomyGenerator:
    """
    Generates the full INFORMATIV segment taxonomy for StackAdapt.

    Supports three intelligence sources (in priority order):
      1. Graph intelligence export from batch refresh script
      2. Live graph cache (BayesianPriors, mechanism synergies)
      3. JSON priors and fast lookup tables
    """

    def __init__(self):
        self._priors: Optional[Dict[str, Any]] = None
        self._fast_lookup: Optional[Dict[str, Any]] = None
        self._graph_intel: Optional[Dict[str, Any]] = None
        self._graph_cache = None

    def load_data(self) -> None:
        """Load priors and fast lookup tables."""
        priors_path = _PROJECT_ROOT / "data" / "learning" / "ingestion_merged_priors.json"
        if priors_path.exists():
            with open(priors_path) as f:
                self._priors = json.load(f)
            logger.info("Loaded priors: %d keys", len(self._priors))

        lookup_path = _PROJECT_ROOT / "data" / "effectiveness_index" / "fast_lookup_tables.json"
        if lookup_path.exists():
            with open(lookup_path) as f:
                self._fast_lookup = json.load(f)
            logger.info("Loaded fast lookup tables")

        # Try loading graph intelligence export if available
        graph_export_path = _PROJECT_ROOT / "data" / "stackadapt" / "graph_intelligence_export.json"
        if graph_export_path.exists():
            try:
                with open(graph_export_path) as f:
                    self._graph_intel = json.load(f)
                n_combos = self._graph_intel.get("total_combinations", 0)
                logger.info("Loaded graph intelligence export: %d category x archetype combos", n_combos)
            except Exception as e:
                logger.warning("Failed to load graph intelligence export: %s", e)

        # Try loading graph cache for BayesianPriors + synergies
        try:
            from adam.api.stackadapt.graph_cache import get_graph_cache
            self._graph_cache = get_graph_cache()
            health = self._graph_cache.get_health()
            logger.info(
                "Graph cache available: %d BayesianPriors, %d synergies, %d antagonisms",
                health.get("bayesian_prior_count", 0),
                health.get("synergy_count", 0),
                health.get("antagonism_count", 0),
            )
        except Exception as e:
            logger.info("Graph cache not available (will use JSON priors only): %s", e)

    def load_graph_intelligence(self, graph_intel: Dict[str, Any]) -> None:
        """
        Load graph intelligence data directly (called by batch refresh script).
        Expects the category_archetype_edges dict from export_edge_analysis().
        """
        self._graph_intel = {
            "category_archetype_edges": graph_intel,
            "total_combinations": len(graph_intel),
        }
        logger.info(
            "Loaded graph intelligence: %d category x archetype combinations",
            len(graph_intel),
        )

    def generate(self) -> List[SegmentDefinition]:
        """Generate the full taxonomy across all three tiers."""
        start = time.time()
        now_iso = datetime.now(timezone.utc).isoformat()
        segments: List[SegmentDefinition] = []

        segments.extend(self._generate_tier1(now_iso))
        segments.extend(self._generate_tier2(now_iso))
        segments.extend(self._generate_tier3(now_iso))

        elapsed = time.time() - start
        logger.info(
            "Generated %d segments in %.2fs (T1=%d, T2=%d, T3=%d)",
            len(segments), elapsed,
            sum(1 for s in segments if s.tier == 1),
            sum(1 for s in segments if s.tier == 2),
            sum(1 for s in segments if s.tier == 3),
        )
        return segments

    def export_json(self, segments: List[SegmentDefinition], output_path: Path) -> None:
        """Export taxonomy to JSON file."""
        output_path.parent.mkdir(parents=True, exist_ok=True)

        intel_sources = ["json_priors"]
        if self._graph_intel:
            intel_sources.append("graph_edge_export")
        if self._graph_cache and self._graph_cache.neo4j_available:
            intel_sources.append("graph_cache_live")

        data = {
            "provider": "INFORMATIV",
            "version": "2.0.0",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "intelligence_sources": intel_sources,
            "total_segments": len(segments),
            "tiers": {
                "tier_1_archetype": sum(1 for s in segments if s.tier == 1),
                "tier_2_mechanism": sum(1 for s in segments if s.tier == 2),
                "tier_3_category": sum(1 for s in segments if s.tier == 3),
            },
            "segments": [asdict(s) for s in segments],
        }
        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)
        logger.info("Exported taxonomy to %s", output_path)

    # ─── Tier 1: Archetype Segments ─────────────────────────────────────────

    def _generate_tier1(self, now_iso: str) -> List[SegmentDefinition]:
        segments = []
        for archetype, ndf in _ARCHETYPE_NDF_PROFILES.items():
            mechs = self._get_top_mechanisms(archetype, "", k=5)
            total_sample = sum(m.get("sample_size", 0) for m in mechs)

            framing = "gain" if ndf["approach_avoidance"] > 0 else "loss"
            construal = "concrete" if ndf["temporal_horizon"] < 0.5 else "abstract"
            detail = "high" if ndf["cognitive_engagement"] > 0.65 else "moderate"

            primary = mechs[0]["mechanism"] if mechs else "social_proof"
            creative_params = {
                "framing": framing,
                "construal_level": construal,
                "detail_level": detail,
                "primary_mechanism": primary,
            }

            synergies = self._get_mechanism_synergies(primary)
            if synergies:
                creative_params["synergistic_mechanisms"] = synergies[:3]

            ctr_lift, conv_lift, confidence = self._compute_graph_backed_lift(
                archetype, "", total_sample, mechs,
            )

            segments.append(SegmentDefinition(
                segment_id=f"informativ_{archetype}",
                name=f"INFORMATIV {archetype.title()}",
                tier=1,
                archetype=archetype,
                ndf_profile=ndf,
                top_mechanisms=mechs,
                creative_parameters=creative_params,
                expected_ctr_lift_pct=ctr_lift,
                expected_conv_lift_pct=conv_lift,
                confidence_level=confidence,
                evidence_sample_size=total_sample,
                description=_ARCHETYPE_DESCRIPTIONS.get(archetype, ""),
                internal_cpm=2.50,
                created_at=now_iso,
            ))
        return segments

    # ─── Tier 2: Mechanism-Optimized Segments ───────────────────────────────

    def _generate_tier2(self, now_iso: str) -> List[SegmentDefinition]:
        segments = []
        for archetype, ndf in _ARCHETYPE_NDF_PROFILES.items():
            mechs = self._get_top_mechanisms(archetype, "", k=7)
            for mech_info in mechs[:6]:
                mech = mech_info["mechanism"]
                rate = mech_info.get("success_rate", 0.2)
                sample = mech_info.get("sample_size", 0)
                mech_label = _MECHANISM_LABELS.get(mech, mech.replace("_", " ").title())

                creative_params: Dict[str, Any] = {
                    "primary_mechanism": mech,
                    "framing": "gain" if ndf["approach_avoidance"] > 0 else "loss",
                    "optimized_for": mech,
                }

                synergies = self._get_mechanism_synergies(mech)
                antagonisms = self._get_mechanism_antagonisms(mech)
                if synergies:
                    creative_params["synergistic_mechanisms"] = synergies[:3]
                if antagonisms:
                    creative_params["avoid_combining_with"] = antagonisms[:2]

                bp_confidence = self._get_bayesian_confidence(mech, "")
                if bp_confidence:
                    mech_info = dict(mech_info)
                    mech_info["bayesian_confidence"] = bp_confidence

                ctr_lift = round(min(55.0, max(20.0, rate * 160)), 1)
                conv_lift = round(min(65.0, max(25.0, rate * 190)), 1)

                if sample > 100000:
                    confidence = "field_validated"
                elif sample > 10000:
                    confidence = "replicated"
                elif bp_confidence and bp_confidence.get("n_observations", 0) > 1000:
                    confidence = "bayesian_backed"
                else:
                    confidence = "ingestion_derived"

                desc = (
                    f"{archetype.title()} archetype optimized for {mech_label} mechanism. "
                    f"Success rate: {rate:.1%} across {sample:,} observations."
                )
                if synergies:
                    desc += f" Synergizes with: {', '.join(synergies[:2])}."

                segments.append(SegmentDefinition(
                    segment_id=f"informativ_{archetype}_{mech}",
                    name=f"INFORMATIV {archetype.title()} — {mech_label} Optimized",
                    tier=2,
                    archetype=archetype,
                    mechanism_focus=mech,
                    ndf_profile=ndf,
                    top_mechanisms=[mech_info],
                    creative_parameters=creative_params,
                    expected_ctr_lift_pct=ctr_lift,
                    expected_conv_lift_pct=conv_lift,
                    confidence_level=confidence,
                    evidence_sample_size=sample,
                    description=desc,
                    internal_cpm=3.00,
                    created_at=now_iso,
                ))
        return segments

    # ─── Tier 3: Category-Specific Segments ─────────────────────────────────

    def _generate_tier3(self, now_iso: str) -> List[SegmentDefinition]:
        segments = []
        categories = self._get_categories()

        for cat in categories:
            cat_slug = cat.lower().replace(" ", "_").replace("&", "and")
            for archetype, base_ndf in _ARCHETYPE_NDF_PROFILES.items():
                ndf = self._blend_ndf_with_category(base_ndf, cat)
                mechs = self._get_top_mechanisms(archetype, cat, k=5)
                total_sample = sum(m.get("sample_size", 0) for m in mechs)

                framing = "gain" if ndf["approach_avoidance"] > 0 else "loss"
                primary = mechs[0]["mechanism"] if mechs else "social_proof"

                creative_params: Dict[str, Any] = {
                    "framing": framing,
                    "primary_mechanism": primary,
                    "category": cat,
                }

                # Enrich with graph edge data for this category x archetype
                edge_data = self._get_graph_edge_data(cat, archetype)
                if edge_data:
                    composite = edge_data.get("averages", {}).get("composite_alignment")
                    reg_fit = edge_data.get("averages", {}).get("regulatory_fit_score")
                    if reg_fit is not None:
                        creative_params["graph_framing"] = "gain" if reg_fit > 0.5 else "loss"
                    if composite is not None:
                        creative_params["graph_composite_alignment"] = composite
                    total_sample = max(total_sample, edge_data.get("edge_count", 0))

                ctr_lift, conv_lift, confidence = self._compute_graph_backed_lift(
                    archetype, cat, total_sample, mechs,
                )

                desc = (
                    f"{archetype.title()} archetype in {cat}. "
                    f"Category-specific effectiveness from 937M-review corpus."
                )
                if edge_data:
                    ec = edge_data.get("edge_count", 0)
                    desc += f" Graph: {ec:,} BRAND_CONVERTED edges analyzed."

                segments.append(SegmentDefinition(
                    segment_id=f"informativ_{cat_slug}_{archetype}",
                    name=f"INFORMATIV {cat} — {archetype.title()}",
                    tier=3,
                    archetype=archetype,
                    category=cat,
                    ndf_profile=ndf,
                    top_mechanisms=mechs,
                    creative_parameters=creative_params,
                    expected_ctr_lift_pct=ctr_lift,
                    expected_conv_lift_pct=conv_lift,
                    confidence_level=confidence,
                    evidence_sample_size=total_sample,
                    description=desc,
                    internal_cpm=3.50,
                    created_at=now_iso,
                ))
        return segments

    # ─── Graph Intelligence Helpers ────────────────────────────────────────

    def _get_graph_edge_data(
        self, category: str, archetype: str,
    ) -> Optional[Dict[str, Any]]:
        """Get BRAND_CONVERTED edge data from graph intelligence export."""
        if not self._graph_intel:
            return None
        edges = self._graph_intel.get("category_archetype_edges", {})
        return edges.get(f"{category}:{archetype}")

    def _get_mechanism_synergies(self, mechanism: str) -> List[str]:
        """Get synergistic mechanisms from graph cache."""
        if self._graph_cache:
            return self._graph_cache.get_synergies_for(mechanism)
        return []

    def _get_mechanism_antagonisms(self, mechanism: str) -> List[str]:
        """Get antagonistic mechanisms from graph cache."""
        if self._graph_cache:
            return self._graph_cache.get_antagonisms_for(mechanism)
        return []

    def _get_bayesian_confidence(
        self, mechanism: str, category: str,
    ) -> Optional[Dict[str, Any]]:
        """Get BayesianPrior-backed confidence for a mechanism in a category."""
        if not self._graph_cache:
            return None
        return self._graph_cache.get_bayesian_mechanism_confidence(
            category or "all", mechanism,
        )

    def _compute_graph_backed_lift(
        self,
        archetype: str,
        category: str,
        total_sample: int,
        mechs: List[Dict[str, Any]],
    ) -> tuple:
        """
        Compute lift and confidence using graph evidence when available.
        Returns (ctr_lift, conv_lift, confidence_level).
        """
        # Try graph edge data for category-specific lift
        if category:
            edge_data = self._get_graph_edge_data(category, archetype)
            if edge_data:
                composite = edge_data.get("averages", {}).get("composite_alignment")
                edge_count = edge_data.get("edge_count", 0)
                if composite is not None and edge_count > 50:
                    ctr = round(min(55.0, max(20.0, composite * 130)), 1)
                    conv = round(min(65.0, max(25.0, composite * 160)), 1)
                    if edge_count > 10000:
                        conf = "graph_field_validated"
                    elif edge_count > 1000:
                        conf = "graph_validated"
                    else:
                        conf = "graph_directional"
                    return ctr, conv, conf

        # Try BayesianPrior for mechanism-level confidence
        if mechs and self._graph_cache:
            primary = mechs[0]["mechanism"]
            bp = self._graph_cache.get_bayesian_mechanism_confidence(
                category or "all", primary,
            )
            if bp and bp["n_observations"] > 100:
                score = bp["weighted_score"]
                n_obs = bp["n_observations"]
                ctr = round(min(55.0, max(20.0, score * 150)), 1)
                conv = round(min(65.0, max(25.0, score * 180)), 1)
                if n_obs > 100000:
                    conf = "bayesian_field_validated"
                elif n_obs > 10000:
                    conf = "bayesian_replicated"
                else:
                    conf = "bayesian_moderate"
                return ctr, conv, conf

        # Fall back to JSON priors
        if total_sample > 100000:
            conf = "field_validated"
        elif total_sample > 10000:
            conf = "replicated"
        else:
            conf = "ingestion_derived"

        if category:
            return 35.0, 42.0, conf
        return 30.0, 35.0, conf

    # ─── Helpers ────────────────────────────────────────────────────────────

    def _get_top_mechanisms(self, archetype: str, category: str, k: int = 5) -> List[Dict[str, Any]]:
        """
        Get top-k mechanisms using the strongest available intelligence.

        Priority:
          1. Graph edge dimension averages (per-mechanism scores from BRAND_CONVERTED)
          2. BayesianPrior nodes (graph cache)
          3. Category-specific JSON priors
          4. Global JSON priors
          5. Research-grounded defaults
        """
        # Priority 1: Graph edge-level mechanism scores
        if category and self._graph_intel:
            edge_data = self._get_graph_edge_data(category, archetype)
            if edge_data and edge_data.get("edge_count", 0) > 50:
                avgs = edge_data.get("averages", {})
                mech_scores = {}
                for dim_key, score in avgs.items():
                    for mech_name in _MECHANISM_LABELS:
                        if dim_key == f"{mech_name}_score" and score is not None:
                            mech_scores[mech_name] = float(score)

                if len(mech_scores) >= 3:
                    scored = []
                    for mech, score in sorted(mech_scores.items(), key=lambda x: x[1], reverse=True):
                        scored.append({
                            "mechanism": mech,
                            "success_rate": round(score, 4),
                            "sample_size": edge_data.get("edge_count", 0),
                            "categories_seen": 1,
                            "source": "graph_edges",
                        })
                    return scored[:k]

        # Priority 2: BayesianPrior-backed mechanism ranking
        if category and self._graph_cache:
            bp_scores = {}
            for mech_name in _MECHANISM_LABELS:
                bp = self._graph_cache.get_bayesian_mechanism_confidence(category, mech_name)
                if bp and bp["n_observations"] > 50:
                    bp_scores[mech_name] = bp

            if len(bp_scores) >= 3:
                scored = []
                for mech, data in sorted(bp_scores.items(), key=lambda x: x[1]["weighted_score"], reverse=True):
                    scored.append({
                        "mechanism": mech,
                        "success_rate": data["weighted_score"],
                        "sample_size": data["n_observations"],
                        "categories_seen": data["prior_count"],
                        "source": "bayesian_prior",
                    })
                return scored[:k]

        # Priority 3-4: JSON priors
        if self._priors:
            if category:
                cat_matrix = (self._priors.get("category_effectiveness_matrices") or {}).get(category, {})
                arch_data = cat_matrix.get(archetype, {})
            else:
                arch_data = (self._priors.get("global_effectiveness_matrix") or {}).get(archetype, {})

            if arch_data:
                scored = []
                for mech, info in arch_data.items():
                    if isinstance(info, dict):
                        scored.append({
                            "mechanism": mech,
                            "success_rate": float(info.get("success_rate", 0)),
                            "sample_size": int(info.get("sample_size", 0)),
                            "categories_seen": int(info.get("categories_seen", 0)),
                            "source": "json_priors",
                        })
                    else:
                        scored.append({
                            "mechanism": mech,
                            "success_rate": float(info),
                            "sample_size": 0,
                            "categories_seen": 0,
                            "source": "json_priors",
                        })
                scored.sort(key=lambda x: x["success_rate"], reverse=True)
                return scored[:k]

        return [
            {"mechanism": "social_proof", "success_rate": 0.22, "sample_size": 0, "categories_seen": 0, "source": "default"},
            {"mechanism": "reciprocity", "success_rate": 0.30, "sample_size": 0, "categories_seen": 0, "source": "default"},
            {"mechanism": "authority", "success_rate": 0.24, "sample_size": 0, "categories_seen": 0, "source": "default"},
            {"mechanism": "scarcity", "success_rate": 0.25, "sample_size": 0, "categories_seen": 0, "source": "default"},
            {"mechanism": "commitment", "success_rate": 0.18, "sample_size": 0, "categories_seen": 0, "source": "default"},
        ][:k]

    def _get_categories(self) -> List[str]:
        """Return categories from priors."""
        if self._priors:
            cats = self._priors.get("category_effectiveness_matrices", {})
            return sorted(cats.keys())
        return [
            "All_Beauty", "Electronics", "Health_and_Personal_Care",
            "Home_and_Kitchen", "Sports_and_Outdoors",
        ]

    def _blend_ndf_with_category(
        self, base_ndf: Dict[str, float], category: str,
    ) -> Dict[str, float]:
        """Blend archetype NDF with category-level NDF distribution."""
        blended = dict(base_ndf)
        if self._priors:
            cat_ndf = (self._priors.get("category_ndf_profiles") or {}).get(category)
            if cat_ndf:
                for dim in blended:
                    if dim in cat_ndf:
                        blended[dim] = round(blended[dim] * 0.6 + float(cat_ndf[dim]) * 0.4, 4)
        return blended


def generate_taxonomy(output_path: Optional[str] = None) -> List[SegmentDefinition]:
    """Convenience function to generate and optionally export the full taxonomy."""
    gen = TaxonomyGenerator()
    gen.load_data()
    segments = gen.generate()

    if output_path:
        gen.export_json(segments, Path(output_path))
    else:
        default_path = _PROJECT_ROOT / "data" / "stackadapt" / "informativ_taxonomy.json"
        gen.export_json(segments, default_path)

    return segments


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    out = sys.argv[1] if len(sys.argv) > 1 else None
    segments = generate_taxonomy(out)
    print(f"\nGenerated {len(segments)} segments")
    for tier in (1, 2, 3):
        count = sum(1 for s in segments if s.tier == tier)
        print(f"  Tier {tier}: {count} segments")
