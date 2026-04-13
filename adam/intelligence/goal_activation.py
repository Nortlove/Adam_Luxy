# =============================================================================
# Nonconscious Goal Activation Model
# Location: adam/intelligence/goal_activation.py
# =============================================================================
"""
Nonconscious Goal Activation Model — Active Learning System.

Grounded in Bargh's auto-motive model (1990), Chartrand et al. (2008),
and Custers & Aarts (2010). Page content activates nonconscious goals
through learned situation-goal associations. The ad then serves as
the goal-fulfillment stimulus — noticed automatically through
goal-directed selective attention (Dijksterhuis & Aarts, 2010).

This is NOT concept/trait priming (which decays in seconds).
Goals persist, intensify when unfulfilled, shield against competitors,
and drive selective attention toward goal-relevant stimuli.

THREE-LAYER ACTIVE LEARNING:
  Layer 1 (Individual): Each person is a unique experiment — puzzle solver
  Layer 2 (Context): Each page is a hypothesis about goal activation —
    outcomes update goal-page mappings, marker weights, fulfillment strengths
  Layer 3 (Hunt): System actively decides WHERE to look next based on
    epistemic value — high uncertainty → bid more to learn

The hardcoded keyword lists and fulfillment mappings are PRIORS that get
updated by observed outcomes. The system becomes more intelligent over time.

Architecture:
    Page text → goal activation (prior + learned weights) →
    crossover score → targeting decision → impression → outcome →
    update goal weights, page-goal posteriors, fulfillment strengths →
    inform next hunt decision (epistemic value drives exploration)
"""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# =============================================================================
# NONCONSCIOUS GOAL TAXONOMY
# =============================================================================
# Each goal maps to the fundamental motivational system it serves,
# the cognitive biases that signal its activation, and the archetypes
# whose ad-fulfillment aligns with it.

@dataclass
class NonconsciousGoal:
    """A nonconscious goal that page content can activate."""
    id: str
    name: str
    description: str
    motivational_system: str  # evolutionary basis
    # Which biases, when detected in page content, indicate this goal is being activated?
    activating_biases: List[str]
    # Which archetypes have ads that FULFILL this goal?
    fulfills_archetypes: List[str]
    # How does goal activation relate to affect? (Custers & Aarts, 2010)
    requires_positive_affect: bool
    # Goal persistence properties (Forster et al., 2007)
    persistence_minutes: float  # how long the goal stays active after priming
    shields_against: List[str]  # competing goals this one suppresses (Shah, 2003)


