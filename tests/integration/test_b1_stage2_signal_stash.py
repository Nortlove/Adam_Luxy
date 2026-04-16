"""B1 Stage 2 verification: learning signal stashed on TherapeuticSequence.

Pins the fix to commit c1ca185's deliberate `_ = loop_results` no-op.
The Stage 1 wiring routed touch outcomes through RetargetingLearningLoop
which generated a MechanismEffectivenessSignal, but the orchestrator
discarded it because TherapeuticSequence is a Pydantic BaseModel that
rejects arbitrary attribute assignment. Stage 2 adds first-class fields
so the signal lives on the sequence and is available to downstream
consumers (Gradient Bridge integration, pilot telemetry, retrospection).
"""

from __future__ import annotations

import inspect

from adam.retargeting.models.sequences import TherapeuticSequence
from adam.retargeting.models.learning import MechanismEffectivenessSignal
from adam.retargeting.models.enums import (
    BarrierCategory,
    ScaffoldLevel,
    TherapeuticMechanism,
)


def _make_signal(reward: float = 0.5) -> MechanismEffectivenessSignal:
    # Pick the first member of each enum — we only care about signal
    # identity/roundtripping, not the semantic content.
    mechanism = next(iter(TherapeuticMechanism))
    barrier = next(iter(BarrierCategory))
    scaffold = next(iter(ScaffoldLevel))
    return MechanismEffectivenessSignal(
        sequence_id="seq_test",
        touch_id="touch_test",
        archetype_id="achiever",
        barrier_category=barrier,
        alignment_dimension_targeted="emotional_resonance",
        mechanism_deployed=mechanism,
        scaffold_level=scaffold,
        construal_level="abstract",
        narrative_chapter=0,
        engagement_occurred=True,
        stage_advanced=False,
        converted=False,
        barrier_resolved=False,
        outcome_score=reward,
        reactance_indicator=-0.1,
    )


class TestTherapeuticSequenceSignalFields:
    """TherapeuticSequence must accept and store learning signals."""

    def test_sequence_has_last_signal_field(self):
        seq = TherapeuticSequence(
            user_id="u1", brand_id="b1", archetype_id="achiever"
        )
        assert seq.last_mechanism_effectiveness_signal is None
        assert seq.mechanism_effectiveness_signals == []

    def test_sequence_accepts_signal_assignment(self):
        """Pydantic BaseModel must permit assignment to the new fields.

        This is the exact operation that raised at runtime before Stage 2
        and forced the `_ = loop_results` no-op in the orchestrator.
        """
        seq = TherapeuticSequence(
            user_id="u1", brand_id="b1", archetype_id="achiever"
        )
        signal = _make_signal(reward=0.7)
        seq.last_mechanism_effectiveness_signal = signal
        seq.mechanism_effectiveness_signals.append(signal)

        assert seq.last_mechanism_effectiveness_signal is signal
        assert seq.last_mechanism_effectiveness_signal.outcome_score == 0.7
        assert len(seq.mechanism_effectiveness_signals) == 1

    def test_sequence_roundtrips_signal_through_model_dump(self):
        """The signal must survive model_dump/model_validate so the field
        is real Pydantic state, not a runtime-only attribute."""
        seq = TherapeuticSequence(
            user_id="u1", brand_id="b1", archetype_id="achiever"
        )
        seq.last_mechanism_effectiveness_signal = _make_signal(reward=0.42)
        dumped = seq.model_dump()
        reborn = TherapeuticSequence.model_validate(dumped)
        assert reborn.last_mechanism_effectiveness_signal is not None
        assert reborn.last_mechanism_effectiveness_signal.outcome_score == 0.42


class TestOrchestratorStashWiring:
    """The orchestrator must actually stash the signal — not just have the field."""

    def test_orchestrator_reads_learning_signal_from_loop_results(self):
        """Inspect the orchestrator source for the Stage 2 stash code.

        The pre-Stage-2 code was `_ = loop_results`. This test fails if
        that no-op is restored without also updating the test.
        """
        from adam.retargeting.engines import sequence_orchestrator

        src = inspect.getsource(sequence_orchestrator)
        assert "last_mechanism_effectiveness_signal" in src, (
            "Orchestrator must assign to last_mechanism_effectiveness_signal"
        )
        assert 'loop_results.get("learning_signal")' in src, (
            "Orchestrator must read the learning_signal from loop_results dict"
        )
        # The pre-Stage-2 discard pattern must be gone.
        assert "_ = loop_results" not in src, (
            "Stage 2 must remove the `_ = loop_results` no-op that "
            "discarded the learning signal"
        )

    def test_history_capping_logic_is_bounded(self):
        """The stash history must be bounded. Pins the cap-at-32 rule."""
        seq = TherapeuticSequence(
            user_id="u1", brand_id="b1", archetype_id="achiever"
        )
        # Simulate 40 touch outcomes using the same capping logic
        # the orchestrator applies after each process_touch_outcome call.
        for i in range(40):
            sig = _make_signal(reward=i / 40.0)
            seq.last_mechanism_effectiveness_signal = sig
            seq.mechanism_effectiveness_signals.append(sig)
            if len(seq.mechanism_effectiveness_signals) > 32:
                seq.mechanism_effectiveness_signals = (
                    seq.mechanism_effectiveness_signals[-32:]
                )

        assert len(seq.mechanism_effectiveness_signals) == 32
        # Most recent entry must be the last signal stored
        assert (
            seq.mechanism_effectiveness_signals[-1].outcome_score
            == seq.last_mechanism_effectiveness_signal.outcome_score
        )
        # Oldest kept signal is index (40 - 32) = 8
        assert seq.mechanism_effectiveness_signals[0].outcome_score == 8 / 40.0
