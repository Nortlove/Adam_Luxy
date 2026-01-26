# =============================================================================
# ADAM Verification Constraint Models
# Location: adam/verification/models/constraints.py
# =============================================================================

"""
CONSTRAINT MODELS

Models for psychological and logical constraints that
atom outputs must satisfy.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


# =============================================================================
# ENUMS
# =============================================================================

class ConstraintType(str, Enum):
    """Types of constraints."""
    
    # Logical constraints
    MUTUAL_EXCLUSION = "mutual_exclusion"  # Can't be both
    IMPLICATION = "implication"            # If A then B
    RANGE = "range"                        # Value must be in range
    
    # Psychological constraints
    REGULATORY_CONSISTENCY = "regulatory_consistency"
    CONSTRUAL_CONSISTENCY = "construal_consistency"
    AROUSAL_COHERENCE = "arousal_coherence"
    
    # Safety constraints
    VULNERABLE_PROTECTION = "vulnerable_protection"
    MANIPULATION_LIMIT = "manipulation_limit"
    DARK_PATTERN_AVOIDANCE = "dark_pattern_avoidance"


class ConstraintSeverity(str, Enum):
    """How severe a constraint violation is."""
    
    INFO = "info"           # Log but allow
    WARNING = "warning"     # Allow with flag
    ERROR = "error"         # Block unless corrected
    CRITICAL = "critical"   # Always block


# =============================================================================
# CONSTRAINT DEFINITION
# =============================================================================

class Constraint(BaseModel):
    """Definition of a constraint."""
    
    constraint_id: str = Field(
        default_factory=lambda: f"con_{uuid4().hex[:8]}"
    )
    name: str
    description: str
    
    # Type and severity
    constraint_type: ConstraintType
    severity: ConstraintSeverity = Field(default=ConstraintSeverity.ERROR)
    
    # What atoms this applies to
    applies_to_atoms: List[str] = Field(default_factory=list)
    
    # Condition (simplified rule)
    condition: str = ""  # Human-readable condition
    
    # Active
    active: bool = Field(default=True)


class ConstraintResult(BaseModel):
    """Result of checking a single constraint."""
    
    constraint_id: str
    constraint_name: str
    
    # Result
    satisfied: bool
    
    # Details
    violation_message: Optional[str] = None
    violation_data: Dict[str, Any] = Field(default_factory=dict)
    
    # Severity if violated
    severity: ConstraintSeverity = Field(default=ConstraintSeverity.ERROR)
    
    # Can it be auto-corrected?
    correctable: bool = Field(default=False)
    correction_suggestion: Optional[str] = None


# =============================================================================
# PSYCHOLOGICAL CONSTRAINTS
# =============================================================================

class PsychologicalConstraint(Constraint):
    """
    Constraint based on psychological theory.
    
    These encode psychological invariants that shouldn't be violated.
    """
    
    # Research basis
    research_citation: str = ""
    
    # Expected relationship
    antecedent_atom: str = ""
    antecedent_value: str = ""
    consequent_atom: str = ""
    expected_consequent: str = ""
    
    # Allowable deviation
    tolerance: float = Field(ge=0.0, le=1.0, default=0.2)


# Default psychological constraints
DEFAULT_PSYCHOLOGICAL_CONSTRAINTS = [
    PsychologicalConstraint(
        name="high_arousal_prevents_abstraction",
        description="High arousal should reduce abstract construal (Yerkes-Dodson)",
        constraint_type=ConstraintType.AROUSAL_COHERENCE,
        severity=ConstraintSeverity.WARNING,
        applies_to_atoms=["atom_construal_level"],
        research_citation="Yerkes & Dodson, 1908",
        antecedent_atom="arousal",
        antecedent_value="high",
        consequent_atom="construal_level",
        expected_consequent="concrete",
        tolerance=0.3,
    ),
    PsychologicalConstraint(
        name="prevention_scarcity_alignment",
        description="Prevention focus should prefer scarcity messaging",
        constraint_type=ConstraintType.REGULATORY_CONSISTENCY,
        severity=ConstraintSeverity.INFO,
        applies_to_atoms=["atom_regulatory_focus", "atom_mechanism_activation"],
        research_citation="Higgins, 1997",
        antecedent_atom="regulatory_focus",
        antecedent_value="prevention",
        consequent_atom="mechanism",
        expected_consequent="scarcity",
        tolerance=0.4,
    ),
    PsychologicalConstraint(
        name="promotion_abstract_alignment",
        description="Promotion focus aligns with abstract construal",
        constraint_type=ConstraintType.CONSTRUAL_CONSISTENCY,
        severity=ConstraintSeverity.INFO,
        applies_to_atoms=["atom_regulatory_focus", "atom_construal_level"],
        research_citation="Lee, Keller, & Sternthal, 2010",
        antecedent_atom="regulatory_focus",
        antecedent_value="promotion",
        consequent_atom="construal_level",
        expected_consequent="abstract",
        tolerance=0.3,
    ),
]


# =============================================================================
# SAFETY CONSTRAINTS
# =============================================================================

class SafetyConstraint(Constraint):
    """Constraint for safety and ethics."""
    
    # Population this protects
    protected_population: str = ""
    
    # Detection signal
    detection_signal: str = ""
    detection_threshold: float = Field(ge=0.0, le=1.0, default=0.5)
    
    # Action on violation
    fallback_action: str = ""


DEFAULT_SAFETY_CONSTRAINTS = [
    SafetyConstraint(
        name="high_neuroticism_protection",
        description="Avoid fear-based messaging for high-neuroticism users",
        constraint_type=ConstraintType.VULNERABLE_PROTECTION,
        severity=ConstraintSeverity.ERROR,
        protected_population="high_neuroticism",
        detection_signal="neuroticism_score",
        detection_threshold=0.8,
        fallback_action="use_positive_framing",
    ),
    SafetyConstraint(
        name="excessive_scarcity_limit",
        description="Limit scarcity mechanism intensity to prevent manipulation",
        constraint_type=ConstraintType.MANIPULATION_LIMIT,
        severity=ConstraintSeverity.WARNING,
        detection_signal="scarcity_intensity",
        detection_threshold=0.9,
        fallback_action="reduce_intensity",
    ),
    SafetyConstraint(
        name="dark_pattern_avoidance",
        description="Block dark pattern mechanisms",
        constraint_type=ConstraintType.DARK_PATTERN_AVOIDANCE,
        severity=ConstraintSeverity.CRITICAL,
        detection_signal="dark_pattern_detected",
        detection_threshold=0.1,
        fallback_action="block_and_log",
    ),
]
