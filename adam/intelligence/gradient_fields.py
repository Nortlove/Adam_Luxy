"""
Psychological Gradient Fields
==============================

The foundational computational primitive for INFORMATIV.

A gradient field answers: for each alignment dimension, what is
∂P(conversion_quality) / ∂dimension, conditioned on buyer cluster
and product category?

This replaces categorical outputs ("use authority", "gain framing")
with continuous optimization vectors that tell you EXACTLY which
psychological dimensions to adjust, in what direction, by how much,
and what the expected lift would be.

In physics, a gradient field tells you the direction of steepest
change. Our 20-dimensional psychological space (7 core edge dimensions +
13 extended dimensions from intelligence modules) creates a
psychological gradient field for every product-buyer combination.

No other system can do this. It requires bilateral annotation
(both ad and buyer side) with conversion evidence on the edge.

Implementation
--------------
For each (archetype, category) cell:
    X = alignment dimensions on BRAND_CONVERTED edges
    Y = composite_alignment (conversion quality signal)
    β = OLS coefficients = gradient vector
    optimal = top-quartile mean per dimension

At query time:
    gap = optimal - current_alignment
    priority = gradient × gap = expected lift from optimizing each dimension
    Sort by |priority| descending = the steepest path to better performance.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# The alignment dimensions we compute gradients over.
# Core dimensions come from BRAND_CONVERTED edge properties.
# Extended dimensions come from intelligence modules (inferred at query time
# or pre-computed from review/product annotations).
GRADIENT_DIMENSIONS = [
    # --- Core edge dimensions (from BRAND_CONVERTED edges) ---
    "avg_reg_fit",
    "avg_construal_fit",
    "avg_personality_align",
    "avg_emotional",
    "avg_value",
    "avg_evo",
    "avg_linguistic",
    "avg_confidence",
    # --- Extended dimensions (from intelligence module annotations) ---
    "avg_persuasion_susceptibility",
    "avg_cognitive_load_tolerance",
    "avg_narrative_transport",
    "avg_social_proof_sensitivity",
    "avg_loss_aversion_intensity",
    "avg_temporal_discounting",
    "avg_brand_relationship_depth",
    "avg_autonomy_reactance",
    "avg_information_seeking",
    "avg_mimetic_desire",
    "avg_interoceptive_awareness",
    "avg_cooperative_framing_fit",
    "avg_decision_entropy",
]

# Human-readable names for each dimension
# ---------------------------------------------------------------------------
# Theory-driven interaction pairs (∂²P/∂dim_i∂dim_j)
#
# These pairs are selected based on psychological theory, not data mining.
# Each pair has a testable theoretical rationale for why the two dimensions
# should interact (amplify or suppress each other's effect on conversion).
#
# Full polynomial expansion (20 choose 2 = 190 terms) would require 10x
# the sample size and risk overfitting. These 12 pairs capture the most
# important interactions with minimal additional parameters.
# ---------------------------------------------------------------------------
INTERACTION_PAIRS = [
    # (dim_a, dim_b, theoretical_rationale)
    ("avg_reg_fit", "avg_emotional",
     "Promotion focus + emotional intensity amplifies urgency"),
    ("avg_construal_fit", "avg_cognitive_load_tolerance",
     "Abstract messaging requires cognitive capacity to process"),
    ("avg_social_proof_sensitivity", "avg_personality_align",
     "Social proof works stronger when personality-matched"),
    ("avg_loss_aversion_intensity", "avg_emotional",
     "Loss framing + emotional intensity maximizes fear appeal"),
    ("avg_autonomy_reactance", "avg_persuasion_susceptibility",
     "High reactance suppresses direct persuasion effectiveness"),
    ("avg_narrative_transport", "avg_construal_fit",
     "Stories work better with abstract (interpretive) mindset"),
    ("avg_information_seeking", "avg_cognitive_load_tolerance",
     "Info-seekers who can handle complexity respond to detailed arguments"),
    ("avg_mimetic_desire", "avg_value",
     "Wanting what others want + shared values = strong unity signal"),
    ("avg_temporal_discounting", "avg_emotional",
     "Present-focused + emotional = high urgency receptivity"),
    ("avg_decision_entropy", "avg_social_proof_sensitivity",
     "Uncertain buyers rely more heavily on social proof"),
    ("avg_cooperative_framing_fit", "avg_personality_align",
     "Fairness matters more when buyer identifies with brand"),
    ("avg_brand_relationship_depth", "avg_mimetic_desire",
     "Deep brand attachment + mimetic desire = powerful loyalty signal"),
]


DIMENSION_LABELS = {
    # Core
    "avg_reg_fit": "regulatory_fit",
    "avg_construal_fit": "construal_fit",
    "avg_personality_align": "personality_alignment",
    "avg_emotional": "emotional_resonance",
    "avg_value": "value_alignment",
    "avg_evo": "evolutionary_motive",
    "avg_linguistic": "linguistic_style",
    "avg_confidence": "persuasion_confidence",
    # Extended
    "avg_persuasion_susceptibility": "persuasion_susceptibility",
    "avg_cognitive_load_tolerance": "cognitive_load_tolerance",
    "avg_narrative_transport": "narrative_transport",
    "avg_social_proof_sensitivity": "social_proof_sensitivity",
    "avg_loss_aversion_intensity": "loss_aversion_intensity",
    "avg_temporal_discounting": "temporal_discounting",
    "avg_brand_relationship_depth": "brand_relationship_depth",
    "avg_autonomy_reactance": "autonomy_reactance",
    "avg_information_seeking": "information_seeking",
    "avg_mimetic_desire": "mimetic_desire",
    "avg_interoceptive_awareness": "interoceptive_awareness",
    "avg_cooperative_framing_fit": "cooperative_framing_fit",
    "avg_decision_entropy": "decision_entropy",
}


@dataclass
class GradientVector:
    """Pre-computed gradient for an (archetype, category) cell.

    The gradient tells us: for each alignment dimension, what is the
    marginal effect on conversion quality? A gradient of +0.34 on
    regulatory_fit means a 0.1 increase in reg_fit predicts 3.4%
    more conversion lift.
    """
    # ∂outcome/∂dimension for each alignment dimension
    gradients: Dict[str, float] = field(default_factory=dict)

    # Mean alignment values in this cell (population center)
    means: Dict[str, float] = field(default_factory=dict)

    # Optimal alignment values (top-quartile conversion mean)
    optima: Dict[str, float] = field(default_factory=dict)

    # Standard deviations (for normalization)
    stds: Dict[str, float] = field(default_factory=dict)

    # Interaction terms: ∂²outcome/∂dim_i∂dim_j
    # Key format: "dim_i × dim_j" → coefficient
    # These capture dimension interaction effects the linear model misses.
    interaction_terms: Dict[str, float] = field(default_factory=dict)

    # Metadata
    archetype: str = ""
    category: str = ""
    n_edges: int = 0
    r_squared: float = 0.0
    r_squared_with_interactions: float = 0.0

    @property
    def is_valid(self) -> bool:
        from adam.config.settings import get_settings
        cfg = get_settings().cascade
        return self.n_edges >= cfg.gradient_min_edges and self.r_squared > cfg.gradient_min_r_squared


@dataclass
class OptimizationPriority:
    """A single dimension optimization recommendation.

    This is the actionable output: "adjust this dimension by this much,
    expect this lift."
    """
    dimension: str            # Human-readable dimension name
    current_value: float      # This product's current alignment
    optimal_value: float      # Where it should be (top-quartile mean)
    gradient: float           # ∂outcome/∂dim (direction and magnitude)
    gap: float                # optimal - current
    expected_lift_delta: float  # gradient * gap * 100 (percentage points)
    creative_direction: str   # What to actually DO in the creative


@dataclass
class GradientIntelligence:
    """Complete gradient intelligence for a query.

    This is the new core output: not "use authority" but
    "here are the 3 dimensions to optimize, ranked by expected lift."
    """
    optimization_priorities: List[OptimizationPriority]
    current_alignment: Dict[str, float]
    gradient_field: Dict[str, float]
    optimal_alignment: Dict[str, float]
    total_expected_lift_delta: float
    field_metadata: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Gradient computation (batch, runs offline or at cache refresh)
# ---------------------------------------------------------------------------
def compute_gradient_field(
    edge_rows: List[Dict[str, float]],
    archetype: str,
    category: str,
) -> GradientVector:
    """Compute the gradient field from raw BRAND_CONVERTED edge data.

    This is a bounded OLS regression:
        Y = composite_alignment
        X = [reg_fit, construal_fit, personality, emotional, value, evo, ...]
        β = gradient vector

    Args:
        edge_rows: List of dicts, each with GRADIENT_DIMENSIONS keys plus
                   'composite_alignment' as the outcome variable.
        archetype: Buyer archetype for this cell.
        category: Product category for this cell.

    Returns:
        GradientVector with gradients, means, optima, and metadata.
    """
    from adam.config.settings import get_settings
    min_edges = get_settings().cascade.gradient_min_edges
    if len(edge_rows) < min_edges:
        return GradientVector(archetype=archetype, category=category, n_edges=len(edge_rows))

    try:
        import numpy as np
    except ImportError:
        logger.warning("numpy not available — gradient fields require numpy")
        return GradientVector(archetype=archetype, category=category, n_edges=len(edge_rows))

    dim_keys = [k for k in GRADIENT_DIMENSIONS if k != "avg_confidence"]
    n = len(edge_rows)
    p = len(dim_keys)

    # Build matrices
    X = np.zeros((n, p))
    Y = np.zeros(n)

    for i, row in enumerate(edge_rows):
        for j, key in enumerate(dim_keys):
            X[i, j] = float(row.get(key, 0.5) or 0.5)
        Y[i] = float(row.get("composite_alignment", row.get("avg_composite", 0.5)) or 0.5)

    # Compute means and stds
    means = {dim_keys[j]: float(X[:, j].mean()) for j in range(p)}
    stds = {dim_keys[j]: float(X[:, j].std()) for j in range(p)}

    # Top-quartile optima: mean of edges with Y in top 25%
    q75 = np.percentile(Y, 75)
    top_mask = Y >= q75
    if top_mask.sum() >= 5:
        optima = {dim_keys[j]: float(X[top_mask, j].mean()) for j in range(p)}
    else:
        optima = dict(means)

    # Standardize X for regression (so coefficients are comparable)
    X_std = np.copy(X)
    for j in range(p):
        s = stds[dim_keys[j]]
        if s > 1e-8:
            X_std[:, j] = (X[:, j] - means[dim_keys[j]]) / s

    # Add intercept
    X_design = np.column_stack([np.ones(n), X_std])

    # OLS: β = (X'X)^{-1} X'Y  (linear-only model)
    try:
        XtX = X_design.T @ X_design
        XtY = X_design.T @ Y
        # Add small ridge for numerical stability
        XtX += np.eye(p + 1) * 1e-6
        beta = np.linalg.solve(XtX, XtY)
    except np.linalg.LinAlgError:
        logger.warning("Singular matrix in gradient computation for %s×%s", archetype, category)
        return GradientVector(archetype=archetype, category=category, n_edges=n)

    # R-squared (linear model)
    Y_pred = X_design @ beta
    ss_res = ((Y - Y_pred) ** 2).sum()
    ss_tot = ((Y - Y.mean()) ** 2).sum()
    r_squared = 1.0 - (ss_res / ss_tot) if ss_tot > 1e-8 else 0.0

    # Extract standardized coefficients (skip intercept at index 0)
    gradients = {}
    for j, key in enumerate(dim_keys):
        gradients[key] = round(float(beta[j + 1]), 4)

    # --- Interaction terms (theory-driven pairs) ---
    # Only compute if we have enough data (interaction terms need ~5x more
    # samples per parameter than linear terms to avoid overfitting).
    interaction_labeled = {}
    r_squared_interactions = r_squared
    min_edges_for_interactions = min_edges * 5  # ~150 edges

    if n >= min_edges_for_interactions:
        try:
            # Build interaction columns for theory-driven pairs
            interaction_cols = []
            interaction_names = []
            for dim_a, dim_b, _rationale in INTERACTION_PAIRS:
                idx_a = dim_keys.index(dim_a) if dim_a in dim_keys else -1
                idx_b = dim_keys.index(dim_b) if dim_b in dim_keys else -1
                if idx_a >= 0 and idx_b >= 0:
                    # Product of standardized values
                    interaction_col = X_std[:, idx_a] * X_std[:, idx_b]
                    interaction_cols.append(interaction_col)
                    label_a = DIMENSION_LABELS.get(dim_a, dim_a)
                    label_b = DIMENSION_LABELS.get(dim_b, dim_b)
                    interaction_names.append(f"{label_a} × {label_b}")

            if interaction_cols:
                # Expand design matrix with interaction terms
                X_interactions = np.column_stack(interaction_cols)
                X_full = np.column_stack([X_design, X_interactions])
                n_params = X_full.shape[1]

                XtX_full = X_full.T @ X_full
                XtY_full = X_full.T @ Y
                XtX_full += np.eye(n_params) * 1e-6
                beta_full = np.linalg.solve(XtX_full, XtY_full)

                # R-squared with interactions
                Y_pred_full = X_full @ beta_full
                ss_res_full = ((Y - Y_pred_full) ** 2).sum()
                r_squared_interactions = 1.0 - (ss_res_full / ss_tot) if ss_tot > 1e-8 else 0.0

                # Only keep interaction terms if they improve R² meaningfully
                r2_improvement = r_squared_interactions - r_squared
                if r2_improvement > 0.005:  # 0.5% improvement threshold
                    # Extract interaction coefficients
                    n_linear = p + 1  # intercept + linear terms
                    for k, name in enumerate(interaction_names):
                        coeff = float(beta_full[n_linear + k])
                        if abs(coeff) > 0.01:  # Only keep meaningful interactions
                            interaction_labeled[name] = round(coeff, 4)

                    # Update linear gradients from the full model
                    for j, key in enumerate(dim_keys):
                        gradients[key] = round(float(beta_full[j + 1]), 4)

                    logger.info(
                        "Interaction terms for %s×%s: %d significant (ΔR²=%.4f)",
                        archetype, category, len(interaction_labeled), r2_improvement,
                    )
                else:
                    r_squared_interactions = r_squared
                    logger.debug(
                        "Interaction terms for %s×%s: no improvement (ΔR²=%.4f)",
                        archetype, category, r2_improvement,
                    )

        except (np.linalg.LinAlgError, ValueError) as e:
            logger.debug("Interaction term computation skipped for %s×%s: %s", archetype, category, e)

    # Convert keys to human-readable labels
    gradient_labeled = {DIMENSION_LABELS.get(k, k): v for k, v in gradients.items()}
    means_labeled = {DIMENSION_LABELS.get(k, k): v for k, v in means.items()}
    optima_labeled = {DIMENSION_LABELS.get(k, k): v for k, v in optima.items()}
    stds_labeled = {DIMENSION_LABELS.get(k, k): v for k, v in stds.items()}

    return GradientVector(
        gradients=gradient_labeled,
        means=means_labeled,
        optima=optima_labeled,
        stds=stds_labeled,
        interaction_terms=interaction_labeled,
        archetype=archetype,
        category=category,
        n_edges=n,
        r_squared=round(r_squared, 4),
        r_squared_with_interactions=round(r_squared_interactions, 4),
    )


# ---------------------------------------------------------------------------
# Query-time computation: given gradient + current alignment → priorities
# ---------------------------------------------------------------------------

# Creative direction templates per dimension.
# These describe WHAT to adjust in the creative — not mechanism labels.
_CREATIVE_DIRECTION = {
    "regulatory_fit": {
        "positive": "Strengthen gain framing — promotion-focused messaging is driving conversions in this cell. Emphasize opportunities, aspirations, and positive outcomes.",
        "negative": "Shift toward prevention framing — loss-avoidance messaging is driving conversions. Emphasize protection, security, and what could be missed.",
    },
    "construal_fit": {
        "positive": "Shift toward abstract messaging — big-picture, aspirational language is driving conversions. Lead with transformation narrative, not product specs.",
        "negative": "Shift toward concrete messaging — specific, tangible details are driving conversions. Lead with features, quantities, and immediate benefits.",
    },
    "personality_alignment": {
        "positive": "Increase brand-personality resonance — the creative should mirror the buyer's self-concept. Emphasize identity-congruent traits (e.g., competence for achievers, warmth for connectors).",
        "negative": "Reduce personality signaling — conversions in this cell are driven by other dimensions. Tone down identity-based messaging.",
    },
    "emotional_resonance": {
        "positive": "Increase emotional intensity — emotionally evocative creative is driving conversions. Use vivid imagery, personal stories, and affective language.",
        "negative": "Reduce emotional intensity — rational, information-dense creative is driving conversions. Lead with evidence, comparisons, and logical arguments.",
    },
    "value_alignment": {
        "positive": "Strengthen value-based messaging — conversions are driven by shared values between brand and buyer. Emphasize what the brand stands for, not just what it sells.",
        "negative": "De-emphasize value messaging — functional utility is driving conversions more than brand values. Focus on product performance and results.",
    },
    "evolutionary_motive": {
        "positive": "Activate primal motivation — conversions are driven by deep evolutionary needs (status, belonging, safety, mate attraction). Make the appeal visceral, not cerebral.",
        "negative": "Use higher-order appeals — rational and social motivations outperform primal drives in this cell. Appeal to competence, learning, and social contribution.",
    },
    "linguistic_style": {
        "positive": "Match linguistic register — conversions correlate with language style matching between ad and buyer. Adopt the buyer segment's natural vocabulary and sentence structure.",
        "negative": "Differentiate linguistic register — standing out linguistically is more effective than matching. Use distinctive, memorable language.",
    },
    # --- Extended dimensions ---
    "persuasion_susceptibility": {
        "positive": "Increase persuasion intensity — this buyer segment is receptive to direct persuasion techniques. Layer multiple mechanisms (social proof + authority + scarcity).",
        "negative": "Soften persuasion — this segment resists overt persuasion. Use subtle, indirect approaches. Let evidence speak; avoid hard sells.",
    },
    "cognitive_load_tolerance": {
        "positive": "Increase information density — this segment processes complex information well. Include comparisons, specifications, and detailed value propositions.",
        "negative": "Simplify radically — this segment has low cognitive load tolerance. One message, one CTA, minimal decision complexity.",
    },
    "narrative_transport": {
        "positive": "Lead with story — this segment is transported by narrative. Use customer journey stories, transformation arcs, and vivid scenarios.",
        "negative": "Lead with facts — this segment resists narrative. Use bullet points, data tables, and direct claims.",
    },
    "social_proof_sensitivity": {
        "positive": "Amplify social signals — this segment is highly influenced by others' behavior. Show ratings, review counts, 'bestseller' badges, and peer testimonials.",
        "negative": "Emphasize individuality — this segment values independent judgment. Highlight unique features and personal fit over crowd behavior.",
    },
    "loss_aversion_intensity": {
        "positive": "Emphasize potential loss — this segment feels losses more intensely. Frame around what they'll miss, risk of inaction, and disappearing opportunities.",
        "negative": "Emphasize potential gain — this segment responds to upside. Frame around what they'll achieve, opportunities ahead, and positive transformation.",
    },
    "temporal_discounting": {
        "positive": "Emphasize immediate payoff — this segment strongly prefers present rewards. Highlight instant access, same-day delivery, and immediate results.",
        "negative": "Emphasize long-term value — this segment invests for the future. Highlight durability, lifetime value, and compounding benefits.",
    },
    "brand_relationship_depth": {
        "positive": "Deepen brand connection — this segment has strong parasocial brand attachment. Use brand voice, heritage, and community belonging.",
        "negative": "Lead with product merit — this segment doesn't value brand attachment. Focus on objective quality, price, and functional superiority.",
    },
    "autonomy_reactance": {
        "positive": "Respect autonomy — this segment resists pressure. Use 'you decide' framing, present options without pushing, and avoid urgency tactics.",
        "negative": "Guide decisively — this segment welcomes direction. Use clear recommendations, 'best choice' labels, and confident CTAs.",
    },
    "information_seeking": {
        "positive": "Provide depth — this segment actively seeks information. Include detailed specs, comparison guides, and expert analysis.",
        "negative": "Provide curation — this segment prefers curated recommendations. Distill to key insights and top picks.",
    },
    "mimetic_desire": {
        "positive": "Activate mimetic triggers — this segment wants what valued others want. Show influencer use, celebrity associations, and 'chosen by' signals.",
        "negative": "Activate differentiation — this segment wants to stand out. Show exclusivity, limited editions, and 'ahead of the curve' positioning.",
    },
    "interoceptive_awareness": {
        "positive": "Activate sensory language — this segment is body-signal aware. Use tactile, visceral descriptions: 'feel the difference', texture, warmth, comfort.",
        "negative": "Use cognitive language — this segment processes abstractly. Use analytical framing: performance metrics, efficiency ratings, specifications.",
    },
    "cooperative_framing_fit": {
        "positive": "Frame as mutual benefit — this segment responds to fairness and reciprocity. Emphasize win-win, shared value, and 'we're in this together'.",
        "negative": "Frame as competitive advantage — this segment responds to winning. Emphasize getting ahead, outperforming, and personal advantage.",
    },
    "decision_entropy": {
        "positive": "Reduce choice complexity — this segment experiences decision paralysis. Simplify to 'recommended choice', use comparison tables, and provide clear defaults.",
        "negative": "Offer rich options — this segment enjoys exploring choices. Present variety, customization, and detailed feature matrices.",
    },
}


def compute_optimization_priorities(
    gradient: GradientVector,
    current_alignment: Dict[str, float],
    top_n: int = 3,
) -> GradientIntelligence:
    """Given pre-computed gradient and current alignment, compute priorities.

    This is the query-time function. It runs in < 1ms (pure arithmetic).

    For each dimension:
        gap = optimal - current
        expected_lift = gradient * gap * scale_factor

    Sort by |expected_lift| descending = steepest path to improvement.
    """
    priorities: List[OptimizationPriority] = []
    total_lift = 0.0

    for dim in gradient.gradients:
        grad_val = gradient.gradients[dim]
        current = current_alignment.get(dim, gradient.means.get(dim, 0.5))
        optimal = gradient.optima.get(dim, 0.5)
        gap = optimal - current

        # Expected lift delta in percentage points
        # gradient is standardized, so multiply by std to get raw scale,
        # then by gap to get expected change
        dim_std = gradient.stds.get(dim, 0.15)
        expected_lift = grad_val * (gap / max(dim_std, 0.01)) * 100.0

        # Creative direction based on gradient sign
        direction_key = "positive" if grad_val > 0 else "negative"
        direction_templates = _CREATIVE_DIRECTION.get(dim, {})
        creative_dir = direction_templates.get(direction_key, f"Adjust {dim} in {'positive' if grad_val > 0 else 'negative'} direction.")

        # Personalize the direction with specific numbers
        if abs(gap) > 0.05:
            creative_dir += f" Current: {current:.2f}, optimal for this cell: {optimal:.2f} (gap: {gap:+.2f})."

        priorities.append(OptimizationPriority(
            dimension=dim,
            current_value=round(current, 3),
            optimal_value=round(optimal, 3),
            gradient=round(grad_val, 4),
            gap=round(gap, 3),
            expected_lift_delta=round(expected_lift, 2),
            creative_direction=creative_dir,
        ))
        total_lift += abs(expected_lift)

    # --- Add interaction effects to lift estimates ---
    # For each significant interaction pair, compute the joint effect:
    # interaction_lift = β_ij * (val_i - mean_i) * (val_j - mean_j)
    # This captures non-linear effects that the linear model misses.
    interaction_lift_total = 0.0
    for pair_name, coeff in gradient.interaction_terms.items():
        parts = pair_name.split(" × ")
        if len(parts) != 2:
            continue
        dim_i, dim_j = parts
        val_i = current_alignment.get(dim_i, gradient.means.get(dim_i, 0.5))
        val_j = current_alignment.get(dim_j, gradient.means.get(dim_j, 0.5))
        mean_i = gradient.means.get(dim_i, 0.5)
        mean_j = gradient.means.get(dim_j, 0.5)
        # Interaction contribution: product of deviations from mean
        ix_lift = coeff * (val_i - mean_i) * (val_j - mean_j) * 100.0
        interaction_lift_total += ix_lift
        total_lift += abs(ix_lift)

    # Sort by absolute expected lift (highest impact first)
    priorities.sort(key=lambda p: abs(p.expected_lift_delta), reverse=True)

    return GradientIntelligence(
        optimization_priorities=priorities[:top_n],
        current_alignment={k: round(v, 3) for k, v in current_alignment.items()},
        gradient_field={k: round(v, 4) for k, v in gradient.gradients.items()},
        optimal_alignment={k: round(v, 3) for k, v in gradient.optima.items()},
        total_expected_lift_delta=round(total_lift, 2),
        field_metadata={
            "archetype": gradient.archetype,
            "category": gradient.category,
            "n_edges_in_gradient": gradient.n_edges,
            "r_squared": gradient.r_squared,
            "r_squared_with_interactions": gradient.r_squared_with_interactions,
            "gradient_dimensions": len(gradient.gradients),
            "interaction_terms": len(gradient.interaction_terms),
            "interaction_lift_pct": round(interaction_lift_total, 2),
        },
    )


# ---------------------------------------------------------------------------
# Neo4j query to extract raw edge data for gradient computation
# ---------------------------------------------------------------------------
GRADIENT_EDGE_QUERY = """
MATCH (pd:ProductDescription)-[bc:BRAND_CONVERTED]->(ar:AnnotatedReview)
WHERE ($category = '' OR pd.category_path STARTS WITH $category)
  AND ($archetype = '' OR ar.user_archetype = $archetype)
