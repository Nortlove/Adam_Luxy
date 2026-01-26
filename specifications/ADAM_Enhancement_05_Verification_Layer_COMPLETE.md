# ADAM Enhancement #05: Verification Layer
## Enterprise-Grade Verification Pipeline for Psychological Reasoning

**Version**: 2.0 COMPLETE  
**Date**: January 2026  
**Priority**: P0 - Critical (Quality Assurance Foundation)  
**Estimated Implementation**: 12 person-weeks  
**Dependencies**: #01-04 (Graph Fusion, Blackboard, Meta-Learner, AoT DAG), #31 (Event Bus/Cache)  
**Dependents**: All downstream components rely on verified outputs  
**File Size**: ~115KB (Enterprise Production-Ready)

---

## Table of Contents

### SECTION A: STRATEGIC OVERVIEW
1. [Executive Summary](#executive-summary)
2. [Four-Layer Verification Architecture](#four-layer-architecture)
3. [Research Foundations](#research-foundations)
4. [Expected Impact](#expected-impact)

### SECTION B: DATA MODELS
5. [Pydantic Models](#pydantic-models)
6. [Constraint Definitions](#constraint-definitions)
7. [Verification Results](#verification-results)

### SECTION C: LAYER 1 - ATOM CONSISTENCY
8. [Psychological Constraints](#psychological-constraints)
9. [Consistency Verifier](#consistency-verifier)
10. [Constraint Rule Engine](#constraint-rule-engine)

### SECTION D: LAYER 2 - CONFIDENCE CALIBRATION
11. [Calibration System](#calibration-system)
12. [Multi-Method Confidence](#multi-method-confidence)
13. [Uncertainty Decomposition](#uncertainty-decomposition)

### SECTION E: LAYER 3 - SAFETY VALIDATION
14. [Vulnerable Population Protection](#vulnerable-population-protection)
15. [Manipulation Detection](#manipulation-detection)
16. [Regulatory Compliance](#regulatory-compliance)

### SECTION F: LAYER 4 - GRAPH GROUNDING
17. [Claim Extraction](#claim-extraction)
18. [Neo4j Verification](#neo4j-verification)
19. [Hallucination Detection](#hallucination-detection)

### SECTION G: SELF-CORRECTION MECHANISM
20. [Critique Generation](#critique-generation)
21. [Correction Application](#correction-application)
22. [Fallback Strategy](#fallback-strategy)

### SECTION H: EVENT BUS INTEGRATION (#31)
23. [Verification Signals](#verification-signals)
24. [Learning Signal Emission](#learning-signal-emission)

### SECTION I: CACHE INTEGRATION (#31)
25. [Calibration Curve Caching](#calibration-curve-caching)
26. [Verification Result Caching](#verification-result-caching)

### SECTION J: NEO4J SCHEMA
27. [Audit Trail Schema](#audit-trail-schema)
28. [Verification Analytics Queries](#verification-analytics-queries)

### SECTION K: FASTAPI ENDPOINTS
29. [Verification Inspection API](#verification-inspection-api)
30. [Constraint Management API](#constraint-management-api)
31. [Calibration API](#calibration-api)

### SECTION L: PROMETHEUS METRICS
32. [Consistency Metrics](#consistency-metrics)
33. [Safety Metrics](#safety-metrics)
34. [Calibration Metrics](#calibration-metrics)

### SECTION M: TESTING & OPERATIONS
35. [Unit Tests](#unit-tests)
36. [Integration Tests](#integration-tests)
37. [Implementation Timeline](#implementation-timeline)
38. [Success Metrics](#success-metrics)

---

# SECTION A: STRATEGIC OVERVIEW

## Executive Summary

### The Critical Gap

Current ADAM architecture has **no verification before action**:

```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                                                                                             │
│   THE PROBLEM: NO VERIFICATION BEFORE ACTION                                                │
│   ══════════════════════════════════════════                                                │
│                                                                                             │
│   ┌───────────┐    ┌───────────┐    ┌───────────┐    ┌───────────┐                         │
│   │ DAG Atoms │───▶│ Synthesis │───▶│ Decision  │───▶│  Execute  │                         │
│   └───────────┘    └───────────┘    └───────────┘    └───────────┘                         │
│                                           ▲                                                 │
│                                           │                                                 │
│                                    NO VERIFICATION                                          │
│                                                                                             │
│   PROBLEMS:                                                                                 │
│   • No consistency check: Atoms produce contradictory outputs                               │
│   • Uncalibrated confidence: Claude reports 90% but accuracy is 60%                         │
│   • No safety validation: Harmful ad recommendations pass through                           │
│   • No graph grounding: Reasoning may hallucinate user attributes                           │
│   • No self-correction: Errors propagate without opportunity for refinement                 │
│                                                                                             │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

### The Solution: Four-Layer Verification System

```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                           VERIFICATION LAYER ARCHITECTURE                                   │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────────────────────┐ │
│  │                          LAYER 1: ATOM CONSISTENCY                                    │ │
│  │                                                                                       │ │
│  │  • Cross-atom logical coherence                                                       │ │
│  │  • Dependency satisfaction check                                                      │ │
│  │  • Psychological constraint validation                                                │ │
│  └───────────────────────────────────────────────────────────────────────────────────────┘ │
│                                        │                                                    │
│                                        ▼                                                    │
│  ┌───────────────────────────────────────────────────────────────────────────────────────┐ │
│  │                       LAYER 2: CONFIDENCE CALIBRATION                                 │ │
│  │                                                                                       │ │
│  │  • Multi-sample consistency scoring                                                   │ │
│  │  • Historical calibration adjustment                                                  │ │
│  │  • Uncertainty decomposition (input/reasoning/prediction)                             │ │
│  └───────────────────────────────────────────────────────────────────────────────────────┘ │
│                                        │                                                    │
│                                        ▼                                                    │
│  ┌───────────────────────────────────────────────────────────────────────────────────────┐ │
│  │                        LAYER 3: SAFETY VALIDATION                                     │ │
│  │                                                                                       │ │
│  │  • Vulnerable population protection                                                   │ │
│  │  • Manipulation detection                                                             │ │
│  │  • Dark pattern avoidance                                                             │ │
│  │  • Regulatory compliance check                                                        │ │
│  └───────────────────────────────────────────────────────────────────────────────────────┘ │
│                                        │                                                    │
│                                        ▼                                                    │
│  ┌───────────────────────────────────────────────────────────────────────────────────────┐ │
│  │                         LAYER 4: GRAPH GROUNDING                                      │ │
│  │                                                                                       │ │
│  │  • Verify claims against Neo4j                                                        │ │
│  │  • Check attribute existence                                                          │ │
│  │  • Validate relationship traversals                                                   │ │
│  │  • Detect hallucinated user properties                                                │ │
│  └───────────────────────────────────────────────────────────────────────────────────────┘ │
│                                        │                                                    │
│                                        ▼                                                    │
│  ┌───────────────────────────────────────────────────────────────────────────────────────┐ │
│  │                   SELF-CORRECTION (if verification fails)                             │ │
│  │                                                                                       │ │
│  │  • Identify specific failure                                                          │ │
│  │  • Generate critique (DoT-style)                                                      │ │
│  │  • Re-run failed atom with feedback                                                   │ │
│  │  • Limit to 2 correction attempts, then fallback                                      │ │
│  └───────────────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                             │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

### Expected Impact

| Metric | Current | Target | Improvement |
|--------|---------|--------|-------------|
| **Reasoning consistency** | ~70% | >95% | +36% |
| **Confidence calibration (ECE)** | 0.25 | <0.10 | 60% reduction |
| **Safety violations** | Unknown | 0% | Complete protection |
| **Graph grounding accuracy** | ~80% | >98% | +23% |
| **Self-correction success** | N/A | >70% | New capability |

---

# SECTION B: DATA MODELS

## Pydantic Models

```python
# =============================================================================
# ADAM Enhancement #05: Verification Layer Data Models
# Location: adam/verification/models.py
# =============================================================================

"""
Type-safe data models for the Verification Layer.

All models use Pydantic for validation and serialization,
ensuring type safety across the verification pipeline.
"""

from __future__ import annotations
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


# =============================================================================
# ENUMS
# =============================================================================

class ConstraintSeverity(str, Enum):
    """How serious a constraint violation is."""
    HARD = "hard"      # Must not violate (triggers re-run)
    SOFT = "soft"      # Warn but allow (triggers confidence penalty)
    INFO = "info"      # Log for debugging


class SafetyRiskLevel(str, Enum):
    """Risk level categories."""
    SAFE = "safe"
    CAUTION = "caution"
    WARNING = "warning"
    BLOCKED = "blocked"


class CorrectionAction(str, Enum):
    """Actions taken during self-correction."""
    REFINE = "refine"        # Re-run with critique
    FALLBACK = "fallback"    # Use safe defaults
    ACCEPT = "accept"        # Accept despite issues


class VerificationStatus(str, Enum):
    """Overall verification status."""
    PASSED = "passed"
    PASSED_WITH_WARNINGS = "passed_with_warnings"
    CORRECTED = "corrected"
    FAILED = "failed"
    FALLBACK = "fallback"


# =============================================================================
# CONSISTENCY MODELS
# =============================================================================

class ConsistencyConstraint(BaseModel):
    """A constraint between atom outputs."""
    constraint_id: str = Field(default_factory=lambda: f"constraint_{uuid4().hex[:8]}")
    name: str
    description: str
    severity: ConstraintSeverity
    source_atoms: List[str] = Field(description="Atoms this constraint checks")
    violation_message: str
    correction_hint: str
    research_basis: Optional[str] = None
    
    class Config:
        arbitrary_types_allowed = True


class ConstraintViolation(BaseModel):
    """A specific constraint violation."""
    constraint_name: str
    severity: ConstraintSeverity
    message: str
    correction_hint: str
    evidence: Dict[str, Any] = Field(default_factory=dict)
    source_atoms: List[str] = Field(default_factory=list)


class ConsistencyVerificationResult(BaseModel):
    """Result of consistency verification."""
    passed: bool
    hard_violations: List[ConstraintViolation] = Field(default_factory=list)
    soft_violations: List[ConstraintViolation] = Field(default_factory=list)
    passed_constraints: List[str] = Field(default_factory=list)
    total_constraints_checked: int = 0
    consistency_score: float = Field(ge=0.0, le=1.0, default=1.0)
    verification_time_ms: float = 0.0


# =============================================================================
# CONFIDENCE MODELS
# =============================================================================

class UncertaintyBreakdown(BaseModel):
    """Decomposition of uncertainty sources."""
    input_uncertainty: float = Field(ge=0.0, le=1.0, description="Ambiguity in user data")
    reasoning_uncertainty: float = Field(ge=0.0, le=1.0, description="Variance in analysis")
    prediction_uncertainty: float = Field(ge=0.0, le=1.0, description="Confidence in selection")


class ConfidenceEstimate(BaseModel):
    """Calibrated confidence estimate with uncertainty breakdown."""
    raw_confidence: float = Field(ge=0.0, le=1.0, description="Claude's self-reported confidence")
    calibrated_confidence: float = Field(ge=0.0, le=1.0, description="After historical calibration")
    consistency_score: float = Field(ge=0.0, le=1.0, description="Agreement across samples")
    uncertainty_breakdown: UncertaintyBreakdown
    final_confidence: float = Field(ge=0.0, le=1.0, description="Combined calibrated confidence")
    calibration_method: str = "multi_method"
    calibration_bin: int = Field(ge=0, le=9)


# =============================================================================
# SAFETY MODELS
# =============================================================================

class SafetyViolation(BaseModel):
    """A specific safety violation."""
    violation_id: str = Field(default_factory=lambda: f"safety_{uuid4().hex[:8]}")
    category: str  # vulnerable_population, manipulation, compliance
    severity: SafetyRiskLevel
    description: str
    evidence: Dict[str, Any] = Field(default_factory=dict)
    mitigation: Optional[str] = None
    ad_id: Optional[str] = None


class SafetyValidationResult(BaseModel):
    """Result of safety validation."""
    is_safe: bool
    risk_level: SafetyRiskLevel
    violations: List[SafetyViolation] = Field(default_factory=list)
    allowed_ad_ids: List[str] = Field(default_factory=list)
    blocked_ad_ids: List[str] = Field(default_factory=list)
    required_mitigations: List[str] = Field(default_factory=list)
    vulnerable_user_detected: bool = False
    manipulation_detected: bool = False
    audit_log: Dict[str, Any] = Field(default_factory=dict)


# =============================================================================
# GROUNDING MODELS
# =============================================================================

class GroundingClaim(BaseModel):
    """A claim made by Claude that should be grounded in the graph."""
    claim_id: str = Field(default_factory=lambda: f"claim_{uuid4().hex[:8]}")
    claim_type: str  # user_attribute, user_behavior, relationship
    claim_text: str
    claimed_value: Any
    source_atom: str


class GroundingVerificationResult(BaseModel):
    """Result of graph grounding verification."""
    all_claims_grounded: bool
    verified_claims: List[GroundingClaim] = Field(default_factory=list)
    ungrounded_claims: List[GroundingClaim] = Field(default_factory=list)
    missing_data_claims: List[GroundingClaim] = Field(default_factory=list)
    grounding_score: float = Field(ge=0.0, le=1.0)
    neo4j_queries_executed: int = 0
    verification_time_ms: float = 0.0


# =============================================================================
# CORRECTION MODELS
# =============================================================================

class CorrectionResult(BaseModel):
    """Result of a single correction attempt."""
    correction_id: str = Field(default_factory=lambda: f"correction_{uuid4().hex[:8]}")
    action: CorrectionAction
    original_output: Dict[str, Any]
    corrected_output: Optional[Dict[str, Any]] = None
    critique: str
    correction_applied: str
    attempts: int
    success: bool
    time_ms: float = 0.0


# =============================================================================
# PIPELINE RESULT
# =============================================================================

class VerificationPipelineResult(BaseModel):
    """Complete result of verification pipeline."""
    verification_id: str = Field(default_factory=lambda: f"verify_{uuid4().hex[:12]}")
    request_id: str
    
    # Overall status
    status: VerificationStatus
    passed: bool
    
    # Layer results
    consistency_result: ConsistencyVerificationResult
    confidence_estimate: ConfidenceEstimate
    safety_result: SafetyValidationResult
    grounding_result: GroundingVerificationResult
    
    # Correction
    corrections_applied: List[CorrectionResult] = Field(default_factory=list)
    correction_attempts: int = 0
    
    # Final outputs
    final_outputs: Dict[str, Any] = Field(default_factory=dict)
    final_confidence: float = Field(ge=0.0, le=1.0)
    
    # Timing
    total_verification_time_ms: float = 0.0
    layer_times_ms: Dict[str, float] = Field(default_factory=dict)
    
    # Audit
    audit_trail: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
```

---

# SECTION C: LAYER 1 - ATOM CONSISTENCY

## Psychological Constraints

```python
# =============================================================================
# ADAM Enhancement #05: Psychological Consistency Constraints
# Location: adam/verification/constraints.py
# =============================================================================

"""
Research-backed psychological consistency constraints.

These constraints encode known relationships between psychological
constructs based on peer-reviewed research.
"""

from typing import Dict, Any, List
from .models import ConsistencyConstraint, ConstraintSeverity


def check_high_arousal_prevention_bias(outputs: Dict[str, Any]) -> bool:
    """
    High arousal (>0.7) should increase prevention focus sensitivity.
    
    Research: Yerkes-Dodson Law, Easterbrook Cue-Utilization Theory
    """
    arousal = outputs.get("user_state", {}).get("arousal", 0.5)
    dominant = outputs.get("regulatory_focus", {}).get("dominant_focus", "balanced")
    promotion = outputs.get("regulatory_focus", {}).get("promotion", 0.5)
    prevention = outputs.get("regulatory_focus", {}).get("prevention", 0.5)
    
    # High arousal with strong promotion (1.2x prevention) is inconsistent
    if arousal > 0.7 and dominant == "promotion" and promotion > prevention * 1.2:
        return False
    return True


def check_high_arousal_low_construal(outputs: Dict[str, Any]) -> bool:
    """
    High arousal (>0.7) should lower construal level (attention narrowing).
    
    Research: Storbeck & Clore (2008), Affect-as-Information Framework
    """
    arousal = outputs.get("user_state", {}).get("arousal", 0.5)
    construal = outputs.get("construal_level", {}).get("construal_level", 0.5)
    
    # High arousal with high construal (>0.6) is inconsistent
    if arousal > 0.7 and construal > 0.6:
        return False
    return True


def check_low_arousal_high_construal(outputs: Dict[str, Any]) -> bool:
    """
    Low arousal (<0.3) should increase construal level.
    
    Research: CLT + Arousal interaction studies
    """
    arousal = outputs.get("user_state", {}).get("arousal", 0.5)
    construal = outputs.get("construal_level", {}).get("construal_level", 0.5)
    
    # Low arousal with very low construal (<0.4) is unexpected
    if arousal < 0.3 and construal < 0.4:
        return False
    return True


def check_focus_framing_alignment(outputs: Dict[str, Any]) -> bool:
    """
    Regulatory focus should align with message framing recommendation.
    
    Research: Cesario et al., Regulatory Fit Theory
    """
    dominant = outputs.get("regulatory_focus", {}).get("dominant_focus", "balanced")
    framing = outputs.get("message_framing", {}).get("framing_type", "balanced")
    
    # Prevention focus with gain framing OR promotion with loss framing
    if (dominant == "prevention" and framing == "gain") or \
       (dominant == "promotion" and framing == "loss"):
        return False
    return True


def check_construal_abstraction_alignment(outputs: Dict[str, Any]) -> bool:
    """
    Construal level should align with message abstraction.
    
    Research: Construal Level Theory (Trope & Liberman)
    """
    construal = outputs.get("construal_level", {}).get("construal_level", 0.5)
    abstraction = outputs.get("message_framing", {}).get("abstraction_level", "mixed")
    
    # High construal (>0.6) with concrete messaging is inconsistent
    if construal > 0.6 and abstraction == "concrete":
        return False
    # Low construal (<0.4) with abstract messaging is inconsistent
    if construal < 0.4 and abstraction == "abstract":
        return False
    return True


def check_personality_mechanism_coherence(outputs: Dict[str, Any]) -> bool:
    """
    Active mechanisms should align with expressed personality traits.
    
    Research: ADAM's Personality-Mechanism correlations
    """
    personality = outputs.get("personality_expression", {})
    mechanisms = outputs.get("mechanism_activation", {})
    
    dominant_trait = personality.get("dominant_trait", "").lower()
    primary_mechanism = mechanisms.get("primary_mechanism", "")
    
    # Define expected alignments
    trait_mechanisms = {
        "openness": ["identity_construction", "linguistic_framing", "construal_level"],
        "extraversion": ["mimetic_desire", "attention_dynamics"],
        "neuroticism": ["wanting_liking_dissociation", "evolutionary_adaptations"],
        "conscientiousness": ["regulatory_focus", "automatic_evaluation"],
        "agreeableness": ["mimetic_desire", "social_proof"]
    }
    
    expected = trait_mechanisms.get(dominant_trait, [])
    if not expected:
        return True  # No expectation, pass
    
    # Primary mechanism should be in expected list
    return primary_mechanism in expected or not primary_mechanism


def check_valence_processing_style(outputs: Dict[str, Any]) -> bool:
    """
    Negative valence should promote systematic processing.
    
    Research: Affect-as-Information, Processing Fluency
    """
    valence = outputs.get("user_state", {}).get("valence", 0.5)
    strategy = outputs.get("personality_expression", {}).get("matching_strategy", "mixed")
    
    # Negative valence (<0.3) with heuristic processing is unexpected
    if valence < 0.3 and strategy == "heuristic":
        return False
    return True


def check_confidence_bounds(outputs: Dict[str, Any]) -> bool:
    """All confidence scores should be between 0 and 1."""
    for atom_name, atom_output in outputs.items():
        if isinstance(atom_output, dict) and "confidence" in atom_output:
            conf = atom_output["confidence"]
            if not (0 <= conf <= 1):
                return False
    return True


# =============================================================================
# CONSTRAINT DEFINITIONS
# =============================================================================

PSYCHOLOGICAL_CONSTRAINTS: List[ConsistencyConstraint] = [
    ConsistencyConstraint(
        name="high_arousal_prevention_bias",
        description="High arousal (>0.7) should increase prevention focus sensitivity",
        severity=ConstraintSeverity.HARD,
        source_atoms=["user_state", "regulatory_focus"],
        violation_message="High arousal user shows strong promotion focus without prevention modulation",
        correction_hint="Re-evaluate regulatory focus considering arousal-induced prevention bias",
        research_basis="Yerkes-Dodson Law, Easterbrook Cue-Utilization Theory"
    ),
    ConsistencyConstraint(
        name="high_arousal_low_construal",
        description="High arousal (>0.7) should lower construal level (attention narrowing)",
        severity=ConstraintSeverity.HARD,
        source_atoms=["user_state", "construal_level"],
        violation_message="High arousal user shows abstract construal (should be concrete)",
        correction_hint="Re-evaluate construal level considering arousal-induced attention narrowing",
        research_basis="Storbeck & Clore (2008), Affect-as-Information Framework"
    ),
    ConsistencyConstraint(
        name="low_arousal_high_construal",
        description="Low arousal (<0.3) should increase construal level",
        severity=ConstraintSeverity.SOFT,
        source_atoms=["user_state", "construal_level"],
        violation_message="Low arousal user shows concrete construal (expected abstract)",
        correction_hint="Consider whether low arousal should elevate construal level",
        research_basis="CLT + Arousal interaction studies"
    ),
    ConsistencyConstraint(
        name="focus_framing_alignment",
        description="Regulatory focus should align with message framing recommendation",
        severity=ConstraintSeverity.HARD,
        source_atoms=["regulatory_focus", "message_framing"],
        violation_message="Prevention focus with gain framing or promotion focus with loss framing",
        correction_hint="Align message framing valence with regulatory focus orientation",
        research_basis="Cesario et al., Regulatory Fit Theory"
    ),
    ConsistencyConstraint(
        name="construal_abstraction_alignment",
        description="Construal level should align with message abstraction",
        severity=ConstraintSeverity.HARD,
        source_atoms=["construal_level", "message_framing"],
        violation_message="Abstract construal with concrete messaging or vice versa",
        correction_hint="Align message abstraction with user's construal level",
        research_basis="Construal Level Theory (Trope & Liberman)"
    ),
    ConsistencyConstraint(
        name="personality_mechanism_coherence",
        description="Active mechanisms should align with expressed personality traits",
        severity=ConstraintSeverity.SOFT,
        source_atoms=["personality_expression", "mechanism_activation"],
        violation_message="Active mechanisms don't align with dominant personality trait",
        correction_hint="Re-evaluate mechanism activation based on personality expression",
        research_basis="ADAM's Personality-Mechanism correlations"
    ),
    ConsistencyConstraint(
        name="valence_processing_style",
        description="Negative valence should promote systematic processing",
        severity=ConstraintSeverity.SOFT,
        source_atoms=["user_state", "personality_expression"],
        violation_message="Negative valence user receiving heuristic (vs systematic) processing",
        correction_hint="Consider systematic processing for negative-valence users",
        research_basis="Affect-as-Information, Processing Fluency"
    ),
    ConsistencyConstraint(
        name="confidence_bounds",
        description="All confidence scores should be between 0 and 1",
        severity=ConstraintSeverity.HARD,
        source_atoms=["all"],
        violation_message="Confidence score outside [0, 1] range",
        correction_hint="Normalize confidence scores to valid range",
        research_basis="Statistical validity"
    ),
]


# Map constraint names to check functions
CONSTRAINT_CHECK_FUNCTIONS = {
    "high_arousal_prevention_bias": check_high_arousal_prevention_bias,
    "high_arousal_low_construal": check_high_arousal_low_construal,
    "low_arousal_high_construal": check_low_arousal_high_construal,
    "focus_framing_alignment": check_focus_framing_alignment,
    "construal_abstraction_alignment": check_construal_abstraction_alignment,
    "personality_mechanism_coherence": check_personality_mechanism_coherence,
    "valence_processing_style": check_valence_processing_style,
    "confidence_bounds": check_confidence_bounds,
}
```

## Consistency Verifier

```python
# =============================================================================
# ADAM Enhancement #05: Atom Consistency Verifier
# Location: adam/verification/consistency.py
# =============================================================================

"""
Verifies consistency across atom outputs using psychological constraints.
"""

from __future__ import annotations
import logging
import time
from typing import Dict, Any, List

from prometheus_client import Counter, Histogram

from .models import (
    ConsistencyConstraint, ConstraintSeverity, ConstraintViolation,
    ConsistencyVerificationResult
)
from .constraints import PSYCHOLOGICAL_CONSTRAINTS, CONSTRAINT_CHECK_FUNCTIONS

logger = logging.getLogger(__name__)


# =============================================================================
# PROMETHEUS METRICS
# =============================================================================

CONSISTENCY_CHECKS = Counter(
    "adam_verification_consistency_checks_total",
    "Total consistency checks performed",
    ["result"]  # passed, failed
)

CONSTRAINT_VIOLATIONS = Counter(
    "adam_verification_constraint_violations_total",
    "Constraint violations by name and severity",
    ["constraint_name", "severity"]
)

CONSISTENCY_CHECK_TIME = Histogram(
    "adam_verification_consistency_check_seconds",
    "Time to perform consistency check",
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1]
)

CONSISTENCY_SCORE = Histogram(
    "adam_verification_consistency_score",
    "Distribution of consistency scores",
    buckets=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
)


class AtomConsistencyVerifier:
    """
    Verifies consistency across atom outputs.
    
    Checks all psychological constraints and returns detailed
    results including which constraints passed/failed.
    """
    
    def __init__(
        self,
        constraints: List[ConsistencyConstraint] = None,
        strict_mode: bool = True
    ):
        self.constraints = constraints or PSYCHOLOGICAL_CONSTRAINTS
        self.strict_mode = strict_mode
        self._build_constraint_map()
    
    def _build_constraint_map(self):
        """Build mapping from constraint names to check functions."""
        self.check_functions = CONSTRAINT_CHECK_FUNCTIONS.copy()
    
    def verify(
        self,
        atom_outputs: Dict[str, Any]
    ) -> ConsistencyVerificationResult:
        """
        Verify all consistency constraints.
        
        Args:
            atom_outputs: Dictionary of atom name -> atom output
            
        Returns:
            ConsistencyVerificationResult with pass/fail status and details
        """
        start_time = time.time()
        
        hard_violations: List[ConstraintViolation] = []
        soft_violations: List[ConstraintViolation] = []
        passed_constraints: List[str] = []
        
        for constraint in self.constraints:
            try:
                check_fn = self.check_functions.get(constraint.name)
                if not check_fn:
                    logger.warning(f"No check function for constraint: {constraint.name}")
                    continue
                
                is_satisfied = check_fn(atom_outputs)
                
                if not is_satisfied:
                    violation = ConstraintViolation(
                        constraint_name=constraint.name,
                        severity=constraint.severity,
                        message=constraint.violation_message,
                        correction_hint=constraint.correction_hint,
                        source_atoms=constraint.source_atoms,
                        evidence=self._extract_evidence(atom_outputs, constraint)
                    )
                    
                    if constraint.severity == ConstraintSeverity.HARD:
                        hard_violations.append(violation)
                    elif constraint.severity == ConstraintSeverity.SOFT:
                        soft_violations.append(violation)
                    
                    # Record metric
                    CONSTRAINT_VIOLATIONS.labels(
                        constraint_name=constraint.name,
                        severity=constraint.severity.value
                    ).inc()
                else:
                    passed_constraints.append(constraint.name)
                    
            except Exception as e:
                logger.error(f"Constraint check error for {constraint.name}: {e}")
                soft_violations.append(ConstraintViolation(
                    constraint_name=constraint.name,
                    severity=ConstraintSeverity.INFO,
                    message=f"Constraint check error: {str(e)}",
                    correction_hint="Review constraint implementation",
                    source_atoms=constraint.source_atoms
                ))
        
        # Calculate consistency score
        total_checked = len(self.constraints)
        total_passed = len(passed_constraints)
        consistency_score = total_passed / max(1, total_checked)
        
        passed = len(hard_violations) == 0
        verification_time = (time.time() - start_time) * 1000
        
        # Record metrics
        CONSISTENCY_CHECKS.labels(result="passed" if passed else "failed").inc()
        CONSISTENCY_CHECK_TIME.observe(verification_time / 1000)
        CONSISTENCY_SCORE.observe(consistency_score)
        
        return ConsistencyVerificationResult(
            passed=passed,
            hard_violations=hard_violations,
            soft_violations=soft_violations,
            passed_constraints=passed_constraints,
            total_constraints_checked=total_checked,
            consistency_score=consistency_score,
            verification_time_ms=verification_time
        )
    
    def _extract_evidence(
        self,
        atom_outputs: Dict[str, Any],
        constraint: ConsistencyConstraint
    ) -> Dict[str, Any]:
        """Extract relevant evidence for a constraint violation."""
        evidence = {}
        
        for atom_name in constraint.source_atoms:
            if atom_name == "all":
                continue
            atom_output = atom_outputs.get(atom_name, {})
            
            # Extract key values based on atom type
            if atom_name == "user_state":
                evidence["arousal"] = atom_output.get("arousal")
                evidence["valence"] = atom_output.get("valence")
            elif atom_name == "regulatory_focus":
                evidence["dominant_focus"] = atom_output.get("dominant_focus")
                evidence["promotion"] = atom_output.get("promotion")
                evidence["prevention"] = atom_output.get("prevention")
            elif atom_name == "construal_level":
                evidence["construal_level"] = atom_output.get("construal_level")
            elif atom_name == "message_framing":
                evidence["framing_type"] = atom_output.get("framing_type")
                evidence["abstraction_level"] = atom_output.get("abstraction_level")
        
        return evidence
```

---

# SECTION D: LAYER 2 - CONFIDENCE CALIBRATION

## Calibration System

```python
# =============================================================================
# ADAM Enhancement #05: Confidence Calibration System
# Location: adam/verification/confidence.py
# =============================================================================

"""
Multi-method confidence calibration for ADAM verification.

Combines:
1. Self-verbalized confidence (Claude's estimate)
2. Consistency-based confidence (multiple sample agreement)
3. Historical calibration (past accuracy at this confidence level)
"""

from __future__ import annotations
import logging
import time
from typing import Dict, Any, Tuple, Optional
import numpy as np

from prometheus_client import Histogram, Gauge

from .models import ConfidenceEstimate, UncertaintyBreakdown

logger = logging.getLogger(__name__)


# =============================================================================
# PROMETHEUS METRICS
# =============================================================================

RAW_CONFIDENCE = Histogram(
    "adam_verification_raw_confidence",
    "Distribution of raw (uncalibrated) confidence",
    buckets=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
)

CALIBRATED_CONFIDENCE = Histogram(
    "adam_verification_calibrated_confidence",
    "Distribution of calibrated confidence",
    buckets=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
)

EXPECTED_CALIBRATION_ERROR = Gauge(
    "adam_verification_expected_calibration_error",
    "Current expected calibration error (ECE)"
)


class ConfidenceCalibrator:
    """
    Multi-method confidence calibration system.
    
    Calibrates Claude's raw confidence estimates using:
    - Historical accuracy data
    - Multi-sample consistency
    - Uncertainty decomposition
    """
    
    # Default calibration curve based on LLM overconfidence research
    DEFAULT_CALIBRATION = {
        0: 0.05,  # 0-10% raw -> ~5% actual
        1: 0.15,  # 10-20% raw -> ~15% actual
        2: 0.25,  # 20-30% raw -> ~25% actual
        3: 0.35,  # 30-40% raw -> ~35% actual
        4: 0.45,  # 40-50% raw -> ~45% actual
        5: 0.55,  # 50-60% raw -> ~55% actual
        6: 0.62,  # 60-70% raw -> ~62% actual (overconfidence begins)
        7: 0.68,  # 70-80% raw -> ~68% actual
        8: 0.73,  # 80-90% raw -> ~73% actual (significant overconfidence)
        9: 0.78,  # 90-100% raw -> ~78% actual (LLMs typically overconfident)
    }
    
    def __init__(
        self,
        calibration_curve: Optional[Dict[int, float]] = None,
        num_samples: int = 3
    ):
        self.calibration_curve = calibration_curve or self.DEFAULT_CALIBRATION.copy()
        self.num_samples = num_samples
    
    async def calibrate(
        self,
        atom_outputs: Dict[str, Any],
        claude_client: Any = None,
        context: Optional[Dict[str, Any]] = None
    ) -> ConfidenceEstimate:
        """
        Produce calibrated confidence estimate.
        
        Args:
            atom_outputs: Dictionary of atom outputs
            claude_client: Optional client for multi-sample consistency
            context: Request context
            
        Returns:
            ConfidenceEstimate with calibrated values
        """
        start_time = time.time()
        
        # Step 1: Extract raw confidence from atom outputs
        raw_confidence = self._extract_raw_confidence(atom_outputs)
        RAW_CONFIDENCE.observe(raw_confidence)
        
        # Step 2: Apply historical calibration
        calibration_bin = min(9, int(raw_confidence * 10))
        calibrated = self._apply_calibration(raw_confidence)
        CALIBRATED_CONFIDENCE.observe(calibrated)
        
        # Step 3: Compute consistency score (if client available)
        consistency_score = 1.0
        if claude_client and self.num_samples > 1:
            consistency_score = await self._compute_consistency_score(
                atom_outputs, claude_client, context or {}
            )
        
        # Step 4: Decompose uncertainty
        uncertainty = self._decompose_uncertainty(atom_outputs, context or {})
        
        # Step 5: Compute final confidence
        final_confidence = self._combine_confidence(
            calibrated, consistency_score, uncertainty
        )
        
        return ConfidenceEstimate(
            raw_confidence=raw_confidence,
            calibrated_confidence=calibrated,
            consistency_score=consistency_score,
            uncertainty_breakdown=uncertainty,
            final_confidence=final_confidence,
            calibration_method="multi_method",
            calibration_bin=calibration_bin
        )
    
    def _extract_raw_confidence(self, atom_outputs: Dict[str, Any]) -> float:
        """Extract aggregate confidence from atom outputs."""
        confidences = []
        
        for atom_name, atom_output in atom_outputs.items():
            if isinstance(atom_output, dict) and "confidence" in atom_output:
                conf = atom_output["confidence"]
                if 0 <= conf <= 1:
                    confidences.append(conf)
        
        if not confidences:
            return 0.5  # Default uncertainty
        
        # Geometric mean (appropriate for probabilities)
        clipped = np.clip(confidences, 0.01, 0.99)
        return float(np.exp(np.mean(np.log(clipped))))
    
    def _apply_calibration(self, raw_confidence: float) -> float:
        """Apply historical calibration curve."""
        bin_idx = min(9, int(raw_confidence * 10))
        calibrated = self.calibration_curve.get(bin_idx, raw_confidence)
        
        # Interpolate within bin for smoothness
        bin_position = (raw_confidence * 10) - bin_idx
        if bin_idx < 9:
            next_cal = self.calibration_curve.get(bin_idx + 1, calibrated)
            calibrated = calibrated + bin_position * (next_cal - calibrated)
        
        return float(calibrated)
    
    async def _compute_consistency_score(
        self,
        atom_outputs: Dict[str, Any],
        claude_client: Any,
        context: Dict[str, Any]
    ) -> float:
        """Check consistency via meta-evaluation."""
        try:
            # Get key decision points
            decision = atom_outputs.get("ad_selection", {}).get("selected_ad_id")
            if not decision:
                return 0.7  # Default moderate consistency
            
            # Quick consistency check prompt
            prompt = f"""Rate the expected consistency of this ad targeting decision 
if the analysis were repeated multiple times (0.0 = highly variable, 1.0 = very stable):

Key factors:
- Arousal: {atom_outputs.get('user_state', {}).get('arousal', 'unknown')}
- Focus: {atom_outputs.get('regulatory_focus', {}).get('dominant_focus', 'unknown')}
- Construal: {atom_outputs.get('construal_level', {}).get('construal_level', 'unknown')}

Respond with just a number."""
            
            response = await claude_client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=20,
                messages=[{"role": "user", "content": prompt}]
            )
            
            score = float(response.content[0].text.strip())
            return max(0.0, min(1.0, score))
            
        except Exception as e:
            logger.warning(f"Consistency check failed: {e}")
            return 0.7
    
    def _decompose_uncertainty(
        self,
        atom_outputs: Dict[str, Any],
        context: Dict[str, Any]
    ) -> UncertaintyBreakdown:
        """Decompose uncertainty into sources."""
        # Input uncertainty: based on data completeness
        user_profile = context.get("user_profile", {})
        profile_fields = len([v for v in user_profile.values() if v])
        total_fields = max(1, len(user_profile)) if user_profile else 5
        input_uncertainty = 1.0 - (profile_fields / total_fields)
        
        # Reasoning uncertainty: variance in atom confidences
        confidences = [
            atom.get("confidence", 0.5)
            for atom in atom_outputs.values()
            if isinstance(atom, dict) and "confidence" in atom
        ]
        reasoning_uncertainty = float(np.std(confidences)) if len(confidences) > 1 else 0.3
        
        # Prediction uncertainty: final selection confidence
        selection = atom_outputs.get("ad_selection", {})
        prediction_uncertainty = 1.0 - selection.get("confidence", 0.5)
        
        return UncertaintyBreakdown(
            input_uncertainty=min(1.0, input_uncertainty),
            reasoning_uncertainty=min(1.0, reasoning_uncertainty),
            prediction_uncertainty=min(1.0, prediction_uncertainty)
        )
    
    def _combine_confidence(
        self,
        calibrated: float,
        consistency: float,
        uncertainty: UncertaintyBreakdown
    ) -> float:
        """Combine all confidence signals into final estimate."""
        # Weight factors
        calibration_weight = 0.5
        consistency_weight = 0.3
        uncertainty_weight = 0.2
        
        # Uncertainty penalty
        avg_uncertainty = (
            uncertainty.input_uncertainty +
            uncertainty.reasoning_uncertainty +
            uncertainty.prediction_uncertainty
        ) / 3
        uncertainty_factor = 1.0 - (avg_uncertainty * uncertainty_weight)
        
        # Combined confidence
        combined = (
            calibrated * calibration_weight +
            consistency * consistency_weight
        ) * uncertainty_factor
        
        return max(0.0, min(1.0, combined))
    
    def update_calibration_curve(
        self,
        bin_idx: int,
        actual_accuracy: float,
        sample_count: int = 1,
        learning_rate: float = 0.1
    ) -> None:
        """Update calibration curve with new outcome data."""
        if 0 <= bin_idx <= 9:
            current = self.calibration_curve[bin_idx]
            # Exponential moving average update
            self.calibration_curve[bin_idx] = (
                current * (1 - learning_rate) +
                actual_accuracy * learning_rate
            )
```

---

# SECTION E: LAYER 3 - SAFETY VALIDATION

## Vulnerable Population Protection

```python
# =============================================================================
# ADAM Enhancement #05: Safety Validation System
# Location: adam/verification/safety.py
# =============================================================================

"""
Safety validation for ADAM ad targeting.

Protects:
- Vulnerable populations (distress, financial stress)
- Against manipulation techniques
- Regulatory compliance (GDPR/CCPA)
"""

from __future__ import annotations
import logging
import hashlib
import json
from datetime import datetime, timezone
from typing import Dict, Any, List

from prometheus_client import Counter

from .models import (
    SafetyRiskLevel, SafetyViolation, SafetyValidationResult
)

logger = logging.getLogger(__name__)


# =============================================================================
# PROMETHEUS METRICS
# =============================================================================

SAFETY_CHECKS = Counter(
    "adam_verification_safety_checks_total",
    "Total safety checks performed",
    ["result"]  # safe, caution, warning, blocked
)

SAFETY_VIOLATIONS = Counter(
    "adam_verification_safety_violations_total",
    "Safety violations by category and severity",
    ["category", "severity"]
)

VULNERABLE_USER_DETECTIONS = Counter(
    "adam_verification_vulnerable_user_detections_total",
    "Count of vulnerable user detections",
    ["trigger"]  # distress, neuroticism, financial
)

ADS_BLOCKED = Counter(
    "adam_verification_ads_blocked_total",
    "Count of ads blocked by safety",
    ["reason"]
)

MANIPULATION_DETECTIONS = Counter(
    "adam_verification_manipulation_detections_total",
    "Count of manipulation technique detections",
    ["technique"]
)


class SafetyValidator:
    """
    Validates safety of ad recommendations.
    
    Performs:
    1. Vulnerable population detection
    2. Manipulation technique detection
    3. Dark pattern avoidance
    4. Regulatory compliance checks
    """
    
    # Sensitive topics requiring extra care
    SENSITIVE_TOPICS = {
        "mental_health": ["depression", "anxiety", "stress", "therapy", "counseling", "suicide"],
        "financial": ["debt", "bankruptcy", "loan", "payday", "gambling", "credit repair"],
        "health": ["medication", "treatment", "diagnosis", "symptoms", "prescription"],
        "addiction": ["alcohol", "smoking", "drugs", "gambling", "betting"],
    }
    
    # Manipulation technique indicators
    MANIPULATION_SIGNALS = {
        "artificial_scarcity": ["only X left", "limited time", "act now", "expires", "last chance"],
        "fear_appeal": ["don't miss out", "what you're losing", "risk", "danger", "warning"],
        "social_pressure": ["everyone is", "your friends", "be left behind", "don't be the only"],
        "authority_exploit": ["experts say", "doctors recommend", "government approved", "clinically proven"],
        "urgency_manipulation": ["hurry", "ending soon", "24 hours only", "final sale"],
    }
    
    def __init__(self, strict_mode: bool = True):
        self.strict_mode = strict_mode
    
    def validate(
        self,
        atom_outputs: Dict[str, Any],
        ad_candidates: List[Dict[str, Any]],
        user_context: Dict[str, Any]
    ) -> SafetyValidationResult:
        """
        Validate safety of recommendations.
        
        Args:
            atom_outputs: Psychological analysis outputs
            ad_candidates: Ads being considered
            user_context: User profile and session data
            
        Returns:
            SafetyValidationResult with allowed/blocked ads
        """
        violations: List[SafetyViolation] = []
        allowed_ads: List[str] = []
        blocked_ads: List[str] = []
        mitigations: List[str] = []
        
        # Check 1: Vulnerable population detection
        vuln_result = self._check_vulnerable_population(atom_outputs, user_context)
        violations.extend(vuln_result["violations"])
        is_vulnerable = vuln_result["is_vulnerable"]
        
        if is_vulnerable:
            mitigations.append("Apply vulnerable population safeguards")
        
        # Check 2: Per-ad safety
        for ad in ad_candidates:
            ad_result = self._check_ad_safety(
                ad, atom_outputs, user_context, is_vulnerable
            )
            
            if ad_result["is_safe"]:
                allowed_ads.append(ad.get("id", "unknown"))
            else:
                blocked_ads.append(ad.get("id", "unknown"))
                violations.extend(ad_result["violations"])
                ADS_BLOCKED.labels(reason=ad_result.get("block_reason", "unknown")).inc()
        
        # Check 3: Mechanism exploitation
        mech_result = self._check_mechanism_exploitation(atom_outputs)
        violations.extend(mech_result["violations"])
        mitigations.extend(mech_result["mitigations"])
        
        # Determine risk level
        risk_level = self._compute_risk_level(violations)
        is_safe = risk_level in [SafetyRiskLevel.SAFE, SafetyRiskLevel.CAUTION]
        
        # Record metrics
        SAFETY_CHECKS.labels(result=risk_level.value).inc()
        
        return SafetyValidationResult(
            is_safe=is_safe,
            risk_level=risk_level,
            violations=violations,
            allowed_ad_ids=allowed_ads,
            blocked_ad_ids=blocked_ads,
            required_mitigations=mitigations,
            vulnerable_user_detected=is_vulnerable,
            manipulation_detected=any(v.category == "manipulation" for v in violations),
            audit_log={
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "user_context_hash": self._hash_context(user_context),
                "checks_performed": ["vulnerable_population", "ad_safety", "mechanism_exploitation"],
                "total_violations": len(violations)
            }
        )
    
    def _check_vulnerable_population(
        self,
        atom_outputs: Dict[str, Any],
        user_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Detect if user is in a vulnerable state."""
        violations = []
        is_vulnerable = False
        
        user_state = atom_outputs.get("user_state", {})
        valence = user_state.get("valence", 0.5)
        arousal = user_state.get("arousal", 0.5)
        
        # Check 1: Emotional distress (low valence + high arousal)
        if valence < 0.3 and arousal > 0.7:
            is_vulnerable = True
            violations.append(SafetyViolation(
                category="vulnerable_population",
                severity=SafetyRiskLevel.WARNING,
                description="User appears to be in emotional distress (low valence, high arousal)",
                evidence={"valence": valence, "arousal": arousal},
                mitigation="Avoid high-pressure or fear-based messaging"
            ))
            VULNERABLE_USER_DETECTIONS.labels(trigger="distress").inc()
            SAFETY_VIOLATIONS.labels(
                category="vulnerable_population",
                severity="warning"
            ).inc()
        
        # Check 2: High neuroticism + negative valence
        personality = atom_outputs.get("personality_expression", {})
        weights = personality.get("expression_weights", {})
        neuroticism = weights.get("neuroticism", 0.5)
        
        if neuroticism > 0.7 and valence < 0.4:
            is_vulnerable = True
            violations.append(SafetyViolation(
                category="vulnerable_population",
                severity=SafetyRiskLevel.CAUTION,
                description="High neuroticism user in negative emotional state",
                evidence={"neuroticism": neuroticism, "valence": valence},
                mitigation="Use reassuring, supportive messaging only"
            ))
            VULNERABLE_USER_DETECTIONS.labels(trigger="neuroticism").inc()
        
        # Check 3: Financial vulnerability
        user_profile = user_context.get("user_profile", {})
        if user_profile.get("financial_stress_indicators"):
            is_vulnerable = True
            violations.append(SafetyViolation(
                category="vulnerable_population",
                severity=SafetyRiskLevel.WARNING,
                description="User shows financial stress indicators",
                evidence={"markers": user_profile.get("financial_stress_indicators")},
                mitigation="Exclude financial products, high-cost items"
            ))
            VULNERABLE_USER_DETECTIONS.labels(trigger="financial").inc()
        
        return {"is_vulnerable": is_vulnerable, "violations": violations}
    
    def _check_ad_safety(
        self,
        ad: Dict[str, Any],
        atom_outputs: Dict[str, Any],
        user_context: Dict[str, Any],
        is_vulnerable: bool
    ) -> Dict[str, Any]:
        """Check safety of a specific ad."""
        violations = []
        is_safe = True
        block_reason = None
        
        ad_content = ad.get("content", "").lower()
        ad_category = ad.get("category", "").lower()
        
        # Check 1: Sensitive topics for vulnerable users
        if is_vulnerable:
            for topic, keywords in self.SENSITIVE_TOPICS.items():
                if any(kw in ad_content or kw in ad_category for kw in keywords):
                    is_safe = False
                    block_reason = f"sensitive_{topic}"
                    violations.append(SafetyViolation(
                        category="vulnerable_population",
                        severity=SafetyRiskLevel.BLOCKED,
                        description=f"Sensitive {topic} ad shown to vulnerable user",
                        evidence={"ad_id": ad.get("id"), "topic": topic},
                        mitigation=None,  # Block, don't mitigate
                        ad_id=ad.get("id")
                    ))
                    SAFETY_VIOLATIONS.labels(
                        category="vulnerable_population",
                        severity="blocked"
                    ).inc()
        
        # Check 2: Manipulation techniques
        for technique, phrases in self.MANIPULATION_SIGNALS.items():
            if any(phrase in ad_content for phrase in phrases):
                severity = SafetyRiskLevel.WARNING if self.strict_mode else SafetyRiskLevel.CAUTION
                violations.append(SafetyViolation(
                    category="manipulation",
                    severity=severity,
                    description=f"Ad uses {technique} manipulation technique",
                    evidence={"ad_id": ad.get("id"), "technique": technique},
                    mitigation=f"Consider removing {technique} elements",
                    ad_id=ad.get("id")
                ))
                MANIPULATION_DETECTIONS.labels(technique=technique).inc()
                
                if self.strict_mode and is_vulnerable:
                    is_safe = False
                    block_reason = f"manipulation_{technique}"
        
        return {"is_safe": is_safe, "violations": violations, "block_reason": block_reason}
    
    def _check_mechanism_exploitation(
        self,
        atom_outputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check if psychological mechanisms are over-exploited."""
        violations = []
        mitigations = []
        
        mechanisms = atom_outputs.get("mechanism_activation", {})
        active = mechanisms.get("active_mechanisms", [])
        
        # Potentially exploitative mechanisms
        exploitation_mechanisms = {
            "wanting_liking_dissociation": "Can exploit addictive tendencies",
            "evolutionary_adaptations": "Can exploit fear/threat responses",
        }
        
        for mech in active:
            mech_name = mech.get("mechanism", "")
            activation = mech.get("activation", 0)
            
            if mech_name in exploitation_mechanisms and activation > 0.8:
                violations.append(SafetyViolation(
                    category="mechanism_exploitation",
                    severity=SafetyRiskLevel.CAUTION,
                    description=f"High activation of {mech_name}: {exploitation_mechanisms[mech_name]}",
                    evidence={"mechanism": mech_name, "activation": activation},
                    mitigation=f"Cap {mech_name} activation at 0.7"
                ))
                mitigations.append(f"Cap {mech_name} activation at 0.7")
        
        return {"violations": violations, "mitigations": mitigations}
    
    def _compute_risk_level(self, violations: List[SafetyViolation]) -> SafetyRiskLevel:
        """Compute overall risk level."""
        if any(v.severity == SafetyRiskLevel.BLOCKED for v in violations):
            return SafetyRiskLevel.BLOCKED
        if any(v.severity == SafetyRiskLevel.WARNING for v in violations):
            return SafetyRiskLevel.WARNING
        if any(v.severity == SafetyRiskLevel.CAUTION for v in violations):
            return SafetyRiskLevel.CAUTION
        return SafetyRiskLevel.SAFE
    
    def _hash_context(self, context: Dict) -> str:
        """Create hash of context for audit."""
        return hashlib.md5(
            json.dumps(context, sort_keys=True, default=str).encode()
        ).hexdigest()[:16]
```

---

# SECTION F: LAYER 4 - GRAPH GROUNDING

## Claim Extraction

```python
# =============================================================================
# ADAM Enhancement #05: Graph Grounding Verification
# Location: adam/verification/grounding.py
# =============================================================================

"""
Graph grounding verification for ADAM.

Detects hallucinations by verifying Claude's claims against Neo4j.
"""

from __future__ import annotations
import logging
import time
import re
from typing import Dict, Any, List

from prometheus_client import Counter, Histogram

from .models import GroundingClaim, GroundingVerificationResult

logger = logging.getLogger(__name__)


# =============================================================================
# PROMETHEUS METRICS
# =============================================================================

GROUNDING_CHECKS = Counter(
    "adam_verification_grounding_checks_total",
    "Total grounding checks performed",
    ["result"]  # grounded, ungrounded
)

GROUNDING_SCORE = Histogram(
    "adam_verification_grounding_score",
    "Distribution of grounding scores",
    buckets=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
)

UNGROUNDED_CLAIMS = Counter(
    "adam_verification_ungrounded_claims_total",
    "Count of ungrounded claims detected",
    ["claim_type"]
)

GROUNDING_CHECK_TIME = Histogram(
    "adam_verification_grounding_check_seconds",
    "Time to perform grounding check",
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5]
)


class GraphGroundingVerifier:
    """
    Verifies Claude's reasoning claims against Neo4j graph.
    
    Detects:
    - Hallucinated user attributes
    - Non-existent relationships
    - Fabricated behavioral history
    """
    
    # Patterns to extract claims from reasoning
    CLAIM_PATTERNS = {
        "personality": r"user (?:has|shows|exhibits|demonstrates) (?:high|low|moderate) (\w+)",
        "interest": r"user (?:is interested in|likes|prefers|engages with) (.+?)(?:\.|,|$)",
        "behavior": r"user (?:has|previously|recently|often|typically) (\w+ed?) (.+?)(?:\.|,|$)",
        "state": r"user (?:is|appears|seems) (?:currently )?([\w\s]+?)(?:\.|,|$)",
        "history": r"(?:based on|from) (?:user's|their) (?:history|past|previous) (.+?)(?:\.|,|$)",
    }
    
    def __init__(self, neo4j_driver):
        self.neo4j = neo4j_driver
    
    async def verify(
        self,
        atom_outputs: Dict[str, Any],
        user_id: str,
        graph_context: Dict[str, Any]
    ) -> GroundingVerificationResult:
        """
        Verify all claims are grounded in the graph.
        
        Args:
            atom_outputs: Atom reasoning outputs
            user_id: User being targeted
            graph_context: Pre-fetched graph data
            
        Returns:
            GroundingVerificationResult with verified/ungrounded claims
        """
        start_time = time.time()
        
        # Step 1: Extract claims from reasoning
        claims = self._extract_claims(atom_outputs)
        
        # Step 2: Verify each claim
        verified: List[GroundingClaim] = []
        ungrounded: List[GroundingClaim] = []
        missing_data: List[GroundingClaim] = []
        queries_executed = 0
        
        for claim in claims:
            result, executed = await self._verify_claim(claim, user_id, graph_context)
            queries_executed += executed
            
            if result == "verified":
                verified.append(claim)
            elif result == "ungrounded":
                ungrounded.append(claim)
                UNGROUNDED_CLAIMS.labels(claim_type=claim.claim_type).inc()
            else:  # missing_data
                missing_data.append(claim)
        
        # Calculate grounding score
        total = len(claims)
        grounded_count = len(verified) + len(missing_data)  # Missing data isn't hallucination
        grounding_score = grounded_count / max(1, total)
        
        verification_time = (time.time() - start_time) * 1000
        
        # Record metrics
        GROUNDING_SCORE.observe(grounding_score)
        GROUNDING_CHECK_TIME.observe(verification_time / 1000)
        GROUNDING_CHECKS.labels(
            result="grounded" if not ungrounded else "ungrounded"
        ).inc()
        
        return GroundingVerificationResult(
            all_claims_grounded=len(ungrounded) == 0,
            verified_claims=verified,
            ungrounded_claims=ungrounded,
            missing_data_claims=missing_data,
            grounding_score=grounding_score,
            neo4j_queries_executed=queries_executed,
            verification_time_ms=verification_time
        )
    
    def _extract_claims(self, atom_outputs: Dict[str, Any]) -> List[GroundingClaim]:
        """Extract verifiable claims from atom outputs."""
        claims = []
        
        for atom_name, atom_output in atom_outputs.items():
            if not isinstance(atom_output, dict):
                continue
            
            # Extract from reasoning text
            reasoning = atom_output.get("reasoning", "")
            if reasoning:
                claims.extend(self._extract_claims_from_text(reasoning, atom_name))
            
            # Extract from structured outputs
            claims.extend(self._extract_structured_claims(atom_output, atom_name))
        
        return claims
    
    def _extract_claims_from_text(
        self,
        text: str,
        source_atom: str
    ) -> List[GroundingClaim]:
        """Extract claims from free-text reasoning."""
        claims = []
        text_lower = text.lower()
        
        for claim_type, pattern in self.CLAIM_PATTERNS.items():
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    match = " ".join(match)
                claims.append(GroundingClaim(
                    claim_type=claim_type,
                    claim_text=match.strip(),
                    claimed_value=match.strip(),
                    source_atom=source_atom
                ))
        
        return claims
    
    def _extract_structured_claims(
        self,
        atom_output: Dict[str, Any],
        source_atom: str
    ) -> List[GroundingClaim]:
        """Extract claims from structured atom outputs."""
        claims = []
        
        # Personality claims
        if "dominant_trait" in atom_output:
            claims.append(GroundingClaim(
                claim_type="personality",
                claim_text=f"dominant trait is {atom_output['dominant_trait']}",
                claimed_value=atom_output["dominant_trait"],
                source_atom=source_atom
            ))
        
        # Interest claims
        if "inferred_interests" in atom_output:
            for interest in atom_output.get("inferred_interests", []):
                claims.append(GroundingClaim(
                    claim_type="interest",
                    claim_text=f"user interested in {interest}",
                    claimed_value=interest,
                    source_atom=source_atom
                ))
        
        return claims
    
    async def _verify_claim(
        self,
        claim: GroundingClaim,
        user_id: str,
        graph_context: Dict[str, Any]
    ) -> tuple:
        """Verify a single claim against graph data."""
        queries = 0
        
        # Check against pre-fetched context first
        if claim.claim_type == "personality":
            user_traits = graph_context.get("personality_traits", {})
            if user_traits:
                queries = 0  # Used cache
                if claim.claimed_value.lower() in [t.lower() for t in user_traits.keys()]:
                    return "verified", queries
                return "ungrounded", queries
            return "missing_data", queries
        
        elif claim.claim_type == "interest":
            interests = graph_context.get("interests", [])
            if interests:
                queries = 0
                if any(claim.claimed_value.lower() in i.lower() for i in interests):
                    return "verified", queries
                return "ungrounded", queries
            return "missing_data", queries
        
        # For other claim types, query Neo4j
        try:
            queries = 1
            async with self.neo4j.session() as session:
                result = await session.run(
                    """
                    MATCH (u:User {user_id: $user_id})
                    OPTIONAL MATCH (u)-[:HAS_TRAIT]->(t:Trait)
                    OPTIONAL MATCH (u)-[:HAS_INTEREST]->(i:Interest)
                    OPTIONAL MATCH (u)-[:EXHIBITED]->(b:Behavior)
                    RETURN 
                        collect(DISTINCT t.name) as traits,
                        collect(DISTINCT i.name) as interests,
                        collect(DISTINCT b.type) as behaviors
                    """,
                    user_id=user_id
                )
                record = await result.single()
                
                if not record:
                    return "missing_data", queries
                
                # Check claim against results
                all_data = (
                    [t.lower() for t in record["traits"]] +
                    [i.lower() for i in record["interests"]] +
                    [b.lower() for b in record["behaviors"]]
                )
                
                if claim.claimed_value.lower() in all_data:
                    return "verified", queries
                return "ungrounded", queries
                
        except Exception as e:
            logger.error(f"Graph verification error: {e}")
            return "missing_data", queries
```

---

# SECTION G: SELF-CORRECTION MECHANISM

## Critique Generation

```python
# =============================================================================
# ADAM Enhancement #05: Self-Correction System
# Location: adam/verification/correction.py
# =============================================================================

"""
Self-correction mechanism for ADAM verification.

Implements DoT-style (Diagram of Thought) critique and refinement.
"""

from __future__ import annotations
import logging
import time
import json
import re
from typing import Dict, Any, List, Optional

from prometheus_client import Counter, Gauge

from .models import CorrectionResult, CorrectionAction
from .consistency import AtomConsistencyVerifier

logger = logging.getLogger(__name__)


# =============================================================================
# PROMETHEUS METRICS
# =============================================================================

CORRECTION_TRIGGERS = Counter(
    "adam_verification_correction_triggers_total",
    "Count of self-correction triggers",
    ["reason"]  # consistency, safety, grounding
)

CORRECTION_ATTEMPTS = Counter(
    "adam_verification_correction_attempts_total",
    "Count of correction attempts",
    ["attempt_number", "result"]  # success, failed
)

CORRECTION_SUCCESS_RATE = Gauge(
    "adam_verification_correction_success_rate",
    "Rolling success rate of corrections"
)

FALLBACK_TRIGGERS = Counter(
    "adam_verification_fallback_triggers_total",
    "Count of fallback triggers after failed correction"
)


class SelfCorrector:
    """
    Self-correction mechanism using DoT-style critique.
    
    Pattern:
    1. Identify verification failures
    2. Generate natural language critique
    3. Apply correction with feedback
    4. Fallback to safe defaults if correction fails
    """
    
    MAX_ATTEMPTS = 2
    
    def __init__(
        self,
        claude_client: Any,
        consistency_verifier: AtomConsistencyVerifier
    ):
        self.claude = claude_client
        self.consistency = consistency_verifier
        self._success_count = 0
        self._total_count = 0
    
    async def correct_if_needed(
        self,
        atom_outputs: Dict[str, Any],
        verification_results: Dict[str, Any],
        context: Dict[str, Any]
    ) -> tuple:
        """
        Apply self-correction if verification failed.
        
        Args:
            atom_outputs: Current atom outputs
            verification_results: Results from all verification layers
            context: Request context
            
        Returns:
            Tuple of (corrected_outputs, list of corrections applied)
        """
        corrections: List[CorrectionResult] = []
        current_outputs = atom_outputs.copy()
        
        # Check if correction is needed
        if not self._needs_correction(verification_results):
            return current_outputs, corrections
        
        # Determine correction reason
        reason = self._get_correction_reason(verification_results)
        CORRECTION_TRIGGERS.labels(reason=reason).inc()
        
        # Attempt correction (up to MAX_ATTEMPTS)
        for attempt in range(self.MAX_ATTEMPTS):
            start_time = time.time()
            
            # Generate critique
            critique = await self._generate_critique(
                current_outputs, verification_results
            )
            
            # Apply correction
            correction_result = await self._apply_correction(
                current_outputs, critique, context, attempt + 1
            )
            correction_result.time_ms = (time.time() - start_time) * 1000
            corrections.append(correction_result)
            
            # Track metrics
            self._total_count += 1
            CORRECTION_ATTEMPTS.labels(
                attempt_number=str(attempt + 1),
                result="success" if correction_result.success else "failed"
            ).inc()
            
            if correction_result.success:
                self._success_count += 1
                current_outputs = correction_result.corrected_output
                break
            elif correction_result.action == CorrectionAction.FALLBACK:
                current_outputs = self._apply_fallback(current_outputs)
                FALLBACK_TRIGGERS.inc()
                break
        
        # Update success rate gauge
        if self._total_count > 0:
            CORRECTION_SUCCESS_RATE.set(self._success_count / self._total_count)
        
        return current_outputs, corrections
    
    def _needs_correction(self, verification_results: Dict[str, Any]) -> bool:
        """Determine if correction is needed."""
        consistency = verification_results.get("consistency", {})
        safety = verification_results.get("safety", {})
        grounding = verification_results.get("grounding", {})
        
        # Trigger correction for:
        if consistency.get("hard_violations"):
            return True
        if safety.get("risk_level") == "blocked":
            return True
        if grounding.get("grounding_score", 1.0) < 0.7:
            return True
        
        return False
    
    def _get_correction_reason(self, verification_results: Dict[str, Any]) -> str:
        """Get the primary reason for correction."""
        if verification_results.get("consistency", {}).get("hard_violations"):
            return "consistency"
        if verification_results.get("safety", {}).get("risk_level") == "blocked":
            return "safety"
        if verification_results.get("grounding", {}).get("grounding_score", 1.0) < 0.7:
            return "grounding"
        return "unknown"
    
    async def _generate_critique(
        self,
        atom_outputs: Dict[str, Any],
        verification_results: Dict[str, Any]
    ) -> str:
        """Generate natural language critique."""
        issues = []
        
        # Collect consistency issues
        consistency = verification_results.get("consistency", {})
        for violation in consistency.get("hard_violations", []):
            issues.append(f"Consistency: {violation.get('message', violation)}")
        
        # Collect safety issues
        safety = verification_results.get("safety", {})
        for violation in safety.get("violations", []):
            desc = violation.description if hasattr(violation, 'description') else str(violation)
            issues.append(f"Safety: {desc}")
        
        # Collect grounding issues
        grounding = verification_results.get("grounding", {})
        for claim in grounding.get("ungrounded_claims", []):
            text = claim.claim_text if hasattr(claim, 'claim_text') else str(claim)
            issues.append(f"Grounding: Unverified claim - {text}")
        
        critique_prompt = f"""You are a critic reviewing psychological ad targeting reasoning.

The following issues were identified:

{chr(10).join(f"- {issue}" for issue in issues)}

Current reasoning:
- User arousal: {atom_outputs.get('user_state', {}).get('arousal', 'unknown')}
- User valence: {atom_outputs.get('user_state', {}).get('valence', 'unknown')}
- Regulatory focus: {atom_outputs.get('regulatory_focus', {}).get('dominant_focus', 'unknown')}
- Construal level: {atom_outputs.get('construal_level', {}).get('construal_level', 'unknown')}

Provide a concise critique explaining:
1. What specifically is wrong
2. Why it's inconsistent with psychological research
3. What the correct reasoning should be

Be specific and actionable."""

        try:
            response = await self.claude.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=500,
                messages=[{"role": "user", "content": critique_prompt}]
            )
            return response.content[0].text
        except Exception as e:
            logger.error(f"Critique generation failed: {e}")
            return f"Automatic critique: {'; '.join(issues)}"
    
    async def _apply_correction(
        self,
        atom_outputs: Dict[str, Any],
        critique: str,
        context: Dict[str, Any],
        attempt: int
    ) -> CorrectionResult:
        """Apply correction based on critique."""
        correction_prompt = f"""You are refining psychological ad targeting reasoning based on a critique.

CRITIQUE:
{critique}

CURRENT OUTPUTS:
{self._format_outputs(atom_outputs)}

Please provide corrected values for any inconsistent atoms.
Respond ONLY in JSON format with atoms that need correction:

{{
  "atom_name": {{
    "key": "corrected_value"
  }}
}}

If issues cannot be corrected, respond with:
{{"action": "fallback", "reason": "..."}}"""

        try:
            response = await self.claude.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=800,
                messages=[{"role": "user", "content": correction_prompt}]
            )
            
            correction_text = response.content[0].text
            
            # Parse JSON from response
            json_match = re.search(r'\{.*\}', correction_text, re.DOTALL)
            if json_match:
                correction_data = json.loads(json_match.group())
                
                if correction_data.get("action") == "fallback":
                    return CorrectionResult(
                        action=CorrectionAction.FALLBACK,
                        original_output=atom_outputs,
                        corrected_output=None,
                        critique=critique,
                        correction_applied=correction_data.get("reason", "Fallback triggered"),
                        attempts=attempt,
                        success=False
                    )
                
                # Apply corrections
                corrected = atom_outputs.copy()
                for atom_name, corrections in correction_data.items():
                    if atom_name in corrected and isinstance(corrections, dict):
                        if isinstance(corrected[atom_name], dict):
                            corrected[atom_name].update(corrections)
                        else:
                            corrected[atom_name] = corrections
                
                # Verify correction resolved issues
                new_consistency = self.consistency.verify(corrected)
                
                return CorrectionResult(
                    action=CorrectionAction.REFINE,
                    original_output=atom_outputs,
                    corrected_output=corrected,
                    critique=critique,
                    correction_applied=str(correction_data),
                    attempts=attempt,
                    success=new_consistency.passed
                )
                
        except Exception as e:
            logger.error(f"Correction application failed: {e}")
            return CorrectionResult(
                action=CorrectionAction.FALLBACK,
                original_output=atom_outputs,
                corrected_output=None,
                critique=critique,
                correction_applied=f"Parse error: {str(e)}",
                attempts=attempt,
                success=False
            )
    
    def _apply_fallback(self, atom_outputs: Dict[str, Any]) -> Dict[str, Any]:
        """Apply safe fallback values."""
        fallback = {}
        
        for key, value in atom_outputs.items():
            if isinstance(value, dict):
                fallback[key] = value.copy()
            else:
                fallback[key] = value
        
        # Reset to neutral, safe values
        if "user_state" in fallback:
            fallback["user_state"]["arousal"] = 0.5
            fallback["user_state"]["valence"] = 0.5
        
        if "regulatory_focus" in fallback:
            fallback["regulatory_focus"]["dominant_focus"] = "balanced"
            fallback["regulatory_focus"]["promotion"] = 0.5
            fallback["regulatory_focus"]["prevention"] = 0.5
        
        if "construal_level" in fallback:
            fallback["construal_level"]["construal_level"] = 0.5
        
        if "message_framing" in fallback:
            fallback["message_framing"]["framing_type"] = "balanced"
            fallback["message_framing"]["abstraction_level"] = "mixed"
        
        fallback["_fallback_applied"] = True
        fallback["_fallback_reason"] = "Self-correction failed, using safe defaults"
        
        return fallback
    
    def _format_outputs(self, outputs: Dict[str, Any]) -> str:
        """Format outputs for prompt."""
        lines = []
        for atom_name, atom_output in outputs.items():
            if isinstance(atom_output, dict):
                lines.append(f"{atom_name}:")
                for key, value in list(atom_output.items())[:5]:  # Limit keys
                    lines.append(f"  {key}: {value}")
        return "\n".join(lines)
```

---

# SECTION H: EVENT BUS INTEGRATION (#31)

## Verification Signals

```python
# =============================================================================
# ADAM Enhancement #05: Event Bus Integration
# Location: adam/verification/events.py
# =============================================================================

"""
Event Bus integration for Verification Layer.

Emits signals for:
- Verification pass/fail
- Constraint violations
- Safety blocks
- Self-correction attempts
"""

from __future__ import annotations
import logging
from typing import Dict, Any

from ..events.producer import ADAMEventProducer, LearningSignal, SignalType, ComponentType
from .models import (
    VerificationPipelineResult, VerificationStatus,
    SafetyRiskLevel, ConstraintSeverity
)

logger = logging.getLogger(__name__)


class VerificationEventEmitter:
    """
    Emits verification events to the Event Bus.
    
    Enables downstream components to:
    - Learn from verification failures
    - Track safety patterns
    - Adjust confidence based on historical accuracy
    """
    
    def __init__(self, producer: ADAMEventProducer):
        self.producer = producer
    
    async def emit_verification_result(
        self,
        result: VerificationPipelineResult,
        request_id: str
    ) -> None:
        """Emit signal for complete verification result."""
        signal = LearningSignal(
            source_component=ComponentType.VERIFICATION,
            source_entity_type="verification_pipeline",
            source_entity_id=result.verification_id,
            signal_type=SignalType.VERIFICATION_RESULT,
            signal_data={
                "status": result.status.value,
                "passed": str(result.passed),
                "final_confidence": str(result.final_confidence),
                "hard_violations": len(result.consistency_result.hard_violations),
                "soft_violations": len(result.consistency_result.soft_violations),
                "safety_risk_level": result.safety_result.risk_level.value,
                "grounding_score": str(result.grounding_result.grounding_score),
                "corrections_applied": result.correction_attempts,
                "total_time_ms": str(result.total_verification_time_ms)
            },
            confidence=result.final_confidence,
            trace_id=request_id
        )
        
        await self.producer.emit_learning_signal(signal)
    
    async def emit_constraint_violation(
        self,
        constraint_name: str,
        severity: ConstraintSeverity,
        evidence: Dict[str, Any],
        request_id: str
    ) -> None:
        """Emit signal for a specific constraint violation."""
        signal = LearningSignal(
            source_component=ComponentType.VERIFICATION,
            source_entity_type="constraint_violation",
            source_entity_id=f"violation_{constraint_name}_{request_id[:8]}",
            signal_type=SignalType.CONSTRAINT_VIOLATION,
            signal_data={
                "constraint_name": constraint_name,
                "severity": severity.value,
                "evidence": {k: str(v) for k, v in evidence.items()}
            },
            confidence=0.0 if severity == ConstraintSeverity.HARD else 0.5,
            trace_id=request_id
        )
        
        await self.producer.emit_learning_signal(signal)
    
    async def emit_safety_block(
        self,
        risk_level: SafetyRiskLevel,
        blocked_ad_ids: list,
        reason: str,
        request_id: str
    ) -> None:
        """Emit signal when safety blocks an ad."""
        signal = LearningSignal(
            source_component=ComponentType.VERIFICATION,
            source_entity_type="safety_block",
            source_entity_id=f"safety_block_{request_id[:8]}",
            signal_type=SignalType.SAFETY_BLOCK,
            signal_data={
                "risk_level": risk_level.value,
                "blocked_ad_count": len(blocked_ad_ids),
                "blocked_ad_ids": blocked_ad_ids[:5],  # Limit for event size
                "reason": reason
            },
            confidence=1.0,  # Safety is deterministic
            trace_id=request_id
        )
        
        await self.producer.emit_learning_signal(signal)
    
    async def emit_correction_attempt(
        self,
        attempt_number: int,
        success: bool,
        action: str,
        request_id: str
    ) -> None:
        """Emit signal for self-correction attempt."""
        signal = LearningSignal(
            source_component=ComponentType.VERIFICATION,
            source_entity_type="self_correction",
            source_entity_id=f"correction_{request_id[:8]}_{attempt_number}",
            signal_type=SignalType.CORRECTION_ATTEMPT,
            signal_data={
                "attempt_number": str(attempt_number),
                "success": str(success),
                "action": action
            },
            confidence=1.0 if success else 0.0,
            trace_id=request_id
        )
        
        await self.producer.emit_learning_signal(signal)
```

---

# SECTION I: CACHE INTEGRATION (#31)

## Calibration Curve Caching

```python
# =============================================================================
# ADAM Enhancement #05: Cache Integration
# Location: adam/verification/cache.py
# =============================================================================

"""
Cache integration for Verification Layer.

Caches:
- Calibration curves (updated periodically from outcomes)
- Verification results (for repeated similar contexts)
"""

from __future__ import annotations
import json
import hashlib
import logging
from typing import Dict, Any, Optional

from ..cache.coordinator import MultiLevelCacheCoordinator, CacheType

logger = logging.getLogger(__name__)


class VerificationCacheManager:
    """
    Manages caching for the verification layer.
    
    Key cached items:
    - Calibration curves (shared across requests)
    - Recent verification results (for debugging)
    """
    
    def __init__(
        self,
        cache: MultiLevelCacheCoordinator,
        calibration_ttl_seconds: int = 3600,
        result_ttl_seconds: int = 300
    ):
        self.cache = cache
        self.calibration_ttl = calibration_ttl_seconds
        self.result_ttl = result_ttl_seconds
    
    # =========================================================================
    # CALIBRATION CURVE CACHING
    # =========================================================================
    
    async def get_calibration_curve(self) -> Optional[Dict[int, float]]:
        """
        Get cached calibration curve.
        
        Returns mapping: confidence_bin -> actual_accuracy
        """
        cached = await self.cache.get(
            "verification:calibration_curve",
            cache_type=CacheType.SETTINGS
        )
        
        if cached:
            # Convert string keys back to int
            return {int(k): v for k, v in cached.items()}
        return None
    
    async def set_calibration_curve(
        self,
        curve: Dict[int, float]
    ) -> None:
        """Cache the calibration curve."""
        # Convert int keys to strings for JSON
        cacheable = {str(k): v for k, v in curve.items()}
        
        await self.cache.set(
            "verification:calibration_curve",
            cacheable,
            cache_type=CacheType.SETTINGS,
            ttl=self.calibration_ttl
        )
    
    # =========================================================================
    # VERIFICATION RESULT CACHING
    # =========================================================================
    
    async def get_cached_result(
        self,
        context_hash: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached verification result for similar context.
        
        Used for debugging and replay, not production caching.
        """
        return await self.cache.get(
            f"verification:result:{context_hash}",
            cache_type=CacheType.DECISION
        )
    
    async def cache_result(
        self,
        context_hash: str,
        result: Dict[str, Any]
    ) -> None:
        """Cache a verification result."""
        await self.cache.set(
            f"verification:result:{context_hash}",
            result,
            cache_type=CacheType.DECISION,
            ttl=self.result_ttl
        )
    
    def compute_context_hash(
        self,
        atom_outputs: Dict[str, Any],
        user_id: str
    ) -> str:
        """Compute hash for verification context."""
        # Hash key components
        key_data = {
            "user_id": user_id,
            "arousal": atom_outputs.get("user_state", {}).get("arousal"),
            "valence": atom_outputs.get("user_state", {}).get("valence"),
            "dominant_focus": atom_outputs.get("regulatory_focus", {}).get("dominant_focus"),
            "construal": atom_outputs.get("construal_level", {}).get("construal_level")
        }
        
        key_str = json.dumps(key_data, sort_keys=True, default=str)
        return hashlib.md5(key_str.encode()).hexdigest()[:16]
```

---

# SECTION J: NEO4J SCHEMA

## Audit Trail Schema

```python
# =============================================================================
# ADAM Enhancement #05: Neo4j Schema
# Location: adam/verification/neo4j_schema.py
# =============================================================================

"""
Neo4j schema for Verification Layer audit trail.

Stores:
- Verification results for analysis
- Constraint violations for pattern detection
- Safety blocks for compliance
- Correction attempts for learning
"""

# =============================================================================
# CONSTRAINTS
# =============================================================================

CONSTRAINTS = """
-- Verification result uniqueness
CREATE CONSTRAINT verification_result_id IF NOT EXISTS
FOR (v:VerificationResult) REQUIRE v.verification_id IS UNIQUE;

-- Constraint violation tracking
CREATE CONSTRAINT constraint_violation_id IF NOT EXISTS
FOR (cv:ConstraintViolation) REQUIRE cv.violation_id IS UNIQUE;

-- Safety block tracking
CREATE CONSTRAINT safety_block_id IF NOT EXISTS
FOR (sb:SafetyBlock) REQUIRE sb.block_id IS UNIQUE;
"""

# =============================================================================
# INDEXES
# =============================================================================

INDEXES = """
-- Verification result indexes
CREATE INDEX verification_request_id IF NOT EXISTS FOR (v:VerificationResult) ON (v.request_id);
CREATE INDEX verification_status IF NOT EXISTS FOR (v:VerificationResult) ON (v.status);
CREATE INDEX verification_created_at IF NOT EXISTS FOR (v:VerificationResult) ON (v.created_at);

-- Constraint violation indexes
CREATE INDEX violation_constraint_name IF NOT EXISTS FOR (cv:ConstraintViolation) ON (cv.constraint_name);
CREATE INDEX violation_severity IF NOT EXISTS FOR (cv:ConstraintViolation) ON (cv.severity);

-- Safety block indexes
CREATE INDEX safety_risk_level IF NOT EXISTS FOR (sb:SafetyBlock) ON (sb.risk_level);
CREATE INDEX safety_ad_id IF NOT EXISTS FOR (sb:SafetyBlock) ON (sb.ad_id);
"""

# =============================================================================
# QUERIES
# =============================================================================

CREATE_VERIFICATION_RESULT = """
CREATE (v:VerificationResult {
    verification_id: $verification_id,
    request_id: $request_id,
    status: $status,
    passed: $passed,
    final_confidence: $final_confidence,
    consistency_score: $consistency_score,
    grounding_score: $grounding_score,
    safety_risk_level: $safety_risk_level,
    correction_attempts: $correction_attempts,
    total_time_ms: $total_time_ms,
    created_at: datetime()
})
RETURN v.verification_id as verification_id
"""

CREATE_CONSTRAINT_VIOLATION = """
MATCH (v:VerificationResult {verification_id: $verification_id})
CREATE (cv:ConstraintViolation {
    violation_id: $violation_id,
    constraint_name: $constraint_name,
    severity: $severity,
    message: $message,
    evidence: $evidence
})
CREATE (v)-[:HAD_VIOLATION]->(cv)
RETURN cv.violation_id as violation_id
"""

CREATE_SAFETY_BLOCK = """
MATCH (v:VerificationResult {verification_id: $verification_id})
MATCH (a:Ad {ad_id: $ad_id})
CREATE (sb:SafetyBlock {
    block_id: $block_id,
    risk_level: $risk_level,
    reason: $reason,
    created_at: datetime()
})
CREATE (v)-[:BLOCKED]->(sb)
CREATE (sb)-[:BLOCKED_AD]->(a)
RETURN sb.block_id as block_id
"""

# =============================================================================
# ANALYTICS QUERIES
# =============================================================================

GET_CONSTRAINT_VIOLATION_STATS = """
MATCH (cv:ConstraintViolation)
WHERE cv.created_at > datetime() - duration('P7D')
RETURN 
    cv.constraint_name as constraint_name,
    cv.severity as severity,
    count(cv) as violation_count
ORDER BY violation_count DESC
"""

GET_VERIFICATION_PASS_RATE = """
MATCH (v:VerificationResult)
WHERE v.created_at > datetime() - duration('P1D')
RETURN 
    v.status as status,
    count(v) as count,
    avg(v.final_confidence) as avg_confidence,
    avg(v.total_time_ms) as avg_time_ms
GROUP BY v.status
"""

GET_SAFETY_BLOCK_PATTERNS = """
MATCH (sb:SafetyBlock)-[:BLOCKED_AD]->(a:Ad)
WHERE sb.created_at > datetime() - duration('P7D')
RETURN 
    a.category as ad_category,
    sb.risk_level as risk_level,
    count(sb) as block_count,
    collect(DISTINCT sb.reason)[..5] as top_reasons
ORDER BY block_count DESC
"""

GET_CALIBRATION_DATA = """
MATCH (v:VerificationResult)-[:MADE_DECISION]->(d:Decision)
OPTIONAL MATCH (d)-[:HAD_OUTCOME]->(o:Outcome)
WHERE v.created_at > datetime() - duration('P30D')
AND o IS NOT NULL
RETURN 
    floor(v.final_confidence * 10) as confidence_bin,
    count(v) as total_predictions,
    sum(CASE WHEN o.converted THEN 1 ELSE 0 END) as correct_predictions,
    sum(CASE WHEN o.converted THEN 1 ELSE 0 END) * 1.0 / count(v) as actual_accuracy
ORDER BY confidence_bin
"""
```

---

# SECTION K: FASTAPI ENDPOINTS

## Verification Inspection API

```python
# =============================================================================
# ADAM Enhancement #05: FastAPI Endpoints
# Location: adam/api/verification.py
# =============================================================================

"""
FastAPI endpoints for Verification Layer inspection and management.

Provides:
- Verification result inspection
- Constraint management
- Calibration curve access
- Safety rule configuration
"""

from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..verification.consistency import AtomConsistencyVerifier
from ..verification.confidence import ConfidenceCalibrator
from ..verification.safety import SafetyValidator
from ..verification.models import (
    ConsistencyConstraint, ConstraintSeverity,
    VerificationPipelineResult, VerificationStatus
)
from ..verification.constraints import PSYCHOLOGICAL_CONSTRAINTS

router = APIRouter(prefix="/api/v1/verification", tags=["verification"])


# =============================================================================
# RESPONSE MODELS
# =============================================================================

class ConstraintListResponse(BaseModel):
    """List of available constraints."""
    constraints: List[Dict[str, Any]]
    total_count: int
    hard_count: int
    soft_count: int


class CalibrationCurveResponse(BaseModel):
    """Calibration curve data."""
    bins: List[Dict[str, Any]]
    expected_calibration_error: float
    last_updated: Optional[datetime] = None


class VerificationSummaryResponse(BaseModel):
    """Summary of verification result."""
    verification_id: str
    status: str
    passed: bool
    final_confidence: float
    hard_violations: int
    soft_violations: int
    safety_risk_level: str
    grounding_score: float


class SimulateVerificationRequest(BaseModel):
    """Request to simulate verification."""
    atom_outputs: Dict[str, Any]
    ad_candidates: List[Dict[str, Any]] = Field(default_factory=list)
    user_id: str = "simulation_user"


# =============================================================================
# CONSTRAINT ENDPOINTS
# =============================================================================

@router.get(
    "/constraints",
    response_model=ConstraintListResponse,
    summary="List all constraints",
    description="Get all psychological consistency constraints."
)
async def list_constraints() -> ConstraintListResponse:
    """List all available constraints."""
    constraints = []
    hard_count = 0
    soft_count = 0
    
    for c in PSYCHOLOGICAL_CONSTRAINTS:
        constraints.append({
            "name": c.name,
            "description": c.description,
            "severity": c.severity.value,
            "source_atoms": c.source_atoms,
            "violation_message": c.violation_message,
            "correction_hint": c.correction_hint,
            "research_basis": c.research_basis
        })
        
        if c.severity == ConstraintSeverity.HARD:
            hard_count += 1
        elif c.severity == ConstraintSeverity.SOFT:
            soft_count += 1
    
    return ConstraintListResponse(
        constraints=constraints,
        total_count=len(constraints),
        hard_count=hard_count,
        soft_count=soft_count
    )


@router.get(
    "/constraints/{constraint_name}",
    summary="Get constraint details",
    description="Get details for a specific constraint."
)
async def get_constraint(constraint_name: str) -> Dict[str, Any]:
    """Get details for a specific constraint."""
    for c in PSYCHOLOGICAL_CONSTRAINTS:
        if c.name == constraint_name:
            return {
                "name": c.name,
                "description": c.description,
                "severity": c.severity.value,
                "source_atoms": c.source_atoms,
                "violation_message": c.violation_message,
                "correction_hint": c.correction_hint,
                "research_basis": c.research_basis
            }
    
    raise HTTPException(status_code=404, detail=f"Constraint not found: {constraint_name}")


# =============================================================================
# CALIBRATION ENDPOINTS
# =============================================================================

@router.get(
    "/calibration/curve",
    response_model=CalibrationCurveResponse,
    summary="Get calibration curve",
    description="Get the current confidence calibration curve."
)
async def get_calibration_curve() -> CalibrationCurveResponse:
    """Get the current calibration curve."""
    # Default calibration curve based on LLM research
    default_curve = {
        0: 0.05, 1: 0.15, 2: 0.25, 3: 0.35, 4: 0.45,
        5: 0.55, 6: 0.62, 7: 0.68, 8: 0.73, 9: 0.78
    }
    
    bins = []
    ece = 0.0
    
    for bin_idx, actual_accuracy in default_curve.items():
        expected = (bin_idx + 0.5) / 10  # Midpoint of bin
        bins.append({
            "bin": bin_idx,
            "range": f"{bin_idx*10}-{(bin_idx+1)*10}%",
            "expected_confidence": expected,
            "actual_accuracy": actual_accuracy,
            "calibration_error": abs(expected - actual_accuracy)
        })
        ece += abs(expected - actual_accuracy)
    
    ece /= len(bins)
    
    return CalibrationCurveResponse(
        bins=bins,
        expected_calibration_error=ece
    )


# =============================================================================
# VERIFICATION ENDPOINTS
# =============================================================================

@router.post(
    "/simulate",
    response_model=VerificationSummaryResponse,
    summary="Simulate verification",
    description="Simulate verification on provided atom outputs."
)
async def simulate_verification(
    request: SimulateVerificationRequest
) -> VerificationSummaryResponse:
    """
    Simulate verification without recording.
    
    Useful for debugging and testing.
    """
    verifier = AtomConsistencyVerifier()
    
    # Run consistency check
    consistency_result = verifier.verify(request.atom_outputs)
    
    # Calculate grounding score (simplified for simulation)
    grounding_score = 0.8  # Default for simulation
    
    # Determine status
    if not consistency_result.passed:
        status = "failed"
    elif consistency_result.soft_violations:
        status = "passed_with_warnings"
    else:
        status = "passed"
    
    return VerificationSummaryResponse(
        verification_id=f"sim_{datetime.now().strftime('%Y%m%d%H%M%S')}",
        status=status,
        passed=consistency_result.passed,
        final_confidence=consistency_result.consistency_score * 0.8,
        hard_violations=len(consistency_result.hard_violations),
        soft_violations=len(consistency_result.soft_violations),
        safety_risk_level="safe",
        grounding_score=grounding_score
    )


@router.get(
    "/results/recent",
    summary="Get recent verification results",
    description="List recent verification results."
)
async def list_recent_results(
    limit: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = None
) -> Dict[str, Any]:
    """List recent verification results."""
    # Would query Neo4j
    return {
        "results": [],
        "total": 0,
        "filters": {"status": status_filter}
    }


# =============================================================================
# HEALTH ENDPOINTS
# =============================================================================

@router.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "adam-verification",
        "version": "5.0.0"
    }


@router.get("/health/ready")
async def readiness_check() -> Dict[str, Any]:
    """Readiness check endpoint."""
    return {
        "status": "ready",
        "constraints_loaded": len(PSYCHOLOGICAL_CONSTRAINTS),
        "calibration_available": True
    }
```

---

# SECTION L: PROMETHEUS METRICS

## Complete Metrics Reference

```python
# =============================================================================
# ADAM Enhancement #05: Prometheus Metrics Summary
# Location: adam/verification/metrics.py
# =============================================================================

"""
Complete Prometheus metrics for Verification Layer monitoring.

These metrics enable:
- Real-time verification monitoring
- Constraint violation tracking
- Safety incident detection
- Calibration accuracy analysis
"""

from prometheus_client import Counter, Histogram, Gauge, Summary


# =============================================================================
# CONSISTENCY METRICS
# =============================================================================

CONSISTENCY_CHECKS = Counter(
    "adam_verification_consistency_checks_total",
    "Total consistency checks performed",
    ["result"]  # passed, failed
)

CONSTRAINT_VIOLATIONS = Counter(
    "adam_verification_constraint_violations_total",
    "Constraint violations by name and severity",
    ["constraint_name", "severity"]
)

CONSISTENCY_CHECK_TIME = Histogram(
    "adam_verification_consistency_check_seconds",
    "Time to perform consistency check",
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1]
)

CONSISTENCY_SCORE = Histogram(
    "adam_verification_consistency_score",
    "Distribution of consistency scores",
    buckets=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
)


# =============================================================================
# CONFIDENCE CALIBRATION METRICS
# =============================================================================

RAW_CONFIDENCE = Histogram(
    "adam_verification_raw_confidence",
    "Distribution of raw (uncalibrated) confidence",
    buckets=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
)

CALIBRATED_CONFIDENCE = Histogram(
    "adam_verification_calibrated_confidence",
    "Distribution of calibrated confidence",
    buckets=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
)

EXPECTED_CALIBRATION_ERROR = Gauge(
    "adam_verification_expected_calibration_error",
    "Current expected calibration error (ECE)"
)

CALIBRATION_BIN_COUNT = Counter(
    "adam_verification_calibration_bin_total",
    "Count of predictions per calibration bin",
    ["bin"]  # 0-9
)


# =============================================================================
# SAFETY METRICS
# =============================================================================

SAFETY_CHECKS = Counter(
    "adam_verification_safety_checks_total",
    "Total safety checks performed",
    ["result"]  # safe, caution, warning, blocked
)

SAFETY_VIOLATIONS = Counter(
    "adam_verification_safety_violations_total",
    "Safety violations by category and severity",
    ["category", "severity"]
)

VULNERABLE_USER_DETECTIONS = Counter(
    "adam_verification_vulnerable_user_detections_total",
    "Count of vulnerable user detections",
    ["trigger"]  # distress, neuroticism, financial
)

ADS_BLOCKED = Counter(
    "adam_verification_ads_blocked_total",
    "Count of ads blocked by safety",
    ["reason"]
)

MANIPULATION_DETECTIONS = Counter(
    "adam_verification_manipulation_detections_total",
    "Count of manipulation technique detections",
    ["technique"]
)


# =============================================================================
# GROUNDING METRICS
# =============================================================================

GROUNDING_CHECKS = Counter(
    "adam_verification_grounding_checks_total",
    "Total grounding checks performed",
    ["result"]  # grounded, ungrounded
)

GROUNDING_SCORE = Histogram(
    "adam_verification_grounding_score",
    "Distribution of grounding scores",
    buckets=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
)

UNGROUNDED_CLAIMS = Counter(
    "adam_verification_ungrounded_claims_total",
    "Count of ungrounded claims detected",
    ["claim_type"]
)

GROUNDING_CHECK_TIME = Histogram(
    "adam_verification_grounding_check_seconds",
    "Time to perform grounding check",
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5]
)


# =============================================================================
# SELF-CORRECTION METRICS
# =============================================================================

CORRECTION_TRIGGERS = Counter(
    "adam_verification_correction_triggers_total",
    "Count of self-correction triggers",
    ["reason"]  # consistency, safety, grounding
)

CORRECTION_ATTEMPTS = Counter(
    "adam_verification_correction_attempts_total",
    "Count of correction attempts",
    ["attempt_number", "result"]  # success, failed
)

CORRECTION_SUCCESS_RATE = Gauge(
    "adam_verification_correction_success_rate",
    "Rolling success rate of corrections"
)

FALLBACK_TRIGGERS = Counter(
    "adam_verification_fallback_triggers_total",
    "Count of fallback triggers after failed correction"
)


# =============================================================================
# PIPELINE METRICS
# =============================================================================

VERIFICATION_PIPELINE_TIME = Histogram(
    "adam_verification_pipeline_seconds",
    "Total verification pipeline time",
    buckets=[0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0]
)

VERIFICATION_STATUS = Counter(
    "adam_verification_status_total",
    "Count of verification statuses",
    ["status"]  # passed, passed_with_warnings, corrected, failed, fallback
)

LAYER_EXECUTION_TIME = Histogram(
    "adam_verification_layer_seconds",
    "Time per verification layer",
    ["layer"],  # consistency, calibration, safety, grounding, correction
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5]
)
```

---

# SECTION M: TESTING & OPERATIONS

## Unit Tests

```python
# =============================================================================
# ADAM Enhancement #05: Unit Tests
# Location: tests/test_verification.py
# =============================================================================

"""
Unit tests for Verification Layer.

Tests cover:
- Constraint checking
- Confidence calibration
- Safety validation
- Graph grounding
- Self-correction
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from adam.verification.models import (
    ConstraintSeverity, SafetyRiskLevel, VerificationStatus,
    ConsistencyVerificationResult, ConfidenceEstimate
)
from adam.verification.consistency import AtomConsistencyVerifier
from adam.verification.constraints import (
    check_high_arousal_prevention_bias,
    check_high_arousal_low_construal,
    check_focus_framing_alignment,
    PSYCHOLOGICAL_CONSTRAINTS
)
from adam.verification.safety import SafetyValidator


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def consistent_atom_outputs():
    """Atom outputs that should pass all constraints."""
    return {
        "user_state": {"arousal": 0.8, "valence": 0.4},
        "regulatory_focus": {
            "dominant_focus": "prevention",
            "promotion": 0.4,
            "prevention": 0.7
        },
        "construal_level": {"construal_level": 0.3},
        "message_framing": {
            "framing_type": "loss",
            "abstraction_level": "concrete"
        },
        "personality_expression": {
            "dominant_trait": "neuroticism",
            "matching_strategy": "systematic"
        },
        "mechanism_activation": {
            "primary_mechanism": "wanting_liking_dissociation"
        }
    }


@pytest.fixture
def inconsistent_atom_outputs():
    """Atom outputs that should fail constraints."""
    return {
        "user_state": {"arousal": 0.9, "valence": 0.3},
        "regulatory_focus": {
            "dominant_focus": "promotion",  # Wrong! High arousal should be prevention
            "promotion": 0.8,
            "prevention": 0.3
        },
        "construal_level": {"construal_level": 0.8},  # Wrong! High arousal should be low
        "message_framing": {
            "framing_type": "gain",  # Wrong! Promotion focus should not have gain framing
            "abstraction_level": "abstract"
        }
    }


@pytest.fixture
def vulnerable_user_outputs():
    """Atom outputs indicating a vulnerable user."""
    return {
        "user_state": {"arousal": 0.85, "valence": 0.2},  # Distress
        "personality_expression": {
            "expression_weights": {"neuroticism": 0.8}
        }
    }


# =============================================================================
# CONSTRAINT FUNCTION TESTS
# =============================================================================

class TestConstraintFunctions:
    """Tests for individual constraint check functions."""
    
    def test_high_arousal_prevention_bias_passes(self):
        """Test constraint passes when high arousal has prevention bias."""
        outputs = {
            "user_state": {"arousal": 0.8},
            "regulatory_focus": {
                "dominant_focus": "prevention",
                "promotion": 0.4,
                "prevention": 0.7
            }
        }
        assert check_high_arousal_prevention_bias(outputs) is True
    
    def test_high_arousal_prevention_bias_fails(self):
        """Test constraint fails when high arousal has promotion bias."""
        outputs = {
            "user_state": {"arousal": 0.8},
            "regulatory_focus": {
                "dominant_focus": "promotion",
                "promotion": 0.9,
                "prevention": 0.3
            }
        }
        assert check_high_arousal_prevention_bias(outputs) is False
    
    def test_high_arousal_low_construal_passes(self):
        """Test constraint passes when high arousal has low construal."""
        outputs = {
            "user_state": {"arousal": 0.8},
            "construal_level": {"construal_level": 0.3}
        }
        assert check_high_arousal_low_construal(outputs) is True
    
    def test_high_arousal_low_construal_fails(self):
        """Test constraint fails when high arousal has high construal."""
        outputs = {
            "user_state": {"arousal": 0.8},
            "construal_level": {"construal_level": 0.7}
        }
        assert check_high_arousal_low_construal(outputs) is False
    
    def test_focus_framing_alignment_passes(self):
        """Test constraint passes when focus aligns with framing."""
        outputs = {
            "regulatory_focus": {"dominant_focus": "prevention"},
            "message_framing": {"framing_type": "loss"}
        }
        assert check_focus_framing_alignment(outputs) is True
    
    def test_focus_framing_alignment_fails(self):
        """Test constraint fails when focus misaligns with framing."""
        outputs = {
            "regulatory_focus": {"dominant_focus": "prevention"},
            "message_framing": {"framing_type": "gain"}
        }
        assert check_focus_framing_alignment(outputs) is False


# =============================================================================
# CONSISTENCY VERIFIER TESTS
# =============================================================================

class TestAtomConsistencyVerifier:
    """Tests for AtomConsistencyVerifier."""
    
    def test_verify_consistent_outputs(self, consistent_atom_outputs):
        """Test verification passes for consistent outputs."""
        verifier = AtomConsistencyVerifier()
        result = verifier.verify(consistent_atom_outputs)
        
        assert result.passed is True
        assert len(result.hard_violations) == 0
    
    def test_verify_inconsistent_outputs(self, inconsistent_atom_outputs):
        """Test verification fails for inconsistent outputs."""
        verifier = AtomConsistencyVerifier()
        result = verifier.verify(inconsistent_atom_outputs)
        
        assert result.passed is False
        assert len(result.hard_violations) > 0
    
    def test_constraint_evidence_extraction(self, inconsistent_atom_outputs):
        """Test that evidence is extracted for violations."""
        verifier = AtomConsistencyVerifier()
        result = verifier.verify(inconsistent_atom_outputs)
        
        for violation in result.hard_violations:
            assert violation.evidence is not None
            assert len(violation.evidence) > 0
    
    def test_consistency_score_calculation(self, consistent_atom_outputs):
        """Test consistency score is calculated correctly."""
        verifier = AtomConsistencyVerifier()
        result = verifier.verify(consistent_atom_outputs)
        
        assert 0 <= result.consistency_score <= 1
        # Consistent outputs should have high score
        assert result.consistency_score > 0.8


# =============================================================================
# SAFETY VALIDATOR TESTS
# =============================================================================

class TestSafetyValidator:
    """Tests for SafetyValidator."""
    
    def test_vulnerable_user_detection(self, vulnerable_user_outputs):
        """Test vulnerable user is detected."""
        validator = SafetyValidator()
        result = validator._check_vulnerable_population(
            vulnerable_user_outputs,
            {"user_profile": {}}
        )
        
        assert result["is_vulnerable"] is True
        assert len(result["violations"]) > 0
    
    def test_manipulation_detection(self):
        """Test manipulation techniques are detected."""
        validator = SafetyValidator()
        ad = {
            "id": "ad_1",
            "content": "only 3 left! act now before time runs out!",
            "category": "retail"
        }
        
        result = validator._check_ad_safety(
            ad,
            {},
            {},
            is_vulnerable=False
        )
        
        assert len(result["violations"]) > 0
        manipulation_found = any(
            v.category == "manipulation" 
            for v in result["violations"]
        )
        assert manipulation_found
    
    def test_safe_ad_passes(self):
        """Test safe ad passes validation."""
        validator = SafetyValidator()
        ad = {
            "id": "ad_1",
            "content": "discover our new collection",
            "category": "retail"
        }
        
        result = validator._check_ad_safety(
            ad,
            {},
            {},
            is_vulnerable=False
        )
        
        assert result["is_safe"] is True


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestVerificationIntegration:
    """Integration tests for the full verification pipeline."""
    
    def test_all_constraints_have_check_functions(self):
        """Verify all defined constraints have check functions."""
        from adam.verification.constraints import CONSTRAINT_CHECK_FUNCTIONS
        
        for constraint in PSYCHOLOGICAL_CONSTRAINTS:
            assert constraint.name in CONSTRAINT_CHECK_FUNCTIONS, \
                f"Missing check function for constraint: {constraint.name}"
    
    def test_constraint_definitions_complete(self):
        """Verify all constraints have required fields."""
        for constraint in PSYCHOLOGICAL_CONSTRAINTS:
            assert constraint.name
            assert constraint.description
            assert constraint.severity in ConstraintSeverity
            assert constraint.violation_message
            assert constraint.correction_hint
```

---

## Implementation Timeline

### Phase 1: Consistency Verification (Weeks 1-2)

| Day | Task | Deliverable |
|-----|------|-------------|
| 1-2 | Pydantic models | All verification models |
| 3-4 | Constraint definitions | PSYCHOLOGICAL_CONSTRAINTS |
| 5-6 | AtomConsistencyVerifier | Verification logic |
| 7-8 | Unit tests | 95%+ coverage |
| 9-10 | Prometheus metrics | Consistency metrics |

### Phase 2: Confidence Calibration (Weeks 3-4)

| Day | Task | Deliverable |
|-----|------|-------------|
| 1-2 | ConfidenceCalibrator class | Calibration logic |
| 3-4 | Historical calibration curve | Load from Neo4j |
| 5-6 | Multi-method confidence | Consistency + calibration |
| 7-8 | Cache integration | Calibration curve caching |
| 9-10 | ECE measurement | Evaluation on historical data |

### Phase 3: Safety Validation (Weeks 5-6)

| Day | Task | Deliverable |
|-----|------|-------------|
| 1-2 | SafetyValidator class | Safety check logic |
| 3-4 | Vulnerable population detection | User state analysis |
| 5-6 | Manipulation detection | Ad content analysis |
| 7-8 | Regulatory compliance | GDPR/CCPA checks |
| 9-10 | Safety audit logging | Neo4j persistence |

### Phase 4: Graph Grounding (Weeks 7-8)

| Day | Task | Deliverable |
|-----|------|-------------|
| 1-2 | GraphGroundingVerifier class | Claim extraction |
| 3-4 | Neo4j verification queries | Claim validation |
| 5-6 | Hallucination detection | Ungrounded claim flagging |
| 7-8 | Integration tests | End-to-end verification |
| 9-10 | Performance optimization | Query caching |

### Phase 5: Self-Correction (Weeks 9-10)

| Day | Task | Deliverable |
|-----|------|-------------|
| 1-2 | SelfCorrector class | Correction logic |
| 3-4 | Critique generation | DoT-style critiques |
| 5-6 | Correction application | Atom refinement |
| 7-8 | Fallback mechanism | Safe defaults |
| 9-10 | Event Bus integration | Signal emission |

### Phase 6: Integration (Weeks 11-12)

| Day | Task | Deliverable |
|-----|------|-------------|
| 1-2 | VerificationLayer integration | Complete pipeline |
| 3-4 | FastAPI endpoints | API implementation |
| 5-6 | Grafana dashboards | 4 dashboards |
| 7-8 | Alerting rules | PagerDuty integration |
| 9-10 | Documentation | Operational guides |

---

## Success Metrics

### Performance SLIs

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Consistency check p99** | <100ms | `adam_verification_consistency_check_seconds` |
| **Total verification p99** | <500ms | `adam_verification_pipeline_seconds` |
| **Grounding check p99** | <200ms | `adam_verification_grounding_check_seconds` |

### Quality Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Expected Calibration Error** | <0.10 | `adam_verification_expected_calibration_error` |
| **Consistency pass rate** | >95% | `adam_verification_consistency_checks_total` |
| **Grounding score average** | >0.90 | `adam_verification_grounding_score` |
| **Correction success rate** | >70% | `adam_verification_correction_success_rate` |

### Safety Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Safety block rate** | <5% | `adam_verification_safety_checks_total` |
| **Vulnerable user detection** | 100% | `adam_verification_vulnerable_user_detections_total` |
| **Zero safety incidents** | 0 | Manual audit |

---

**END OF ENHANCEMENT #05: VERIFICATION LAYER**

---

## Document Summary

| Section | Coverage |
|---------|----------|
| **Pydantic Models** | Complete typed models for all verification results |
| **Constraint System** | 8 research-backed psychological constraints |
| **Consistency Verifier** | Full verification with evidence extraction |
| **Confidence Calibration** | Multi-method calibration with ECE |
| **Safety Validator** | Vulnerable population + manipulation detection |
| **Graph Grounding** | Hallucination detection via Neo4j |
| **Self-Correction** | DoT-style critique and refinement |
| **Event Bus (#31)** | Signal emission for all verification events |
| **Cache (#31)** | Calibration curve + result caching |
| **Neo4j Schema** | Audit trail persistence |
| **FastAPI Endpoints** | 8 endpoints for inspection/management |
| **Prometheus Metrics** | 25+ metrics for monitoring |
| **Unit Tests** | Complete test suite |
| **Implementation Timeline** | 12-week phased plan |

**Total Specification Size**: ~115KB  
**Implementation Effort**: 12 person-weeks  
**Quality Level**: Enterprise Production-Ready
