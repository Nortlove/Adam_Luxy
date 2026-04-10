# =============================================================================
# Causal Decomposition Engine
# Location: adam/intelligence/causal_decomposition.py
# =============================================================================

"""
Decomposes a conversion into its CAUSAL INGREDIENTS.

This is the connective tissue between the system's three intelligence types:
- EMPIRICAL (gradient fields): which dimensions had highest marginal impact
- INFERENTIAL (theory graph): which causal chain was active
- DISCOVERY (emergence): does this violate current understanding

Given a single conversion event with full context, this engine identifies
the 3-5 dimensions that were the ACTIVE CAUSAL INGREDIENTS — not all 20
dimensions, but the specific ones that drove THIS conversion.

The output — a CausalRecipe — is the foundation for hypothesis generation.
It answers: "WHY did this specific buyer convert on this specific page
with this specific mechanism at this specific touch position?"

Cross-disciplinary inspiration:
- MOLECULAR BIOLOGY: Gene expression analysis identifies which genes
  are "turned on" in a specific cell state. We identify which
  psychological dimensions are "activated" in a conversion.
- EPIDEMIOLOGY: Koch's postulates require isolating the causal agent.
  We isolate the causal dimensions from the 20-dimensional space.
- FORENSIC SCIENCE: Crime scene reconstruction from evidence.
  We reconstruct the psychological sequence from outcome evidence.
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class CausalIngredient:
    """A single causal dimension that contributed to a conversion."""

    dimension: str                    # e.g., "cognitive_load_tolerance"
    value: float                      # The actual value (0-1)
    gradient_magnitude: float         # ∂P/∂dim — how much this dim affects conversion
    page_gradient_magnitude: float    # ∂P/∂page_dim — page amplification
    theory_support: float             # 0-1 — how strongly theory predicts this
    causal_role: str                  # "primary", "amplifier", "moderator", "enabler"
    evidence: str                     # Human-readable explanation

    @property
    def combined_strength(self) -> float:
        """Combined causal strength from all three intelligence sources."""
        return (
            self.gradient_magnitude * 0.4
            + self.page_gradient_magnitude * 0.3
            + self.theory_support * 0.3
        )


@dataclass
class CausalRecipe:
    """The causal decomposition of a single conversion.

    Contains the 3-5 dimensions that were the active ingredients,
    the causal chain that was activated, and the conditions under
    which this recipe is expected to produce conversion again.
    """

    # The conversion context
    decision_id: str
    archetype: str
    mechanism: str
    barrier: str
    page_url: str
    touch_position: int

    # The causal ingredients (ranked by combined_strength)
    ingredients: List[CausalIngredient] = field(default_factory=list)

    # The theory chain that was active
    active_chain: Optional[Dict[str, Any]] = None
    chain_confidence: float = 0.0

    # Transferable conditions (for hypothesis generation)
    conditions: Dict[str, Tuple[str, float]] = field(default_factory=dict)
    # e.g., {"cognitive_load_tolerance": (">", 0.7), "regulatory_fit": ("<", 0.15)}

    # Whether this conversion violates current predictions
    is_surprising: bool = False
    surprise_reason: str = ""

    # Metadata
    decomposed_at: float = field(default_factory=time.time)
    decomposition_confidence: float = 0.0

    @property
    def primary_ingredients(self) -> List[CausalIngredient]:
        """Top 3-5 ingredients by combined strength."""
        sorted_ing = sorted(self.ingredients, key=lambda x: x.combined_strength, reverse=True)
        # Take ingredients until combined strength drops below 50% of top
        if not sorted_ing:
            return []
        threshold = sorted_ing[0].combined_strength * 0.5
        return [i for i in sorted_ing if i.combined_strength >= threshold][:5]

    @property
    def recipe_signature(self) -> str:
        """Compact string representation for matching."""
        parts = []
        for dim, (op, val) in sorted(self.conditions.items()):
            parts.append(f"{dim}{op}{val:.2f}")
        return f"{self.mechanism}|{'&'.join(parts)}"


class CausalDecompositionEngine:
    """Decomposes conversions into causal ingredients.

    Orchestrates three intelligence sources to identify WHY a conversion
    happened, not just THAT it happened.

    Integration:
    - Called from OutcomeHandler after a conversion
    - Feeds CausalRecipe to InferentialHypothesisEngine
    - Updates theory graph with validated causal links
    """

    def __init__(self):
        self._recipes: List[CausalRecipe] = []
        self._max_recipes = 10_000

    def decompose(
        self,
        decision_id: str,
        metadata: Dict[str, Any],
        success: bool,
    ) -> Optional[CausalRecipe]:
        """Decompose a conversion into its causal ingredients.

        Args:
            decision_id: The decision that led to conversion
            metadata: Full context from outcome handler
            success: Whether this was a conversion (True) or failure (False)

        Returns:
            CausalRecipe if decomposition succeeds, None otherwise
        """
        if not success:
            # Failures are also informative — they tell us what DIDN'T work
            # But the decomposition logic differs (we look for what was missing)
            return self._decompose_failure(decision_id, metadata)

        archetype = metadata.get("archetype", "")
        mechanism = metadata.get("mechanism_sent", "")
        barrier = metadata.get("barrier_diagnosed", "")
        page_url = metadata.get("page_url", "")
        touch_position = metadata.get("touch_position", 0)

        if not mechanism:
            return None

        # ── SOURCE 1: BUYER GRADIENT FIELD ──
        # Which buyer dimensions had the highest marginal conversion impact?
        buyer_gradients = self._get_buyer_gradients(archetype, metadata.get("product_category", ""))

        # ── SOURCE 2: PAGE GRADIENT FIELD ──
        # Which page dimensions amplified the mechanism?
        page_gradients = self._get_page_gradients(mechanism, barrier)

        # ── SOURCE 3: THEORY GRAPH ──
        # Which causal chain (State→Need→Mechanism) was active?
        theory_chain, chain_confidence = self._get_active_chain(
            mechanism, barrier, metadata
        )

        # ── INTERSECT: Find the causal ingredients ──
        # Dimensions that appear as important in ALL THREE sources
        # are the most likely causal agents
        ingredients = self._compute_ingredients(
            metadata=metadata,
            buyer_gradients=buyer_gradients,
            page_gradients=page_gradients,
            theory_chain=theory_chain,
        )

        # ── COMPUTE CONDITIONS ──
        # Threshold conditions for hypothesis generation
        conditions = self._extract_conditions(ingredients, metadata)

        # ── CHECK FOR SURPRISE ──
        # Does this conversion violate current predictions?
        is_surprising, surprise_reason = self._check_surprise(
            mechanism, metadata, buyer_gradients
        )

        recipe = CausalRecipe(
            decision_id=decision_id,
            archetype=archetype,
            mechanism=mechanism,
            barrier=barrier,
            page_url=page_url,
            touch_position=touch_position,
            ingredients=ingredients,
            active_chain=theory_chain,
            chain_confidence=chain_confidence,
            conditions=conditions,
            is_surprising=is_surprising,
            surprise_reason=surprise_reason,
            decomposition_confidence=self._compute_confidence(
                buyer_gradients, page_gradients, theory_chain
            ),
        )

        # Store for pattern analysis
        self._recipes.append(recipe)
        if len(self._recipes) > self._max_recipes:
            self._recipes = self._recipes[-self._max_recipes:]

        logger.info(
            "Causal decomposition: %s → %d ingredients, chain_conf=%.2f, surprising=%s",
            mechanism, len(recipe.primary_ingredients),
            chain_confidence, is_surprising,
        )

        return recipe

    def _get_buyer_gradients(self, archetype: str, category: str) -> Dict[str, float]:
        """Get buyer-side gradient field: ∂P/∂buyer_dimension."""
        # Try Neo4j BayesianPrior nodes with gradient_ properties
        try:
            from neo4j import GraphDatabase
            from adam.config.settings import get_settings
            s = get_settings()
            driver = GraphDatabase.driver(
                "bolt://localhost:7687",
                auth=(s.neo4j.username, s.neo4j.password),
            )
            with driver.session() as session:
                r = session.run("""
                    MATCH (bp:BayesianPrior {category: $cat, archetype: $arch, prior_type: 'gradient_field'})
                    WHERE bp.gradient_n_edges > 0
                    RETURN bp
                """, cat=category, arch=archetype).single()

                if r:
                    node = r["bp"]
                    gradients = {}
                    for key in node.keys():
                        if key.startswith("gradient_") and key != "gradient_n_edges" and key != "gradient_computed_at":
                            dim = key.replace("gradient_", "")
                            val = node[key]
                            if isinstance(val, (int, float)):
                                gradients[dim] = float(val)
                    driver.close()
                    if gradients:
                        logger.debug("Loaded %d buyer gradients for %s/%s", len(gradients), archetype, category)
                        return gradients
            driver.close()
        except Exception as e:
            logger.debug("Buyer gradient lookup failed: %s", e)

        # Fallback: try graph cache
        try:
            from adam.api.stackadapt.graph_cache import GraphIntelligenceCache
            cache = GraphIntelligenceCache()
            gf = cache.get_gradient_field(archetype, category)
            if gf and hasattr(gf, 'gradients'):
                return gf.gradients
        except Exception:
            pass

        return {}

    def _get_page_gradients(self, mechanism: str, barrier: str) -> Dict[str, float]:
        """Get page-side gradient field: ∂P/∂page_dimension."""
        try:
            from adam.intelligence.page_gradient_fields import get_page_gradient_accumulator
            acc = get_page_gradient_accumulator()
            field = acc.get_gradient(mechanism, barrier)
            if field and field.is_valid:
                return field.gradients
        except Exception:
            pass
        return {}

    def _get_active_chain(
        self, mechanism: str, barrier: str, metadata: Dict[str, Any]
    ) -> Tuple[Optional[Dict[str, Any]], float]:
        """Get the theory graph causal chain that was active for this conversion."""
        try:
            from adam.intelligence.graph.reasoning_chain_generator import (
                generate_chains_local,
            )
            # Extract NDF-like profile from edge dimensions in metadata
            edge_dims = metadata.get("alignment_scores", {})
            if not edge_dims:
                edge_dims = metadata.get("page_edge_dimensions", {})

            ndf_profile = {
                "approach_avoidance": edge_dims.get("regulatory_fit", 0.5),
                "temporal_horizon": edge_dims.get("construal_fit", 0.5),
                "social_calibration": edge_dims.get("social_proof_sensitivity", 0.5),
                "uncertainty_tolerance": edge_dims.get("decision_entropy", 0.5),
                "status_sensitivity": edge_dims.get("value_alignment", 0.5),
                "cognitive_engagement": edge_dims.get("cognitive_load_tolerance", 0.5),
                "arousal_seeking": edge_dims.get("emotional_resonance", 0.5),
            }

            chains = generate_chains_local(
                ndf_profile=ndf_profile,
                category=metadata.get("product_category", ""),
            )

            if chains:
                # Chains are InferentialChain objects — convert to dict for uniform access
                for chain in chains:
                    chain_dict = chain.to_dict() if hasattr(chain, 'to_dict') else {}
                    rec_mech = chain_dict.get("recommended_mechanism", "")
                    coherence = chain_dict.get("confidence", 0.5)
                    if rec_mech == mechanism:
                        return chain_dict, coherence
                # If no exact match, return the top chain
                top_dict = chains[0].to_dict() if hasattr(chains[0], 'to_dict') else {}
                return top_dict, top_dict.get("confidence", 0.5) * 0.7
        except Exception as e:
            logger.debug("Theory chain generation failed: %s", e)

        return None, 0.0

    def _compute_ingredients(
        self,
        metadata: Dict[str, Any],
        buyer_gradients: Dict[str, float],
        page_gradients: Dict[str, float],
        theory_chain: Optional[Dict[str, Any]],
    ) -> List[CausalIngredient]:
        """Compute causal ingredients by intersecting three intelligence sources."""
        # Get the actual dimension values from the decision context
        edge_dims = metadata.get("alignment_scores", {})
        page_dims = metadata.get("page_edge_dimensions", {})

        # All dimensions to consider
        all_dims = set()
        all_dims.update(buyer_gradients.keys())
        all_dims.update(page_gradients.keys())
        all_dims.update(edge_dims.keys())

        # Theory-supported dimensions
        theory_dims = set()
        if theory_chain:
            for step in theory_chain.get("steps", []):
                dim = step.get("dimension", "")
                if dim:
                    theory_dims.add(dim)
            # Also extract from active states/needs
            for state in theory_chain.get("active_states", []):
                theory_dims.add(state)

        ingredients = []
        for dim in all_dims:
            buyer_grad = abs(buyer_gradients.get(dim, 0.0))
            page_grad = abs(page_gradients.get(dim, 0.0))
            theory_sup = 0.7 if dim in theory_dims else 0.0
            dim_value = edge_dims.get(dim, page_dims.get(dim, 0.5))

            # Skip dimensions with no signal from any source
            if buyer_grad < 0.01 and page_grad < 0.01 and theory_sup < 0.01:
                continue

            # Determine causal role
            if buyer_grad > 0.1 and theory_sup > 0.5:
                role = "primary"
            elif page_grad > 0.1:
                role = "amplifier"
            elif theory_sup > 0.5:
                role = "moderator"
            else:
                role = "enabler"

            # Generate evidence string
            evidence_parts = []
            if buyer_grad > 0.05:
                evidence_parts.append(f"buyer gradient {buyer_grad:.3f}")
            if page_grad > 0.05:
                evidence_parts.append(f"page amplification {page_grad:.3f}")
            if theory_sup > 0:
                evidence_parts.append("theory-supported")

            ingredients.append(CausalIngredient(
                dimension=dim,
                value=dim_value,
                gradient_magnitude=buyer_grad,
                page_gradient_magnitude=page_grad,
                theory_support=theory_sup,
                causal_role=role,
                evidence=", ".join(evidence_parts) if evidence_parts else "weak signal",
            ))

        return sorted(ingredients, key=lambda x: x.combined_strength, reverse=True)

    def _extract_conditions(
        self,
        ingredients: List[CausalIngredient],
        metadata: Dict[str, Any],
    ) -> Dict[str, Tuple[str, float]]:
        """Extract threshold conditions from top ingredients for hypothesis generation."""
        conditions = {}
        for ing in ingredients[:5]:  # Top 5 ingredients
            if ing.combined_strength < 0.1:
                continue
            # Determine threshold direction from value
            if ing.value > 0.6:
                conditions[ing.dimension] = (">", round(ing.value - 0.15, 2))
            elif ing.value < 0.4:
                conditions[ing.dimension] = ("<", round(ing.value + 0.15, 2))
            # Near-neutral values aren't condition-worthy
        return conditions

    def _check_surprise(
        self,
        mechanism: str,
        metadata: Dict[str, Any],
        buyer_gradients: Dict[str, float],
    ) -> Tuple[bool, str]:
        """Check if this conversion violates current predictions.

        Surprises are the most valuable learning events — they indicate
        the theory is wrong or incomplete, which drives discovery.
        """
        # Check: was this mechanism the predicted one?
        predicted_mech = metadata.get("cascade_mechanism_selected", "")
        if predicted_mech and predicted_mech != mechanism:
            return True, f"Predicted {predicted_mech} but {mechanism} converted"

        # Check: was the predicted probability low?
        predicted_prob = metadata.get("decision_probability", 0.0)
        if predicted_prob < 0.3:
            return True, f"Low predicted probability ({predicted_prob:.2f}) but converted"

        return False, ""

    def _decompose_failure(
        self, decision_id: str, metadata: Dict[str, Any]
    ) -> Optional[CausalRecipe]:
        """Decompose a failure — what was MISSING that would have caused conversion?"""
        # For now, record the failure context for hypothesis testing
        # Full failure decomposition is a future enhancement
        return None

    def _compute_confidence(
        self,
        buyer_gradients: Dict[str, float],
        page_gradients: Dict[str, float],
        theory_chain: Optional[Dict[str, Any]],
    ) -> float:
        """Overall confidence in the decomposition."""
        scores = []
        if buyer_gradients:
            scores.append(0.8)  # Have empirical buyer gradients
        if page_gradients:
            scores.append(0.7)  # Have page gradients
        if theory_chain:
            scores.append(0.9)  # Have theory backing
        return sum(scores) / max(len(scores), 1) if scores else 0.2

    @property
    def stats(self) -> Dict[str, Any]:
        total = len(self._recipes)
        surprising = sum(1 for r in self._recipes if r.is_surprising)
        avg_ingredients = (
            sum(len(r.primary_ingredients) for r in self._recipes) / max(total, 1)
        )
        return {
            "total_decompositions": total,
            "surprising_conversions": surprising,
            "avg_primary_ingredients": round(avg_ingredients, 1),
        }


# =============================================================================
# SINGLETON
# =============================================================================

_engine: Optional[CausalDecompositionEngine] = None


def get_causal_decomposition_engine() -> CausalDecompositionEngine:
    global _engine
    if _engine is None:
        _engine = CausalDecompositionEngine()
    return _engine
