"""
TaxonomyMapper — maps ADAM psychological constructs to targeting taxonomy.

INFORMATIV uses its own taxonomy namespace (INFORMATIV-*) rather than
pseudo-IAB codes. Our segments represent psychological constructs, not
content categories — they don't map to the IAB Content Taxonomy at all.

The INFORMATIV namespace is clearly prefixed so SSP/DSP platforms can
recognize these as custom audience segments rather than content taxonomy.

Namespace structure:
    INFORMATIV-PSY-{nnn}    Psychological construct segments
    INFORMATIV-MECH-{nnn}   Persuasion mechanism segments
    INFORMATIV-PERS-{nnn}   Personality trait segments
    INFORMATIV-NDF-{nnn}    NDF dimension segments
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# INFORMATIV Taxonomy — Psychological Construct Segments
# ---------------------------------------------------------------------------
ADAM_TO_TAXONOMY = {
    # --- Psychological construct segments (PSY series) ---
    "promotion_focus":              {"id": "INFORMATIV-PSY-001", "tier": "Construct", "name": "Achievement & Goal Setting"},
    "prevention_focus":             {"id": "INFORMATIV-PSY-002", "tier": "Construct", "name": "Safety & Security Orientation"},
    "future_orientation":           {"id": "INFORMATIV-PSY-003", "tier": "Construct", "name": "Long-Term Planning"},
    "present_orientation":          {"id": "INFORMATIV-PSY-004", "tier": "Construct", "name": "Immediate Gratification"},
    "social_proof_susceptibility":  {"id": "INFORMATIV-PSY-005", "tier": "Construct", "name": "Social Validation Seeking"},
    "status_seeking":               {"id": "INFORMATIV-PSY-006", "tier": "Construct", "name": "Status & Prestige"},
    "need_for_cognition":           {"id": "INFORMATIV-PSY-007", "tier": "Construct", "name": "Deep Information Processing"},
    "sensation_seeking":            {"id": "INFORMATIV-PSY-008", "tier": "Construct", "name": "Novelty & Stimulation"},
    "uncertainty_intolerance":      {"id": "INFORMATIV-PSY-009", "tier": "Construct", "name": "Certainty Seeking"},
    "loss_aversion":                {"id": "INFORMATIV-PSY-010", "tier": "Construct", "name": "Loss Sensitivity"},
    "brand_loyalty":                {"id": "INFORMATIV-PSY-011", "tier": "Construct", "name": "Brand Attachment"},
    "price_sensitivity":            {"id": "INFORMATIV-PSY-012", "tier": "Construct", "name": "Value Optimization"},
    "identity_salience":            {"id": "INFORMATIV-PSY-013", "tier": "Construct", "name": "Identity-Driven Purchase"},
    "conformity_need":              {"id": "INFORMATIV-PSY-014", "tier": "Construct", "name": "Social Conformity"},
    "autonomy_reactance":           {"id": "INFORMATIV-PSY-015", "tier": "Construct", "name": "Autonomy & Independence"},
    "narrative_transport":          {"id": "INFORMATIV-PSY-016", "tier": "Construct", "name": "Story Engagement"},
    "cognitive_load_tolerance":     {"id": "INFORMATIV-PSY-017", "tier": "Construct", "name": "Information Capacity"},
    "mimetic_desire":               {"id": "INFORMATIV-PSY-018", "tier": "Construct", "name": "Mimetic Aspiration"},
    "cooperative_framing":          {"id": "INFORMATIV-PSY-019", "tier": "Construct", "name": "Fairness & Reciprocity"},
    "decision_entropy":             {"id": "INFORMATIV-PSY-020", "tier": "Construct", "name": "Decision Complexity"},

    # --- Persuasion mechanism segments (MECH series) ---
    "social_proof":                 {"id": "INFORMATIV-MECH-001", "tier": "Mechanism", "name": "Social Proof Receptivity"},
    "scarcity":                     {"id": "INFORMATIV-MECH-002", "tier": "Mechanism", "name": "Scarcity Responsiveness"},
    "authority":                    {"id": "INFORMATIV-MECH-003", "tier": "Mechanism", "name": "Authority Trust"},
    "reciprocity":                  {"id": "INFORMATIV-MECH-004", "tier": "Mechanism", "name": "Reciprocity Drive"},
    "commitment_consistency":       {"id": "INFORMATIV-MECH-005", "tier": "Mechanism", "name": "Commitment Consistency"},
    "commitment":                   {"id": "INFORMATIV-MECH-005", "tier": "Mechanism", "name": "Commitment Consistency"},
    "liking":                       {"id": "INFORMATIV-MECH-006", "tier": "Mechanism", "name": "Affinity & Liking"},
    "unity":                        {"id": "INFORMATIV-MECH-007", "tier": "Mechanism", "name": "Shared Identity"},
    "anchoring":                    {"id": "INFORMATIV-MECH-008", "tier": "Mechanism", "name": "Anchoring & Framing"},
    "loss_aversion":                {"id": "INFORMATIV-MECH-009", "tier": "Mechanism", "name": "Loss Aversion Mechanism"},
    "cognitive_ease":               {"id": "INFORMATIV-MECH-010", "tier": "Mechanism", "name": "Cognitive Ease"},
    "curiosity":                    {"id": "INFORMATIV-MECH-011", "tier": "Mechanism", "name": "Curiosity Gap"},

    # --- Personality trait segments (PERS series) ---
    "openness":                     {"id": "INFORMATIV-PERS-001", "tier": "Personality", "name": "Openness to Experience"},
    "conscientiousness":            {"id": "INFORMATIV-PERS-002", "tier": "Personality", "name": "Organized & Disciplined"},
    "extraversion":                 {"id": "INFORMATIV-PERS-003", "tier": "Personality", "name": "Social & Outgoing"},
    "agreeableness":                {"id": "INFORMATIV-PERS-004", "tier": "Personality", "name": "Cooperative & Empathetic"},
    "neuroticism":                  {"id": "INFORMATIV-PERS-005", "tier": "Personality", "name": "Emotionally Responsive"},
}

class TaxonomyMapper:
    """
    Maps ADAM psychological constructs to the INFORMATIV taxonomy namespace.

    SSP/DSP platforms can register the INFORMATIV namespace as a custom
    audience taxonomy. The IDs are stable and semantically meaningful.
    """

    def map_constructs(self, constructs: Dict[str, float]) -> List[Dict[str, Any]]:
        """Map ADAM construct names to INFORMATIV taxonomy entries."""
        mapped = []
        for construct, value in constructs.items():
            if construct in ADAM_TO_TAXONOMY and value > 0.5:
                entry = ADAM_TO_TAXONOMY[construct]
                mapped.append({
                    "construct": construct,
                    "value": round(value, 3),
                    "taxonomy_id": entry["id"],
                    "tier": entry["tier"],
                    "name": entry["name"],
                })
        mapped.sort(key=lambda x: x["value"], reverse=True)
        return mapped

    def map_mechanisms(self, mechanisms: List[str]) -> List[Dict[str, Any]]:
        """Map mechanism names to INFORMATIV taxonomy entries."""
        mapped = []
        for m in mechanisms:
            if m in ADAM_TO_TAXONOMY:
                entry = ADAM_TO_TAXONOMY[m]
                mapped.append({
                    "mechanism": m,
                    "taxonomy_id": entry["id"],
                    "name": entry["name"],
                })
        return mapped

    def get_targeting_keys(
        self,
        mechanisms: List[str],
        constructs: Optional[Dict[str, float]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Generate a complete set of targeting keys for a content profile.
        This is the output that gets pushed to SSP/DSP platforms.
        """
        mech_mapped = self.map_mechanisms(mechanisms)
        construct_mapped = self.map_constructs(constructs or {})

        all_taxonomy_ids = list(set(
            [m["taxonomy_id"] for m in mech_mapped]
            + [m["taxonomy_id"] for m in construct_mapped]
        ))

        return {
            "taxonomy_namespace": "INFORMATIV",
            "taxonomy_ids": all_taxonomy_ids,
            "adam_mechanism_targeting": [m["mechanism"] for m in mech_mapped],
            "adam_construct_targeting": {m["construct"]: m["value"] for m in construct_mapped},
            "targeting_depth": len(all_taxonomy_ids),
            "source": "informativ_adam",
        }
