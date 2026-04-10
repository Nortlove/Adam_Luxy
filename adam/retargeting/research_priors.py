# =============================================================================
# Therapeutic Retargeting Engine — Research Effect Size Priors
# Location: adam/retargeting/research_priors.py
# Spec: Enhancement #33, Section A.2
# =============================================================================

"""
Canonical effect size reference — FACT-CHECKED v2.0

Each entry carries BOTH the published effect size and the calibrated estimate.
The calibrated estimate accounts for: publication bias, INFORMATIV's 0.62
lab-to-production factor, and domain-specific replication evidence.

Bayesian priors use CALIBRATED values, not published values.
"""

RESEARCH_EFFECT_SIZES = {
    # -----------------------------------------------------------------------
    # Stage-matching (Domain 1: TTM)
    # -----------------------------------------------------------------------
    "ttm_stage_matched_intervention": {
        "published_d": 0.46,
        "calibrated_d": 0.30,
        "source": "Krebs_2010",
        "k": 88,
        "calibration_note": "Applied 0.62 lab-to-production factor",
    },
    "ttm_pros_increase_required": {
        "d": 1.00,
        "source": "Hall_Rossi_2008",
        "k": 120,
        "verified": True,
        "note": "120 datasets, 48 behaviors, ~50,000 participants",
    },
    "ttm_cons_decrease_required": {
        "d": 0.56,
        "source": "Hall_Rossi_2008",
        "k": 120,
        "verified": True,
    },

    # -----------------------------------------------------------------------
    # Alliance and rupture-repair (Domain 2)
    # -----------------------------------------------------------------------
    "therapeutic_alliance_outcome": {
        "r": 0.278,
        "d": 0.579,
        "source": "Fluckiger_2018",
        "k": 295,
        "verified": True,
        "note": "Face-to-face. Teletherapy-specific: r=.15 (Aafjes-van Doorn 2024)",
    },
    "rupture_repair_outcome": {
        "r": 0.29,
        "d": 0.62,
        "source": "Eubanks_2018",
        "k": 11,
        "verified": True,
        "note": "N=1,314. Wide CI [.10, .47]. Training in repair: r=.11 nonsignificant.",
    },

    # -----------------------------------------------------------------------
    # Scaffolding (Domain 3)
    # -----------------------------------------------------------------------
    "computer_scaffolding_between_subjects": {
        "g": 0.46,
        "source": "Belland_Walker_Kim_Lefler_2017",
        "k": 144,
        "verified": True,
        "metric": "between-subjects (scaffolded vs control)",
    },
    # NOTE: g=3.13 from Belland/Walker/Kim 2017 Bayesian NMA is a WITHIN-SUBJECTS
    # pre-post metric from a SINGLE STUDY (Xin et al. 2017). Not comparable.

    # -----------------------------------------------------------------------
    # Persuasion knowledge (Domain 4)
    # -----------------------------------------------------------------------
    "pk_explanatory_power_ratio": {
        "ratio": 0.50,
        "source": "Eisend_Tarrahi_2022",
        "k": 148,
        "verified": True,
        "note": "PK->evaluations r=-.098, PK->behavior r=-.122",
    },

    # -----------------------------------------------------------------------
    # Narrative transportation (Domain 5)
    # -----------------------------------------------------------------------
    "transportation_affective": {
        "r": 0.57,
        "source": "VanLaer_2014",
        "k": 132,
        "verified": True,
        "note": "76 articles. 2019 follow-up confirmed commercial/UGC moderation.",
    },
    "transportation_critical_thought_reduction": {
        "r": -0.20,
        "source": "VanLaer_2014",
        "verified": True,
    },
    "narrative_behavior_change": {
        "r": 0.23,
        "source": "Braddock_Dillard_2016",
        "verified": True,
    },

    # -----------------------------------------------------------------------
    # FITD (Domain 6)
    # -----------------------------------------------------------------------
    "foot_in_door": {
        "r": 0.16,
        "source": "Dillard_1984",
    },
    "byaf_technique": {
        "published_g": 0.44,
        "calibrated_g": 0.11,
        "source": "Fillon_Souchet_Pascual_Girandola_2023",
        "k": 52,
        "note": "g=0.11 for 7 low-bias studies. R-index 9.77%. Effectively null for digital.",
    },

    # -----------------------------------------------------------------------
    # Reactance (Domain 7)
    # -----------------------------------------------------------------------
    "freedom_threat_anger": {
        "r": 0.21,
        "source": "ReactanceMeta_2025",
        "k": 28,
    },
    "anger_persuasion_reduction": {
        "r": -0.23,
        "source": "ReactanceMeta_2025",
    },
    "privacy_control_click_multiplier": {
        "ratio": 2.0,
        "source": "Tucker_2014",
        "verified": True,
        "note": "JMR: 'nearly twice as likely'",
    },

    # -----------------------------------------------------------------------
    # SDT (Domain 8)
    # -----------------------------------------------------------------------
    "autonomy_support_intrinsic_motivation": {
        "r": 0.42,
        "source": "Ng_2012",
        "k": 184,
        "verified": True,
        "note": "Health care contexts. Ryan et al. (2023) reviewed 60 SDT meta-analyses.",
    },

    # -----------------------------------------------------------------------
    # CLT (Domain 9) — DOWNGRADED
    # -----------------------------------------------------------------------
    "construal_level_distance_abstraction": {
        "published_d": 0.36,
        "calibrated_d": 0.10,
        "source": "Soderberg_2015",
        "k": 267,
        "note": (
            "SEVERE publication bias. Schimmack (2022): 14% expected discovery "
            "rate vs 74% observed = 500% inflation. Preregistered replication d=0.10."
        ),
    },
    "construal_fit_advertising": {
        "significant": True,
        "source": "Dogan_Erdogan_2020",
        "note": "F(1,346)=21.36, p<.001. FIT effect survives even if basic link is weak.",
    },

    # -----------------------------------------------------------------------
    # Psychological ownership (Domain 10)
    # -----------------------------------------------------------------------
    "peck_shu_ownership": {
        "mean_diff": 0.43,
        "source": "Peck_Shu_2009",
        "note": (
            "Touch->ownership (3.27 vs 2.84 on 7-point). "
            "Valuation increase ONLY with pleasant touch."
        ),
    },
    "ikea_effect": {
        "d": 0.57,
        "source": "Pelled_2026",
        "k": 55,
        "verified": True,
    },
    "cart_abandonment_3email_vs_1": {
        "multiplier": 6.5,
        "source": "industry_benchmark",
    },

    # -----------------------------------------------------------------------
    # Cognitive dissonance (Domain 11)
    # -----------------------------------------------------------------------
    "dissonance_overall": {"d": 0.61, "source": "Kenworthy_2011"},
    "dissonance_artifact_corrected": {"d": 0.26, "source": "Izuma_Murayama_2013"},

    # -----------------------------------------------------------------------
    # Social learning (Domain 12)
    # -----------------------------------------------------------------------
    "self_efficacy_performance": {
        "r": 0.38,
        "source": "Stajkovic_Luthans_1998",
        "k": 114,
        "verified": True,
    },

    # -----------------------------------------------------------------------
    # Dual process / mere exposure (Domain 13)
    # -----------------------------------------------------------------------
    "mere_exposure_overall": {
        "r": 0.26,
        "source": "Bornstein_1989",
        "k": 208,
        "verified": True,
        "note": "208 contrasts from 134 studies",
    },
    "mere_exposure_subliminal": {
        "r": 0.40,
        "source": "Bornstein_1989",
        "note": "CORRECTED from r=.53. Best estimate for brief/subliminal: r~.37-.49.",
    },
    "mere_exposure_peak_range": {
        "min": 10,
        "max": 35,
        "source": "Montoya_2017",
    },

    # -----------------------------------------------------------------------
    # Implementation intentions (Domain 14) — CORRECTED
    # -----------------------------------------------------------------------
    "implementation_intentions": {
        "published_d": 0.65,
        "calibrated_d": 0.25,
        "source": "Gollwitzer_Sheeran_2006",
        "k": 94,
        "note": (
            "Authors acknowledge 'substantial' pub bias (Egger's b=1.06). "
            "Domain-specific: physical activity d=0.14-0.31. Use calibrated_d=0.25."
        ),
        "update_source": "Sheeran_Listrom_Gollwitzer_2024",
        "update_k": 642,
    },

    # -----------------------------------------------------------------------
    # Web atmospherics (Domain 15)
    # -----------------------------------------------------------------------
    "visual_design_credibility_pct": {
        "pct": 0.461,
        "source": "Fogg_Stanford",
    },
    "color_arousal_warm": {"r": 0.15, "source": "Roschk_2017", "k": 66},
    "trust_purchase_intention": {"r": 0.434, "source": "Wang_2022"},

    # -----------------------------------------------------------------------
    # LLM persuasion (Domain 16) — NEW
    # -----------------------------------------------------------------------
    "llm_persuasion_debate": {
        "or": 1.812,
        "source": "Salvi_2024_NatureHumanBehaviour",
        "note": (
            "81.2% higher odds of agreement. Effect driven by factual argument "
            "quality, NOT psychological technique selection."
        ),
    },
    "llm_multiturn_threshold": {
        "turns": 4,
        "source": "Bozdag_2025",
        "note": "As few as 4 conversational turns significantly increases effectiveness.",
    },
    "llm_demographic_personalization": {
        "effect": "null",
        "source": "Hackenburg_Margetts_2024_PNAS",
        "note": (
            "Surface demographic personalization produces NO persuasive advantage. "
            "Only deep psychological personalization works."
        ),
    },

    # -----------------------------------------------------------------------
    # Personality-matched persuasion — CORRECTED with caveats
    # -----------------------------------------------------------------------
    "personality_matched_clicks": {
        "published_lift": 0.40,
        "calibrated_lift": 0.20,
        "source": "Matz_2017",
        "N": 3_500_000,
        "note": (
            "Only 2 of 5 tests significant. Study 1 found ZERO click effect. "
            "Calibrated lift halves the published estimate."
        ),
    },
    "personality_matched_purchases": {
        "published_lift": 0.50,
        "calibrated_lift": 0.25,
        "source": "Matz_2017",
        "note": "Same caveats as clicks. Use calibrated values for priors.",
    },
    "hirsh_agreeableness_match": {
        "r_diff": 0.25,
        "source": "Hirsh_2012",
        "verified": True,
    },
    "matz_2024_llm_personality": {
        "effective": True,
        "source": "Matz_2024_ScientificReports",
        "N": 1788,
        "note": "ChatGPT personality-matched messages effective across personality, ideology, moral foundations.",
    },

    # -----------------------------------------------------------------------
    # Ad repetition
    # -----------------------------------------------------------------------
    "max_attitude_exposures": {
        "n": 10,
        "source": "Schmidt_Eisend_2015",
        "k": 37,
        "verified": True,
    },
    "affect_decay_rate": {
        "rate": -0.62,
        "source": "Schmidt_Eisend_2015",
        "verified": True,
    },
    "memory_decay_rate": {
        "rate": -0.32,
        "source": "Schmidt_Eisend_2015",
        "verified": True,
    },

    # -----------------------------------------------------------------------
    # INFORMATIV calibration
    # -----------------------------------------------------------------------
    "lab_to_production_calibration": {
        "factor": 0.62,
        "source": "INFORMATIV_internal",
    },
}
