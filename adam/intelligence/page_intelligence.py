"""
Page-Level Psychological Intelligence
=======================================

Pre-indexes ad placement pages to enable real-time page-level psychological
profiling at bid time.

The problem: at bid time (<50ms), we can't fetch and analyze a page. But we
CAN look up a pre-computed profile in <2ms.

The solution: an offline pipeline continuously crawls and psychologically
profiles the pages where StackAdapt places ads. At bid time, a Redis lookup
returns the full psychological profile of the page.

This gives us the trilateral resonance layer:
    buyer_psychology × ad_psychology × page_psychology

Three tiers of resolution:
    1. Domain-level (698K mappings, in-memory) — "nytimes.com → informed mindset"
    2. URL-pattern-level (Redis, ~50K patterns) — "nytimes.com/business/* → financial concern"
    3. Full-page-level (Redis, ~500K URLs) — specific article psychological profile

Architecture:
    - PageInventoryTracker: learns placement inventory from live bid requests
    - PageProfiler: analyzes page content into PagePsychologicalProfile
    - PageIntelligenceCache: Redis-backed lookup for real-time serving
    - PageCrawlOrchestrator: batch pipeline that crawls and profiles pages
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Redis key prefix for page profiles
_REDIS_PREFIX = "informativ:page:"
_REDIS_TTL = 7 * 24 * 60 * 60  # 7 days

# Maximum pages to track in the inventory
_MAX_INVENTORY_SIZE = 100_000

# Minimum impressions before a domain is worth crawling
_MIN_IMPRESSIONS_TO_CRAWL = 5


# ---------------------------------------------------------------------------
# Page Psychological Profile — what we store per page/URL pattern
# ---------------------------------------------------------------------------

@dataclass
class PagePsychologicalProfile:
    """Full psychological intelligence about a page where an ad will appear.

    This captures everything the page does to the buyer's psychological
    state BEFORE they see the ad. The page is not neutral background —
    it's an active psychological agent that primes needs, sets emotional
    state, establishes trust context, and opens/closes persuasion channels.

    Seven intelligence layers:

    1. ACTIVATED NEEDS — What the content makes the reader want/need
       right now. A page about financial instability activates security
       needs, expert-seeking needs, loss-prevention needs. These are the
       exact channels the ad should deploy through.

    2. EMOTIONAL FIELD — Not just valence/arousal, but the emotional
       trajectory (problem→solution, threat→resolution) and the specific
       emotions activated (anxiety, aspiration, curiosity, fear, trust).

    3. COGNITIVE STATE — How much mental bandwidth remains after
       processing the content. Dense investigative journalism leaves less
       room for complex ad messaging than a photo gallery.

    4. CREDIBILITY CONTEXT — The publisher's authority transfers to ads
       (halo effect). A NYT ad carries different weight than a blog ad.
       Also: is the content editorial or sponsored? Expert or opinion?

    5. PRIMED CATEGORIES — What product/service categories the content
       naturally makes the reader think about. A home renovation article
       primes tool/material intent. A skin problem article primes beauty.

    6. PERSUASION CHANNEL STATE — Which Cialdini channels are OPEN
       (the content primed receptivity) vs CLOSED (the content created
       resistance/skepticism). A page debunking scams CLOSES scarcity
       and opens authority.

    7. COMPETITIVE ENVIRONMENT — Ad density, competing messages,
       attention competition from page elements.
    """

    # ── Identity ──
    url_pattern: str = ""
    domain: str = ""
    last_crawled: float = 0.0
    crawl_count: int = 0

    # ══════════════════════════════════════════════════════════════════
    # LAYER 1: ACTIVATED NEEDS
    # What the content makes the reader want/need RIGHT NOW
    # ══════════════════════════════════════════════════════════════════
    activated_needs: Dict[str, float] = field(default_factory=dict)
    """Top psychological needs the page activates, scored 0-1.
    Examples: security, belonging, competence, autonomy, status,
    information, entertainment, self_improvement, health_concern,
    financial_security, social_validation, problem_solving"""

    need_urgency: float = 0.0
    """How urgently the page frames the activated needs (0=informational, 1=crisis)"""

    problem_solution_frame: str = ""
    """Does the page present a problem? A solution? Both?
    Values: problem_only, solution_only, problem_and_solution,
    aspirational, informational, crisis, none"""

    # ══════════════════════════════════════════════════════════════════
    # LAYER 2: EMOTIONAL FIELD
    # The emotional state and trajectory the page creates
    # ══════════════════════════════════════════════════════════════════
    emotional_valence: float = 0.0       # -1 (negative) to +1 (positive)
    emotional_arousal: float = 0.5       # 0 (calm) to 1 (excited)
    emotional_dominance: float = 0.5     # 0 (powerless/anxious) to 1 (empowered/in control)

    dominant_emotions: List[str] = field(default_factory=list)
    """Top 3 specific emotions: anxiety, trust, curiosity, fear, excitement,
    nostalgia, frustration, hope, anger, sadness, joy, surprise"""

    emotional_trajectory: str = ""
    """How emotions shift through the content:
    escalating (gets more intense), resolving (tension→relief),
    stable (consistent tone), oscillating (back and forth)"""

    # ══════════════════════════════════════════════════════════════════
    # LAYER 3: COGNITIVE STATE
    # Mental bandwidth available for ad processing
    # ══════════════════════════════════════════════════════════════════
    cognitive_load: float = 0.5          # 0 (simple) to 1 (complex)
    remaining_bandwidth: float = 0.5     # 0 (depleted) to 1 (available)

    processing_mode: str = ""
    """What processing mode the content activates:
    analytical (central route), emotional (peripheral route),
    scanning (quick heuristics), immersive (deep engagement)"""

    attention_competition: float = 0.0
    """How much the page competes for attention with ads: 0=low, 1=high.
    Video, interactive elements, breaking news all increase competition."""

    # ══════════════════════════════════════════════════════════════════
    # LAYER 4: CREDIBILITY CONTEXT
    # Trust and authority signals that transfer to ads
    # ══════════════════════════════════════════════════════════════════
    publisher_authority: float = 0.5     # 0 (unknown blog) to 1 (NYT/Reuters)
    content_credibility: str = ""        # editorial, expert, opinion, sponsored, ugc
    trust_transfer_potential: float = 0.5
    """How much of the page's credibility transfers to ads on it.
    High on editorial pages, low on UGC/comment sections."""

    # ══════════════════════════════════════════════════════════════════
    # LAYER 5: PRIMED CATEGORIES
    # What products/services the content makes the reader think about
    # ══════════════════════════════════════════════════════════════════
    primed_categories: List[str] = field(default_factory=list)
    """Product categories the content naturally primes intent for.
    A home renovation article primes: tools, paint, furniture, contractors.
    A fitness article primes: supplements, equipment, apparel."""

    purchase_intent_signal: float = 0.0  # 0 (none) to 1 (high)

    funnel_stage_signal: str = ""
    """Where in the purchase funnel the reader likely is:
    awareness (learning about category), consideration (comparing options),
    decision (ready to buy), post_purchase (already bought, reviewing)"""

    # ══════════════════════════════════════════════════════════════════
    # LAYER 6: PERSUASION CHANNEL STATE
    # Which mechanisms are OPEN (primed) vs CLOSED (resistant)
    # ══════════════════════════════════════════════════════════════════
    mechanism_adjustments: Dict[str, float] = field(default_factory=dict)
    """Per-mechanism effectiveness multiplier. >1.0 = channel OPEN, <1.0 = CLOSED."""

    open_channels: List[str] = field(default_factory=list)
    """Mechanisms the page has primed receptivity for."""

    closed_channels: List[str] = field(default_factory=list)
    """Mechanisms the page has created resistance to.
    E.g., a page debunking marketing tricks CLOSES scarcity/urgency."""

    channel_reasoning: Dict[str, str] = field(default_factory=dict)
    """Why each channel is open/closed. E.g.:
    {'authority': 'Page cites expert sources, reader primed to trust experts',
     'scarcity': 'Page criticizes manipulative marketing, reader skeptical of urgency'}"""

    # ══════════════════════════════════════════════════════════════════
    # LAYER 7: COMPETITIVE ENVIRONMENT
    # Ad density, competing messages, attention dynamics
    # ══════════════════════════════════════════════════════════════════
    estimated_ad_density: str = ""       # low, moderate, high, very_high
    content_ad_ratio: float = 0.0        # Content words / total words (higher = less ad clutter)

    # ══════════════════════════════════════════════════════════════════
    # LAYER 8: PRIMED DECISION-MAKING STYLE
    # The cognitive machinery the page has activated in the reader
    # ══════════════════════════════════════════════════════════════════
    primed_decision_style: Dict[str, Any] = field(default_factory=dict)
    """How the page primes the reader to make decisions:
    - decision_speed: deliberative | moderate | impulsive
    - risk_orientation: risk_averse | balanced | risk_seeking
    - social_frame: conformity | balanced | independent
    - temporal_frame: immediate | moderate | future_oriented
    - elm_route: central | mixed | peripheral
    - construal_level: abstract | moderate | concrete
    - evidence_needed: high | moderate | low
    - persuasion_framing: logical_argument | balanced | emotional_appeal
    - frame_as: protection_and_prevention | balanced_value | opportunity_and_gain
    - voice: collective | authoritative | individual
    - ad_should_provide: specific guidance on what the ad needs
    - ad_should_avoid: specific guidance on what would backfire
    """

    # ══════════════════════════════════════════════════════════════════
    # NDF-ALIGNED CONSTRUCT ACTIVATIONS (preserved for congruence computation)
    # ══════════════════════════════════════════════════════════════════
    construct_activations: Dict[str, float] = field(default_factory=dict)
    """NDF dimensions extracted from page linguistic markers."""

    # ══════════════════════════════════════════════════════════════════
    # CONTENT CLASSIFICATION
    # ══════════════════════════════════════════════════════════════════
    mindset: str = "unknown"             # informed, purchasing, social, etc.
    primary_topic: str = ""              # e.g., "personal finance", "beauty tips"
    content_type: str = ""               # article, product_page, forum, social, video

    # ══════════════════════════════════════════════════════════════════
    # CREATIVE RECOMMENDATIONS
    # The synthesis: given everything above, what should the ad do?
    # ══════════════════════════════════════════════════════════════════
    optimal_tone: str = ""
    recommended_complexity: str = ""     # simple, moderate, detailed
    avoid_tactics: List[str] = field(default_factory=list)

    recommended_ad_strategy: str = ""
    """High-level creative strategy given the page context.
    E.g., 'Align with reader's activated security need using authority
    mechanism. Page has established expert trust context. Use concrete,
    evidence-based messaging. Avoid urgency (page has primed skepticism
    toward pressure tactics).'"""

    # ══════════════════════════════════════════════════════════════════
    # METADATA
    # ══════════════════════════════════════════════════════════════════
    confidence: float = 0.0             # 0-1
    profile_source: str = "domain_heuristic"  # domain_heuristic, crawled, deep_analyzed

    # ══════════════════════════════════════════════════════════════════
    # LAYER 9: NARRATIVE ARC
    # How the content's emotional journey shapes ad receptivity
    # ══════════════════════════════════════════════════════════════════
    narrative_arc_type: str = ""        # tension_release, crescendo, steady_state, oscillating, declination
    narrative_valence_trajectory: List[float] = field(default_factory=list)  # per-segment valence
    cognitive_momentum: float = 0.5     # 0 (disengaged) to 1 (flow state)
    ad_position_optimal: str = ""       # early, mid, late, post_climax

    # ══════════════════════════════════════════════════════════════════
    # LAYER 10: RHETORICAL STRUCTURE
    # How arguments are constructed — determines ELM route precisely
    # ══════════════════════════════════════════════════════════════════
    argument_structure: str = ""        # inductive, deductive, analogical, narrative, enumerated, adversarial
    evidence_density: float = 0.0       # ratio of claim-backed vs unsupported statements
    rhetorical_appeals: Dict[str, float] = field(default_factory=dict)  # ethos, pathos, logos weights

    # ══════════════════════════════════════════════════════════════════
    # LAYER 11: SEMANTIC TOPIC EMBEDDING
    # Vector representation for similarity matching
    # ══════════════════════════════════════════════════════════════════
    topic_cluster_id: str = ""
    semantic_distance_to_categories: Dict[str, float] = field(default_factory=dict)

    # ══════════════════════════════════════════════════════════════════
    # LAYER 12: SOCIAL PROOF SIGNALS
    # Engagement and social validation cues from the page
    # ══════════════════════════════════════════════════════════════════
    social_proof_signals: Dict[str, Any] = field(default_factory=dict)
    # Keys: comment_count, share_count, expert_citations, rating_present, rating_value, engagement_level

    # ══════════════════════════════════════════════════════════════════
    # LAYER 13: TEMPORAL CONTEXT
    # Content freshness and time-sensitive signals
    # ══════════════════════════════════════════════════════════════════
    content_freshness: str = ""         # breaking, recent, dated, evergreen
    temporal_relevance_score: float = 0.5
    seasonal_context: str = ""          # holiday, tax_season, back_to_school, etc.

    # ══════════════════════════════════════════════════════════════════
    # LAYER 14: ATTENTION COMPETITION (DOM-derived)
    # How much the page competes with ads for reader attention
    # ══════════════════════════════════════════════════════════════════
    ad_slot_count: int = 0
    ad_slot_positions: List[str] = field(default_factory=list)
    competing_cta_count: int = 0
    video_autoplay_detected: bool = False
    interstitial_detected: bool = False
    scroll_depth_to_content: float = 0.0
    estimated_viewability: float = 0.5

    # ══════════════════════════════════════════════════════════════════
    # LAYER 15: FULL-WIDTH EDGE DIMENSIONS (PRIMARY — replaces NDF)
    # These are the SAME 20 dimensions the bilateral cascade uses for
    # mechanism scoring. Extracted directly from text, not compressed
    # through NDF. NDF (construct_activations) is the FALLBACK only.
    # ══════════════════════════════════════════════════════════════════
    edge_dimensions: Dict[str, float] = field(default_factory=dict)
    """Full 20-dimension edge profile in the same space as BRAND_CONVERTED edges.
    When populated, the cascade should use THESE instead of construct_activations.
    Keys: regulatory_fit, construal_fit, personality_alignment, emotional_resonance,
    value_alignment, evolutionary_motive, linguistic_style, persuasion_susceptibility,
    cognitive_load_tolerance, narrative_transport, social_proof_sensitivity,
    loss_aversion_intensity, temporal_discounting, brand_relationship_depth,
    autonomy_reactance, information_seeking, mimetic_desire, interoceptive_awareness,
    cooperative_framing_fit, decision_entropy"""

    edge_scoring_tier: str = ""  # "graph_prior", "full_extraction", "ndf_fallback"

    # ══════════════════════════════════════════════════════════════════
    # VERSIONING
    # ══════════════════════════════════════════════════════════════════
    profile_version: int = 3            # Increment on schema changes
    scoring_passes_completed: List[str] = field(default_factory=list)

    def to_redis_dict(self) -> Dict[str, Any]:
        """Serialize for Redis storage. JSON-encodes complex fields."""
        return {
            "url_pattern": self.url_pattern,
            "domain": self.domain,
            "last_crawled": self.last_crawled,
            # Layer 1: Activated needs
            "activated_needs": json.dumps(self.activated_needs),
            "need_urgency": self.need_urgency,
            "problem_solution_frame": self.problem_solution_frame,
            # Layer 2: Emotional field
            "emotional_valence": self.emotional_valence,
            "emotional_arousal": self.emotional_arousal,
            "emotional_dominance": self.emotional_dominance,
            "dominant_emotions": json.dumps(self.dominant_emotions),
            "emotional_trajectory": self.emotional_trajectory,
            # Layer 3: Cognitive state
            "cognitive_load": self.cognitive_load,
            "remaining_bandwidth": self.remaining_bandwidth,
            "processing_mode": self.processing_mode,
            "attention_competition": self.attention_competition,
            # Layer 4: Credibility
            "publisher_authority": self.publisher_authority,
            "content_credibility": self.content_credibility,
            "trust_transfer_potential": self.trust_transfer_potential,
            # Layer 5: Primed categories
            "primed_categories": json.dumps(self.primed_categories),
            "purchase_intent_signal": self.purchase_intent_signal,
            "funnel_stage_signal": self.funnel_stage_signal,
            # Layer 6: Persuasion channels
            "mechanism_adjustments": json.dumps(self.mechanism_adjustments),
            "open_channels": json.dumps(self.open_channels),
            "closed_channels": json.dumps(self.closed_channels),
            "channel_reasoning": json.dumps(self.channel_reasoning),
            # Layer 7: Competitive
            "estimated_ad_density": self.estimated_ad_density,
            "content_ad_ratio": self.content_ad_ratio,
            # Layer 8: Decision style
            "primed_decision_style": json.dumps(self.primed_decision_style),
            # NDF + Classification
            "construct_activations": json.dumps(self.construct_activations),
            "mindset": self.mindset,
            "primary_topic": self.primary_topic,
            "content_type": self.content_type,
            # Creative recommendations
            "optimal_tone": self.optimal_tone,
            "recommended_complexity": self.recommended_complexity,
            "avoid_tactics": json.dumps(self.avoid_tactics),
            "recommended_ad_strategy": self.recommended_ad_strategy,
            # Meta
            "confidence": self.confidence,
            "profile_source": self.profile_source,
            # Layer 9: Narrative arc
            "narrative_arc_type": self.narrative_arc_type,
            "narrative_valence_trajectory": json.dumps(self.narrative_valence_trajectory),
            "cognitive_momentum": self.cognitive_momentum,
            "ad_position_optimal": self.ad_position_optimal,
            # Layer 10: Rhetorical structure
            "argument_structure": self.argument_structure,
            "evidence_density": self.evidence_density,
            "rhetorical_appeals": json.dumps(self.rhetorical_appeals),
            # Layer 11: Semantic topic
            "topic_cluster_id": self.topic_cluster_id,
            "semantic_distance_to_categories": json.dumps(self.semantic_distance_to_categories),
            # Layer 12: Social proof
            "social_proof_signals": json.dumps(self.social_proof_signals),
            # Layer 13: Temporal context
            "content_freshness": self.content_freshness,
            "temporal_relevance_score": self.temporal_relevance_score,
            "seasonal_context": self.seasonal_context,
            # Layer 14: Attention competition
            "ad_slot_count": self.ad_slot_count,
            "ad_slot_positions": json.dumps(self.ad_slot_positions),
            "competing_cta_count": self.competing_cta_count,
            "video_autoplay_detected": int(self.video_autoplay_detected),
            "interstitial_detected": int(self.interstitial_detected),
            "scroll_depth_to_content": self.scroll_depth_to_content,
            "estimated_viewability": self.estimated_viewability,
            # Layer 15: Full-width edge dimensions
            "edge_dimensions": json.dumps(self.edge_dimensions),
            "edge_scoring_tier": self.edge_scoring_tier,
            # Versioning
            "profile_version": self.profile_version,
            "scoring_passes_completed": json.dumps(self.scoring_passes_completed),
        }

    @classmethod
    def from_redis_dict(cls, data: Dict[str, Any]) -> "PagePsychologicalProfile":
        """Deserialize from Redis."""

        def _json_load(val, default):
            if isinstance(val, str):
                try:
                    return json.loads(val)
                except (json.JSONDecodeError, TypeError):
                    return default
            return val if val is not None else default

        return cls(
            url_pattern=data.get("url_pattern", ""),
            domain=data.get("domain", ""),
            last_crawled=float(data.get("last_crawled", 0)),
            # Layer 1
            activated_needs=_json_load(data.get("activated_needs"), {}),
            need_urgency=float(data.get("need_urgency", 0)),
            problem_solution_frame=data.get("problem_solution_frame", ""),
            # Layer 2
            emotional_valence=float(data.get("emotional_valence", 0)),
            emotional_arousal=float(data.get("emotional_arousal", 0.5)),
            emotional_dominance=float(data.get("emotional_dominance", 0.5)),
            dominant_emotions=_json_load(data.get("dominant_emotions"), []),
            emotional_trajectory=data.get("emotional_trajectory", ""),
            # Layer 3
            cognitive_load=float(data.get("cognitive_load", 0.5)),
            remaining_bandwidth=float(data.get("remaining_bandwidth", 0.5)),
            processing_mode=data.get("processing_mode", ""),
            attention_competition=float(data.get("attention_competition", 0)),
            # Layer 4
            publisher_authority=float(data.get("publisher_authority", 0.5)),
            content_credibility=data.get("content_credibility", ""),
            trust_transfer_potential=float(data.get("trust_transfer_potential", 0.5)),
            # Layer 5
            primed_categories=_json_load(data.get("primed_categories"), []),
            purchase_intent_signal=float(data.get("purchase_intent_signal", 0)),
            funnel_stage_signal=data.get("funnel_stage_signal", ""),
            # Layer 6
            mechanism_adjustments=_json_load(data.get("mechanism_adjustments"), {}),
            open_channels=_json_load(data.get("open_channels"), []),
            closed_channels=_json_load(data.get("closed_channels"), []),
            channel_reasoning=_json_load(data.get("channel_reasoning"), {}),
            # Layer 7
            estimated_ad_density=data.get("estimated_ad_density", ""),
            content_ad_ratio=float(data.get("content_ad_ratio", 0)),
            # Layer 8
            primed_decision_style=_json_load(data.get("primed_decision_style"), {}),
            # NDF + Classification
            construct_activations=_json_load(data.get("construct_activations"), {}),
            mindset=data.get("mindset", "unknown"),
            primary_topic=data.get("primary_topic", ""),
            content_type=data.get("content_type", ""),
            # Creative
            optimal_tone=data.get("optimal_tone", ""),
            recommended_complexity=data.get("recommended_complexity", ""),
            avoid_tactics=_json_load(data.get("avoid_tactics"), []),
            recommended_ad_strategy=data.get("recommended_ad_strategy", ""),
            # Meta
            confidence=float(data.get("confidence", 0)),
            profile_source=data.get("profile_source", "domain_heuristic"),
            # Layer 9
            narrative_arc_type=data.get("narrative_arc_type", ""),
            narrative_valence_trajectory=_json_load(data.get("narrative_valence_trajectory"), []),
            cognitive_momentum=float(data.get("cognitive_momentum", 0.5)),
            ad_position_optimal=data.get("ad_position_optimal", ""),
            # Layer 10
            argument_structure=data.get("argument_structure", ""),
            evidence_density=float(data.get("evidence_density", 0)),
            rhetorical_appeals=_json_load(data.get("rhetorical_appeals"), {}),
            # Layer 11
            topic_cluster_id=data.get("topic_cluster_id", ""),
            semantic_distance_to_categories=_json_load(data.get("semantic_distance_to_categories"), {}),
            # Layer 12
            social_proof_signals=_json_load(data.get("social_proof_signals"), {}),
            # Layer 13
            content_freshness=data.get("content_freshness", ""),
            temporal_relevance_score=float(data.get("temporal_relevance_score", 0.5)),
            seasonal_context=data.get("seasonal_context", ""),
            # Layer 14
            ad_slot_count=int(data.get("ad_slot_count", 0)),
            ad_slot_positions=_json_load(data.get("ad_slot_positions"), []),
            competing_cta_count=int(data.get("competing_cta_count", 0)),
            video_autoplay_detected=bool(int(data.get("video_autoplay_detected", 0))),
            interstitial_detected=bool(int(data.get("interstitial_detected", 0))),
            scroll_depth_to_content=float(data.get("scroll_depth_to_content", 0)),
            estimated_viewability=float(data.get("estimated_viewability", 0.5)),
            # Layer 15
            edge_dimensions=_json_load(data.get("edge_dimensions"), {}),
            edge_scoring_tier=data.get("edge_scoring_tier", ""),
            # Versioning
            profile_version=int(data.get("profile_version", 1)),
            scoring_passes_completed=_json_load(data.get("scoring_passes_completed"), []),
        )