GOAL_TAXONOMY: Dict[str, NonconsciousGoal] = {

    # ── AFFILIATION / TRUST GOALS ──

    "affiliation_safety": NonconsciousGoal(
        id="affiliation_safety",
        name="Find something trustworthy",
        description=(
            "Activated by content displaying reliability, consistency, credibility. "
            "The reader's attachment system seeks a dependable entity. "
            "The LUXY ad fulfills this by presenting itself as the trusted choice."
        ),
        motivational_system="attachment",  # Bowlby
        activating_biases=[
            "authority_bias",       # deference to credible sources → seeking trust
            "mere_exposure",        # familiarity = safety signal
            "endowment_effect",     # protecting what's valued → relationship maintenance
            "illusory_truth",       # repeated = true → trust through consistency
            "in_group_favoritism",  # "people like me trust this" → belonging safety
        ],
        fulfills_archetypes=["trusting_loyalist", "dependable_loyalist", "careful_truster"],
        requires_positive_affect=True,
        persistence_minutes=15.0,
        shields_against=["novelty_exploration", "status_competition"],
    ),

    "social_alignment": NonconsciousGoal(
        id="social_alignment",
        name="Do what others are doing",
        description=(
            "Activated by content showing group behavior, consensus, social norms. "
            "The conformity drive seeks alignment with relevant peers. "
            "The LUXY ad fulfills this with '50,000 executives choose...' messaging."
        ),
        motivational_system="affiliation",  # Kenrick/Cialdini
        activating_biases=[
            "bandwagon_effect",        # group adoption → join the group
            "social_comparison",       # evaluating self vs others → match them
            "false_consensus",         # assuming others agree → confirming alignment
            "in_group_favoritism",     # "our kind does this" → group membership
            "identifiable_victim",     # personal stories → empathic contagion
        ],
        fulfills_archetypes=["consensus_seeker", "trusting_loyalist"],
        requires_positive_affect=True,
        persistence_minutes=10.0,
        shields_against=["autonomy_assertion", "novelty_exploration"],
    ),

    # ── THREAT REDUCTION / PREVENTION GOALS ──

    "threat_reduction": NonconsciousGoal(
        id="threat_reduction",
        name="Eliminate a source of risk",
        description=(
            "Activated by content highlighting risks, failures, negative outcomes. "
            "The self-protection system seeks to neutralize threats. "
            "The LUXY ad fulfills this with safety guarantees and risk elimination."
        ),
        motivational_system="self_protection",  # Kenrick
        activating_biases=[
            "loss_aversion",       # pain of loss → prevent the loss
            "negativity_bias",     # negative info dominates → address the threat
            "zero_risk_bias",      # want to ELIMINATE risk, not just reduce it
            "normalcy_bias",       # content disrupting normalcy → threat activated
            "risk_compensation",   # safety cues → license to act on protected threat
            "ostrich_effect",      # avoiding threat info → when forced to see it, goal activates
        ],
        fulfills_archetypes=["prevention_planner", "careful_truster"],
        requires_positive_affect=False,  # Threat goals activate even without positive affect
        persistence_minutes=20.0,  # Threat goals are highly persistent
        shields_against=["novelty_exploration", "indulgence_permission"],
    ),

    # ── EXPLORATION / NOVELTY GOALS ──

    "novelty_exploration": NonconsciousGoal(
        id="novelty_exploration",
        name="Discover something new and exciting",
        description=(
            "Activated by content about innovation, discovery, new experiences. "
            "Panksepp's SEEKING system drives approach toward novel stimuli. "
            "The LUXY ad fulfills this by framing the ride as an undiscovered experience."
        ),
        motivational_system="exploration",  # Panksepp SEEKING
        activating_biases=[
            "appeal_to_novelty",   # new = better → seek the new thing
            "contrast_effect",     # differences amplified → notice what's different
            "optimism_bias",       # believe good things will happen → approach the new
            "attentional_bias",    # attention captured by novel stimuli
        ],
        fulfills_archetypes=["explorer"],
        requires_positive_affect=True,
        persistence_minutes=10.0,
        shields_against=["threat_reduction", "affiliation_safety"],
    ),

    # ── COMPETENCE / MASTERY GOALS ──

    "competence_verification": NonconsciousGoal(
        id="competence_verification",
        name="Confirm quality and standards are met",
        description=(
            "Activated by content about standards, metrics, performance evaluation. "
            "The competence system seeks to verify that quality is present. "
            "The LUXY ad fulfills this with credentials, metrics, consistency data."
        ),
        motivational_system="status_hierarchy",  # Kenrick
        activating_biases=[
            "authority_bias",          # deference to experts → verify through authority
            "effort_justification",    # effort signals quality → seek quality signals
            "confirmation_bias",       # seeking confirming evidence → want to confirm quality
            "peak_end_rule",           # judging by highlights → seek quality highlights
        ],
        fulfills_archetypes=["dependable_loyalist", "reliable_cooperator"],
        requires_positive_affect=False,
        persistence_minutes=12.0,
        shields_against=["indulgence_permission", "novelty_exploration"],
    ),

    # ── PLANNING / COMPLETION GOALS ──

    "planning_completion": NonconsciousGoal(
        id="planning_completion",
        name="Close an open planning loop",
        description=(
            "Activated by content about scheduling, planning, open tasks, unfinished business. "
            "Zeigarnik effect: unfinished tasks persist in memory and create tension. "
            "The LUXY ad fulfills this with 'Book your Tuesday pickup now' — closing the loop."
        ),
        motivational_system="goal_management",  # Zeigarnik/Lewin
        activating_biases=[
            "zeigarnik_effect",        # unfinished task → complete it
            "planning_fallacy",        # planning content → planning goal activated
            "sunk_cost",               # already invested → complete the investment
            "ikea_effect",             # effort invested → value completion
            "hyperbolic_discounting",  # immediate resolution preferred
        ],
        fulfills_archetypes=["reliable_cooperator"],
        requires_positive_affect=False,
        persistence_minutes=30.0,  # Zeigarnik goals are extremely persistent
        shields_against=["social_alignment"],
    ),

    # ── INDULGENCE / REWARD GOALS ──

    "indulgence_permission": NonconsciousGoal(
        id="indulgence_permission",
        name="I deserve this / permission to spend",
        description=(
            "Activated by content about achievement, reward, self-care, luxury. "
            "Self-licensing: virtuous behavior creates permission for indulgence. "
            "The LUXY ad fulfills this with 'You've earned this ride' messaging."
        ),
        motivational_system="reward",  # Dopaminergic approach
        activating_biases=[
            "self_licensing",          # "I've been good" → permission to indulge
            "restraint_bias",          # overestimate self-control → indulge freely
            "mental_accounting",       # "this is from bonus money" → spend freely
            "hyperbolic_discounting",  # want it NOW → immediate reward
            "effort_justification",    # worked hard → deserve reward
            "positivity_effect",       # focus on positive → approach reward
        ],
        fulfills_archetypes=["easy_decider", "status_seeker", "explorer"],
        requires_positive_affect=True,
        persistence_minutes=8.0,  # Reward goals have shorter persistence
        shields_against=["threat_reduction", "competence_verification"],
    ),

    # ── STATUS / IDENTITY GOALS ──

    "status_signaling": NonconsciousGoal(
        id="status_signaling",
        name="Signal my position in the hierarchy",
        description=(
            "Activated by content about success, achievement, social comparison, luxury. "
            "Status hierarchy navigation: signal competence and position to peers. "
            "The LUXY ad fulfills this with exclusivity and peer-level messaging."
        ),
        motivational_system="mate_attraction_hierarchy",  # Kenrick
        activating_biases=[
            "social_comparison",       # comparing to others → signal superiority
            "self_reference_effect",   # self-relevant processing → identity maintenance
            "framing_effect",          # positive frame → approach status-enhancing options
            "bandwagon_effect",        # "top people do this" → join the elite
            "contrast_effect",         # comparison amplified → notice status differences
        ],
        fulfills_archetypes=["status_seeker"],
        requires_positive_affect=True,
        persistence_minutes=12.0,
        shields_against=["threat_reduction", "planning_completion"],
    ),
}


