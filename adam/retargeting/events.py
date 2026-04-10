# =============================================================================
# Therapeutic Retargeting Engine — Kafka Event Schemas
# Location: adam/retargeting/events.py
# Spec: Enhancement #33, Section F.3
# =============================================================================

"""
Kafka event topic definitions for the Therapeutic Retargeting Engine.

7 topics cover the full lifecycle of a retargeting sequence:
diagnosis → touch creation → delivery → outcome → sequence completion →
rupture detection → site scoring.
"""

KAFKA_TOPICS = {
    "retargeting.barrier.diagnosed": {
        "schema": "ConversionBarrierDiagnosis",
        "consumers": ["mechanism_selector", "dashboard", "learning_pipeline"],
        "description": "Emitted when a barrier diagnosis is produced for a user.",
    },
    "retargeting.touch.created": {
        "schema": "TherapeuticTouch",
        "consumers": ["creative_generator", "delivery_engine", "dashboard"],
        "description": "Emitted when a new therapeutic touch is built.",
    },
    "retargeting.touch.delivered": {
        "schema": "TherapeuticTouch + delivery_metadata",
        "consumers": ["outcome_observer", "reactance_tracker"],
        "description": "Emitted when a touch is actually served to the user.",
    },
    "retargeting.outcome.observed": {
        "schema": "BarrierResolutionOutcome",
        "consumers": ["prior_updater", "gradient_bridge", "dashboard"],
        "description": "Emitted when an outcome (click, conversion, ignore) is observed.",
    },
    "retargeting.sequence.completed": {
        "schema": "SequenceLearningReport",
        "consumers": ["bayesian_hierarchy", "cross_archetype_transfer"],
        "description": "Emitted when a sequence ends (converted, suppressed, exhausted).",
    },
    "retargeting.rupture.detected": {
        "schema": "RuptureAssessment",
        "consumers": ["repair_strategy_selector", "dashboard"],
        "description": "Emitted when a rupture is detected in an active sequence.",
    },
    "retargeting.site.scored": {
        "schema": "SitePsychologicalProfile",
        "consumers": ["whitelist_generator", "neo4j_writer"],
        "description": "Emitted when a site is psychologically profiled.",
    },
}
