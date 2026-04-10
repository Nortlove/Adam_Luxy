#!/usr/bin/env python3
"""
HELPFUL VOTE INTELLIGENCE
=========================

Transforms helpful votes from a simple weighting signal into
actionable intelligence for all three ADAM systems:

1. **Graph Database**: Archetype → Mechanism effectiveness matrix
2. **AoT Atoms**: Pre-fetched evidence with persuasive templates  
3. **LangGraph**: Orchestration data for routing decisions

KEY INSIGHT: Helpful votes are PROOF that persuasive language worked.
A review with 500 helpful votes means 500 people found that reviewer's
perspective convincing enough to influence their decision.

What we extract:
- Persuasive templates (actual phrases that worked)
- Mechanism → Effectiveness correlation (which techniques convert)
- Archetype affinity (what psychological profiles respond)
- Brand-customer alignment patterns

Phase 1: Fix Learning Loop - Redesign Helpful Vote Processing
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
import math

logger = logging.getLogger(__name__)


# =============================================================================
# INFLUENCE TIERS (Based on helpful vote distribution)
# =============================================================================

class InfluenceTier:
    """
    Influence tier based on helpful vote count.
    
    Based on Amazon review helpful vote distribution:
    - 99% of reviews: 0-10 votes
    - 0.9%: 11-50 votes  
    - 0.09%: 51-200 votes
    - 0.01%: 200+ votes (viral influencers)
    """
    
    VIRAL = "viral"           # 200+ votes - exceptional influencer
    VERY_HIGH = "very_high"   # 51-200 votes - significant influence
    HIGH = "high"             # 11-50 votes - above average
    MODERATE = "moderate"     # 3-10 votes - typical helpful
    LOW = "low"               # 0-2 votes - baseline
    
    @classmethod
    def from_votes(cls, votes: int, verified: bool = False) -> str:
        """Classify into influence tier."""
        # Verified purchase boosts effective vote count
        effective = votes * 1.2 if verified else votes
        
        if effective >= 200:
            return cls.VIRAL
        elif effective >= 51:
            return cls.VERY_HIGH
        elif effective >= 11:
            return cls.HIGH
        elif effective >= 3:
            return cls.MODERATE
        else:
            return cls.LOW
    
    @classmethod
    def get_weight(cls, tier: str) -> float:
        """Get learning weight for tier."""
        weights = {
            cls.VIRAL: 5.0,        # 5x learning signal
            cls.VERY_HIGH: 3.0,    # 3x learning signal
            cls.HIGH: 2.0,         # 2x learning signal
            cls.MODERATE: 1.2,     # Slight boost
            cls.LOW: 1.0,          # Baseline
        }
        return weights.get(tier, 1.0)


# =============================================================================
# PERSUASIVE TEMPLATE EXTRACTION
# =============================================================================

# Patterns that indicate persuasive intent
PERSUASIVE_PATTERNS = {
    # Social proof
    "social_proof": [
        r"(?:my|our) (?:husband|wife|partner|family|friends) (?:also|loves?)",
        r"everyone (?:loves?|wants?|asks? about)",
        r"(?:highly|strongly) recommend(?:ed)?",
        r"best (?:purchase|buy|decision) (?:I've|we've) (?:made|ever)",
        r"already (?:bought|purchased|ordered) (?:\w+ )?(?:more|another)",
    ],
    # Authority
    "authority": [
        r"as (?:a|an) (?:professional|expert|doctor|trainer|chef|designer)",
        r"(?:years?|decades?) of experience",
        r"compared to (?:other|many|various) (?:brands?|products?|options?)",
        r"tested (?:extensively|thoroughly|many)",
    ],
    # Scarcity
    "scarcity": [
        r"(?:grab|get|buy) (?:this|them|one) (?:before|while)",
        r"(?:selling|going|running) out (?:fast|quickly)",
        r"wish (?:I'd|I had) (?:bought|found) (?:this|these) (?:sooner|earlier)",
        r"(?:don't|do not) (?:wait|hesitate)",
    ],
    # Reciprocity
    "reciprocity": [
        r"(?:save|saved) (?:me|us) (?:time|money|hassle|trouble)",
        r"(?:hope|hopefully) this (?:helps?|review helps)",
        r"(?:wanted|want) to share (?:my|this)",
    ],
    # Commitment/Consistency
    "commitment": [
        r"(?:use|using) (?:it|this|these) (?:every|daily|regularly)",
        r"(?:been|have been) (?:using|buying) for (?:months?|years?)",
        r"(?:always|will always) (?:buy|use|recommend)",
        r"(?:loyal|devoted) (?:customer|fan|user)",
    ],
    # Liking
    "liking": [
        r"absolutely (?:love|adore|obsessed)",
        r"game ?changer",
        r"life ?(?:changing|saver)",
        r"can't (?:live|imagine|go) without",
        r"holy grail",
    ],
    # Fear of missing out
    "fomo": [
        r"you won't (?:regret|be disappointed)",
        r"(?:what|why) (?:are you|were you) waiting",
        r"(?:stop|quit) (?:looking|searching|hesitating)",
        r"(?:this|these) (?:is|are) (?:it|the one)",
    ],
}


@dataclass
class PersuasiveTemplate:
    """A persuasive language template extracted from high-vote reviews."""
    
    template_id: str
    mechanism: str                    # Cialdini principle
    pattern: str                      # The actual text pattern
    example_text: str                 # Real example from review
    vote_count: int                   # Helpful votes on source
    effectiveness_score: float        # Computed effectiveness
    archetype_affinity: Dict[str, float] = field(default_factory=dict)  # Which archetypes respond
    brand_categories: List[str] = field(default_factory=list)           # Product categories
    
    def to_aot_evidence(self) -> Dict[str, Any]:
        """Convert to format AoT atoms expect."""
        return {
            "type": "persuasive_template",
            "mechanism": self.mechanism,
            "pattern": self.pattern,
            "effectiveness": self.effectiveness_score,
            "archetype_affinity": self.archetype_affinity,
            "evidence_strength": min(1.0, math.log10(self.vote_count + 1) / 3),
        }


@dataclass
class MechanismEffectiveness:
    """Effectiveness of a mechanism for an archetype."""
    
    mechanism: str
    archetype: str
    success_count: int = 0
    total_count: int = 0
    weighted_success: float = 0.0
    weighted_total: float = 0.0
    example_templates: List[str] = field(default_factory=list)
    
    @property
    def success_rate(self) -> float:
        """Simple success rate."""
        return self.success_count / self.total_count if self.total_count > 0 else 0.5
    
    @property
    def weighted_success_rate(self) -> float:
        """Helpful-vote-weighted success rate."""
        return self.weighted_success / self.weighted_total if self.weighted_total > 0 else 0.5
    
    @property
    def confidence(self) -> float:
        """Confidence based on sample size."""
        return min(0.95, self.total_count / 100)
    
    def to_graph_edge(self) -> Dict[str, Any]:
        """Convert to format for Neo4j edge properties."""
        return {
            "mechanism": self.mechanism,
            "archetype": self.archetype,
            "success_rate": self.success_rate,
            "weighted_success_rate": self.weighted_success_rate,
            "confidence": self.confidence,
            "sample_size": self.total_count,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }


# =============================================================================
# HELPFUL VOTE INTELLIGENCE PROCESSOR
# =============================================================================

class HelpfulVoteIntelligence:
    """
    Transforms helpful vote data into intelligence for all ADAM systems.
    
    Produces:
    1. For Graph: Archetype → Mechanism effectiveness matrix
    2. For AoT: Pre-fetched evidence with templates
    3. For LangGraph: Routing recommendations
    """
    
    def __init__(self):
        # Compiled patterns for efficiency
        self._patterns = {}
        for mechanism, patterns in PERSUASIVE_PATTERNS.items():
            self._patterns[mechanism] = [
                re.compile(p, re.IGNORECASE) for p in patterns
            ]
        
        # Effectiveness matrix: (archetype, mechanism) -> MechanismEffectiveness
        self._effectiveness_matrix: Dict[Tuple[str, str], MechanismEffectiveness] = {}
        
        # Template library
        self._templates: List[PersuasiveTemplate] = []
        
        # Stats
        self._reviews_processed = 0
        self._high_vote_reviews = 0
    
    def process_review(
        self,
        review_text: str,
        helpful_votes: int,
        verified_purchase: bool,
        archetype: Optional[str] = None,
        product_category: Optional[str] = None,
        rating: float = 0.0,
    ) -> Dict[str, Any]:
        """
        Process a single review and extract intelligence.
        
        Returns dict with:
        - tier: Influence tier
        - mechanisms_detected: List of persuasion mechanisms found
        - templates_extracted: List of new templates (if high-vote)
        - effectiveness_updates: Dict of mechanism->archetype updates
        """
        self._reviews_processed += 1
        
        # Classify influence tier
        tier = InfluenceTier.from_votes(helpful_votes, verified_purchase)
        weight = InfluenceTier.get_weight(tier)
        
        # Detect persuasion mechanisms
        mechanisms_detected = self._detect_mechanisms(review_text)
        
        result = {
            "tier": tier,
            "weight": weight,
            "mechanisms_detected": list(mechanisms_detected.keys()),
            "templates_extracted": [],
            "effectiveness_updates": {},
        }
        
        # Only extract templates from high-vote reviews
        if tier in (InfluenceTier.VIRAL, InfluenceTier.VERY_HIGH, InfluenceTier.HIGH):
            self._high_vote_reviews += 1
            
            # Extract templates
            for mechanism, matches in mechanisms_detected.items():
                for match in matches:
                    template = PersuasiveTemplate(
                        template_id=f"tpl_{hash(match) % 1000000:06x}",
                        mechanism=mechanism,
                        pattern=match,
                        example_text=match,
                        vote_count=helpful_votes,
                        effectiveness_score=self._compute_effectiveness(
                            helpful_votes, rating, verified_purchase
                        ),
                        archetype_affinity={archetype: 1.0} if archetype else {},
                        brand_categories=[product_category] if product_category else [],
                    )
                    self._templates.append(template)
                    result["templates_extracted"].append(template.pattern)
        
        # Update effectiveness matrix
        if archetype and mechanisms_detected:
            is_success = rating >= 4.0 and helpful_votes >= 3
            
            for mechanism in mechanisms_detected:
                key = (archetype, mechanism)
                
                if key not in self._effectiveness_matrix:
                    self._effectiveness_matrix[key] = MechanismEffectiveness(
                        mechanism=mechanism,
                        archetype=archetype,
                    )
                
                eff = self._effectiveness_matrix[key]
                eff.total_count += 1
                eff.weighted_total += weight
                
                if is_success:
                    eff.success_count += 1
                    eff.weighted_success += weight
                
                # Add example template
                if tier in (InfluenceTier.VIRAL, InfluenceTier.VERY_HIGH):
                    if len(eff.example_templates) < 5:
                        example = list(mechanisms_detected[mechanism])[0] if mechanisms_detected[mechanism] else ""
                        if example:
                            eff.example_templates.append(example)
                
                result["effectiveness_updates"][mechanism] = eff.weighted_success_rate
        
        return result
    
    def _detect_mechanisms(self, text: str) -> Dict[str, Set[str]]:
        """Detect persuasion mechanisms and extract matching text."""
        detected = {}
        
        for mechanism, patterns in self._patterns.items():
            matches = set()
            for pattern in patterns:
                for match in pattern.finditer(text):
                    matches.add(match.group(0))
            
            if matches:
                detected[mechanism] = matches
        
        return detected
    
    def _compute_effectiveness(
        self,
        helpful_votes: int,
        rating: float,
        verified: bool,
    ) -> float:
        """Compute effectiveness score for a template."""
        # Base from votes (log scale)
        vote_factor = math.log10(helpful_votes + 1) / 3  # 0-1 for 1-1000 votes
        
        # Rating factor
        rating_factor = (rating - 1) / 4  # 0-1 for 1-5 stars
        
        # Verified boost
        verified_boost = 1.2 if verified else 1.0
        
        # Combined score
        return min(1.0, vote_factor * 0.6 + rating_factor * 0.3 + 0.1) * verified_boost
    
    # =========================================================================
    # OUTPUT FOR GRAPH DATABASE
    # =========================================================================
    
    def get_graph_effectiveness_matrix(self) -> List[Dict[str, Any]]:
        """
        Get effectiveness matrix for Neo4j.
        
        Returns list of edge property dicts for:
        (:Archetype)-[:RESPONDS_TO {effectiveness}]->(:Mechanism)
        """
        return [
            eff.to_graph_edge()
            for eff in self._effectiveness_matrix.values()
            if eff.total_count >= 3  # Minimum sample size
        ]
    
    async def persist_to_graph(self, driver) -> int:
        """
        Persist effectiveness matrix to Neo4j.
        
        Creates/updates edges:
        (:Archetype)-[:RESPONDS_TO]->(:CognitiveMechanism)
        """
        if not driver:
            return 0
        
        query = """
        UNWIND $edges AS edge
        MERGE (a:Archetype {name: edge.archetype})
        MERGE (m:CognitiveMechanism {name: edge.mechanism})
        MERGE (a)-[r:RESPONDS_TO]->(m)
        SET r.success_rate = edge.success_rate,
            r.weighted_success_rate = edge.weighted_success_rate,
            r.confidence = edge.confidence,
            r.sample_size = edge.sample_size,
            r.updated_at = datetime($updated_at)
        RETURN count(*) AS updated
        """
        
        edges = self.get_graph_effectiveness_matrix()
        if not edges:
            return 0
        
        try:
            async with driver.session() as session:
                result = await session.run(
                    query,
                    edges=edges,
                    updated_at=datetime.now(timezone.utc).isoformat(),
                )
                record = await result.single()
                return record["updated"] if record else 0
        except Exception as e:
            logger.error(f"Failed to persist effectiveness matrix: {e}")
            return 0
    
    # =========================================================================
    # OUTPUT FOR AOT ATOMS
    # =========================================================================
    
    def get_aot_evidence(
        self,
        archetype: Optional[str] = None,
        mechanism: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Get pre-fetched evidence for AoT atoms.
        
        Returns templates formatted for atom consumption.
        """
        # Filter templates
        templates = self._templates
        
        if archetype:
            templates = [
                t for t in templates
                if archetype in t.archetype_affinity
            ]
        
        if mechanism:
            templates = [
                t for t in templates
                if t.mechanism == mechanism
            ]
        
        # Sort by effectiveness
        templates = sorted(
            templates,
            key=lambda t: t.effectiveness_score,
            reverse=True,
        )[:limit]
        
        return [t.to_aot_evidence() for t in templates]
    
    def get_mechanism_priors(
        self,
        archetype: str,
    ) -> Dict[str, Dict[str, float]]:
        """
        Get mechanism priors for an archetype.
        
        Returns dict: mechanism -> {success_rate, confidence, sample_size}
        
        Used by MechanismActivation atom for prior injection.
        """
        priors = {}
        
        for (arch, mech), eff in self._effectiveness_matrix.items():
            if arch == archetype:
                priors[mech] = {
                    "success_rate": eff.weighted_success_rate,
                    "confidence": eff.confidence,
                    "sample_size": eff.total_count,
                }
        
        return priors
    
    # =========================================================================
    # OUTPUT FOR LANGGRAPH
    # =========================================================================
    
    def get_langgraph_routing_data(self) -> Dict[str, Any]:
        """
        Get routing recommendations for LangGraph.
        
        Returns data for LangGraph to make orchestration decisions:
        - Which mechanisms to prioritize per archetype
        - Confidence levels for routing decisions
        - Template availability status
        """
        # Compute archetype -> ranked mechanisms
        archetype_rankings = {}
        
        for (arch, mech), eff in self._effectiveness_matrix.items():
            if arch not in archetype_rankings:
                archetype_rankings[arch] = []
            
            archetype_rankings[arch].append({
                "mechanism": mech,
                "score": eff.weighted_success_rate * eff.confidence,
                "confidence": eff.confidence,
                "sample_size": eff.total_count,
            })
        
        # Sort by score
        for arch in archetype_rankings:
            archetype_rankings[arch] = sorted(
                archetype_rankings[arch],
                key=lambda x: x["score"],
                reverse=True,
            )
        
        return {
            "archetype_mechanism_rankings": archetype_rankings,
            "template_count": len(self._templates),
            "high_confidence_archetypes": [
                arch for arch, rankings in archetype_rankings.items()
                if any(r["confidence"] > 0.7 for r in rankings)
            ],
            "coverage": {
                "archetypes": len(archetype_rankings),
                "mechanisms": len(set(m for _, m in self._effectiveness_matrix.keys())),
                "reviews_processed": self._reviews_processed,
                "high_vote_reviews": self._high_vote_reviews,
            },
        }
    
    # =========================================================================
    # STATS & HEALTH
    # =========================================================================
    
    def get_stats(self) -> Dict[str, Any]:
        """Get processing statistics."""
        return {
            "reviews_processed": self._reviews_processed,
            "high_vote_reviews": self._high_vote_reviews,
            "templates_extracted": len(self._templates),
            "effectiveness_pairs": len(self._effectiveness_matrix),
            "archetypes_covered": len(set(a for a, _ in self._effectiveness_matrix.keys())),
            "mechanisms_covered": len(set(m for _, m in self._effectiveness_matrix.keys())),
        }


# =============================================================================
# SINGLETON
# =============================================================================

_intelligence: Optional[HelpfulVoteIntelligence] = None


def get_helpful_vote_intelligence() -> HelpfulVoteIntelligence:
    """Get singleton helpful vote intelligence processor."""
    global _intelligence
    if _intelligence is None:
        _intelligence = HelpfulVoteIntelligence()
    return _intelligence


def reset_helpful_vote_intelligence() -> None:
    """Reset singleton for testing."""
    global _intelligence
    _intelligence = None
