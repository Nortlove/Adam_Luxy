# =============================================================================
# ADAM C4 (REDUCED) — HumanDeviation Log-and-Tag
# Location: adam/intelligence/deviation_lifecycle.py
# =============================================================================

"""HumanDeviation log-and-tag substrate.

Per `docs/CLAUDE_CODE_DIRECTIVE_FULL_BUILD.md` Section 8.1, the full
adjudication pipeline this module previously contained has been CUT.
The directive's reasoning: at pilot N the verdict machinery cannot
produce defensible adjudications without M2 counterfactual estimates,
and M2 itself is moving offline. Adjudication-without-M2 is theatre.

What remains: the **log-and-tag** capability. The platform records
that a partner override happened, attaches a categorical reason tag,
emits the A14 calibration-pending flag, and stops there. No verdict
machinery, no horizon scheduling, no thresholds, no
DeviationAdjudication record.

The recorded HumanDeviation entries flow as inputs to the offline
pipeline (Spine #12) where they may inform mechanism-discovery.
That's where the value lives — not in real-time adjudication.

Decision-time consumer (Rule A check): NONE at decision time. This
module produces records that the offline pipeline reads. Justified
under the same Markov-blanket separation as Spine #12 — slow brain
inputs, no serving-path coupling.
"""

from __future__ import annotations

import logging
from typing import List

from adam.intelligence.dialogue_ledger.models import HumanDeviation

logger = logging.getLogger(__name__)


# =============================================================================
# A14 flag constant
# =============================================================================


DEVIATION_LOGGED_FLAG: str = "DEVIATION_LOGGED"


# =============================================================================
# Log-and-tag emission
# =============================================================================


def record_deviation_a14_flag(
    deviation: HumanDeviation,
    atom_id: str = "deviation_lifecycle",
) -> List[str]:
    """Emit DEVIATION_LOGGED flag for a recorded HumanDeviation.

    Increments the Prometheus a14_flag_active counter. Returns the list
    of flags applied (always [DEVIATION_LOGGED] for any recorded
    deviation).
    """
    _increment_a14_counter(atom_id, DEVIATION_LOGGED_FLAG)
    return [DEVIATION_LOGGED_FLAG]


def _increment_a14_counter(atom_id: str, flag: str) -> None:
    """Non-fatal Prometheus counter increment."""
    try:
        from adam.infrastructure.prometheus.metrics import get_metrics
        pm = get_metrics()
        pm.a14_flag_active.labels(atom_id=atom_id, a14_flag=flag).inc()
    except Exception as exc:
        logger.debug("Deviation A14 metric emission failed: %s", exc)


__all__ = [
    "DEVIATION_LOGGED_FLAG",
    "record_deviation_a14_flag",
]
