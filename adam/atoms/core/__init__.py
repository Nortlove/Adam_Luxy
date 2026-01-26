# =============================================================================
# ADAM Core Atoms
# =============================================================================

"""
Core atom implementations for psychological reasoning.

The 7 atoms in the DAG:
1. UserStateAtom - Current psychological state
2. RegulatoryFocusAtom - Promotion vs prevention
3. ConstrualLevelAtom - Abstract vs concrete
4. PersonalityExpressionAtom - Big Five expression
5. MechanismActivationAtom - Which mechanisms to activate
6. MessageFramingAtom - How to frame the message
7. AdSelectionAtom - Final ad selection
"""

from adam.atoms.core.base import BaseAtom
from adam.atoms.core.user_state import UserStateAtom
from adam.atoms.core.regulatory_focus import RegulatoryFocusAtom
from adam.atoms.core.construal_level import ConstrualLevelAtom
from adam.atoms.core.personality_expression import PersonalityExpressionAtom
from adam.atoms.core.mechanism_activation import MechanismActivationAtom
from adam.atoms.core.message_framing import MessageFramingAtom
from adam.atoms.core.ad_selection import AdSelectionAtom

__all__ = [
    "BaseAtom",
    "UserStateAtom",
    "RegulatoryFocusAtom",
    "ConstrualLevelAtom",
    "PersonalityExpressionAtom",
    "MechanismActivationAtom",
    "MessageFramingAtom",
    "AdSelectionAtom",
]
