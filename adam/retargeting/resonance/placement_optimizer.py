# =============================================================================
# Resonance Engineering — Layer 3: MATCH
# Location: adam/retargeting/resonance/placement_optimizer.py
# =============================================================================

"""
Dynamic Placement Optimization.

Given (this buyer, this barrier, this mechanism, this touch position),
compute the IDEAL page mindstate and translate to StackAdapt bid multipliers.

Replaces static domain whitelists with per-touch, per-archetype, dynamically
evolving placement targeting based on resonance scores.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from adam.retargeting.resonance.models import (
    PageMindstateVector,
    ResonanceScore,
    ALL_MINDSTATE_DIMS,
)
from adam.retargeting.resonance.resonance_model import ResonanceModel
from adam.retargeting.resonance.cold_start import get_ideal_vector, compute_theory_resonance
from adam.retargeting.resonance.resonance_gradient import (
    compute_resonance_gradient,
    rank_dimensions_by_resonance_impact,
)

logger = logging.getLogger(__name__)

# Bid multiplier thresholds
BID_AMPLIFY_THRESHOLD = 1.3   # Resonance above this = bid up
BID_NEUTRAL_THRESHOLD = 0.8   # Below this = bid down
BID_BLACKLIST_THRESHOLD = 0.5  # Below this = don't bid at all
MAX_BID_MULTIPLIER = 2.5
MIN_BID_MULTIPLIER = 0.3


class PlacementOptimizer:
    """Computes optimal placement strategy for each retargeting decision.

    Usage:
        optimizer = PlacementOptimizer(resonance_model)

        # For a specific decision, compute the ideal page environment
        ideal = optimizer.compute_ideal_mindstate("evidence_proof", "trust_deficit", "careful_truster")

        # Given available pages, compute bid multipliers
        multipliers = optimizer.compute_bid_multipliers(ideal, available_page_mindstates)

        # Generate full domain targeting for StackAdapt
        targeting = optimizer.generate_domain_targeting(
            archetype, touch_position, mechanism, barrier, scored_pages
        )
    """

    def __init__(self, resonance_model: Optional[ResonanceModel] = None):
        self._model = resonance_model or ResonanceModel()
        self._bid_boosts: Dict[str, float] = {}  # domain → bid multiplier from similarity expansion

    def compute_ideal_mindstate(
        self,
        mechanism: str,
        barrier: str = "",
        archetype: str = "",
    ) -> PageMindstateVector:
        """Compute the ideal page mindstate for a specific configuration.

        Uses the resonance gradient to determine which page dimensions
        should be maximized/minimized for this mechanism.

        Returns a PageMindstateVector representing the optimal page environment.
        """
        ideal_vec = get_ideal_vector(mechanism)

        # Convert ideal vector to a mindstate: positive ideal = high value, negative = low
        dims = {}
        for i, dim in enumerate(ALL_MINDSTATE_DIMS[:20]):
            # Map ideal direction to a target value
            # Positive ideal → target 0.8, Negative → target 0.2, Zero → target 0.5
            if ideal_vec[i] > 0.1:
                dims[dim] = 0.5 + ideal_vec[i]
            elif ideal_vec[i] < -0.1:
                dims[dim] = 0.5 + ideal_vec[i]
            else:
                dims[dim] = 0.5

        ndf = {}
        for i, dim in enumerate(ALL_MINDSTATE_DIMS[20:27]):
            idx = 20 + i
            ndf[dim] = np.clip(0.5 + ideal_vec[idx], 0.0, 1.0)

        return PageMindstateVector(
            edge_dimensions=dims,
            ndf_activations=ndf,
            emotional_valence=np.clip(0.5 + (ideal_vec[27] if len(ideal_vec) > 27 else 0), -1, 1),
            emotional_arousal=np.clip(0.5 + (ideal_vec[28] if len(ideal_vec) > 28 else 0), 0, 1),
            cognitive_load=np.clip(0.5 + (ideal_vec[29] if len(ideal_vec) > 29 else 0), 0, 1),
            publisher_authority=np.clip(0.5 + (ideal_vec[30] if len(ideal_vec) > 30 else 0), 0, 1),
            remaining_bandwidth=np.clip(0.5 + (ideal_vec[31] if len(ideal_vec) > 31 else 0), 0, 1),
            domain="ideal",
            confidence=1.0,
        )

    def compute_bid_multipliers(
        self,
        mechanism: str,
        barrier: str,
        archetype: str,
        page_mindstates: Dict[str, PageMindstateVector],
    ) -> Dict[str, float]:
        """For each available page, compute a bid multiplier based on resonance.

        Args:
            mechanism: The mechanism being deployed
            barrier: The barrier being targeted
            archetype: User archetype
            page_mindstates: {domain_or_url: PageMindstateVector}

        Returns:
            {domain_or_url: bid_multiplier} where:
            > 1.0 = bid higher (amplifying resonance)
            = 1.0 = bid normally
            < 1.0 = bid lower (dampening resonance)
            = 0.0 = do not bid (anti-resonant)
        """
        multipliers = {}

        for domain, mindstate in page_mindstates.items():
            score = self._model.compute_resonance(
                mindstate, mechanism, barrier, archetype
            )
            res = score.resonance_multiplier

            if res >= BID_AMPLIFY_THRESHOLD:
                # High resonance: bid up proportionally
                bid = min(MAX_BID_MULTIPLIER, 1.0 + (res - 1.0) * 0.8)
            elif res >= BID_NEUTRAL_THRESHOLD:
                # Neutral: bid normally
                bid = 1.0
            elif res >= BID_BLACKLIST_THRESHOLD:
                # Low resonance: bid down
                bid = max(MIN_BID_MULTIPLIER, res)
            else:
                # Anti-resonant: blacklist
                bid = 0.0

            multipliers[domain] = round(bid, 3)

        return dict(sorted(multipliers.items(), key=lambda x: x[1], reverse=True))

    def apply_congruence_contrast_strategy(
        self,
        multipliers: Dict[str, float],
        page_mindstates: Dict[str, PageMindstateVector],
        archetype: str,
        mechanism: str,
    ) -> Dict[str, float]:
        """Apply Dahlén (2005) congruence vs contrast strategy.

        Research finding: Ads CONGRUENT with editorial content have higher
        recall but can trigger persuasion knowledge in high-NfC readers.
        For high-NfC archetypes (careful_truster), a CONTRASTING ad on an
        analytical page may outperform because the contrast activates
        System 2 without triggering persuasion knowledge defense.

        Rules:
        - careful_truster + analytical page → BOOST contrast placements
          (evidence_proof on emotional page gets +20% bid boost)
        - status_seeker + aspirational page → BOOST congruent placements
          (narrative_transportation on aspirational page gets +15%)
        - easy_decider + transactional page → BOOST congruent placements
          (loss_framing on booking page gets +25%)

        The strategy evolves: we track congruent vs contrast conversion
        rates per archetype and shift the strategy toward what works.
        """
        # Archetype NfC classification
        high_nfc_archetypes = {"careful_truster", "guardian"}
        low_nfc_archetypes = {"easy_decider"}

        # Mechanism-to-page-type congruence map
        # (mechanism, page_cluster) → congruent?
        congruent_pairs = {
            ("evidence_proof", "analytical"): True,
            ("narrative_transportation", "aspirational"): True,
            ("social_proof_matched", "social"): True,
            ("loss_framing", "transactional"): True,
            ("implementation_intention", "transactional"): True,
        }

        adjusted = dict(multipliers)

        for domain, mindstate in page_mindstates.items():
            if domain not in adjusted:
                continue

            page_cluster = self._classify_page_cluster(mindstate)
            is_congruent = congruent_pairs.get((mechanism, page_cluster), None)

            if is_congruent is None:
                continue  # No opinion on this combo

            if archetype in high_nfc_archetypes:
                # High NfC: contrast can work better (Dahlén 2005)
                if not is_congruent:
                    # Contrasting placement — boost for high-NfC
                    adjusted[domain] = min(
                        MAX_BID_MULTIPLIER,
                        adjusted[domain] * 1.20,
                    )
                else:
                    # Congruent placement — slight dampening for high-NfC
                    # (persuasion knowledge risk)
                    adjusted[domain] *= 0.95
            elif archetype in low_nfc_archetypes:
                # Low NfC: congruence always wins (no PK defense)
                if is_congruent:
                    adjusted[domain] = min(
                        MAX_BID_MULTIPLIER,
                        adjusted[domain] * 1.25,
                    )
            else:
                # Default: slight congruence preference
                if is_congruent:
                    adjusted[domain] = min(
                        MAX_BID_MULTIPLIER,
                        adjusted[domain] * 1.10,
                    )

        return adjusted

    def _classify_page_cluster(self, mindstate: PageMindstateVector) -> str:
        """Classify a page into a psychological cluster.

        Uses the 5-cluster model from creative_adapter:
        analytical, emotional, social, transactional, aspirational.
        """
        dims = mindstate.edge_dimensions or {}
        clt = dims.get("cognitive_load_tolerance", 0.5)
        er = dims.get("emotional_resonance", 0.5)
        sps = dims.get("social_proof_sensitivity", 0.5)
        asp = dims.get("value_alignment", 0.5)

        scores = {
            "analytical": clt * 0.6 + (1 - er) * 0.4,
            "emotional": er * 0.6 + (1 - clt) * 0.4,
            "social": sps * 0.7 + er * 0.3,
            "transactional": (1 - clt) * 0.4 + (1 - er) * 0.3 + (1 - sps) * 0.3,
            "aspirational": asp * 0.5 + er * 0.3 + (1 - clt) * 0.2,
        }
        return max(scores, key=scores.get)

    def generate_domain_targeting(
        self,
        archetype: str,
        touch_position: int,
        mechanism: str,
        barrier: str,
        scored_pages: Dict[str, PageMindstateVector],
    ) -> Dict[str, Any]:
        """Generate complete domain targeting config for StackAdapt.

        Returns a targeting config with:
        - whitelist: domains with resonance > threshold
        - bid_adjustments: {domain: multiplier}
        - blacklist: domains with anti-resonance
        - ideal_mindstate_description: human-readable ideal page description
        """
        multipliers = self.compute_bid_multipliers(
            mechanism, barrier, archetype, scored_pages
        )

        whitelist = [d for d, m in multipliers.items() if m >= 1.0]
        bid_up = {d: m for d, m in multipliers.items() if m > 1.2}
        blacklist = [d for d, m in multipliers.items() if m == 0.0]
        bid_down = {d: m for d, m in multipliers.items() if 0 < m < 0.8}

        # Generate human-readable description of ideal page
        ranked = rank_dimensions_by_resonance_impact(mechanism)
        ideal_description = f"For {mechanism} targeting {barrier} ({archetype}):\n"
        for dim, impact, direction in ranked[:5]:
            ideal_description += f"  - {direction} {dim} (impact={impact:.2f})\n"

        return {
            "archetype": archetype,
            "touch_position": touch_position,
            "mechanism": mechanism,
            "barrier": barrier,
            "whitelist": whitelist,
            "blacklist": blacklist,
            "bid_adjustments": {**bid_up, **bid_down},
            "ideal_mindstate_description": ideal_description,
            "total_domains_scored": len(scored_pages),
            "domains_whitelisted": len(whitelist),
            "domains_blacklisted": len(blacklist),
        }

    # =========================================================================
    # BID-BOOST FROM SIMILARITY EXPANSION
    # =========================================================================

    def add_bid_boost_pages(
        self,
        urls: List[str],
        boost_factor: float = 1.5,
    ) -> int:
        """Add pages similar to converting pages to the bid-boost list.

        Called by the priority crawl drain after finding pages similar
        to a converting page via the similarity index.

        These pages get a bid multiplier > 1.0 because their
        psychological field is similar to a field where conversion
        already happened — empirical resonance evidence.

        Args:
            urls: URLs of psychologically similar pages.
            boost_factor: Bid multiplier for these pages (default 1.5x).

        Returns:
            Number of pages added to boost list.
        """
        added = 0
        for url in urls:
            domain = url.split("/")[0] if "/" in url else url
            if domain not in self._bid_boosts:
                self._bid_boosts[domain] = boost_factor
                added += 1
            else:
                # Average with existing boost (don't override stronger boosts)
                self._bid_boosts[domain] = max(
                    self._bid_boosts[domain], boost_factor
                )

        if added > 0:
            logger.info(
                "Bid-boost: added %d pages at %.1fx (from similarity expansion)",
                added, boost_factor,
            )
        return added

    def get_bid_boost(self, domain: str) -> float:
        """Get bid multiplier for a domain (1.0 = no boost)."""
        return self._bid_boosts.get(domain, 1.0)


# =============================================================================
# SINGLETON
# =============================================================================

_placement_optimizer: Optional["PlacementOptimizer"] = None


def get_placement_optimizer(resonance_model=None) -> "PlacementOptimizer":
    """Get or create the singleton PlacementOptimizer."""
    global _placement_optimizer
    if _placement_optimizer is None:
        _placement_optimizer = PlacementOptimizer(resonance_model=resonance_model)
    return _placement_optimizer