RETURN
  bc.regulatory_fit_score AS avg_reg_fit,
  bc.construal_fit_score AS avg_construal_fit,
  bc.personality_brand_alignment AS avg_personality_align,
  bc.emotional_resonance AS avg_emotional,
  bc.value_alignment AS avg_value,
  bc.evolutionary_motive_match AS avg_evo,
  bc.linguistic_style_matching AS avg_linguistic,
  bc.persuasion_confidence_multiplier AS avg_confidence,
  bc.composite_alignment AS composite_alignment,
  coalesce(bc.persuasion_susceptibility, ar.persuasion_susceptibility) AS avg_persuasion_susceptibility,
  coalesce(bc.cognitive_load_tolerance, ar.cognitive_load_tolerance) AS avg_cognitive_load_tolerance,
  coalesce(bc.narrative_transport, ar.narrative_transport) AS avg_narrative_transport,
  coalesce(bc.social_proof_sensitivity, ar.social_proof_sensitivity) AS avg_social_proof_sensitivity,
  coalesce(bc.loss_aversion_intensity, ar.loss_aversion_intensity) AS avg_loss_aversion_intensity,
  coalesce(bc.temporal_discounting, ar.temporal_discounting) AS avg_temporal_discounting,
  coalesce(bc.brand_relationship_depth, ar.brand_relationship_depth) AS avg_brand_relationship_depth,
  coalesce(bc.autonomy_reactance, ar.autonomy_reactance) AS avg_autonomy_reactance,
  coalesce(bc.information_seeking, ar.information_seeking) AS avg_information_seeking,
  coalesce(bc.mimetic_desire, ar.mimetic_desire) AS avg_mimetic_desire,
  coalesce(bc.interoceptive_awareness, ar.interoceptive_awareness) AS avg_interoceptive_awareness,
  coalesce(bc.cooperative_framing_fit, ar.cooperative_framing_fit) AS avg_cooperative_framing_fit,
  coalesce(bc.decision_entropy, ar.decision_entropy) AS avg_decision_entropy
