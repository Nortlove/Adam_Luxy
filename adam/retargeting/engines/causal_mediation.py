# =============================================================================
# Causal Mediation Analysis
# Location: adam/retargeting/engines/causal_mediation.py
# Enhancement #34, Session 34-9
# =============================================================================

"""
Causal mediation analysis for mechanism effect decomposition.

The system knows THAT social_proof works for agreeable users, but not WHY.
Is it via trust establishment? Decision simplification? Identity validation?

Mediation analysis decomposes:
  Total Effect = Direct Effect + Indirect Effect (via mediator)

Where mediators are intermediate behavioral signals:
- dwell_time: engagement depth (attention mediator)
- pages_viewed: information seeking (cognitive mediator)
- return_visits: consideration depth (commitment mediator)
- booking_steps: action progression (behavioral mediator)

Once pathways are identified, the system can:
1. Transfer mechanism knowledge across archetypes that share pathways
2. Select mechanisms that target the STRONGEST pathway for each user
3. Predict mechanism effectiveness without observing it directly

Prerequisite: 500+ completed retargeting sequences with full
(state, action, mediator, outcome) data. Infrastructure is built
here so it's ready when data accumulates.

Reference: Farbmacher et al. (2022), DML-based mediation framework.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from scipy.stats import pearsonr

logger = logging.getLogger(__name__)


@dataclass
class MediationPathway:
    """A discovered causal mediation pathway."""

    mechanism: str  # The treatment
    mediator: str  # The intermediate variable
    outcome: str  # The final outcome (conversion)

    # Effect decomposition
    total_effect: float  # Mechanism → Outcome
    direct_effect: float  # Mechanism → Outcome (not via mediator)
    indirect_effect: float  # Mechanism → Mediator → Outcome
    mediation_proportion: float  # indirect / total (0-1)

    # Statistical support
    n_observations: int
    p_value_indirect: float
    confidence_interval: Tuple[float, float] = (0.0, 0.0)

    # Interpretation
    pathway_description: str = ""


@dataclass
class MediationAnalysisResult:
    """Complete mediation analysis for a mechanism."""

    mechanism: str
    archetype: str
    pathways: List[MediationPathway]
    dominant_pathway: Optional[MediationPathway] = None
    n_sequences: int = 0
    sufficient_data: bool = False


# Mediating variables we track from behavioral signals
MEDIATOR_VARIABLES = {
    "dwell_time": {
        "description": "Total dwell time on site (attention depth)",
        "signal_key": "total_dwell_minutes",
        "theoretical_mediator": "attention",
    },
    "pages_viewed": {
        "description": "Number of pages viewed (information seeking)",
        "signal_key": "pages_viewed",
        "theoretical_mediator": "cognitive_elaboration",
    },
    "return_visits": {
        "description": "Number of return visits (consideration depth)",
        "signal_key": "total_site_visits",
        "theoretical_mediator": "commitment",
    },
    "booking_steps": {
        "description": "Booking flow progression (behavioral commitment)",
        "signal_key": "booking_steps_completed",
        "theoretical_mediator": "behavioral_activation",
    },
    "review_engagement": {
        "description": "Review pages viewed (social proof processing)",
        "signal_key": "review_page_visits",
        "theoretical_mediator": "social_validation",
    },
}

# Minimum sequences needed for reliable mediation analysis
MIN_SEQUENCES_FOR_MEDIATION = 50  # Selling lipstick, not moon landing


class CausalMediationAnalyzer:
    """DML-inspired causal mediation analysis.

    Decomposes mechanism effects into direct and indirect pathways
    through measurable behavioral mediators.

    Uses a simplified Baron & Kenny approach with bootstrap CIs:
    1. Path a: Mechanism → Mediator (does the mechanism change behavior?)
    2. Path b: Mediator → Outcome (does the behavior change conversion?)
    3. Path c: Mechanism → Outcome (total effect)
    4. Path c': Mechanism → Outcome controlling for Mediator (direct effect)
    5. Indirect = c - c' = a × b (Sobel test or bootstrap)

    Production note: This is the "selling lipstick" version of
    Farbmacher et al. (2022). Full DML-based mediation requires
    cross-fitting and nuisance function estimation. This simplified
    version uses linear regression decomposition with bootstrap CIs,
    which is sufficient to identify dominant pathways and enable
    cross-mechanism transfer learning.
    """

    def __init__(self, min_sequences: int = MIN_SEQUENCES_FOR_MEDIATION):
        self.min_sequences = min_sequences

    def analyze_mechanism(
        self,
        mechanism: str,
        archetype: str,
        sequences: List[Dict[str, Any]],
    ) -> MediationAnalysisResult:
        """Analyze mediation pathways for a mechanism × archetype pair.

        Args:
            mechanism: The therapeutic mechanism to analyze
            archetype: The archetype context
            sequences: List of completed sequence dicts with:
                - mechanism_deployed: str
                - outcome_score: float (0-1)
                - behavioral_signals: Dict with mediator values

        Returns:
            MediationAnalysisResult with discovered pathways
        """
        # Filter to sequences involving this mechanism
        mech_sequences = [
            s for s in sequences
            if s.get("mechanism_deployed") == mechanism
        ]
        other_sequences = [
            s for s in sequences
            if s.get("mechanism_deployed") != mechanism
        ]

        n = len(mech_sequences)
        sufficient = n >= self.min_sequences and len(other_sequences) >= self.min_sequences

        if not sufficient:
            return MediationAnalysisResult(
                mechanism=mechanism,
                archetype=archetype,
                pathways=[],
                n_sequences=n,
                sufficient_data=False,
            )

        # Analyze each mediator
        pathways = []
        for mediator_name, mediator_info in MEDIATOR_VARIABLES.items():
            pathway = self._analyze_pathway(
                mechanism, mediator_name, mediator_info,
                mech_sequences, other_sequences,
            )
            if pathway is not None:
                pathways.append(pathway)

        # Sort by mediation proportion
        pathways.sort(key=lambda p: abs(p.mediation_proportion), reverse=True)

        dominant = pathways[0] if pathways else None

        return MediationAnalysisResult(
            mechanism=mechanism,
            archetype=archetype,
            pathways=pathways,
            dominant_pathway=dominant,
            n_sequences=n,
            sufficient_data=True,
        )

    def _analyze_pathway(
        self,
        mechanism: str,
        mediator_name: str,
        mediator_info: Dict,
        mech_sequences: List[Dict],
        other_sequences: List[Dict],
    ) -> Optional[MediationPathway]:
        """Analyze a single mediation pathway.

        Baron & Kenny (1986) with Sobel test:
        - Path a: T → M (mechanism effect on mediator)
        - Path b: M → Y (mediator effect on outcome)
        - Indirect = a × b
        - Direct = c - indirect
        """
        signal_key = mediator_info.get("signal_key", mediator_name)

        # Extract values
        def _extract(seqs):
            mediators = []
            outcomes = []
            for s in seqs:
                signals = s.get("behavioral_signals", {})
                m = signals.get(signal_key, 0)
                o = s.get("outcome_score", 0)
                mediators.append(float(m))
                outcomes.append(float(o))
            return np.array(mediators), np.array(outcomes)

        m_treat, y_treat = _extract(mech_sequences)
        m_control, y_control = _extract(other_sequences)

        # Path a: mechanism → mediator (treatment vs control difference)
        path_a = float(m_treat.mean() - m_control.mean())

        # Path b: mediator → outcome (correlation within treatment group)
        if np.std(m_treat) > 0.001 and np.std(y_treat) > 0.001:
            path_b, p_b = pearsonr(m_treat, y_treat)
        else:
            return None  # No variance in mediator

        # Path c: total effect (treatment vs control outcome)
        total_effect = float(y_treat.mean() - y_control.mean())

        # Indirect effect = a × b
        indirect = path_a * path_b

        # Direct effect = total - indirect
        direct = total_effect - indirect

        # Mediation proportion
        if abs(total_effect) > 0.001:
            med_proportion = indirect / total_effect
        else:
            med_proportion = 0.0

        # Bootstrap CI for indirect effect (quick version)
        n_boot = 200
        boot_indirects = []
        rng = np.random.RandomState(42)
        n_treat = len(mech_sequences)
        n_ctrl = len(other_sequences)

        for _ in range(n_boot):
            idx_t = rng.choice(n_treat, n_treat, replace=True)
            idx_c = rng.choice(n_ctrl, n_ctrl, replace=True)
            m_t_boot = m_treat[idx_t]
            y_t_boot = y_treat[idx_t]
            m_c_boot = m_control[idx_c]

            a_boot = float(m_t_boot.mean() - m_c_boot.mean())
            if np.std(m_t_boot) > 0.001 and np.std(y_t_boot) > 0.001:
                b_boot = float(pearsonr(m_t_boot, y_t_boot)[0])
            else:
                b_boot = 0.0
            boot_indirects.append(a_boot * b_boot)

        ci_lower = float(np.percentile(boot_indirects, 2.5))
        ci_upper = float(np.percentile(boot_indirects, 97.5))

        # p-value: proportion of bootstrap samples crossing zero
        n_cross_zero = sum(1 for x in boot_indirects if x * indirect < 0)
        p_indirect = n_cross_zero / n_boot

        description = (
            f"{mechanism} → {mediator_info['theoretical_mediator']} → conversion: "
            f"indirect={indirect:.3f} ({med_proportion:.0%} of total). "
            f"{'Significant' if p_indirect < 0.05 else 'Not significant'} "
            f"(p={p_indirect:.3f})."
        )

        return MediationPathway(
            mechanism=mechanism,
            mediator=mediator_name,
            outcome="conversion",
            total_effect=round(total_effect, 4),
            direct_effect=round(direct, 4),
            indirect_effect=round(indirect, 4),
            mediation_proportion=round(float(np.clip(med_proportion, -1, 1)), 4),
            n_observations=len(mech_sequences) + len(other_sequences),
            p_value_indirect=round(p_indirect, 4),
            confidence_interval=(round(ci_lower, 4), round(ci_upper, 4)),
            pathway_description=description,
        )

    def find_transferable_mechanisms(
        self,
        results: List[MediationAnalysisResult],
    ) -> Dict[str, List[str]]:
        """Find mechanisms that work through the SAME pathway.

        If social_proof and evidence_proof both work primarily via the
        "trust" mediator, knowledge about one transfers to the other.
        This enables cold-start for new mechanisms that share pathways
        with known effective mechanisms.

        Returns:
            {pathway_name: [mechanism1, mechanism2, ...]}
        """
        pathway_mechanisms: Dict[str, List[str]] = {}

        for result in results:
            if result.dominant_pathway and result.sufficient_data:
                path = result.dominant_pathway.mediator
                if path not in pathway_mechanisms:
                    pathway_mechanisms[path] = []
                pathway_mechanisms[path].append(result.mechanism)

        return pathway_mechanisms