# =============================================================================
# LINGUISTIC MARKERS FOR GOAL ACTIVATION DETECTION
# =============================================================================
# These are the TEXT FEATURES on a page that indicate a goal is being activated.
# Derived from 140 cognitive bias analyzers, filtered to goal-relevant markers.
# Applied to PAGE CONTENT (not reviews) to detect priming.

GOAL_ACTIVATION_MARKERS: Dict[str, Dict] = {

    "affiliation_safety": {
        "keywords": [
            "trusted", "reliable", "dependable", "consistent", "proven",
            "established", "reputation", "track record", "years of experience",
            "certified", "accredited", "endorsed", "recommended", "preferred",
            "loyalty", "commitment", "dedicated", "faithful", "steady",
            "professional", "expert", "specialist", "authority", "leader",
            "recognized", "awarded", "rated", "reviewed", "verified",
        ],
        "regex_patterns": [
            r"(?:trusted|relied upon|depended on)\s+by\s+(?:thousands|millions|professionals)",
            r"(?:\d+)\s+(?:years|decades)\s+(?:of|in)\s+(?:service|business|experience)",
            r"(?:rated|reviewed|recommended)\s+(?:\d+(?:\.\d+)?)\s+(?:stars|out of)",
            r"(?:industry|market|sector)\s+(?:leader|standard|benchmark)",
        ],
        "negative_markers": [  # These ATTENUATE the goal
            "scam", "fraud", "unreliable", "inconsistent", "unproven",
            "controversial", "disputed", "questionable",
        ],
    },

    "social_alignment": {
        "keywords": [
            "everyone", "popular", "trending", "widespread", "common",
            "mainstream", "many people", "most people", "millions",
            "community", "together", "shared", "collective", "group",
            "peers", "colleagues", "professionals like you", "others",
            "joined", "switched", "adopted", "chosen by", "preferred by",
            "movement", "wave", "growing", "increasingly",
        ],
        "regex_patterns": [
            r"(?:\d+[,.]?\d*)\s+(?:people|users|customers|professionals)\s+(?:chose|use|trust|prefer)",
            r"(?:everyone|everybody|most people)\s+(?:is|are)\s+(?:using|choosing|switching)",
            r"(?:join|joined)\s+(?:thousands|millions|the)\s+(?:of|who)",
            r"(?:fastest|most)\s+(?:growing|popular|adopted)",
        ],
        "negative_markers": [
            "exclusive", "elite", "select few", "invitation only",
            "contrarian", "unconventional", "against the grain",
        ],
    },

    "threat_reduction": {
        "keywords": [
            "risk", "danger", "threat", "unsafe", "hazard", "warning",
            "failure", "problem", "issue", "concern", "worry", "anxiety",
            "accident", "incident", "breach", "vulnerability", "exposed",
            "protect", "prevent", "avoid", "eliminate", "safeguard",
            "insurance", "guarantee", "safety", "security", "defense",
            "loss", "damage", "harm", "cost", "penalty", "fine",
        ],
        "regex_patterns": [
            r"(?:risk|danger|threat)\s+of\s+(?:\w+)",
            r"(?:could|might|may)\s+(?:lose|fail|miss|damage)",
            r"(?:protect|prevent|avoid|eliminate)\s+(?:\w+)\s+(?:risk|danger|loss)",
            r"(?:\d+)%\s+(?:of|chance|probability)\s+(?:\w+)\s+(?:fail|break|miss)",
            r"(?:what happens|consequences)\s+(?:when|if)\s+(?:\w+)\s+(?:fails|breaks|goes wrong)",
        ],
        "negative_markers": [
            "no risk", "risk free", "completely safe", "nothing to worry about",
        ],
    },

    "novelty_exploration": {
        "keywords": [
            "new", "innovative", "revolutionary", "breakthrough", "cutting-edge",
            "discover", "explore", "adventure", "journey", "experience",
            "unprecedented", "first-ever", "never before", "reimagine",
            "transform", "disrupt", "evolve", "next generation", "future",
            "surprising", "unexpected", "remarkable", "extraordinary",
            "hidden", "secret", "untold", "beyond", "frontier",
        ],
        "regex_patterns": [
            r"(?:never|not)\s+(?:seen|experienced|tried|imagined)\s+(?:before|anything like)",
            r"(?:discover|explore|uncover|reveal)\s+(?:the|a|an)\s+(?:\w+)",
            r"(?:new|novel|innovative)\s+(?:way|approach|method|experience)",
            r"what\s+(?:if|happens when)\s+(?:you|we)\s+(?:try|explore|discover)",
        ],
        "negative_markers": [
            "traditional", "conventional", "standard", "usual",
            "tried and true", "proven method", "established practice",
        ],
    },

    "competence_verification": {
        "keywords": [
            "quality", "standard", "benchmark", "metric", "performance",
            "rating", "score", "evaluation", "assessment", "audit",
            "certified", "accredited", "compliance", "regulation",
            "testing", "verified", "validated", "inspection", "review",
            "criteria", "specification", "requirement", "excellence",
            "accuracy", "precision", "consistency", "reliability",
        ],
        "regex_patterns": [
            r"(?:meets|exceeds|surpasses)\s+(?:\w+)\s+(?:standards|requirements|criteria)",
            r"(?:rated|scored|ranked)\s+(?:#?\d+|top|highest|best)",
            r"(?:independently|third-party)\s+(?:verified|tested|audited|certified)",
            r"(?:\d+(?:\.\d+)?)\s+(?:star|rating|score|percent)\s+(?:\w+)",
        ],
        "negative_markers": [
            "unverified", "self-reported", "estimated", "approximate",
            "unaudited", "unregulated",
        ],
    },

    "planning_completion": {
        "keywords": [
            "schedule", "plan", "organize", "coordinate", "arrange",
            "calendar", "agenda", "itinerary", "timeline", "deadline",
            "book", "reserve", "confirm", "set up", "prepare",
            "upcoming", "next week", "tomorrow", "this weekend",
            "pending", "unfinished", "remaining", "outstanding",
            "to-do", "checklist", "step", "phase", "stage",
            "complete", "finish", "finalize", "wrap up",
        ],
        "regex_patterns": [
            r"(?:still|yet|haven't)\s+(?:need|have)\s+to\s+(?:finish|complete|book|plan)",
            r"(?:before|by|until)\s+(?:your|the)\s+(?:trip|flight|meeting|deadline)",
            r"(?:don't forget|remember)\s+to\s+(?:\w+)",
            r"(?:\d+)\s+(?:things|tasks|items|steps)\s+(?:left|remaining|to do)",
        ],
        "negative_markers": [
            "all done", "fully booked", "nothing left", "completed",
        ],
    },

    "indulgence_permission": {
        "keywords": [
            "deserve", "earned", "reward", "treat", "indulge",
            "luxury", "premium", "splurge", "pamper", "self-care",
            "achievement", "milestone", "celebration", "success",
            "hard work", "dedication", "effort", "sacrifice",
            "finally", "about time", "long overdue", "worth it",
            "guilt-free", "no regrets", "life is short", "you only live once",
        ],
        "regex_patterns": [
            r"(?:you|you've)\s+(?:deserve|earned|worked for)\s+(?:this|it|a treat)",
            r"(?:after|following)\s+(?:all that|so much|years of)\s+(?:work|effort|sacrifice)",
            r"(?:treat|reward|pamper)\s+(?:yourself|yourself to)",
            r"(?:life is|it's)\s+(?:too short|about|time)\s+(?:to|for)\s+(?:enjoy|indulge|relax)",
        ],
        "negative_markers": [
            "budget", "save", "cheap", "discount", "frugal",
            "cut costs", "economize", "penny-pinching",
        ],
    },

    "status_signaling": {
        "keywords": [
            "exclusive", "elite", "prestigious", "premium", "luxury",
            "top", "best", "finest", "superior", "world-class",
            "vip", "first class", "executive", "ceo", "founder",
            "success", "achievement", "accomplished", "distinguished",
            "wealthy", "affluent", "high-end", "upscale", "sophisticated",
            "influence", "power", "leadership", "authority", "recognition",
        ],
        "regex_patterns": [
            r"(?:top|leading|most successful)\s+(?:\d+%?|executives|professionals|companies)",
            r"(?:exclusive|invitation-only|members-only)\s+(?:\w+)",
            r"(?:fortune|inc|forbes)\s+(?:\d+|500|list)",
            r"(?:among|join)\s+the\s+(?:best|elite|top|most successful)",
        ],
        "negative_markers": [
            "everyone", "common", "affordable", "budget",
            "mass market", "average", "ordinary",
        ],
    },
}


