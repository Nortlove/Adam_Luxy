# =============================================================================
# ADAM Therapeutic Retargeting Engine — Enhancement #33
# Location: adam/retargeting/
# =============================================================================

"""
Therapeutic Retargeting Engine

Clinical psychology-grade retargeting system built on 16 academic research
domains. Diagnoses WHY a specific person did not convert at a mechanistic
level, selects the academically-validated intervention most likely to resolve
that specific barrier, and learns from the outcome.

Core components:
- Barrier Diagnostic Engine: bilateral edge → barrier diagnosis
- Stage Classifier: behavioral signals → TTM-derived conversion stage
- Mechanism Selector: Thompson Sampling per (mechanism, barrier, archetype)
- Rupture Detector: engagement decay → repair strategy
- Sequence Orchestrator: adaptive decision tree (not linear sequence)
- Narrative Arc Builder: 5-chapter episodic story structure
- Claude Argument Engine: LLM-generated factual arguments
- Learning Loop: outcome → Bayesian posterior update → Gradient Bridge

Integration points:
- OutcomeHandler step 13: barrier-conditioned posterior updates
- DecisionContext: barrier/sequence fields for outcome attribution
- Bilateral Cascade: optional barrier diagnosis at L3+
- CopyGenerationService: delegates to ClaudeArgumentEngine
- Event Bus: 7 Kafka topics for retargeting events
- Redis: RETARGETING cache domain for diagnoses, sequences, priors
"""