LIMIT 50000
"""


def compute_gradient_from_neo4j(
    driver: Any,
    archetype: str,
    category: str,
) -> GradientVector:
    """Compute gradient field by querying Neo4j directly.

    This is for batch pre-computation (scripts/compute_gradient_fields.py).
    """
    try:
        with driver.session() as session:
            results = session.run(
                GRADIENT_EDGE_QUERY,
                archetype=archetype,
                category=category,
            ).data()

        from adam.config.settings import get_settings
        if len(results) < get_settings().cascade.gradient_min_edges:
            logger.info(
                "Insufficient edges for gradient: %s × %s (%d edges)",
                archetype, category, len(results),
            )
            return GradientVector(
                archetype=archetype, category=category, n_edges=len(results),
            )

        # Filter out rows with too many nulls
        clean_rows = []
        for row in results:
            non_null = sum(1 for v in row.values() if v is not None)
            if non_null >= 5:
                clean_rows.append(row)

        return compute_gradient_field(clean_rows, archetype, category)

    except Exception as e:
        logger.warning("Gradient computation failed for %s × %s: %s", archetype, category, e)
        return GradientVector(archetype=archetype, category=category)


# ---------------------------------------------------------------------------
# Gradient field storage format (for BayesianPrior node properties)
# ---------------------------------------------------------------------------
def gradient_to_neo4j_properties(gv: GradientVector) -> Dict[str, Any]:
    """Convert a GradientVector to flat properties for Neo4j storage."""
    props: Dict[str, Any] = {
        "gradient_n_edges": gv.n_edges,
        "gradient_r_squared": gv.r_squared,
        "gradient_r_squared_interactions": gv.r_squared_with_interactions,
    }
    for dim, val in gv.gradients.items():
        props[f"gradient_{dim}"] = val
    for dim, val in gv.means.items():
        props[f"gradient_mean_{dim}"] = val
    for dim, val in gv.optima.items():
        props[f"gradient_optimal_{dim}"] = val
    for dim, val in gv.stds.items():
        props[f"gradient_std_{dim}"] = val
    # Store interaction terms with sanitized keys (× → _x_)
    for pair_name, val in gv.interaction_terms.items():
        safe_key = pair_name.replace(" × ", "_x_").replace(" ", "_")
        props[f"gradient_ix_{safe_key}"] = val
    return props


def gradient_from_neo4j_properties(
    props: Dict[str, Any],
    archetype: str,
    category: str,
) -> GradientVector:
    """Reconstruct a GradientVector from Neo4j node properties."""
    gradients = {}
    means = {}
    optima = {}
    stds = {}
    interaction_terms = {}

    skip_keys = {"gradient_n_edges", "gradient_r_squared", "gradient_r_squared_interactions"}

    for key, val in props.items():
        if val is None:
            continue
        if key.startswith("gradient_optimal_"):
            dim = key[len("gradient_optimal_"):]
            optima[dim] = float(val)
        elif key.startswith("gradient_mean_"):
            dim = key[len("gradient_mean_"):]
            means[dim] = float(val)
        elif key.startswith("gradient_std_"):
            dim = key[len("gradient_std_"):]
            stds[dim] = float(val)
        elif key.startswith("gradient_ix_"):
            # Interaction term: restore "dim_a × dim_b" from "dim_a_x_dim_b"
            pair_key = key[len("gradient_ix_"):]
            # Split on _x_ to get the two dimension names (with underscores preserved)
            parts = pair_key.split("_x_", 1)
            if len(parts) == 2:
                pair_name = f"{parts[0]} × {parts[1]}"
            else:
                pair_name = pair_key
            interaction_terms[pair_name] = float(val)
        elif key.startswith("gradient_") and key not in skip_keys:
            dim = key[len("gradient_"):]
            gradients[dim] = float(val)

    return GradientVector(
        gradients=gradients,
        means=means,
        optima=optima,
        stds=stds,
        interaction_terms=interaction_terms,
        archetype=archetype,
        category=category,
        n_edges=int(props.get("gradient_n_edges", 0)),
        r_squared=float(props.get("gradient_r_squared", 0.0)),
        r_squared_with_interactions=float(props.get("gradient_r_squared_interactions", 0.0)),
    )