# =============================================================================
# GOAL → ARCHETYPE FULFILLMENT MAPPING
# =============================================================================
# For each archetype, which goals does the LUXY Ride ad fulfill,
# and with what strength? The strength reflects how directly the
# ad creative addresses the activated goal.

ARCHETYPE_GOAL_FULFILLMENT: Dict[str, Dict[str, float]] = {
    "trusting_loyalist": {
        "affiliation_safety": 0.95,    # Direct fulfillment — "trusted by 50K+"
        "social_alignment": 0.70,      # "peers choose LUXY"
        "competence_verification": 0.40,
    },
    "dependable_loyalist": {
        "competence_verification": 0.90,  # Direct — credentials, metrics
        "affiliation_safety": 0.75,       # Reliability = trust
        "planning_completion": 0.50,
    },
    "consensus_seeker": {
        "social_alignment": 0.95,        # Direct — "others like you chose"
        "affiliation_safety": 0.60,
    },
    "explorer": {
        "novelty_exploration": 0.95,     # Direct — "experience something new"
        "indulgence_permission": 0.60,   # "you deserve this experience"
        "status_signaling": 0.40,
    },
    "prevention_planner": {
        "threat_reduction": 0.95,        # Direct — "eliminate pickup anxiety"
        "competence_verification": 0.70, # Safety metrics, DOT ratings
        "planning_completion": 0.50,
    },
    "reliable_cooperator": {
        "planning_completion": 0.95,     # Direct — "book your Tuesday pickup"
        "competence_verification": 0.65,
        "affiliation_safety": 0.45,
    },
    "careful_truster": {
        "affiliation_safety": 0.85,
        "threat_reduction": 0.75,
        "competence_verification": 0.80,
    },
    "status_seeker": {
        "status_signaling": 0.95,        # Direct — "join the elite"
        "indulgence_permission": 0.80,   # "you've earned this"
        "novelty_exploration": 0.40,
    },
    "easy_decider": {
        "indulgence_permission": 0.90,   # Direct — "just do it, you deserve it"
        "planning_completion": 0.60,     # "one tap booking"
        "social_alignment": 0.50,
    },
}