# ---------------------------------------------------------------------------
# Page Inventory Tracker — learns which pages StackAdapt uses from live traffic
# ---------------------------------------------------------------------------

class PageInventoryTracker:
    """Learns the placement inventory from live creative intelligence requests.

    Every time a creative intelligence request arrives with a page_url,
    this tracker records it. Over time, it builds a frequency-ranked
    inventory of all placement pages/domains.

    The crawler uses this inventory to decide what to crawl next:
    highest-impression pages get crawled first.
    """

    def __init__(self, max_size: int = _MAX_INVENTORY_SIZE):
        self._domain_counts: Counter = Counter()
        self._url_pattern_counts: Counter = Counter()
        self._recent_urls: List[str] = []  # Last 1000 unique URLs
        self._max_size = max_size

    def record_placement(self, page_url: str) -> None:
        """Record a placement URL from a bid request."""
        if not page_url:
            return

        domain = _extract_domain(page_url)
        if domain:
            self._domain_counts[domain] += 1

        pattern = _url_to_pattern(page_url)
        if pattern:
            self._url_pattern_counts[pattern] += 1

            # Track recent unique URLs for crawling
            if page_url not in self._recent_urls[-100:]:
                self._recent_urls.append(page_url)
                if len(self._recent_urls) > 1000:
                    self._recent_urls = self._recent_urls[-1000:]

    def get_top_domains(self, n: int = 100) -> List[Tuple[str, int]]:
        """Get top N domains by impression count."""
        return self._domain_counts.most_common(n)

    def get_top_patterns(self, n: int = 500) -> List[Tuple[str, int]]:
        """Get top N URL patterns by impression count."""
        return self._url_pattern_counts.most_common(n)

    def get_crawl_candidates(
        self, n: int = 100, min_impressions: int = _MIN_IMPRESSIONS_TO_CRAWL,
    ) -> List[str]:
        """Get URLs that should be crawled next (high impression, not yet crawled)."""
        candidates = [
            pattern for pattern, count in self._url_pattern_counts.most_common(n * 2)
            if count >= min_impressions
        ]
        return candidates[:n]

    @property
    def stats(self) -> Dict[str, Any]:
        return {
            "unique_domains": len(self._domain_counts),
            "unique_patterns": len(self._url_pattern_counts),
            "total_impressions": sum(self._domain_counts.values()),
            "recent_urls_tracked": len(self._recent_urls),
        }


