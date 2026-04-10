# =============================================================================
# Therapeutic Retargeting Engine — Personality x Mechanism Susceptibility
# Location: adam/retargeting/personality_mechanism_matrix.py
# Spec: Enhancement #33, Section A.3
# =============================================================================

"""
Personality x Mechanism Interaction Matrix

Determines which Cialdini mechanism to deploy for each Big Five profile.
Sourced from Alkis & Temizel (2015), Oyibo et al. (2017), replicated
cross-culturally.

Used by BayesianMechanismSelector to modulate Thompson Sampling alpha
based on personality fit: +1 susceptible -> 1.3x alpha boost,
-1 resistant -> 0.7x alpha penalty.
"""

# Format: trait -> {mechanism: susceptibility_direction}
# +1 = susceptible, -1 = resistant, 0 = neutral
PERSONALITY_MECHANISM_SUSCEPTIBILITY = {
    "agreeableness_high": {
        "liking": +1,
        "authority": +1,
        "commitment": +1,
        "social_proof": +1,
        "reciprocity": +1,
        "scarcity": 0,
    },
    "conscientiousness_high": {
        "commitment": +1,
        "reciprocity": +1,
        "liking": -1,
        "authority": 0,
        "social_proof": 0,
        "scarcity": 0,
    },
    "openness_low": {
        "authority": +1,
        "social_proof": +1,
        "liking": +1,
        "commitment": 0,
        "reciprocity": 0,
        "scarcity": 0,
    },
    "neuroticism_high": {
        "social_proof": +1,
        "scarcity": +1,
        "authority": 0,
        "liking": 0,
        "commitment": 0,
        "reciprocity": 0,
    },
    "extraversion_high": {
        "scarcity": +1,
        "liking": 0,
        "social_proof": 0,
        "authority": 0,
        "commitment": 0,
        "reciprocity": 0,
    },
    # Reactance trait (from Enhancement #27 extended constructs)
    "reactance_high": {
        "scarcity": -1,
        "authority": -1,
        "commitment": -1,
        "narrative": +1,
        "autonomy_support": +1,
    },
}