# =============================================================================
# GOAL ACTIVATION SCORER
# =============================================================================

@dataclass
class GoalActivationResult:
    """Result of scoring a page for nonconscious goal activation."""
    goal_scores: Dict[str, float]       # goal_id → activation strength [0, 1]
    dominant_goal: str                   # highest-scoring goal
    dominant_strength: float             # strength of dominant goal
    affect_valence: float               # positive affect level of page [-1, 1]
    goal_shielded: List[str]            # goals suppressed by the dominant goal
    evidence: Dict[str, List[str]]       # goal_id → matched markers


def score_page_goal_activation(
    text: str,
    page_affect_valence: float = 0.5,
) -> GoalActivationResult:
    """Score a page's text for nonconscious goal activation.

    Args:
        text: Page content text (article body, headlines, etc.)
        page_affect_valence: Estimated emotional valence of the page [-1, 1].
            Positive affect amplifies goal potency (Custers & Aarts, 2010).

    Returns:
        GoalActivationResult with per-goal activation scores.
    """
    text_lower = text.lower()
    goal_scores = {}
    evidence = {}

    for goal_id, markers in GOAL_ACTIVATION_MARKERS.items():
        goal_def = GOAL_TAXONOMY[goal_id]
        score = 0.0
        matched = []

        # Keyword matching (each unique match adds to score)
        keyword_hits = 0
        for kw in markers["keywords"]:
            if kw in text_lower:
                keyword_hits += 1
                matched.append(f"kw:{kw}")

        # Normalize: 5+ keyword hits = strong activation
        keyword_score = min(1.0, keyword_hits / 5.0)

        # Regex pattern matching (stronger signal — contextual phrases)
        regex_hits = 0
        for pattern in markers["regex_patterns"]:
            try:
                if re.search(pattern, text_lower):
                    regex_hits += 1
                    matched.append(f"rx:{pattern[:40]}")
            except re.error:
                pass

        # Normalize: 2+ regex hits = strong activation
        regex_score = min(1.0, regex_hits / 2.0)

        # Negative markers attenuate
        neg_hits = sum(1 for nm in markers.get("negative_markers", []) if nm in text_lower)
        attenuation = max(0.0, 1.0 - neg_hits * 0.25)

        # Combined score
        raw_score = (keyword_score * 0.5 + regex_score * 0.5) * attenuation

        # Affect modulation (Custers & Aarts, 2010)
        if goal_def.requires_positive_affect:
            # Positive affect amplifies; negative affect dampens
            affect_multiplier = 0.5 + 0.5 * max(0, page_affect_valence)
            raw_score *= affect_multiplier

        goal_scores[goal_id] = min(1.0, raw_score)
        evidence[goal_id] = matched

    # Determine dominant goal
    if goal_scores:
        dominant = max(goal_scores, key=goal_scores.get)
        dominant_strength = goal_scores[dominant]

        # Goal shielding (Shah, 2003): dominant goal suppresses competitors
        shielded = GOAL_TAXONOMY[dominant].shields_against if dominant_strength > 0.3 else []
    else:
        dominant = ""
        dominant_strength = 0.0
        shielded = []

    return GoalActivationResult(
        goal_scores=goal_scores,
        dominant_goal=dominant,
        dominant_strength=dominant_strength,
        affect_valence=page_affect_valence,
        goal_shielded=shielded,
        evidence=evidence,
    )


def compute_crossover_score(
    goal_activation: GoalActivationResult,
    archetype: str,
) -> float:
    """Compute crossover score: how well does this page prime goals
    that the ad for this archetype fulfills?

    This is the core targeting signal. High crossover = the page has
    activated a nonconscious goal that the LUXY ad for this archetype
    directly fulfills. The person will nonconsciously notice and click.

    Args:
        goal_activation: Page goal activation result
        archetype: Target archetype id

    Returns:
        Crossover score [0, 1]. Higher = better page for this archetype.
    """
    fulfillment = ARCHETYPE_GOAL_FULFILLMENT.get(archetype, {})
    if not fulfillment:
        return 0.0

    score = 0.0
    total_weight = 0.0

    for goal_id, fulfillment_strength in fulfillment.items():
        activation = goal_activation.goal_scores.get(goal_id, 0.0)

        # Goal shielding penalty: if this goal is suppressed by the
        # dominant goal, the ad can't fulfill it effectively
        if goal_id in goal_activation.goal_shielded:
            activation *= 0.2  # Heavy penalty — goal is actively inhibited

        # Crossover = activation × fulfillment
        # Both must be present: page activates the goal AND ad fulfills it
        crossover = activation * fulfillment_strength
        score += crossover
        total_weight += fulfillment_strength

    # Normalize by total possible fulfillment
    if total_weight > 0:
        score /= total_weight

    return min(1.0, score)


