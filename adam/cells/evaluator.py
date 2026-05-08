"""S6.2 cell-conditional predicate evaluator — runs registered
predicates against a CellFeatureSet and emits a CombinedModulation
signal that the bilateral cascade consumes.

Per Q19=α: predicates are Python functions registered via
@cell_predicate decorator. No DSL, no YAML, no parser. Authoring
surface is code-reviewed Python.

Per Q17=Path A only: evaluator integrates with bilateral_cascade
(Path A — inference). Path B (TherapeuticTouch adaptive loop) is
untouched.

Pilot interpretation note (creative_class_boosts / dampens vocabulary):
    For pilot, the "class" identifier in CreativeModulation maps
    DIRECTLY to Cialdini mechanism IDs (social_proof, scarcity,
    authority, etc.) — the granularity the bilateral cascade's
    `result.mechanism_scores` consumes downstream. Post-pilot may
    introduce a creative-class layer atop mechanisms; until then,
    seed predicates emit mechanism IDs as the modulation namespace
    so apply_cell_modulation can multiply mechanism_scores directly.

Bid-time latency target: <5ms p99 for the full predicate sweep with
~10 seed predicates registered. Per-predicate <100us.

Fail-soft semantics: any predicate that raises is logged and skipped.
The evaluator continues with remaining predicates and returns whatever
modulations DID succeed. The cascade continues even if ALL predicates
fail (returns CombinedModulation with is_neutral=True).
"""
import logging
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from adam.cells.features import CellFeatureSet

logger = logging.getLogger(__name__)


# ============================================================================
# Output types
# ============================================================================

@dataclass(frozen=True)
class CreativeModulation:
    """One predicate's emitted modulation when it fires."""

    predicate_name: str
    """Name of the predicate that emitted this modulation
    (for decision-trace + logging)."""

    cell_id: str
    """Cell context the modulation was emitted in."""

    creative_class_boosts: Dict[str, float] = field(default_factory=dict)
    """Class-name → multiplicative boost factor. Pilot vocabulary:
    Cialdini mechanism IDs (social_proof, scarcity, authority, etc.).
    Combined multiplicatively across predicates."""

    creative_class_dampens: Dict[str, float] = field(default_factory=dict)
    """Class-name → multiplicative dampen factor in (0, 1].
    Combined multiplicatively across predicates."""

    diversity_adjustment: float = 0.0
    """Additive adjustment to creative-selection diversity in
    [-0.5, 0.5]. Combined additively across predicates and clipped
    to [-1, 1] in CombinedModulation."""

    reason: str = ""
    """Human-readable rationale for decision-trace logging.
    Not consumed by selection logic."""


@dataclass(frozen=True)
class CombinedModulation:
    """Aggregate result of all firing predicates for one feature set."""

    cell_id: str
    fired_predicates: List[str]
    """Names of predicates that fired (for logging)."""
    class_boosts: Dict[str, float]
    """Multiplicatively combined class boosts."""
    class_dampens: Dict[str, float]
    """Multiplicatively combined class dampens."""
    diversity_adjustment: float
    """Additively combined diversity, clipped to [-1, 1]."""
    reasons: List[str]
    """Concatenated rationales for decision trace."""

    @property
    def is_neutral(self) -> bool:
        """True if no predicates fired AND no boosts/dampens recorded;
        the modulation should be a no-op at the integration seam."""
        return (
            not self.fired_predicates
            and not self.class_boosts
            and not self.class_dampens
            and self.diversity_adjustment == 0.0
        )


# ============================================================================
# Registry + decorator
# ============================================================================

@dataclass(frozen=True)
class PredicateRegistration:
    """Internal registry entry for a registered predicate."""
    name: str
    function: Callable[[CellFeatureSet], Optional[CreativeModulation]]
    docstring: str


_PREDICATE_REGISTRY: List[PredicateRegistration] = []