# ---------------------------------------------------------------------------
# Page Intelligence Cache — Redis-backed lookup for real-time serving
# ---------------------------------------------------------------------------

class PageIntelligenceCache:
    """Redis-backed cache of page psychological profiles.

    At bid time (<2ms), looks up the pre-computed profile for a page URL.
    Falls back to domain-level profile if specific URL not indexed.
    Falls back to ContextIntelligenceService if domain not indexed.
    """

    def __init__(self):
        self._redis = None
        self._local_cache: Dict[str, PagePsychologicalProfile] = {}
        self._local_cache_ts: Dict[str, float] = {}
        self._local_ttl = 300.0  # 5 min local cache

    def _get_redis(self):
        if self._redis is not None:
            return self._redis
        try:
            import redis
            self._redis = redis.Redis(
                host="localhost", port=6379, decode_responses=True,
            )
            self._redis.ping()
            return self._redis
        except Exception:
            return None

    def lookup(self, page_url: str) -> Optional[PagePsychologicalProfile]:
        """Look up page profile with four-tier fallback.

        1. Exact URL pattern match (Redis)
        2. Domain-level pattern match (Redis)
        3. Taxonomy inference (category/author/domain hierarchy)
        4. None (caller falls back to ContextIntelligenceService)

        After any source provides a profile, audience reaction corrections
        are applied as the final step (confirming or correcting the
        content-based NDF prediction with actual audience response data).
        """
        if not page_url:
            return None

        # Check local cache first
        pattern = _url_to_pattern(page_url)
        now = time.time()
        if pattern in self._local_cache:
            if now - self._local_cache_ts.get(pattern, 0) < self._local_ttl:
                return self._local_cache[pattern]

        profile: Optional[PagePsychologicalProfile] = None

        # Try Redis: URL pattern
        r = self._get_redis()
        if r:
            try:
                key = f"{_REDIS_PREFIX}{pattern}"
                data = r.hgetall(key)
                if data:
                    profile = PagePsychologicalProfile.from_redis_dict(data)
            except Exception:
                pass

            # Try Redis: domain-level fallback
            if profile is None:
                domain = _extract_domain(page_url)
                if domain:
                    try:
                        key = f"{_REDIS_PREFIX}domain:{domain}"
                        data = r.hgetall(key)
                        if data:
                            profile = PagePsychologicalProfile.from_redis_dict(data)
                    except Exception:
                        pass

        # Try taxonomy inference: uses category/subcategory/author hierarchy
        # to predict NDF for unscored articles based on learned patterns
        if profile is None:
            domain = _extract_domain(page_url)
            if domain:
                try:
                    from adam.intelligence.domain_taxonomy import get_domain_taxonomy
                    taxonomy = get_domain_taxonomy(domain)
                    inferred = taxonomy.infer_psychology(url=page_url)
                    if inferred:
                        edge_dims = inferred.get("edge_dimensions", {})
                        profile = PagePsychologicalProfile(
                            url_pattern=pattern,
                            domain=domain,
                            last_crawled=0.0,  # Not crawled — inferred
                            edge_dimensions=edge_dims,
                            construct_activations=edge_dims,  # Legacy compat
                            mechanism_adjustments=inferred.get("mechanism_adjustments", {}),
                            mindset=inferred.get("mindset", "unknown"),
                            confidence=inferred.get("confidence", 0.3),
                            profile_source=f"taxonomy_{inferred.get('inference_level', 'domain')}",
                            edge_scoring_tier=f"taxonomy_{inferred.get('inference_level', 'domain')}",
                        )
                        # Populate emotional fields from edge dims
                        profile.emotional_valence = edge_dims.get("regulatory_fit", 0.5) * 2 - 1
                        profile.emotional_arousal = edge_dims.get("emotional_resonance", 0.5)
                        profile.cognitive_load = 1.0 - edge_dims.get("cognitive_load_tolerance", 0.5)
                except Exception:
                    pass

        # Apply audience reaction corrections if available
        # Reactions confirm or correct the content-based NDF prediction
        if profile is not None:
            try:
                from adam.intelligence.reaction_intelligence import get_reaction_cache
                reaction_cache = get_reaction_cache()
                domain = _extract_domain(page_url) or ""
                is_ctv = profile.content_type == "ctv_content"
                content_key = profile.url_pattern if not is_ctv else domain
                reaction = reaction_cache.lookup(content_key, is_ctv=is_ctv)
                if reaction:
                    from adam.intelligence.reaction_intelligence import apply_reaction_corrections
                    profile = apply_reaction_corrections(profile, reaction)
            except Exception:
                pass

            self._local_cache[pattern] = profile
            self._local_cache_ts[pattern] = now
            return profile

        # ── FINAL FALLBACK: URL Intelligence (7-tier resolution) ──
        # Even for completely unknown URLs, extract signals from the URL
        # structure itself: domain, category, content type, slug keywords.
        # This ALWAYS returns something — the system never returns nothing.
        if page_url:
            try:
                from adam.intelligence.url_intelligence import resolve_url_intelligence
                url_result = resolve_url_intelligence(page_url, page_cache=self)
                if url_result and url_result.get("edge_dimensions"):
                    edge_dims = url_result["edge_dimensions"]
                    profile = PagePsychologicalProfile(
                        url_pattern=pattern,
                        domain=_extract_domain(page_url) or "",
                        last_crawled=0.0,
                        edge_dimensions=edge_dims,
                        construct_activations=edge_dims,
                        confidence=url_result.get("confidence", 0.15),
                        profile_source=url_result.get("resolution_tier", "url_intelligence"),
                        edge_scoring_tier=url_result.get("resolution_tier", ""),
                    )
                    # Set emotional fields from edge dims
                    profile.emotional_valence = edge_dims.get("regulatory_fit", 0.5) * 2 - 1
                    profile.emotional_arousal = edge_dims.get("emotional_resonance", 0.5)
                    profile.cognitive_load = 1.0 - edge_dims.get("cognitive_load_tolerance", 0.5)
                    # Set mindset from URL signals
                    url_signals = url_result.get("url_signals", {})
                    profile.primary_topic = url_signals.get("category", "")
                    profile.content_type = url_signals.get("content_type", "article")

                    self._local_cache[pattern] = profile
                    self._local_cache_ts[pattern] = now
                    return profile
            except Exception:
                pass

        return None

    def store(self, profile: PagePsychologicalProfile) -> bool:
        """Store a page profile in Redis."""
        r = self._get_redis()
        if not r:
            return False

        try:
            key = f"{_REDIS_PREFIX}{profile.url_pattern}"
            r.hset(key, mapping=profile.to_redis_dict())
            r.expire(key, _REDIS_TTL)

            # Also store domain-level if this is the best profile for the domain
            domain_key = f"{_REDIS_PREFIX}domain:{profile.domain}"
            existing = r.hget(domain_key, "confidence")
            if existing is None or float(existing) < profile.confidence:
                r.hset(domain_key, mapping=profile.to_redis_dict())
                r.expire(domain_key, _REDIS_TTL)

            return True
        except Exception as e:
            logger.warning("Failed to store page profile: %s", e)
            return False

    @property
    def stats(self) -> Dict[str, Any]:
        r = self._get_redis()
        if not r:
            return {"redis_available": False, "local_cache_size": len(self._local_cache)}
        try:
            # Count keys with our prefix
            cursor, keys = r.scan(0, match=f"{_REDIS_PREFIX}*", count=100)
            estimated = len(keys)  # Rough estimate from first scan
            return {
                "redis_available": True,
                "local_cache_size": len(self._local_cache),
                "estimated_indexed_pages": estimated,
            }
        except Exception:
            return {"redis_available": False, "local_cache_size": len(self._local_cache)}


# ---------------------------------------------------------------------------
# Page Profiler — NDF-grounded psychological analysis of page content
# ---------------------------------------------------------------------------
#
# The page profiler uses the same 7-dimension NDF framework as buyer profiling
# (from NONCONSCIOUS_DECISION_MODELS.md). This enables true trilateral
# congruence: buyer NDF × ad NDF × page NDF.
#
# Each NDF dimension maps to specific linguistic markers in the page content:
#   α (approach_avoidance): gain/loss framing language
#   τ (temporal_horizon): future vs present references
#   σ (social_calibration): we/they vs I language, social references
#   υ (uncertainty_tolerance): hedging vs certainty markers
#   ρ (status_sensitivity): premium/luxury/comparison language
#   κ (cognitive_engagement): causal reasoning, clause complexity
#   λ (arousal_seeking): emotional intensity, exclamation, novelty
#
# The page NDF tells us: what psychological state does this content PRIME
# the buyer into? A prevention-framed news article about financial risk
# creates a negative-α, low-υ state. An aspirational lifestyle blog
# creates a positive-α, high-λ state.