def rank_archetypes_for_page(
    goal_activation: GoalActivationResult,
) -> List[Tuple[str, float]]:
    """Rank all archetypes by crossover score for a given page.

    Returns list of (archetype, crossover_score) sorted descending.
    Use this to determine which archetype's ad to serve on this page.
    """
    scores = []
    for archetype in ARCHETYPE_GOAL_FULFILLMENT:
        cs = compute_crossover_score(goal_activation, archetype)
        scores.append((archetype, cs))

    scores.sort(key=lambda x: -x[1])
    return scores


# =============================================================================
# LAYER 2: ACTIVE LEARNING — GOAL-PAGE POSTERIORS
# =============================================================================
# Every impression is an experiment. The outcome updates our beliefs about:
#   1. Which page features actually activate which goals (marker weights)
#   2. Which goal-archetype-mechanism chains actually produce conversions
#   3. Which fulfillment strengths are real vs theoretical
#
# All priors (keyword weights, fulfillment strengths) are Bayesian and
# get updated from observed evidence. The system becomes more intelligent
# with every impression.

@dataclass
class GoalPagePosterior:
    """Bayesian posterior for a (goal, page_category) pair.

    Tracks whether pages in this category actually activate this goal
    as measured by downstream outcomes (clicks, conversions).
    """
    goal_id: str
    page_category: str          # domain, category, or page-type bucket
    alpha: float = 1.0          # successes (goal-consistent outcomes)
    beta: float = 1.0           # failures (goal-inconsistent outcomes)
    observations: int = 0
    total_crossover_predicted: float = 0.0  # sum of predicted crossover scores
    total_outcome_value: float = 0.0        # sum of actual outcome values

    @property
    def effectiveness(self) -> float:
        """Posterior mean: P(outcome | goal activated on this page type)."""
        return self.alpha / (self.alpha + self.beta)

    @property
    def uncertainty(self) -> float:
        """Posterior variance — high = we need more evidence."""
        a, b = self.alpha, self.beta
        return (a * b) / ((a + b) ** 2 * (a + b + 1))

    @property
    def calibration_error(self) -> float:
        """How far off our predictions are from observed outcomes."""
        if self.observations < 3:
            return 0.5  # high uncertainty = assume moderate error
        predicted_rate = self.total_crossover_predicted / self.observations
        observed_rate = self.total_outcome_value / self.observations
        return abs(predicted_rate - observed_rate)


@dataclass
class FulfillmentPosterior:
    """Bayesian posterior for an (archetype, goal) fulfillment strength.

    Starts at the theoretical prior (from ARCHETYPE_GOAL_FULFILLMENT).
    Updated by observed conversions: did activating this goal for this
    archetype actually lead to conversion?
    """
    archetype: str
    goal_id: str
    alpha: float = 1.0
    beta: float = 1.0
    prior_strength: float = 0.5   # the hardcoded starting value

    @property
    def learned_strength(self) -> float:
        """Posterior mean, blended with prior based on evidence count."""
        n = self.alpha + self.beta - 2  # observations
        if n < 5:
            # Not enough evidence — trust the prior
            blend = n / 5.0
            return self.prior_strength * (1 - blend) + (self.alpha / (self.alpha + self.beta)) * blend
        return self.alpha / (self.alpha + self.beta)

    @property
    def uncertainty(self) -> float:
        a, b = self.alpha, self.beta
        return (a * b) / ((a + b) ** 2 * (a + b + 1))


@dataclass
class MarkerWeightPosterior:
    """Learned weight for a single linguistic marker within a goal.

    Each keyword/regex starts with equal weight. As we observe which
    markers' presence on a page actually predicts goal-consistent outcomes,
    we upweight effective markers and downweight noise.
    """
    marker: str
    goal_id: str
    weight: float = 1.0       # current learned weight (starts at 1.0)
    hits_with_success: int = 0
    hits_with_failure: int = 0
    hits_total: int = 0

    @property
    def learned_weight(self) -> float:
        if self.hits_total < 3:
            return self.weight  # not enough evidence
        success_rate = self.hits_with_success / self.hits_total
        # Weight proportional to success rate, min 0.1 to prevent
        # complete elimination of potentially useful markers
        return max(0.1, min(3.0, success_rate * 2.0))


