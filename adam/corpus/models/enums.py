"""Enums for the corpus annotation pipeline."""

from enum import Enum


class AnnotationTier(str, Enum):
    """Annotation depth tier -- controls how many constructs are scored."""
    TIER_1_CORE = "tier_1_core"          # Core constructs only (~45 scores)
    TIER_2_EXTENDED = "tier_2_extended"   # Extended constructs (~80 scores)
    TIER_3_DEEP = "tier_3_deep"          # Full depth (~120 scores)


class ConversionOutcome(str, Enum):
    """Inferred conversion outcome from review sentiment."""
    SATISFIED = "satisfied"
    NEUTRAL = "neutral"
    REGRET = "regret"
    EVANGELIZED = "evangelized"
    WARNED = "warned"