# Linguistic marker word lists (from Pennebaker LIWC + Gosling taxonomy)
_PROMOTION_WORDS = frozenset([
    "gain", "achieve", "ideal", "hope", "aspire", "dream", "opportunity",
    "grow", "improve", "advance", "win", "succeed", "accomplish", "thrive",
    "progress", "potential", "maximize", "upgrade", "enhance", "earn",
])
_PREVENTION_WORDS = frozenset([
    "safe", "secure", "duty", "protect", "careful", "avoid", "prevent",
    "risk", "danger", "threat", "guard", "caution", "warning", "concern",
    "vulnerable", "defend", "shield", "insurance", "guarantee", "reliable",
])
_FUTURE_WORDS = frozenset([
    "will", "plan", "eventually", "investment", "long-term", "future",
    "tomorrow", "next year", "upcoming", "forecast", "predict", "roadmap",
    "strategy", "vision", "goal", "retirement", "savings", "sustainable",
])
_PRESENT_WORDS = frozenset([
    "now", "immediately", "today", "instant", "right now", "hurry",
    "limited time", "act fast", "don't wait", "currently", "breaking",
    "live", "happening", "urgent", "flash", "tonight", "this week",
])
_SOCIAL_WORDS = frozenset([
    "we", "us", "everyone", "community", "together", "people", "society",
    "family", "friends", "team", "group", "collective", "public", "shared",
    "millions", "thousands", "popular", "trending", "viral", "joined",
])
_CERTAINTY_WORDS = frozenset([
    "definitely", "absolutely", "always", "never", "certain", "proven",
    "guaranteed", "undeniable", "clearly", "obviously", "without doubt",
    "100%", "fact", "confirmed", "established", "conclusive", "definitive",
])
_TENTATIVE_WORDS = frozenset([
    "might", "perhaps", "could", "maybe", "possibly", "appears",
    "seems", "suggests", "likely", "reportedly", "allegedly", "uncertain",
    "debatable", "questionable", "preliminary", "estimated", "roughly",
])
_STATUS_WORDS = frozenset([
    "premium", "luxury", "exclusive", "elite", "best", "top-tier",
    "superior", "finest", "sophisticated", "prestigious", "high-end",
    "award-winning", "world-class", "professional", "expert", "artisan",
])
_CAUSAL_WORDS = frozenset([
    "because", "therefore", "consequently", "which means", "as a result",
    "due to", "caused by", "leads to", "explains", "reason", "evidence",
    "research shows", "study", "according to", "data", "analysis",
])
_AROUSAL_WORDS = frozenset([
    "amazing", "incredible", "unbelievable", "shocking", "stunning",
    "explosive", "revolutionary", "breakthrough", "extraordinary", "epic",
    "mind-blowing", "insane", "wild", "jaw-dropping", "thrilling",
])
_NOVELTY_WORDS = frozenset([
    "new", "different", "unique", "first", "innovative", "novel",
    "unprecedented", "revolutionary", "cutting-edge", "latest", "emerging",
    "never before", "reimagined", "transformed", "disrupting", "fresh",
])


def _count_word_hits(text_lower: str, words: frozenset, word_count: int) -> float:
    """Count normalized frequency of marker words in text."""
    hits = sum(1 for w in words if w in text_lower)
    if word_count == 0:
        return 0.0
    return hits / (word_count / 100.0)