def cell_predicate(name: str):
    """Decorator registering a predicate function with the evaluator.

    Predicate function signature:
        (features: CellFeatureSet) -> Optional[CreativeModulation]

    Returning None means the predicate did not fire (cell condition
    not met). Returning a CreativeModulation means the predicate
    fired and is contributing to creative-selection bias.

    Registration semantics:
      - name must be unique across registry (raises ValueError on
        duplicate at import time)
      - registration happens at module import via decorator side-effect

    Example:
        @cell_predicate(name="high_fomo_promotion")
        def high_fomo_promotion(features):
            if (features.fomo_score > 0.7
                and features.regulatory_focus == RegulatoryFocus.PROMOTION):
                return CreativeModulation(
                    predicate_name="high_fomo_promotion",
                    cell_id=features.cell_id,
                    creative_class_boosts={"scarcity": 1.5},
                    reason="high FOMO + promotion focus",
                )
            return None
    """
    def decorator(func):
        for existing in _PREDICATE_REGISTRY:
            if existing.name == name:
                raise ValueError(
                    f"Duplicate predicate name: {name!r} "
                    f"(already registered)"
                )
        _PREDICATE_REGISTRY.append(
            PredicateRegistration(
                name=name,
                function=func,
                docstring=func.__doc__ or "",
            )
        )
        return func
    return decorator


def get_registered_predicates() -> List[str]:
    """Return list of registered predicate names — for diagnostics
    and admin tooling."""
    return [reg.name for reg in _PREDICATE_REGISTRY]


def _clear_registry_for_testing() -> None:
    """TEST-ONLY helper to reset the registry. Production code must
    not call this."""
    _PREDICATE_REGISTRY.clear()


# ============================================================================
# Evaluator
# ============================================================================

def evaluate_predicates(features: CellFeatureSet) -> CombinedModulation:
    """Run all registered predicates against the feature set; combine
    their modulations into one CombinedModulation.

    Bid-time latency: target <5ms p99 for the full sweep with ~10
    seed predicates.

    Fail-soft: any predicate raising an exception is logged and
    skipped. Remaining predicates continue. Cascade continues even
    if every predicate fails (returns CombinedModulation with
    is_neutral=True).

    Combination semantics:
      - class_boosts: multiplicative across predicates (1.5 × 1.3 = 1.95)
      - class_dampens: multiplicative across predicates (0.7 × 0.9 = 0.63)
      - diversity_adjustment: additive, clipped to [-1, 1]
    """
    fired: List[str] = []
    reasons: List[str] = []
    class_boosts: Dict[str, float] = {}
    class_dampens: Dict[str, float] = {}
    diversity_adjustment = 0.0

    # Snapshot the registry to a list — protects against reentrant
    # decorator calls during evaluation (extremely unlikely but
    # cheap defense).
    for reg in list(_PREDICATE_REGISTRY):
        try:
            modulation = reg.function(features)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Predicate %s raised during evaluation: %s. "
                "Skipping; cascade continues.",
                reg.name, exc,
            )
            continue

        if modulation is None:
            continue

        fired.append(reg.name)
        if modulation.reason:
            reasons.append(modulation.reason)

        for cls, boost in modulation.creative_class_boosts.items():
            class_boosts[cls] = class_boosts.get(cls, 1.0) * boost

        for cls, dampen in modulation.creative_class_dampens.items():
            class_dampens[cls] = class_dampens.get(cls, 1.0) * dampen

        diversity_adjustment += modulation.diversity_adjustment

    diversity_adjustment = max(-1.0, min(1.0, diversity_adjustment))

    return CombinedModulation(
        cell_id=features.cell_id,
        fired_predicates=fired,
        class_boosts=class_boosts,
        class_dampens=class_dampens,
        diversity_adjustment=diversity_adjustment,
        reasons=reasons,
    )


# ============================================================================
# Path A integration helper — apply CombinedModulation to mechanism_scores
# ============================================================================

def apply_cell_modulation(
    mechanism_scores: Dict[str, float],
    modulation: CombinedModulation,
) -> Dict[str, float]:
    """Apply a CombinedModulation to the bilateral cascade's
    mechanism_scores dict.

    Pilot interpretation: CombinedModulation's class_boosts /
    class_dampens use Cialdini mechanism IDs as the class namespace
    (per evaluator.py module docstring). This function multiplies
    matching mechanism_scores by boosts and dampens; mechanisms not
    referenced in the modulation pass through unchanged.

    Class IDs that don't appear in mechanism_scores are silently
    ignored (no error — predicates may emit boosts for mechanisms
    the cascade didn't compute, and that's a no-op rather than a
    failure).

    Returns a NEW dict (does not mutate input). If modulation is
    neutral, returns a shallow copy unchanged.
    """
    if modulation.is_neutral:
        return dict(mechanism_scores)

    modulated = dict(mechanism_scores)
    for mech, boost in modulation.class_boosts.items():
        if mech in modulated:
            modulated[mech] = modulated[mech] * boost
    for mech, dampen in modulation.class_dampens.items():
        if mech in modulated:
            modulated[mech] = modulated[mech] * dampen
    return modulated
