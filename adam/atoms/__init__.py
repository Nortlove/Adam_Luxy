# =============================================================================
# ADAM Atom of Thought DAG (#04)
# =============================================================================

"""
ATOM OF THOUGHT DAG

Multi-source intelligence fusion architecture for psychological reasoning.

The Atom of Thought DAG implements structured reasoning patterns where each
atom synthesizes evidence from 10 intelligence sources before making assessments.

Core Atoms:
- UserStateAtom: Current psychological state assessment
- RegulatoryFocusAtom: Promotion vs prevention orientation
- ConstrualLevelAtom: Abstract vs concrete thinking
- PersonalityExpressionAtom: Big Five expression in context
- MechanismActivationAtom: Which mechanisms to activate
- MessageFramingAtom: How to frame the message
- AdSelectionAtom: Final ad selection

Each atom:
1. Queries all relevant intelligence sources in parallel
2. Detects conflicts between sources
3. Presents multi-source evidence to Claude for integration
4. Captures synthesis as new knowledge
5. Emits learning signals for all sources
"""

from adam.atoms.models.evidence import (
    IntelligenceEvidence,
    MultiSourceEvidence,
    EvidenceConflict,
    FusionResult,
)
from adam.atoms.models.atom_io import (
    AtomInput,
    AtomOutput,
    AtomConfig,
)
from adam.atoms.core.base import BaseAtom
from adam.atoms.core.user_state import UserStateAtom
from adam.atoms.core.regulatory_focus import RegulatoryFocusAtom
from adam.atoms.core.construal_level import ConstrualLevelAtom
from adam.atoms.core.personality_expression import PersonalityExpressionAtom
from adam.atoms.core.mechanism_activation import MechanismActivationAtom
from adam.atoms.core.message_framing import MessageFramingAtom
from adam.atoms.core.ad_selection import AdSelectionAtom
from adam.atoms.dag import AtomDAG

__all__ = [
    # Models
    "IntelligenceEvidence",
    "MultiSourceEvidence",
    "EvidenceConflict",
    "FusionResult",
    "AtomInput",
    "AtomOutput",
    "AtomConfig",
    # Core Atoms (7 atoms per spec)
    "BaseAtom",
    "UserStateAtom",
    "RegulatoryFocusAtom",
    "ConstrualLevelAtom",
    "PersonalityExpressionAtom",
    "MechanismActivationAtom",
    "MessageFramingAtom",
    "AdSelectionAtom",
    # DAG
    "AtomDAG",
]
