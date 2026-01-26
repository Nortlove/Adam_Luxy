# =============================================================================
# ADAM Gradient Bridge (#06)
# =============================================================================

"""
GRADIENT BRIDGE - Cross-Component Learning Signals

The central nervous system of ADAM's learning architecture.
Ensures every outcome improves every component.

Key Capabilities:
1. Multi-Level Credit Attribution - Attribute outcomes to atoms
2. Enriched Bandit Features - 40+ psychological features
3. Empirical Priors for Claude - Historical performance injection
4. Graph Learning - User-mechanism effectiveness tracking
5. Real-Time Signal Propagation - <100ms via Kafka

Components:
- CreditAttributor: Multi-method attribution engine
- FeatureExtractor: Extract psychological features from atoms
- SignalOrchestrator: Route learning signals to all components
- PriorInjector: Inject empirical priors into Claude prompts
"""

from adam.gradient_bridge.models.credit import (
    CreditAssignment,
    AtomCredit,
    ComponentCredit,
    OutcomeAttribution,
)
from adam.gradient_bridge.models.signals import (
    LearningSignal,
    SignalPackage,
    ComponentUpdate,
)
from adam.gradient_bridge.models.features import (
    EnrichedFeatureVector,
    AtomFeatures,
    PsychologicalFeatures,
)
from adam.gradient_bridge.attribution import CreditAttributor
from adam.gradient_bridge.service import GradientBridgeService

__all__ = [
    # Credit Models
    "CreditAssignment",
    "AtomCredit",
    "ComponentCredit",
    "OutcomeAttribution",
    # Signal Models
    "LearningSignal",
    "SignalPackage",
    "ComponentUpdate",
    # Feature Models
    "EnrichedFeatureVector",
    "AtomFeatures",
    "PsychologicalFeatures",
    # Core
    "CreditAttributor",
    "GradientBridgeService",
]