class GoalActivationLearner:
    """Active learning system for the Goal Activation Model.

    Maintains Bayesian posteriors at three levels:
      1. Goal-Page posteriors: does this page category actually activate this goal?
      2. Fulfillment posteriors: does this goal actually drive conversion for this archetype?
      3. Marker weight posteriors: which linguistic features actually predict goal activation?

    Also computes epistemic value for the Hunt (Layer 3):
      "Where should I look next to learn the most?"
    """

    def __init__(self):
        self._goal_page_posteriors: Dict[str, GoalPagePosterior] = {}
        self._fulfillment_posteriors: Dict[str, FulfillmentPosterior] = {}
        self._marker_weights: Dict[str, MarkerWeightPosterior] = {}
        self._observation_buffer: List[Dict] = []

        # Initialize fulfillment posteriors from hardcoded priors
        for archetype, goals in ARCHETYPE_GOAL_FULFILLMENT.items():
            for goal_id, strength in goals.items():
                key = f"{archetype}:{goal_id}"
                self._fulfillment_posteriors[key] = FulfillmentPosterior(
                    archetype=archetype,
                    goal_id=goal_id,
                    alpha=1.0 + strength * 2,  # prior proportional to theoretical strength
                    beta=1.0 + (1 - strength) * 2,
                    prior_strength=strength,
                )

    def record_observation(
        self,
        page_category: str,
        goal_activation: GoalActivationResult,
        archetype: str,
        mechanism: str,
        outcome_value: float,           # 0.0 = no engagement, 1.0 = conversion
        crossover_predicted: float,     # what the model predicted
    ):
        """Record an observation from an impression experiment.

        This is the core learning signal. Every impression that has a
        page context and an outcome updates three levels of posteriors.

        Args:
            page_category: Domain or content category of the page
            goal_activation: The goal activation result from scoring
            archetype: The archetype targeted
            mechanism: The mechanism used in the ad
            outcome_value: The observed outcome [0, 1]
            crossover_predicted: The crossover score we predicted
        """
        observation = {
            "page_category": page_category,
            "dominant_goal": goal_activation.dominant_goal,
            "goal_scores": goal_activation.goal_scores,
            "archetype": archetype,
            "mechanism": mechanism,
            "outcome": outcome_value,
            "predicted": crossover_predicted,
            "evidence_markers": goal_activation.evidence,
        }
        self._observation_buffer.append(observation)

        # --- Update Goal-Page posteriors ---
        for goal_id, activation_score in goal_activation.goal_scores.items():
            if activation_score < 0.05:
                continue  # below detection threshold
            key = f"{goal_id}:{page_category}"
            if key not in self._goal_page_posteriors:
                self._goal_page_posteriors[key] = GoalPagePosterior(
                    goal_id=goal_id, page_category=page_category,
                )
            post = self._goal_page_posteriors[key]
            post.observations += 1
            post.total_crossover_predicted += crossover_predicted
            post.total_outcome_value += outcome_value
            # Weight update proportional to activation score
            # (stronger activation → more credit/blame for outcome)
            weight = activation_score
            if outcome_value > 0.5:
                post.alpha += weight * outcome_value
            else:
                post.beta += weight * (1 - outcome_value)

        # --- Update Fulfillment posteriors ---
        for goal_id, activation_score in goal_activation.goal_scores.items():
            if activation_score < 0.1:
                continue
            key = f"{archetype}:{goal_id}"
            if key in self._fulfillment_posteriors:
                fp = self._fulfillment_posteriors[key]
                if outcome_value > 0.5:
                    fp.alpha += activation_score * outcome_value
                else:
                    fp.beta += activation_score * (1 - outcome_value)

        # --- Update Marker weights ---
        for goal_id, matched_markers in goal_activation.evidence.items():
            for marker_str in matched_markers:
                key = f"{goal_id}:{marker_str}"
                if key not in self._marker_weights:
                    self._marker_weights[key] = MarkerWeightPosterior(
                        marker=marker_str, goal_id=goal_id,
                    )
                mw = self._marker_weights[key]
                mw.hits_total += 1
                if outcome_value > 0.5:
                    mw.hits_with_success += 1
                else:
                    mw.hits_with_failure += 1

    def get_learned_fulfillment(self, archetype: str, goal_id: str) -> float:
        """Get the learned fulfillment strength for an archetype-goal pair.

        Blends prior with observed evidence. Replaces hardcoded
        ARCHETYPE_GOAL_FULFILLMENT as evidence accumulates.
        """
        key = f"{archetype}:{goal_id}"
        if key in self._fulfillment_posteriors:
            return self._fulfillment_posteriors[key].learned_strength
        # Fall back to hardcoded prior
        return ARCHETYPE_GOAL_FULFILLMENT.get(archetype, {}).get(goal_id, 0.0)

    def get_goal_page_effectiveness(self, goal_id: str, page_category: str) -> float:
        """How effective is this page category at activating this goal?

        Returns posterior mean. Starts at 0.5 (uninformed), updated by evidence.
        """
        key = f"{goal_id}:{page_category}"
        if key in self._goal_page_posteriors:
            return self._goal_page_posteriors[key].effectiveness
        return 0.5  # uninformed prior

    # =========================================================================
    # LAYER 3: THE HUNT — EPISTEMIC VALUE
    # =========================================================================

    def compute_epistemic_value(
        self,
        page_category: str,
        archetype: str,
        goal_activation: GoalActivationResult,
    ) -> float:
        """Compute the epistemic (information) value of serving an ad
        on this page for this archetype.

        High epistemic value = we're uncertain about this page-goal-archetype
        chain AND the potential upside is high. The system should bid MORE
        aggressively on high-epistemic-value opportunities even if the
        expected conversion is moderate.

        This drives the active hunt: the system seeks out pages where
        it can learn the most about the goal activation chain.

        Returns:
            Epistemic value [0, 1]. Higher = more informative experiment.
        """
        total_uncertainty = 0.0
        total_potential = 0.0
        n_goals = 0

        for goal_id, activation in goal_activation.goal_scores.items():
            if activation < 0.1:
                continue

            # Goal-page uncertainty
            gp_key = f"{goal_id}:{page_category}"
            if gp_key in self._goal_page_posteriors:
                gp_unc = self._goal_page_posteriors[gp_key].uncertainty
            else:
                gp_unc = 0.25  # maximum uncertainty (uninformed Beta(1,1))

            # Fulfillment uncertainty
            fp_key = f"{archetype}:{goal_id}"
            if fp_key in self._fulfillment_posteriors:
                fp_unc = self._fulfillment_posteriors[fp_key].uncertainty
            else:
                fp_unc = 0.25

            # Combined uncertainty for this goal chain
            chain_uncertainty = (gp_unc + fp_unc) / 2

            # Potential: if this chain works, how valuable would it be?
            # Proportional to activation strength × fulfillment prior
            fulfillment = self.get_learned_fulfillment(archetype, goal_id)
            potential = activation * fulfillment

            total_uncertainty += chain_uncertainty * potential
            total_potential += potential
            n_goals += 1

        if total_potential < 0.01:
            return 0.0

        # Epistemic value = uncertainty weighted by potential
        # We want to explore where both uncertainty is high AND
        # the potential upside is meaningful
        return min(1.0, total_uncertainty / total_potential * 4.0)

    def get_hunt_recommendations(
        self,
        available_page_categories: List[str],
        archetype: str,
        top_k: int = 5,
    ) -> List[Tuple[str, float, float, float]]:
        """Recommend which page categories to hunt for this archetype.

        Balances exploitation (high expected crossover) with exploration
        (high epistemic value). Returns categories ranked by combined score.

        Returns:
            List of (page_category, combined_score, expected_crossover, epistemic_value)
        """
        recommendations = []

        for page_cat in available_page_categories:
            # We'd need the actual page text to score goal activation,
            # but we can use the learned goal-page posteriors as proxies
            expected_crossover = 0.0
            epistemic_value = 0.0

            for goal_id in GOAL_TAXONOMY:
                gp_eff = self.get_goal_page_effectiveness(goal_id, page_cat)
                fulfillment = self.get_learned_fulfillment(archetype, goal_id)
                expected_crossover += gp_eff * fulfillment

                # Epistemic value from uncertainty
                gp_key = f"{goal_id}:{page_cat}"
                if gp_key in self._goal_page_posteriors:
                    gp_unc = self._goal_page_posteriors[gp_key].uncertainty
                else:
                    gp_unc = 0.25  # high — never tested
                epistemic_value += gp_unc * fulfillment

            # Normalize
            n_goals = len(GOAL_TAXONOMY)
            expected_crossover /= n_goals
            epistemic_value /= n_goals

            # Combined: exploit + explore
            # Exploration bonus is highest early (few observations)
            # and decreases as evidence accumulates
            total_obs = sum(
                self._goal_page_posteriors.get(f"{g}:{page_cat}", GoalPagePosterior(g, page_cat)).observations
                for g in GOAL_TAXONOMY
            )
            explore_weight = min(0.5, 5.0 / (1 + total_obs))  # decays with observations
            exploit_weight = 1.0 - explore_weight

            combined = exploit_weight * expected_crossover + explore_weight * epistemic_value

            recommendations.append((page_cat, combined, expected_crossover, epistemic_value))

        recommendations.sort(key=lambda x: -x[1])
        return recommendations[:top_k]

    def get_learning_summary(self) -> Dict:
        """Summary of what the system has learned."""
        return {
            "total_observations": len(self._observation_buffer),
            "goal_page_pairs_tracked": len(self._goal_page_posteriors),
            "fulfillment_pairs_tracked": len(self._fulfillment_posteriors),
            "marker_weights_tracked": len(self._marker_weights),
            "top_effective_goal_pages": sorted(
                [
                    (k, p.effectiveness, p.observations)
                    for k, p in self._goal_page_posteriors.items()
                    if p.observations >= 3
                ],
                key=lambda x: -x[1],
            )[:10],
            "top_calibration_errors": sorted(
                [
                    (k, p.calibration_error, p.observations)
                    for k, p in self._goal_page_posteriors.items()
                    if p.observations >= 5
                ],
                key=lambda x: -x[1],
            )[:10],
            "fulfillment_updates": {
                k: {"learned": p.learned_strength, "prior": p.prior_strength,
                     "delta": p.learned_strength - p.prior_strength,
                     "observations": p.alpha + p.beta - 2}
                for k, p in self._fulfillment_posteriors.items()
                if abs(p.learned_strength - p.prior_strength) > 0.05
            },
        }


# Module-level singleton
_learner: Optional[GoalActivationLearner] = None


def get_goal_learner() -> GoalActivationLearner:
    """Get or create the singleton GoalActivationLearner."""
    global _learner
    if _learner is None:
        _learner = GoalActivationLearner()
    return _learner


def compute_crossover_score_learned(
    goal_activation: GoalActivationResult,
    archetype: str,
) -> float:
    """Crossover score using learned fulfillment strengths.

    Same as compute_crossover_score but uses posteriors that have been
    updated from observed outcomes. Falls back to priors when evidence
    is insufficient.
    """
    learner = get_goal_learner()
    fulfillment_keys = ARCHETYPE_GOAL_FULFILLMENT.get(archetype, {}).keys()
    if not fulfillment_keys:
        return 0.0

    score = 0.0
    total_weight = 0.0

    for goal_id in fulfillment_keys:
        fulfillment_strength = learner.get_learned_fulfillment(archetype, goal_id)
        activation = goal_activation.goal_scores.get(goal_id, 0.0)

        if goal_id in goal_activation.goal_shielded:
            activation *= 0.2

        score += activation * fulfillment_strength
        total_weight += fulfillment_strength

    if total_weight > 0:
        score /= total_weight

    return min(1.0, score)
