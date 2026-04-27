"""ADAM core learning — production runtime canonical.

ADAM has FOUR learning-named packages serving distinct roles. This is
the production runtime canonical. Adding new learning code? Add it
here unless one of the other three serves the specific role better.

The four-package landscape (audit 2026-04-27, G1 status doc):

    adam.core.learning (THIS PACKAGE) — production runtime canonical
        ~15 modules: outcome_handler, theory_learner, thompson_warmstart,
        effect_size_correction, atom_learning_integrations,
        construct_learning_loop, etc. Consumed by 50+ production paths
        (cascade, atoms, daily tasks, dashboard).
        ROLE: every learning surface that fires at decision time or
        outcome time lives here.

    adam.learning — thin convenience aggregator
        2 modules + __init__: emergence_engine, mechanism_interactions.
        The __init__ re-exports from adam.coldstart.unified_learning,
        adam.user.cold_start.service, etc. — no real logic of its own.
        Consumed by 3 callers.
        ROLE: convenience namespace for callers wanting one import to
        reach multiple learning surfaces. Do NOT add new logic here;
        it's an aggregator.

    adam.cold_start.learning — cold-start gradient bridge
        1 module + __init__: gradient_bridge.
        Specifically: ColdStartLearningSignal + ColdStartGradientBridge
        for propagating outcomes back into cold-start archetype priors
        when a buyer has insufficient observation history for the main
        learning loop.
        ROLE: cold-start-only learning. Production cold-start path
        depends on this.

    adam.intelligence.learning — offline-script-only
        1 module + __init__: psychological_learning_integration.
        Consumed by FIVE batch/offline scripts only — zero production
        runtime consumers (audit 2026-04-27). Provides
        LearningCapableComponent wrappers for the psychological-
        intelligence modules so corpus-learning scripts can register
        them with the universal learning architecture.
        ROLE: offline corpus learning. NOT a production runtime path.

Drift prevention rule: do NOT create a fifth learning package. If a
new learning surface is needed, file it under whichever of the four
matches its role. The naming overlap is intentional — each package
holds the surfaces appropriate to its lifecycle.

The G2 pattern of 'multiple competing canonicals' (5 construct ontology
files) does NOT apply here — these four packages do NOT duplicate each
other. They differ by lifecycle (runtime vs cold-start vs offline-batch).
"""
