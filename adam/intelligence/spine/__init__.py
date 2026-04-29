"""ADAM Cognitive Spine — the 13 primitives per CLAUDE_CODE_DIRECTIVE_FULL_BUILD.md.

Each primitive operates at decision time on real served impressions, OR
feeds something that does, OR protects integrity of (1) and (2).

Modules:
    spine_1_n_of_1_engine — Per-User N-of-1 Hierarchical Bayesian Engine
        (BONG online conjugate updates, Kalman state-space wrapping,
        partial pooling via cohort priors). The spine of the spine.

    [Future modules: spine_2_scheduler, spine_3_bilateral_edge,
     spine_4_trilateral_cascade, spine_5_free_energy, spine_6_decision_trace,
     spine_7_cohort_discovery, spine_8_epistemic_bonus, spine_9_kelly_bid,
     spine_10_kalman, spine_11_negative_outcome_adapter,
     spine_12_offline_discovery, spine_13_partner_surface]
"""

from __future__ import annotations