def profile_page_content(
    url: str,
    text_content: str,
    title: str = "",
    meta_description: str = "",
) -> PagePsychologicalProfile:
    """Extract NDF-grounded psychological profile from page content.

    Uses the 7-dimension Nonconscious Decision Fingerprint framework
    (NONCONSCIOUS_DECISION_MODELS.md) to profile the psychological
    state the page content primes in the reader.

    Each dimension is extracted via Pennebaker-inspired linguistic
    marker analysis — the same markers used for buyer NDF extraction
    from reviews, ensuring the page profile lives in the same
    psychological space as buyer profiles.

    This enables true trilateral congruence computation:
        congruence = buyer_NDF · page_NDF · ad_NDF
    """
    domain = _extract_domain(url)
    pattern = _url_to_pattern(url)

    profile = PagePsychologicalProfile(
        url_pattern=pattern,
        domain=domain or "",
        last_crawled=time.time(),
        profile_source="crawled_ndf",
    )

    if not text_content:
        profile.confidence = 0.1
        return profile

    text_lower = text_content.lower()
    words = text_content.split()
    word_count = len(words)

    # ══════════════════════════════════════════════════════════════════
    # NDF DIMENSION EXTRACTION (from page content linguistic markers)
    # ══════════════════════════════════════════════════════════════════

    # α: Approach-Avoidance — does the page prime gain or loss framing?
    promotion = _count_word_hits(text_lower, _PROMOTION_WORDS, word_count)
    prevention = _count_word_hits(text_lower, _PREVENTION_WORDS, word_count)
    alpha = (promotion - prevention) / max(promotion + prevention, 0.01)
    page_approach_avoidance = max(-1.0, min(1.0, alpha))

    # τ: Temporal Horizon — does the page orient toward future or present?
    future = _count_word_hits(text_lower, _FUTURE_WORDS, word_count)
    present = _count_word_hits(text_lower, _PRESENT_WORDS, word_count)
    page_temporal = future / max(future + present, 0.01)

    # σ: Social Calibration — does the page emphasize collective or individual?
    social = _count_word_hits(text_lower, _SOCIAL_WORDS, word_count)
    i_count = text_lower.count(" i ") + text_lower.count(" my ") + text_lower.count(" me ")
    i_per_100 = i_count / max(word_count / 100.0, 0.01)
    page_social = social / max(social + i_per_100, 0.01)

    # υ: Uncertainty Tolerance — does the page convey certainty or ambiguity?
    certainty = _count_word_hits(text_lower, _CERTAINTY_WORDS, word_count)
    tentative = _count_word_hits(text_lower, _TENTATIVE_WORDS, word_count)
    page_uncertainty = tentative / max(certainty + tentative, 0.01)

    # ρ: Status Sensitivity — does the page signal premium/prestige?
    status = _count_word_hits(text_lower, _STATUS_WORDS, word_count)
    page_status = min(1.0, status * 2.0)

    # κ: Cognitive Engagement — does the page demand deep processing?
    causal = _count_word_hits(text_lower, _CAUSAL_WORDS, word_count)
    avg_word_len = sum(len(w) for w in words) / max(1, word_count)
    sentences = max(1, text_content.count(".") + text_content.count("!") + text_content.count("?"))
    avg_sent_len = word_count / sentences
    complexity = (avg_word_len - 3.0) / 4.0 * 0.3 + (avg_sent_len - 10.0) / 20.0 * 0.3 + causal * 0.4
    page_cognitive = max(0.0, min(1.0, complexity))

    # λ: Arousal Seeking — does the page create excitement/stimulation?
    arousal = _count_word_hits(text_lower, _AROUSAL_WORDS, word_count)
    novelty = _count_word_hits(text_lower, _NOVELTY_WORDS, word_count)
    exclamation_density = text_content.count("!") / max(1, sentences)
    page_arousal = min(1.0, (arousal + novelty) * 1.5 + exclamation_density * 0.3)

    # Store NDF as construct activations for downstream use
    profile.construct_activations = {
        "approach_avoidance": round(page_approach_avoidance, 3),
        "temporal_horizon": round(page_temporal, 3),
        "social_calibration": round(page_social, 3),
        "uncertainty_tolerance": round(page_uncertainty, 3),
        "status_sensitivity": round(page_status, 3),
        "cognitive_engagement": round(page_cognitive, 3),
        "arousal_seeking": round(page_arousal, 3),
    }

    # Map NDF to profile fields
    profile.emotional_valence = page_approach_avoidance
    profile.emotional_arousal = page_arousal
    profile.cognitive_load = page_cognitive
    profile.purchase_intent_signal = max(0.0, min(1.0,
        (1.0 - page_temporal) * 0.3 +  # Present-oriented → higher intent
        (1.0 - page_uncertainty) * 0.3 +  # Certain → closer to decision
        page_status * 0.2 +  # Status content → purchase mode
        (page_arousal * 0.2)  # High arousal → action-oriented
    ))

    # ══════════════════════════════════════════════════════════════════
    # CONTENT CLASSIFICATION
    # ══════════════════════════════════════════════════════════════════

    # Multi-signal content classification — avoids false positives from "$" alone
    # (which triggers on news sites mentioning dollar amounts, stock prices, etc.)
    _purchase_cues = sum(1 for w in ["add to cart", "buy now", "checkout", "add to bag",
                                      "shop now", "order now"] if w in text_lower)
    _price_cues = sum(1 for w in ["price", "msrp", "sale price", "regular price",
                                   "free shipping", "in stock"] if w in text_lower)
    _dollar_near_commerce = (
        "$" in text_content
        and any(w in text_lower for w in ["price", "buy", "cart", "order", "shipping", "cost"])
    )
    if _purchase_cues >= 1 or (_price_cues >= 2 and _dollar_near_commerce):
        profile.content_type = "product_page"
        profile.mindset = "purchasing"
    elif any(w in text_lower for w in ["review", "rating", "stars", "recommend"]):
        profile.content_type = "review_page"
        profile.mindset = "researching"
    elif any(w in text_lower for w in ["breaking", "reported", "according to", "officials"]):
        profile.content_type = "article"
        profile.mindset = "informed"
    elif any(w in text_lower for w in ["comment", "reply", "share", "like", "follow"]):
        profile.content_type = "social"
        profile.mindset = "social"
    elif any(w in text_lower for w in ["how to", "tutorial", "guide", "step"]):
        profile.content_type = "educational"
        profile.mindset = "researching"
    elif page_status > 0.5 and page_approach_avoidance > 0.3:
        profile.content_type = "lifestyle"
        profile.mindset = "relaxed"
    else:
        profile.content_type = "article"
        profile.mindset = "informed" if page_cognitive > 0.5 else "relaxed"

    # ══════════════════════════════════════════════════════════════════
    # NDF-GROUNDED MECHANISM ADJUSTMENTS
    # ══════════════════════════════════════════════════════════════════
    # Instead of mindset-to-mechanism lookup tables, derive mechanism
    # adjustments directly from the NDF dimensions using the
    # compute_mechanism_susceptibility equations from
    # NONCONSCIOUS_DECISION_MODELS.md Model 6.

    import math

    def _sigmoid(x: float) -> float:
        return 1.0 / (1.0 + math.exp(-x))

    ndf = profile.construct_activations
    a = ndf["approach_avoidance"]
    t = ndf["temporal_horizon"]
    s = ndf["social_calibration"]
    u = ndf["uncertainty_tolerance"]
    r = ndf["status_sensitivity"]
    k = ndf["cognitive_engagement"]
    l = ndf["arousal_seeking"]

    # Mechanism susceptibility from NDF (Model 6 equations)
    raw_susceptibility = {
        "reciprocity": _sigmoid(0.4 * s + 0.3 * a + 0.2 * (1 - r) + 0.1 * u),
        "commitment": _sigmoid(0.5 * (1 - u) + 0.3 * (1 - l) + 0.2 * t),
        "social_proof": _sigmoid(0.6 * s + 0.2 * (1 - k) + 0.2 * (1 - u)),
        "authority": _sigmoid(0.4 * r + 0.3 * (1 - u) + 0.2 * (1 - k) + 0.1 * (-a)),
        "liking": _sigmoid(0.4 * s + 0.3 * a + 0.2 * l + 0.1 * (1 - r)),
        "scarcity": _sigmoid(0.4 * a + 0.3 * l + 0.2 * (1 - t) + 0.1 * r),
        "unity": _sigmoid(0.6 * s + 0.2 * a + 0.1 * (1 - u) + 0.1 * (1 - l)),
        "loss_aversion": _sigmoid(0.5 * (-a) + 0.3 * (1 - u) + 0.2 * (1 - t)),
        "curiosity": _sigmoid(0.4 * l + 0.3 * k + 0.2 * u + 0.1 * a),
        "cognitive_ease": _sigmoid(0.5 * (1 - k) + 0.3 * (1 - u) + 0.2 * (1 - l)),
    }

    # Convert susceptibility to mechanism adjustment multipliers
    # Baseline is 0.5 (neutral sigmoid output). Above 0.5 → boost; below → dampen.
    profile.mechanism_adjustments = {
        mech: round(0.6 + suscept * 0.8, 3)  # Maps [0,1] → [0.6, 1.4]
        for mech, suscept in raw_susceptibility.items()
    }

    # ══════════════════════════════════════════════════════════════════
    # AVOID TACTICS (from NDF analysis)
    # ══════════════════════════════════════════════════════════════════
    if page_approach_avoidance < -0.3:
        profile.avoid_tactics.append("aspirational_messaging")
        profile.avoid_tactics.append("gain_framing")
    if page_uncertainty > 0.7:
        profile.avoid_tactics.append("definitive_claims")
    if page_social < 0.3 and page_cognitive > 0.6:
        profile.avoid_tactics.append("herd_messaging")
    if page_arousal < 0.2:
        profile.avoid_tactics.append("high_intensity_emotional")

    # ══════════════════════════════════════════════════════════════════
    # TONE AND COMPLEXITY
    # ══════════════════════════════════════════════════════════════════
    if page_cognitive > 0.7:
        profile.recommended_complexity = "detailed"
        profile.optimal_tone = "analytical, evidence-based"
    elif page_cognitive < 0.3:
        profile.recommended_complexity = "simple"
        profile.optimal_tone = "clear, direct"
    else:
        profile.recommended_complexity = "moderate"
        profile.optimal_tone = "balanced"

    if page_approach_avoidance < -0.2:
        profile.optimal_tone = "reassuring, protective"
    elif page_arousal > 0.6:
        profile.optimal_tone = "energetic, compelling"

    # ══════════════════════════════════════════════════════════════════
    # LAYER 1: ACTIVATED NEEDS
    # What the content makes the reader want/need RIGHT NOW
    # ══════════════════════════════════════════════════════════════════
    needs: Dict[str, float] = {}

    # Security need — activated by threat, risk, financial concern
    security_words = sum(1 for w in ["safe", "secure", "protect", "insurance", "guarantee",
                                      "risk", "threat", "danger", "crisis", "warning",
                                      "stability", "reliable", "trust"] if w in text_lower)
    if security_words > 0:
        needs["security"] = min(1.0, security_words / max(1, word_count / 200))

    # Belonging need — activated by community, social, identity
    belonging_words = sum(1 for w in ["community", "together", "belong", "family", "join",
                                       "shared", "tribe", "team", "united", "movement"] if w in text_lower)
    if belonging_words > 0:
        needs["belonging"] = min(1.0, belonging_words / max(1, word_count / 200))

    # Competence need — activated by learning, skill, mastery
    competence_words = sum(1 for w in ["learn", "skill", "master", "improve", "achieve",
                                        "expert", "professional", "succeed", "competent",
                                        "knowledge", "training"] if w in text_lower)
    if competence_words > 0:
        needs["competence"] = min(1.0, competence_words / max(1, word_count / 200))

    # Status need — activated by luxury, premium, exclusive
    if page_status > 0.3:
        needs["status"] = round(page_status, 3)

    # Health concern — activated by health/wellness/medical content
    health_words = sum(1 for w in ["health", "medical", "doctor", "symptom", "treatment",
                                    "wellness", "condition", "diagnosis", "therapy",
                                    "pain", "disease"] if w in text_lower)
    if health_words > 0:
        needs["health_concern"] = min(1.0, health_words / max(1, word_count / 200))

    # Financial security — activated by money, investment, savings
    finance_words = sum(1 for w in ["invest", "savings", "retirement", "mortgage", "budget",
                                     "debt", "income", "portfolio", "financial",
                                     "economy", "inflation"] if w in text_lower)
    if finance_words > 0:
        needs["financial_security"] = min(1.0, finance_words / max(1, word_count / 200))

    # Self-improvement — activated by growth, change, transformation
    growth_words = sum(1 for w in ["transform", "change", "growth", "better", "improve",
                                    "upgrade", "potential", "journey", "progress"] if w in text_lower)
    if growth_words > 0:
        needs["self_improvement"] = min(1.0, growth_words / max(1, word_count / 200))

    # Problem-solving — activated by how-to, solution, fix
    problem_words = sum(1 for w in ["problem", "solution", "fix", "solve", "resolve",
                                     "troubleshoot", "issue", "challenge"] if w in text_lower)
    if problem_words > 0:
        needs["problem_solving"] = min(1.0, problem_words / max(1, word_count / 200))

    profile.activated_needs = {k: round(v, 3) for k, v in sorted(
        needs.items(), key=lambda x: x[1], reverse=True
    )[:5]}

    # Need urgency
    urgency_signals = sum(1 for w in ["urgent", "immediately", "crisis", "emergency",
                                       "critical", "breaking", "alert", "warning",
                                       "deadline", "expires"] if w in text_lower)
    profile.need_urgency = min(1.0, urgency_signals / max(1, word_count / 500))

    # Problem-solution frame
    has_problem = any(w in text_lower for w in ["problem", "issue", "challenge", "risk", "threat", "crisis"])
    has_solution = any(w in text_lower for w in ["solution", "fix", "resolve", "treat", "cure", "answer", "how to"])
    if has_problem and has_solution:
        profile.problem_solution_frame = "problem_and_solution"
    elif has_problem:
        profile.problem_solution_frame = "problem_only"
    elif has_solution:
        profile.problem_solution_frame = "solution_only"
    elif page_approach_avoidance > 0.3:
        profile.problem_solution_frame = "aspirational"
    else:
        profile.problem_solution_frame = "informational"

    # ══════════════════════════════════════════════════════════════════
    # LAYER 2: EMOTIONAL FIELD (expanded beyond valence/arousal)
    # ══════════════════════════════════════════════════════════════════
    _emotion_markers = {
        "anxiety": ["anxiety", "worry", "nervous", "stress", "uncertain", "fearful"],
        "trust": ["trust", "reliable", "proven", "established", "credible", "verified"],
        "curiosity": ["discover", "explore", "wonder", "reveal", "surprising", "mystery"],
        "fear": ["fear", "danger", "threat", "alarming", "terrifying", "scary"],
        "excitement": ["exciting", "thrilling", "amazing", "incredible", "breakthrough"],
        "nostalgia": ["remember", "classic", "tradition", "heritage", "memories", "vintage"],
        "frustration": ["frustrated", "annoying", "failed", "broken", "terrible", "worst"],
        "hope": ["hope", "promising", "optimistic", "bright", "future", "potential"],
    }

    emotion_scores: Dict[str, float] = {}
    for emotion, markers in _emotion_markers.items():
        hits = sum(1 for m in markers if m in text_lower)
        if hits > 0:
            emotion_scores[emotion] = min(1.0, hits / max(1, word_count / 300))

    profile.dominant_emotions = [e for e, _ in sorted(
        emotion_scores.items(), key=lambda x: x[1], reverse=True
    )[:3]]

    # Emotional dominance: empowered vs powerless
    empowered = sum(1 for w in ["control", "empower", "master", "confident", "strong",
                                  "capable", "achieve", "lead"] if w in text_lower)
    powerless = sum(1 for w in ["helpless", "victim", "vulnerable", "overwhelmed",
                                  "trapped", "stuck", "dependent"] if w in text_lower)
    total_dom = empowered + powerless
    profile.emotional_dominance = empowered / max(1, total_dom) if total_dom > 0 else 0.5

    # Emotional trajectory
    if word_count > 200:
        first_half = text_lower[:len(text_lower) // 2]
        second_half = text_lower[len(text_lower) // 2:]
        neg_first = sum(1 for w in ["problem", "risk", "threat", "concern", "fear"] if w in first_half)
        pos_second = sum(1 for w in ["solution", "hope", "improve", "better", "resolve"] if w in second_half)
        neg_second = sum(1 for w in ["problem", "risk", "threat", "concern", "fear"] if w in second_half)
        if neg_first > 1 and pos_second > neg_second:
            profile.emotional_trajectory = "resolving"
        elif neg_second > neg_first:
            profile.emotional_trajectory = "escalating"
        else:
            profile.emotional_trajectory = "stable"
    else:
        profile.emotional_trajectory = "stable"

    # ══════════════════════════════════════════════════════════════════
    # LAYER 3: COGNITIVE STATE (expanded)
    # ══════════════════════════════════════════════════════════════════
    # Remaining bandwidth inversely proportional to cognitive load + length
    length_fatigue = min(0.3, word_count / 5000.0)
    profile.remaining_bandwidth = round(max(0.1, 1.0 - page_cognitive * 0.5 - length_fatigue), 3)

    if page_cognitive > 0.6 and word_count > 500:
        profile.processing_mode = "analytical"
    elif page_arousal > 0.5:
        profile.processing_mode = "emotional"
    elif word_count < 200:
        profile.processing_mode = "scanning"
    else:
        profile.processing_mode = "immersive"

    # Attention competition from page elements
    has_video = any(w in text_lower for w in ["watch video", "play video", "youtube", "embed"])
    has_gallery = any(w in text_lower for w in ["gallery", "slideshow", "photos", "images"])
    profile.attention_competition = min(1.0,
        (0.3 if has_video else 0.0) +
        (0.2 if has_gallery else 0.0) +
        (0.2 if page_arousal > 0.7 else 0.0) +
        (0.1 if "breaking" in text_lower else 0.0)
    )

    # ══════════════════════════════════════════════════════════════════
    # LAYER 4: CREDIBILITY CONTEXT
    # ══════════════════════════════════════════════════════════════════
    _HIGH_AUTHORITY_DOMAINS = frozenset([
        "nytimes.com", "washingtonpost.com", "reuters.com", "bbc.com",
        "apnews.com", "wsj.com", "bloomberg.com", "economist.com",
        "nature.com", "science.org", "nejm.org", "nih.gov", "cdc.gov",
        "harvard.edu", "mit.edu", "stanford.edu",
    ])
    _MEDIUM_AUTHORITY_DOMAINS = frozenset([
        "cnn.com", "foxnews.com", "nbcnews.com", "techcrunch.com",
        "forbes.com", "wired.com", "theverge.com", "webmd.com",
        "healthline.com", "mayoclinic.org", "espn.com",
    ])
    _LOW_AUTHORITY_DOMAINS = frozenset([
        "reddit.com", "quora.com", "medium.com", "substack.com",
        "buzzfeed.com", "huffpost.com",
    ])

    if domain in _HIGH_AUTHORITY_DOMAINS:
        profile.publisher_authority = 0.9
        profile.content_credibility = "editorial"
        profile.trust_transfer_potential = 0.8
    elif domain in _MEDIUM_AUTHORITY_DOMAINS:
        profile.publisher_authority = 0.7
        profile.content_credibility = "editorial"
        profile.trust_transfer_potential = 0.6
    elif domain in _LOW_AUTHORITY_DOMAINS:
        profile.publisher_authority = 0.4
        profile.content_credibility = "ugc"
        profile.trust_transfer_potential = 0.3
    else:
        profile.publisher_authority = 0.5
        profile.content_credibility = "unknown"
        profile.trust_transfer_potential = 0.4

    if any(w in text_lower for w in ["sponsored", "paid partnership", "advertisement", "promoted"]):
        profile.content_credibility = "sponsored"
        profile.trust_transfer_potential *= 0.6

    # ══════════════════════════════════════════════════════════════════
    # LAYER 5: PRIMED CATEGORIES
    # ══════════════════════════════════════════════════════════════════
    _CATEGORY_PRIMERS = {
        "beauty": ["skin", "hair", "makeup", "beauty", "moisturizer", "serum", "cosmetic"],
        "electronics": ["tech", "device", "gadget", "smartphone", "laptop", "software", "app"],
        "health": ["health", "fitness", "supplement", "vitamin", "workout", "diet", "nutrition"],
        "home": ["home", "furniture", "decor", "renovation", "kitchen", "bedroom", "garden"],
        "fashion": ["fashion", "clothing", "style", "outfit", "shoes", "designer", "trend"],
        "finance": ["invest", "savings", "credit", "loan", "mortgage", "banking", "insurance"],
        "automotive": ["car", "vehicle", "driving", "auto", "engine", "electric vehicle", "suv"],
        "travel": ["travel", "hotel", "flight", "vacation", "destination", "resort", "trip"],
        "food": ["recipe", "restaurant", "cooking", "meal", "ingredient", "food", "wine"],
        "education": ["course", "degree", "university", "learning", "certificate", "training"],
    }

    primed = []
    for category, primers in _CATEGORY_PRIMERS.items():
        hits = sum(1 for p in primers if p in text_lower)
        if hits >= 2:
            primed.append(category)
    profile.primed_categories = primed[:5]

    # Funnel stage signal
    if profile.purchase_intent_signal > 0.6:
        profile.funnel_stage_signal = "decision"
    elif any(w in text_lower for w in ["compare", "vs", "versus", "review", "best", "top 10"]):
        profile.funnel_stage_signal = "consideration"
    elif any(w in text_lower for w in ["what is", "guide", "introduction", "basics", "explained"]):
        profile.funnel_stage_signal = "awareness"
    else:
        profile.funnel_stage_signal = "awareness"

    # ══════════════════════════════════════════════════════════════════
    # LAYER 6: PERSUASION CHANNEL STATE (expanded)
    # Determine which channels the page OPENS vs CLOSES
    # ══════════════════════════════════════════════════════════════════
    open_channels: List[str] = []
    closed_channels: List[str] = []
    channel_reasoning: Dict[str, str] = {}

    # Authority: OPENED by expert content, CLOSED by anti-establishment
    if profile.publisher_authority > 0.7 or any(w in text_lower for w in ["expert", "research", "study", "scientist"]):
        open_channels.append("authority")
        channel_reasoning["authority"] = "Page cites expert sources, reader primed to trust expertise"
    elif any(w in text_lower for w in ["scam", "fake", "misleading", "distrust", "corrupt"]):
        closed_channels.append("authority")
        channel_reasoning["authority"] = "Page undermines institutional trust, authority may backfire"

    # Social proof: OPENED by community/social content, CLOSED by individualism
    if page_social > 0.5:
        open_channels.append("social_proof")
        channel_reasoning["social_proof"] = "Page emphasizes collective/community, reader primed for social validation"

    # Scarcity: OPENED by urgency/competition content, CLOSED by anti-manipulation
    if any(w in text_lower for w in ["limited", "exclusive", "competition", "running out"]):
        open_channels.append("scarcity")
        channel_reasoning["scarcity"] = "Page creates scarcity/competition context"
    elif any(w in text_lower for w in ["manipulat", "dark pattern", "pressure tactic", "deceptive"]):
        closed_channels.append("scarcity")
        channel_reasoning["scarcity"] = "Page critiques manipulation, scarcity tactics will feel dishonest"

    # Loss aversion: OPENED by threat/risk content, CLOSED by optimistic content
    if profile.emotional_valence < -0.2 and needs.get("security", 0) > 0.3:
        open_channels.append("loss_aversion")
        channel_reasoning["loss_aversion"] = "Page activates security concerns, loss-prevention messaging resonates"

    # Commitment: OPENED by trust/reliability content
    if "trust" in profile.dominant_emotions or needs.get("security", 0) > 0.5:
        open_channels.append("commitment")
        channel_reasoning["commitment"] = "Page builds trust context, small-step commitment appeals work"

    # Curiosity: OPENED by mystery/discovery content
    if "curiosity" in profile.dominant_emotions or page_arousal > 0.5:
        open_channels.append("curiosity")
        channel_reasoning["curiosity"] = "Page stimulates discovery mindset, curiosity-driven messaging resonates"

    profile.open_channels = open_channels
    profile.closed_channels = closed_channels
    profile.channel_reasoning = channel_reasoning

    # Update mechanism_adjustments based on open/closed channels
    for ch in open_channels:
        if ch in profile.mechanism_adjustments:
            profile.mechanism_adjustments[ch] = min(1.5, profile.mechanism_adjustments[ch] * 1.15)
    for ch in closed_channels:
        if ch in profile.mechanism_adjustments:
            profile.mechanism_adjustments[ch] = max(0.4, profile.mechanism_adjustments[ch] * 0.7)
        profile.avoid_tactics.append(f"{ch}_messaging")

    # ══════════════════════════════════════════════════════════════════
    # LAYER 7: COMPETITIVE ENVIRONMENT
    # ══════════════════════════════════════════════════════════════════
    ad_signals = sum(1 for w in ["advertisement", "sponsored", "ad", "promoted",
                                  "partner content"] if w in text_lower)
    if ad_signals >= 3:
        profile.estimated_ad_density = "very_high"
    elif ad_signals >= 2:
        profile.estimated_ad_density = "high"
    elif ad_signals >= 1:
        profile.estimated_ad_density = "moderate"
    else:
        profile.estimated_ad_density = "low"

    profile.content_ad_ratio = round(word_count / max(1, word_count + ad_signals * 50), 3)

    # ══════════════════════════════════════════════════════════════════
    # LAYER 8: PRIMED DECISION-MAKING STYLE
    #
    # This is the deepest intelligence layer. The page doesn't just
    # activate needs — it primes a specific WAY of making decisions.
    # A comparison article primes analytical/deliberative processing.
    # A crisis article primes fast/heuristic processing. A social
    # feed primes conformity-based decision making.
    #
    # The decision-making style the page primes determines:
    # - HOW the persuasion should be framed (not just what mechanism)
    # - What EVIDENCE structure the ad should use
    # - What COGNITIVE ROUTE will be most effective (central vs peripheral)
    # - How much DETAIL the buyer can process
    # - Whether the buyer will respond to LOGIC or EMOTION
    # ══════════════════════════════════════════════════════════════════
    primed_decision_style: Dict[str, Any] = {}

    # Decision speed: deliberative vs impulsive
    # Dense analytical content → slow, careful evaluation
    # Breaking news / social → fast, heuristic processing
    if page_cognitive > 0.6 and word_count > 500:
        primed_decision_style["decision_speed"] = "deliberative"
        primed_decision_style["evidence_needed"] = "high"
        primed_decision_style["persuasion_framing"] = "logical_argument"
    elif page_arousal > 0.6 or urgency_signals > 2:
        primed_decision_style["decision_speed"] = "impulsive"
        primed_decision_style["evidence_needed"] = "low"
        primed_decision_style["persuasion_framing"] = "emotional_appeal"
    else:
        primed_decision_style["decision_speed"] = "moderate"
        primed_decision_style["evidence_needed"] = "moderate"
        primed_decision_style["persuasion_framing"] = "balanced"

    # Risk orientation: risk-averse vs risk-seeking
    # Prevention/threat content → risk-averse, respond to safety
    # Opportunity/gain content → risk-seeking, respond to upside
    if page_approach_avoidance < -0.2 or needs.get("security", 0) > 0.4:
        primed_decision_style["risk_orientation"] = "risk_averse"
        primed_decision_style["frame_as"] = "protection_and_prevention"
        primed_decision_style["emphasize"] = "guarantees, safety, proven track record"
    elif page_approach_avoidance > 0.3 or needs.get("self_improvement", 0) > 0.4:
        primed_decision_style["risk_orientation"] = "risk_seeking"
        primed_decision_style["frame_as"] = "opportunity_and_gain"
        primed_decision_style["emphasize"] = "upside potential, transformation, what you could gain"
    else:
        primed_decision_style["risk_orientation"] = "balanced"
        primed_decision_style["frame_as"] = "balanced_value"
        primed_decision_style["emphasize"] = "balanced benefits and protections"

    # Social reference frame: independent vs conformity
    # Social content → conformity-based, "everyone is doing this"
    # Expert/analytical content → independent, "you know best"
    if page_social > 0.5 or profile.mindset == "social":
        primed_decision_style["social_frame"] = "conformity"
        primed_decision_style["voice"] = "collective"
        primed_decision_style["social_proof_style"] = "majority_consensus"
    elif page_cognitive > 0.6 and page_social < 0.3:
        primed_decision_style["social_frame"] = "independent"
        primed_decision_style["voice"] = "individual"
        primed_decision_style["social_proof_style"] = "expert_endorsement"
    else:
        primed_decision_style["social_frame"] = "balanced"
        primed_decision_style["voice"] = "authoritative"
        primed_decision_style["social_proof_style"] = "curated_testimonial"

    # Temporal orientation: immediate vs future
    # Present-focused content → respond to "right now"
    # Future-focused content → respond to "investment"
    if page_temporal < 0.3 or profile.need_urgency > 0.5:
        primed_decision_style["temporal_frame"] = "immediate"
        primed_decision_style["urgency_receptivity"] = "high"
        primed_decision_style["cta_style"] = "act_now"
    elif page_temporal > 0.6:
        primed_decision_style["temporal_frame"] = "future_oriented"
        primed_decision_style["urgency_receptivity"] = "low"
        primed_decision_style["cta_style"] = "invest_in_your_future"
    else:
        primed_decision_style["temporal_frame"] = "moderate"
        primed_decision_style["urgency_receptivity"] = "moderate"
        primed_decision_style["cta_style"] = "learn_more"

    # Information processing depth: central vs peripheral route (ELM)
    # This is the key: HOW will they process your ad?
    if page_cognitive > 0.6:
        primed_decision_style["elm_route"] = "central"
        primed_decision_style["ad_should_provide"] = "strong arguments, data, evidence, comparisons"
        primed_decision_style["ad_should_avoid"] = "emotional manipulation, vague claims, hype"
    elif page_arousal > 0.5 and page_cognitive < 0.4:
        primed_decision_style["elm_route"] = "peripheral"
        primed_decision_style["ad_should_provide"] = "social proof, visual cues, celebrity/expert endorsement, emotion"
        primed_decision_style["ad_should_avoid"] = "dense text, complex comparisons, detailed specifications"
    else:
        primed_decision_style["elm_route"] = "mixed"
        primed_decision_style["ad_should_provide"] = "clear value proposition with supporting evidence"
        primed_decision_style["ad_should_avoid"] = "either extreme (neither too analytical nor too emotional)"

    # Construal level: abstract vs concrete
    # Abstract content (ideas, concepts) → abstract messaging
    # Concrete content (specific products, prices) → concrete messaging
    if page_temporal > 0.6:
        primed_decision_style["construal_level"] = "abstract"
        primed_decision_style["message_style"] = "vision, identity, aspiration"
    elif page_temporal < 0.4:
        primed_decision_style["construal_level"] = "concrete"
        primed_decision_style["message_style"] = "specific features, exact numbers, tangible outcomes"
    else:
        primed_decision_style["construal_level"] = "moderate"
        primed_decision_style["message_style"] = "concrete benefits with aspirational wrapper"

    profile.primed_decision_style = primed_decision_style

    # ══════════════════════════════════════════════════════════════════
    # SYNTHESIZED AD STRATEGY RECOMMENDATION
    # ══════════════════════════════════════════════════════════════════
    top_need = max(profile.activated_needs.items(), key=lambda x: x[1])[0] if profile.activated_needs else "general"
    top_open = open_channels[0] if open_channels else "social_proof"
    top_avoid = closed_channels[0] if closed_channels else "none"
    ds = primed_decision_style

    strategy_parts = []

    # Core: what need to target + what channel to use
    strategy_parts.append(f"Target activated {top_need} need via {top_open} channel.")

    # Decision-making style dictates HOW to frame the persuasion
    frame_as = ds.get("frame_as", "balanced_value")
    strategy_parts.append(f"Frame as {frame_as.replace('_', ' ')}.")

    elm = ds.get("elm_route", "mixed")
    if elm == "central":
        strategy_parts.append(
            "Reader is in ANALYTICAL mode — provide strong arguments, data, "
            "evidence, and comparisons. Avoid emotional manipulation or vague claims."
        )
    elif elm == "peripheral":
        strategy_parts.append(
            "Reader is in EMOTIONAL mode — use social proof, visual cues, "
            "endorsements, and feeling-based messaging. Avoid dense text or complex specs."
        )

    # Decision speed → urgency calibration
    speed = ds.get("decision_speed", "moderate")
    if speed == "deliberative":
        strategy_parts.append("Reader is in deliberative mode — give them time, don't pressure.")
    elif speed == "impulsive":
        strategy_parts.append("Reader is in fast-decision mode — clear CTA, simple value prop, act-now.")

    # Social frame → voice
    voice = ds.get("voice", "authoritative")
    strategy_parts.append(f"Use {voice} voice ({ds.get('social_proof_style', 'balanced')} proof style).")

    # Message style from construal
    msg_style = ds.get("message_style", "")
    if msg_style:
        strategy_parts.append(f"Message style: {msg_style}.")

    # Credibility transfer
    if profile.publisher_authority > 0.7:
        strategy_parts.append("Leverage page's editorial authority (high trust transfer).")

    # Bandwidth
    if profile.remaining_bandwidth < 0.3:
        strategy_parts.append("SIMPLIFY — reader has depleted cognitive bandwidth.")

    # Problem-solution alignment
    if profile.problem_solution_frame == "problem_only":
        strategy_parts.append("Page presents PROBLEM without solution — position ad as THE ANSWER.")
    elif profile.problem_solution_frame == "problem_and_solution":
        strategy_parts.append("Page offers solutions — differentiate or build on them.")

    # Avoidance
    if top_avoid != "none":
        strategy_parts.append(f"AVOID {top_avoid} — page has primed resistance.")

    # What to provide / avoid from ELM analysis
    provide = ds.get("ad_should_provide", "")
    avoid = ds.get("ad_should_avoid", "")
    if provide:
        strategy_parts.append(f"Provide: {provide}.")
    if avoid:
        strategy_parts.append(f"Avoid: {avoid}.")

    profile.recommended_ad_strategy = " ".join(strategy_parts)

    # ══════════════════════════════════════════════════════════════════
    # CONFIDENCE
    # ══════════════════════════════════════════════════════════════════
    if word_count > 500:
        profile.confidence = 0.7
    elif word_count > 200:
        profile.confidence = 0.5
    elif word_count > 50:
        profile.confidence = 0.3
    else:
        profile.confidence = 0.15

    # ══════════════════════════════════════════════════════════════════
    # LAYER 9: NARRATIVE ARC (5-segment sentiment analysis)
    # Split content into 5 segments, track valence per segment
    # ══════════════════════════════════════════════════════════════════
    if word_count > 100:
        segment_size = len(text_lower) // 5
        segment_valences = []
        _pos_markers = ["good", "great", "best", "love", "wonderful", "excellent",
                        "happy", "hope", "success", "win", "improve", "better"]
        _neg_markers = ["bad", "worst", "terrible", "fear", "fail", "loss",
                        "crisis", "problem", "risk", "threat", "danger", "pain"]
        for seg_i in range(5):
            seg = text_lower[seg_i * segment_size:(seg_i + 1) * segment_size]
            pos = sum(1 for w in _pos_markers if w in seg)
            neg = sum(1 for w in _neg_markers if w in seg)
            total = pos + neg
            seg_val = (pos - neg) / max(total, 1)
            segment_valences.append(round(seg_val, 3))
        profile.narrative_valence_trajectory = segment_valences

        # Classify arc type
        first_half_avg = sum(segment_valences[:2]) / 2
        second_half_avg = sum(segment_valences[3:]) / 2
        mid_val = segment_valences[2]
        val_range = max(segment_valences) - min(segment_valences)

        if val_range < 0.2:
            profile.narrative_arc_type = "steady_state"
        elif first_half_avg < -0.1 and second_half_avg > 0.1:
            profile.narrative_arc_type = "tension_release"
        elif first_half_avg < second_half_avg and mid_val < second_half_avg:
            profile.narrative_arc_type = "crescendo"
        elif first_half_avg > second_half_avg:
            profile.narrative_arc_type = "declination"
        else:
            profile.narrative_arc_type = "oscillating"

        # Cognitive momentum: flow state indicator
        # High when valence trajectory is smooth (not jarring), moderate arousal
        variance = sum((v - sum(segment_valences)/5)**2 for v in segment_valences) / 5
        smoothness = max(0, 1.0 - variance * 5)
        profile.cognitive_momentum = round(
            0.4 * smoothness + 0.3 * min(1.0, page_arousal * 1.5) + 0.3 * (1.0 - min(1.0, page_cognitive * 1.2)),
            3
        )

        # Optimal ad position: where reader bandwidth peaks
        max_bandwidth_seg = max(range(5), key=lambda i: segment_valences[i])
        if max_bandwidth_seg <= 1:
            profile.ad_position_optimal = "early"
        elif max_bandwidth_seg == 2:
            profile.ad_position_optimal = "mid"
        elif max_bandwidth_seg == 3:
            profile.ad_position_optimal = "late"
        else:
            profile.ad_position_optimal = "post_climax"

    # ══════════════════════════════════════════════════════════════════
    # LAYER 10: RHETORICAL STRUCTURE
    # ══════════════════════════════════════════════════════════════════
    # Evidence markers
    _evidence_markers = ["according to", "research shows", "study", "data",
                         "evidence", "percent", "statistics", "survey", "found that"]
    _claim_markers = ["should", "must", "need to", "important", "crucial",
                      "essential", "clearly", "obviously"]
    _transition_markers = ["however", "therefore", "consequently", "furthermore",
                           "moreover", "in contrast", "on the other hand"]
    _analogy_markers = ["like", "similar to", "just as", "compared to", "reminiscent"]

    evidence_count = sum(1 for m in _evidence_markers if m in text_lower)
    claim_count = sum(1 for m in _claim_markers if m in text_lower)
    transition_count = sum(1 for m in _transition_markers if m in text_lower)
    analogy_count = sum(1 for m in _analogy_markers if m in text_lower)

    profile.evidence_density = round(
        evidence_count / max(1, evidence_count + claim_count), 3
    )

    # Determine argument structure
    if evidence_count > claim_count and transition_count > 2:
        profile.argument_structure = "deductive"
    elif claim_count > evidence_count and evidence_count > 0:
        profile.argument_structure = "inductive"
    elif analogy_count >= 2:
        profile.argument_structure = "analogical"
    elif profile.content_type in ("social", "lifestyle"):
        profile.argument_structure = "narrative"
    elif any(w in text_lower for w in ["first", "second", "third", "step 1", "step 2"]):
        profile.argument_structure = "enumerated"
    elif any(w in text_lower for w in ["debate", "controversy", "critics", "opponents"]):
        profile.argument_structure = "adversarial"
    else:
        profile.argument_structure = "narrative"

    # Rhetorical appeals (Aristotle's triangle)
    # Ethos: credibility/authority signals
    ethos_markers = sum(1 for m in ["expert", "years of experience", "certified",
                                     "award", "professor", "dr.", "ph.d", "study"] if m in text_lower)
    # Pathos: emotional appeal signals
    pathos_markers = sum(1 for m in ["feel", "heart", "love", "fear", "imagine",
                                      "dream", "story", "struggle", "overcome"] if m in text_lower)
    # Logos: logical/rational signals
    logos_markers = sum(1 for m in ["because", "therefore", "data", "percent",
                                     "ratio", "analysis", "calculated", "measured"] if m in text_lower)
    total_appeals = ethos_markers + pathos_markers + logos_markers
    if total_appeals > 0:
        profile.rhetorical_appeals = {
            "ethos": round(ethos_markers / total_appeals, 3),
            "pathos": round(pathos_markers / total_appeals, 3),
            "logos": round(logos_markers / total_appeals, 3),
        }

    # ══════════════════════════════════════════════════════════════════
    # LAYER 13: TEMPORAL CONTEXT
    # ══════════════════════════════════════════════════════════════════
    # Content freshness detection
    _breaking_markers = ["breaking", "just in", "developing", "live update", "happening now"]
    _recent_markers = ["today", "yesterday", "this week", "this morning", "hours ago"]
    _dated_markers = ["years ago", "in 2020", "in 2019", "decade", "historically"]

    if any(m in text_lower for m in _breaking_markers):
        profile.content_freshness = "breaking"
        profile.temporal_relevance_score = 1.0
    elif any(m in text_lower for m in _recent_markers):
        profile.content_freshness = "recent"
        profile.temporal_relevance_score = 0.8
    elif any(m in text_lower for m in _dated_markers):
        profile.content_freshness = "dated"
        profile.temporal_relevance_score = 0.3
    else:
        profile.content_freshness = "evergreen"
        profile.temporal_relevance_score = 0.6

    # Seasonal context detection
    _seasonal_map = {
        "holiday": ["christmas", "thanksgiving", "halloween", "new year", "holiday season", "gift"],
        "tax_season": ["tax", "filing", "irs", "deduction", "refund", "april 15"],
        "back_to_school": ["school", "semester", "college", "dorm", "supplies", "back to school"],
        "summer": ["summer", "vacation", "beach", "outdoor", "barbecue", "pool"],
        "winter": ["winter", "cold", "snow", "heating", "cozy", "fireplace"],
        "new_year_resolution": ["resolution", "new year", "fresh start", "goal setting"],
        "valentines": ["valentine", "romance", "love", "date night", "couple"],
        "black_friday": ["black friday", "cyber monday", "deal", "doorbuster"],
    }
    for season, markers in _seasonal_map.items():
        if sum(1 for m in markers if m in text_lower) >= 2:
            profile.seasonal_context = season
            break

    # ══════════════════════════════════════════════════════════════════
    # LAYER 15: FULL-WIDTH EDGE DIMENSION EXTRACTION (PRIMARY)
    # Extract all 20 edge dimensions directly — NDF is the fallback
    # ══════════════════════════════════════════════════════════════════
    try:
        from adam.intelligence.page_edge_scoring import score_page_full_width
        edge_profile = score_page_full_width(
            text=text_content,
            url=url,
            category=profile.primary_topic or "",
        )
        if edge_profile.dimensions:
            profile.edge_dimensions = edge_profile.dimensions
            profile.edge_scoring_tier = edge_profile.scoring_tier
            # Use edge-derived confidence when it's higher
            if edge_profile.confidence > profile.confidence:
                profile.confidence = edge_profile.confidence
    except Exception as e:
        logger.debug("Full-width edge scoring unavailable, NDF is primary: %s", e)

    # Mark scoring passes completed
    profile.scoring_passes_completed = ["fast_nlp"]
    if profile.edge_dimensions:
        profile.scoring_passes_completed.append("full_width_edge")
    profile.profile_version = 3

    profile.crawl_count = 1
    return profile


def deep_score_profile(
    text_content: str,
    profile: PagePsychologicalProfile,
) -> PagePsychologicalProfile:
    """Pass 1.5: Deep scoring using NLP, embeddings, and discourse analysis.

    Runs 8 techniques that correct and enrich the Pass 1 word-list scoring:
    - Collocation context disambiguation
    - Prospect Theory frame detection
    - Surprisal-based attention prediction
    - Implicit need detection via topic-need matrix
    - Discourse relation scanning for channel gating
    - Negation-aware dependency scoring (spaCy)
    - Semantic NDF via sentence-transformer embeddings
    - Graph-backed category prior blending

    Adds ~0.15 confidence. ~100ms per page (offline, pre-cached).
    """
    if not text_content or len(text_content.split()) < 50:
        return profile

    try:
        from adam.intelligence.deep_page_scoring import deep_score_page

        result = deep_score_page(
            text=text_content,
            raw_ndf=profile.construct_activations,
            current_open_channels=profile.open_channels,
            current_closed_channels=profile.closed_channels,
            category=profile.primary_topic or "",
            word_count=len(text_content.split()),
        )

        # Apply corrected NDF
        if result.get("ndf_corrected"):
            profile.construct_activations = result["ndf_corrected"]
            # Update emotional fields from corrected NDF
            ndf = result["ndf_corrected"]
            profile.emotional_valence = ndf.get("approach_avoidance", profile.emotional_valence)
            profile.emotional_arousal = ndf.get("arousal_seeking", profile.emotional_arousal)
            profile.cognitive_load = ndf.get("cognitive_engagement", profile.cognitive_load)

        # Apply implicit needs (merge with existing)
        if result.get("implicit_needs"):
            for need, strength in result["implicit_needs"].items():
                if need not in profile.activated_needs or abs(strength) > abs(profile.activated_needs.get(need, 0)):
                    profile.activated_needs[need] = strength

        # Apply channel corrections from discourse analysis
        if result.get("channel_corrections"):
            corrections = result["channel_corrections"]
            for ch in corrections.get("should_close", []):
                if ch not in profile.closed_channels:
                    profile.closed_channels.append(ch)
                if ch in profile.open_channels:
                    profile.open_channels.remove(ch)
                if ch in profile.mechanism_adjustments:
                    profile.mechanism_adjustments[ch] = max(0.4, profile.mechanism_adjustments[ch] * 0.65)
            for reason_ch, reason_text in corrections.get("reasoning", {}).items():
                profile.channel_reasoning[reason_ch] = reason_text

        # Store prospect frame and surprisal as extended data
        if result.get("prospect_frame"):
            pf = result["prospect_frame"]
            profile.primed_decision_style["prospect_frame"] = pf.get("prospect_frame", 0.0)
            profile.primed_decision_style["endowment_effect"] = pf.get("endowment_effect", 0.0)

        if result.get("surprisal"):
            s = result["surprisal"]
            # Refine bandwidth with surprisal
            profile.remaining_bandwidth = round(
                0.6 * profile.remaining_bandwidth + 0.4 * (1.0 - s.get("mean_surprisal", 0.5)),
                3,
            )
            profile.primed_decision_style["peak_attention_position"] = s.get("peak_attention_position", 0.5)

        # Update confidence and scoring passes
        profile.confidence = min(1.0, profile.confidence + 0.15)
        if "deep_scoring" not in profile.scoring_passes_completed:
            profile.scoring_passes_completed.append("deep_scoring")

        logger.debug(
            "Deep scoring: %d techniques, %.1fms, conf→%.2f",
            len(result.get("techniques_applied", [])),
            result.get("processing_ms", 0),
            profile.confidence,
        )

    except Exception as e:
        logger.debug("Deep scoring failed: %s", e)

    return profile


def profile_page_structure(
    html_content: str,
    profile: PagePsychologicalProfile,
) -> PagePsychologicalProfile:
    """Pass 2: Structural DOM analysis for page intelligence.

    Extracts signals from HTML structure that text analysis cannot detect:
    - Ad slot count and positions
    - Social proof signals (comment counts, share widgets)
    - Attention competition (autoplay video, interstitials, popups)
    - Schema.org structured data (article type, author, datePublished)
    - Content-to-noise ratio from DOM tree

    Adds ~0.1 confidence to the profile.
    ~20ms per page.
    """
    if not html_content:
        return profile

    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return profile

    try:
        soup = BeautifulSoup(html_content, "html.parser")
    except Exception:
        return profile

    # ── Ad Slot Detection ──
    ad_selectors = [
        "[class*='ad-']", "[class*='advertisement']", "[class*='ad_']",
        "[id*='ad-']", "[id*='ad_']", "[id*='dfp']", "[id*='gpt-']",
        "[class*='adsbygoogle']", "[class*='sponsor']",
        "ins.adsbygoogle", "[data-ad-slot]", "[data-ad-unit]",
    ]
    ad_slots = set()
    for selector in ad_selectors:
        for tag in soup.select(selector):
            ad_slots.add(id(tag))

    profile.ad_slot_count = len(ad_slots)

    # Estimate ad positions (top, middle, bottom of page)
    positions = []
    body = soup.find("body")
    if body and ad_slots:
        all_children = list(body.descendants)
        total = len(all_children)
        for selector in ad_selectors:
            for tag in soup.select(selector):
                try:
                    idx = all_children.index(tag)
                    pos_pct = idx / max(1, total)
                    if pos_pct < 0.25:
                        positions.append("top")
                    elif pos_pct < 0.75:
                        positions.append("middle")
                    else:
                        positions.append("bottom")
                except (ValueError, IndexError):
                    pass
        profile.ad_slot_positions = list(set(positions))

    # ── Social Proof Signals ──
    social_signals: Dict[str, Any] = {}

    # Comment count detection
    comment_selectors = ["[class*='comment']", "[id*='comment']", "[class*='disqus']"]
    comment_elements = 0
    for sel in comment_selectors:
        comment_elements += len(soup.select(sel))
    social_signals["comment_count"] = min(comment_elements, 500)

    # Share widget detection
    share_selectors = ["[class*='share']", "[class*='social']", "[aria-label*='share']"]
    share_elements = 0
    for sel in share_selectors:
        share_elements += len(soup.select(sel))
    social_signals["share_count"] = min(share_elements, 50)

    # Rating detection
    rating_el = soup.find(attrs={"class": re.compile(r"rating|stars|score", re.I)})
    social_signals["rating_present"] = rating_el is not None

    # Expert citations
    cite_count = len(soup.find_all("cite")) + len(soup.find_all("blockquote"))
    social_signals["expert_citations"] = cite_count

    social_signals["engagement_level"] = (
        "high" if comment_elements > 20 or share_elements > 5
        else "moderate" if comment_elements > 5 or share_elements > 2
        else "low"
    )
    profile.social_proof_signals = social_signals

    # ── Attention Competition ──
    # Video autoplay detection
    videos = soup.find_all("video")
    profile.video_autoplay_detected = any(
        v.get("autoplay") is not None for v in videos
    )

    # Interstitial / popup detection
    modal_selectors = ["[class*='modal']", "[class*='overlay']", "[class*='interstitial']",
                       "[class*='popup']", "[class*='lightbox']"]
    profile.interstitial_detected = any(
        len(soup.select(sel)) > 0 for sel in modal_selectors
    )

    # CTA competition
    cta_elements = soup.find_all("a", class_=re.compile(r"cta|button|btn", re.I))
    cta_elements += soup.find_all("button")
    profile.competing_cta_count = len(cta_elements)

    # Estimated viewability based on ad position and competition
    if profile.ad_slot_count == 0:
        profile.estimated_viewability = 0.6  # No detected slots, assume moderate
    elif "top" in profile.ad_slot_positions:
        profile.estimated_viewability = 0.8
    elif "middle" in profile.ad_slot_positions:
        profile.estimated_viewability = 0.65
    else:
        profile.estimated_viewability = 0.4

    # Reduce viewability for high competition
    if profile.competing_cta_count > 10:
        profile.estimated_viewability *= 0.8
    if profile.video_autoplay_detected:
        profile.estimated_viewability *= 0.85
    profile.estimated_viewability = round(profile.estimated_viewability, 3)

    # ── Schema.org Structured Data ──
    schema_scripts = soup.find_all("script", type="application/ld+json")
    for script in schema_scripts:
        try:
            import json as _json
            schema = _json.loads(script.string or "")
            if isinstance(schema, dict):
                schema_type = schema.get("@type", "")
                if schema_type in ("NewsArticle", "Article", "BlogPosting"):
                    profile.content_credibility = "editorial"
                elif schema_type == "Review":
                    profile.content_type = "review_page"
                elif schema_type == "Product":
                    profile.content_type = "product_page"
        except Exception:
            pass

    # ── Scroll Depth to Content ──
    main_content = (
        soup.find("article") or soup.find("main")
        or soup.find("div", role="main")
    )
    if main_content and body:
        # Estimate how far down the page the main content starts
        all_body_children = list(body.children)
        try:
            content_index = list(body.descendants).index(main_content)
            total_descendants = len(list(body.descendants))
            profile.scroll_depth_to_content = round(
                content_index / max(1, total_descendants), 3
            )
        except (ValueError, IndexError):
            profile.scroll_depth_to_content = 0.2  # Default moderate

    # Update confidence and passes
    profile.confidence = min(1.0, profile.confidence + 0.1)
    if "dom_structure" not in profile.scoring_passes_completed:
        profile.scoring_passes_completed.append("dom_structure")

    return profile


# ---------------------------------------------------------------------------
# URL normalization utilities
# ---------------------------------------------------------------------------

def _extract_domain(url: str) -> Optional[str]:
    """Extract clean domain from URL."""
    if not url:
        return None
    url = url.lower().strip()
    for prefix in ("https://", "http://", "//"):
        if url.startswith(prefix):
            url = url[len(prefix):]
    url = url.split("/")[0].split(":")[0]
    if url.startswith("www."):
        url = url[4:]
    return url if url else None


def _url_to_pattern(url: str) -> str:
    """Convert URL to a normalized pattern for caching.

    Strips query params, fragments, and normalizes path segments
    that look like IDs or dates into wildcards.

    Examples:
        "https://nytimes.com/2026/03/15/business/inflation.html"
        → "nytimes.com/*/business/*"

        "https://amazon.com/dp/B09V3KXJPB"
        → "amazon.com/dp/*"
    """
    if not url:
        return ""

    url = url.lower().strip()
    for prefix in ("https://", "http://", "//"):
        if url.startswith(prefix):
            url = url[len(prefix):]

    # Remove query and fragment
    url = url.split("?")[0].split("#")[0]

    # Remove www
    if url.startswith("www."):
        url = url[4:]

    # Split into domain and path
    parts = url.split("/", 1)
    domain = parts[0].split(":")[0]
    path = parts[1] if len(parts) > 1 else ""

    if not path:
        return domain

    # Normalize path: replace ID-like and date-like segments with *
    path_parts = path.rstrip("/").split("/")
    normalized = []
    for part in path_parts:
        if not part:
            continue
        # Date-like (2026, 03, 15)
        if re.match(r"^\d{2,4}$", part):
            normalized.append("*")
        # UUID or hash-like
        elif re.match(r"^[a-f0-9]{8,}$", part):
            normalized.append("*")
        # Amazon ASIN-like
        elif re.match(r"^[A-Z0-9]{10}$", part, re.IGNORECASE):
            normalized.append("*")
        # File with extension
        elif "." in part and part.rsplit(".", 1)[1] in ("html", "htm", "php", "asp"):
            normalized.append("*")
        else:
            normalized.append(part)

    return f"{domain}/{'/'.join(normalized)}" if normalized else domain


# ---------------------------------------------------------------------------
# Singletons
# ---------------------------------------------------------------------------

_inventory_tracker: Optional[PageInventoryTracker] = None
_page_cache: Optional[PageIntelligenceCache] = None


def get_inventory_tracker() -> PageInventoryTracker:
    global _inventory_tracker
    if _inventory_tracker is None:
        _inventory_tracker = PageInventoryTracker()
    return _inventory_tracker


def get_page_intelligence_cache() -> PageIntelligenceCache:
    global _page_cache
    if _page_cache is None:
        _page_cache = PageIntelligenceCache()
    return _page_cache
