# =============================================================================
# ADAM Dialogue Ledger — Loop B Substrate
# Location: adam/intelligence/dialogue_ledger/
# =============================================================================

"""
DIALOGUE LEDGER — Loop B's structured store of human-machine exchange

Per `ADAM_HUMAN_MACHINE_TEAMING_FOUNDATION.md` §9.2 + §11. The Dialogue
Ledger captures every user-system interaction as typed Neo4j nodes
+ relationships so the teaming loop can:

  1. Treat user assertions as HYPOTHESES (status=hypothesis at capture),
     never as ground truth. HMT discipline rule 12.
  2. Instrument each Claim against an outcome horizon so causal
     adjudication is possible after the horizon completes.
  3. Track per-user-per-domain calibration via Brier scores so user
     confidence can be re-weighted by empirical track record.
  4. Surface validated Why-Library entries at recommendation time as
     pre-emptive defensive reasoning.

Schema migration: `adam/infrastructure/neo4j/migrations/019_dialogue_ledger.cypher`.

This package provides the Python service layer that writes/reads the
schema. The migration must be applied before the service operates;
service writes refuse silently when constraints/indexes are missing
and emit a descriptive error to logs.
"""

from adam.intelligence.dialogue_ledger.elicitation import (
    ElicitationContext,
    ForcedPairGenerator,
    RecallabilityProbeGenerator,
    StoryPromptGenerator,
    TimedPairGenerator,
    all_v01_generators,
)
from adam.intelligence.dialogue_ledger.models import (
    Claim,
    ClaimStatus,
    DialogueDomain,
    DialogueUser,
    ElicitationMode,
    HorizonClass,
    LearningStatus,
    LearningStatusState,
)
from adam.intelligence.dialogue_ledger.mood_probe import (
    MoodProbeGenerator,
    SessionMoodState,
)
from adam.intelligence.dialogue_ledger.service import (
    DialogueLedgerService,
    get_dialogue_ledger_service,
)
from adam.intelligence.dialogue_ledger.uncertainty_panel import (
    UncertaintyBucket,
    UncertaintyPanel,
    render_uncertainty_panel,
)

__all__ = [
    "Claim",
    "ClaimStatus",
    "DialogueDomain",
    "DialogueLedgerService",
    "DialogueUser",
    "ElicitationContext",
    "ElicitationMode",
    "ForcedPairGenerator",
    "HorizonClass",
    "LearningStatus",
    "LearningStatusState",
    "MoodProbeGenerator",
    "RecallabilityProbeGenerator",
    "SessionMoodState",
    "StoryPromptGenerator",
    "TimedPairGenerator",
    "UncertaintyBucket",
    "UncertaintyPanel",
    "all_v01_generators",
    "get_dialogue_ledger_service",
    "render_uncertainty_panel",
]
