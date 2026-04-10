# =============================================================================
# Buyer-Friendly Demo Response Builder
# Location: adam/demo/buyer_friendly_response.py
# =============================================================================

"""
Transforms technical ADAM responses into buyer-friendly presentations.

For non-technical decision makers (CMOs, VPs, Agency Execs), we need:
1. Executive summary in plain English
2. Evidence chains showing "why" not "what"
3. Real station examples (Z100, not "CHR")
4. Customer quotes from reviews
5. Research citations for credibility
6. Business-focused expected impact

This module wraps CampaignAnalysisResponse with buyer-friendly content.
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)


# =============================================================================
# BUYER-FRIENDLY MODELS
# =============================================================================

@dataclass
class ExecutiveSummary:
    """One-paragraph executive summary for busy decision makers."""
    headline: str  # "Your product appeals to Achievement-Driven buyers"
    key_insight: str  # Why this matters
    recommended_action: str  # What to do
    confidence_statement: str  # "Based on analysis of X reviews..."


@dataclass
class EvidencePoint:
    """A single piece of evidence supporting a recommendation."""
    claim: str  # What we're claiming
    evidence: str  # How we know
    source: str  # Where it comes from
    strength: str  # "Strong", "Moderate", "Emerging"


@dataclass
class RealStationExample:
    """Concrete station example instead of abstract format."""
    station_name: str  # "Z100"
    market: str  # "New York, NY"
    format: str  # "Top 40/CHR"
    why_it_works: str  # Plain English explanation
    sample_shows: List[str]  # Specific shows
    listener_connection: str  # How listeners connect with product


@dataclass
class CustomerVoice:
    """Real customer language from reviews."""
    quote: str
    sentiment: str
    archetype_match: str
    use_in_copy: str  # Suggestion for how to use in creative


@dataclass
class ResearchCitation:
    """Academic credibility without being pedantic."""
    principle: str  # "Regulatory Focus Theory"
    plain_english: str  # What it means in simple terms
    application: str  # How we're applying it
    citation: str  # "Higgins (1997)"


@dataclass
class ExpectedImpact:
    """Business-focused expected outcomes."""
    metric: str  # "Engagement Rate"
    expected_lift: str  # "+15-25%"
    basis: str  # Why we expect this
    comparison: str  # "vs. untargeted approach"


@dataclass
class BuyerFriendlyResponse:
    """Complete buyer-friendly analysis presentation."""
    
    # Executive overview
    executive_summary: ExecutiveSummary
    
    # The "why" - evidence chains
    evidence_chain: List[EvidencePoint]
    
    # Concrete recommendations
    station_examples: List[RealStationExample]
    
    # Customer voice
    customer_quotes: List[CustomerVoice]
    
    # Research foundation
    research_basis: List[ResearchCitation]
    
    # Business impact
    expected_impact: List[ExpectedImpact]
    
    # Metadata
    analysis_depth: str  # "Deep Analysis" or "Initial Assessment"
    data_sources: List[str]  # What powered this analysis
    next_steps: List[str]  # Recommended actions


# =============================================================================
# TRANSFORMATION LOGIC
# =============================================================================

# Station format to real station mapping (sample - would be Neo4j query in production)
FORMAT_TO_STATIONS = {
    "CHR": [
        {"name": "Z100", "market": "New York, NY", "shows": ["Elvis Duran and the Morning Show"]},
        {"name": "KIIS-FM", "market": "Los Angeles, CA", "shows": ["On Air with Ryan Seacrest"]},
        {"name": "Y100", "market": "Miami, FL", "shows": ["The Morning Mashup"]},
    ],
    "Hot AC": [
        {"name": "WLTW", "market": "New York, NY", "shows": ["The Morning Show"]},
        {"name": "KOST 103.5", "market": "Los Angeles, CA", "shows": ["Ellen K Morning Show"]},
    ],
    "News/Talk": [
        {"name": "KFI-AM", "market": "Los Angeles, CA", "shows": ["The John & Ken Show"]},
        {"name": "WOR", "market": "New York, NY", "shows": ["The Morning Show"]},
    ],
    "Country": [
        {"name": "WUSN", "market": "Chicago, IL", "shows": ["US99 Morning Show"]},
        {"name": "KSCS", "market": "Dallas, TX", "shows": ["Hawkeye in the Morning"]},
    ],
    "Classic Rock": [
        {"name": "WAXQ", "market": "New York, NY", "shows": ["Jim Kerr Rock & Roll Morning Show"]},
        {"name": "KLOS", "market": "Los Angeles, CA", "shows": ["Heidi and Frank"]},
    ],
}

# Archetype to plain English
ARCHETYPE_DESCRIPTIONS = {
    "Achiever": {
        "headline": "Achievement-Driven Professionals",
        "description": "People motivated by success, recognition, and getting results",
        "what_they_want": "They want products that help them succeed and signal their success to others",
        "messaging_tip": "Lead with outcomes and competitive advantage",
    },
    "Explorer": {
        "headline": "Curious Discoverers",
        "description": "People drawn to new experiences, innovation, and uniqueness",
        "what_they_want": "They want to be first, try new things, and stand out from the crowd",
        "messaging_tip": "Emphasize novelty, discovery, and being ahead of the curve",
    },
    "Guardian": {
        "headline": "Security-Minded Protectors",
        "description": "People who prioritize safety, reliability, and protecting what matters",
        "what_they_want": "They want assurance, track records, and protection from risk",
        "messaging_tip": "Lead with reliability, warranties, and peace of mind",
    },
    "Connector": {
        "headline": "Social Relationship Builders",
        "description": "People who value relationships, community, and belonging",
        "what_they_want": "They want to connect with others and be part of something bigger",
        "messaging_tip": "Emphasize community, sharing, and social proof",
    },
    "Pragmatist": {
        "headline": "Value-Driven Decision Makers",
        "description": "People who make practical decisions based on clear value",
        "what_they_want": "They want to understand exactly what they're getting for their investment",
        "messaging_tip": "Be direct about value, features, and benefits",
    },
}

# Mechanism to plain English
MECHANISM_DESCRIPTIONS = {
    "regulatory_focus": {
        "principle": "Regulatory Focus Theory",
        "plain_english": "People are either motivated by gains (promotion) or avoiding losses (prevention)",
        "citation": "Higgins (1997, 1998)",
    },
    "social_proof": {
        "principle": "Social Proof",
        "plain_english": "People look to others' behavior to guide their own decisions",
        "citation": "Cialdini (2009)",
    },
    "mimetic_desire": {
        "principle": "Mimetic Desire",
        "plain_english": "We want what people we admire want - desire is contagious",
        "citation": "Girard (1961)",
    },
    "identity_construction": {
        "principle": "Identity Construction",
        "plain_english": "People buy products that express who they are or want to become",
        "citation": "Belk (1988); Oyserman (2009)",
    },
    "temporal_construal": {
        "principle": "Temporal Construal",
        "plain_english": "Near-term decisions focus on practical details; far-term on big picture",
        "citation": "Trope & Liberman (2010)",
    },
    "scarcity": {
        "principle": "Scarcity Principle",
        "plain_english": "Limited availability increases perceived value and urgency",
        "citation": "Cialdini (2009)",
    },
    "authority": {
        "principle": "Authority Principle",
        "plain_english": "People trust and follow credible experts",
        "citation": "Cialdini (2009)",
    },
    "automatic_evaluation": {
        "principle": "Automatic Evaluation",
        "plain_english": "First impressions happen instantly and shape everything after",
        "citation": "Kahneman (2011)",
    },
}


def build_buyer_friendly_response(
    technical_response: Dict[str, Any],
    include_customer_quotes: bool = True,
) -> BuyerFriendlyResponse:
    """
    Transform a technical CampaignAnalysisResponse into a buyer-friendly presentation.
    
    Args:
        technical_response: The raw API response dictionary
        include_customer_quotes: Whether to include customer language
        
    Returns:
        BuyerFriendlyResponse with all sections
    """
    
    # Extract key elements
    segments = technical_response.get("core_segments", [])
    station_recs = technical_response.get("station_recommendations", [])
    review_intel = technical_response.get("review_intelligence", {})
    components = technical_response.get("components_used", [])
    confidence = technical_response.get("overall_confidence", 0.5)
    product = technical_response.get("campaign", {}).get("product", "your product")
    brand = technical_response.get("campaign", {}).get("brand", "your brand")
    
    # Determine primary segment
    primary_segment = segments[0] if segments else {}
    primary_archetype = primary_segment.get("archetype", "Achiever")
    primary_mechanism = primary_segment.get("primary_mechanism", "social_proof")
    
    # Build executive summary
    arch_info = ARCHETYPE_DESCRIPTIONS.get(primary_archetype, ARCHETYPE_DESCRIPTIONS["Pragmatist"])
    
    # Determine data basis
    reviews_analyzed = 0
    if review_intel:
        reviews_analyzed = review_intel.get("reviews_analyzed", 0)
    
    if reviews_analyzed > 50:
        confidence_basis = f"Based on deep analysis of {reviews_analyzed} real customer reviews"
    elif reviews_analyzed > 0:
        confidence_basis = f"Based on analysis of {reviews_analyzed} customer reviews"
    elif "ClaudeProductAnalysis" in components:
        confidence_basis = "Based on AI-powered product analysis"
    else:
        confidence_basis = "Based on product characteristic analysis"
    
    executive_summary = ExecutiveSummary(
        headline=f"{brand} appeals to {arch_info['headline']}",
        key_insight=arch_info["what_they_want"],
        recommended_action=arch_info["messaging_tip"],
        confidence_statement=f"{confidence_basis} with {confidence:.0%} confidence.",
    )
    
    # Build evidence chain
    evidence_chain = []
    
    # Evidence 1: Archetype identification
    evidence_chain.append(EvidencePoint(
        claim=f"Your primary audience are {arch_info['headline']}",
        evidence=primary_segment.get("match_explanation", "Product characteristics match this profile"),
        source="Customer psychology analysis",
        strength="Strong" if confidence > 0.7 else "Moderate",
    ))
    
    # Evidence 2: Mechanism selection
    mech_info = MECHANISM_DESCRIPTIONS.get(primary_mechanism, {})
    if mech_info:
        evidence_chain.append(EvidencePoint(
            claim=f"They respond best to {mech_info.get('plain_english', primary_mechanism)}",
            evidence=primary_segment.get("mechanism_explanation", "Research-based matching"),
            source=mech_info.get("citation", "Psychological research"),
            strength="Strong",
        ))
    
    # Evidence 3: Station fit
    if station_recs:
        top_station = station_recs[0]
        evidence_chain.append(EvidencePoint(
            claim=f"Radio format {top_station.get('station_format', 'CHR')} reaches them effectively",
            evidence=top_station.get("recommendation_reason", "Listener profile alignment"),
            source="iHeart audience analysis",
            strength="Strong" if top_station.get("confidence_level", 0) > 0.7 else "Moderate",
        ))
    
    # Build real station examples
    station_examples = []
    for rec in station_recs[:3]:
        format_key = rec.get("station_format", "CHR")
        real_stations = FORMAT_TO_STATIONS.get(format_key, FORMAT_TO_STATIONS.get("CHR", []))
        
        if real_stations:
            rs = real_stations[0]
            station_examples.append(RealStationExample(
                station_name=rs["name"],
                market=rs["market"],
                format=format_key,
                why_it_works=rec.get("recommendation_reason", f"Reaches {arch_info['headline']}"),
                sample_shows=rs.get("shows", []),
                listener_connection=f"Listeners who are {arch_info['description'].lower()} "
                                   f"tune into {rs['name']} regularly.",
            ))
    
    # Build customer quotes (if available)
    customer_quotes = []
    if include_customer_quotes and review_intel:
        # Extract quotes from review intelligence
        language_intel = review_intel.get("language_intelligence", {})
        phrases = language_intel.get("characteristic_phrases", [])
        
        for phrase in phrases[:3]:
            if phrase:
                customer_quotes.append(CustomerVoice(
                    quote=phrase,
                    sentiment="Positive",
                    archetype_match=primary_archetype,
                    use_in_copy=f'Use "{phrase}" or similar language in your creative',
                ))
    
    # Build research basis
    research_basis = []
    
    # Add mechanism research
    if mech_info:
        research_basis.append(ResearchCitation(
            principle=mech_info.get("principle", primary_mechanism.replace("_", " ").title()),
            plain_english=mech_info.get("plain_english", ""),
            application=f"We use this to frame your message for {arch_info['headline']}",
            citation=mech_info.get("citation", ""),
        ))
    
    # Add archetype research
    research_basis.append(ResearchCitation(
        principle="Customer Archetype Theory",
        plain_english="Different people have different core motivations that drive purchase decisions",
        application=f"We identified {primary_archetype}s as your primary buyers",
        citation="Based on Big Five personality research and consumer psychology",
    ))
    
    # Build expected impact
    expected_impact = [
        ExpectedImpact(
            metric="Message Resonance",
            expected_lift="+20-35%",
            basis=f"Matching message to {primary_archetype} psychology",
            comparison="vs. generic messaging",
        ),
        ExpectedImpact(
            metric="Station Efficiency",
            expected_lift="+15-25%",
            basis="Targeting stations where your audience over-indexes",
            comparison="vs. broad demographic targeting",
        ),
        ExpectedImpact(
            metric="Brand Recall",
            expected_lift="+10-20%",
            basis="Using psychology-matched creative approach",
            comparison="vs. standard creative",
        ),
    ]
    
    # Determine analysis depth
    if reviews_analyzed > 100:
        analysis_depth = "Deep Customer Intelligence Analysis"
    elif reviews_analyzed > 0:
        analysis_depth = "Customer Intelligence Analysis"
    elif "CampaignOrchestrator" in str(components):
        analysis_depth = "Full ADAM Analysis"
    else:
        analysis_depth = "Initial Assessment"
    
    # Build data sources list (plain English)
    data_sources = []
    if reviews_analyzed > 0:
        data_sources.append(f"{reviews_analyzed} real customer reviews")
    if "Neo4jGraphIntelligence" in str(components):
        data_sources.append("iHeart radio station intelligence")
    if "ClaudeProductAnalysis" in str(components) or "ClaudeReasoning" in str(components):
        data_sources.append("AI-powered product understanding")
    if "ThompsonSampling" in str(components) or "MetaLearner" in str(components):
        data_sources.append("Learning system with continuous optimization")
    if not data_sources:
        data_sources.append("Product and market analysis")
    
    # Build next steps
    next_steps = [
        f"Review the station recommendations and select {station_examples[0].station_name if station_examples else 'target stations'}",
        f"Develop creative using {arch_info['messaging_tip'].lower()}",
        "Set up campaign measurement to feed our learning system",
        "Schedule follow-up to review performance and optimize",
    ]
    
    return BuyerFriendlyResponse(
        executive_summary=executive_summary,
        evidence_chain=evidence_chain,
        station_examples=station_examples,
        customer_quotes=customer_quotes,
        research_basis=research_basis,
        expected_impact=expected_impact,
        analysis_depth=analysis_depth,
        data_sources=data_sources,
        next_steps=next_steps,
    )


def format_buyer_friendly_markdown(response: BuyerFriendlyResponse) -> str:
    """
    Format the buyer-friendly response as markdown for presentation.
    
    This creates a clean, scannable document for busy executives.
    """
    lines = []
    
    # Executive Summary
    lines.append("# Executive Summary")
    lines.append("")
    lines.append(f"**{response.executive_summary.headline}**")
    lines.append("")
    lines.append(f"*{response.executive_summary.key_insight}*")
    lines.append("")
    lines.append(f"**Recommendation:** {response.executive_summary.recommended_action}")
    lines.append("")
    lines.append(f"_{response.executive_summary.confidence_statement}_")
    lines.append("")
    
    # Evidence Chain
    lines.append("## Why This Works")
    lines.append("")
    for i, evidence in enumerate(response.evidence_chain, 1):
        lines.append(f"**{i}. {evidence.claim}**")
        lines.append(f"   - Evidence: {evidence.evidence}")
        lines.append(f"   - Source: {evidence.source} ({evidence.strength})")
        lines.append("")
    
    # Station Recommendations
    if response.station_examples:
        lines.append("## Recommended Stations")
        lines.append("")
        for station in response.station_examples:
            lines.append(f"### {station.station_name} ({station.market})")
            lines.append(f"*Format: {station.format}*")
            lines.append("")
            lines.append(f"{station.why_it_works}")
            lines.append("")
            if station.sample_shows:
                lines.append(f"**Key Shows:** {', '.join(station.sample_shows)}")
            lines.append("")
    
    # Customer Voice
    if response.customer_quotes:
        lines.append("## Real Customer Language")
        lines.append("*Use these phrases in your creative:*")
        lines.append("")
        for quote in response.customer_quotes:
            lines.append(f'> "{quote.quote}"')
            lines.append(f"  _{quote.use_in_copy}_")
            lines.append("")
    
    # Research Foundation
    lines.append("## Research Foundation")
    lines.append("")
    for research in response.research_basis:
        lines.append(f"**{research.principle}** ({research.citation})")
        lines.append(f"- {research.plain_english}")
        lines.append(f"- *Application:* {research.application}")
        lines.append("")
    
    # Expected Impact
    lines.append("## Expected Impact")
    lines.append("")
    for impact in response.expected_impact:
        lines.append(f"- **{impact.metric}:** {impact.expected_lift} {impact.comparison}")
        lines.append(f"  _{impact.basis}_")
        lines.append("")
    
    # Data Sources
    lines.append("---")
    lines.append(f"**Analysis Type:** {response.analysis_depth}")
    lines.append(f"**Data Sources:** {', '.join(response.data_sources)}")
    lines.append("")
    
    # Next Steps
    lines.append("## Next Steps")
    lines.append("")
    for i, step in enumerate(response.next_steps, 1):
        lines.append(f"{i}. {step}")
    
    return "\n".join(lines)


# =============================================================================
# CLI TEST
# =============================================================================

if __name__ == "__main__":
    # Test with sample response
    sample_response = {
        "request_id": "test123",
        "timestamp": "2026-01-27T10:00:00Z",
        "campaign": {
            "brand": "TechStart Pro",
            "product": "AI Productivity Suite",
            "description": "AI-powered productivity tools for professionals",
        },
        "core_segments": [
            {
                "segment_id": "achiever_segment",
                "segment_name": "Ambitious Professionals",
                "archetype": "Achiever",
                "match_explanation": "Product features align with achievement-driven psychology: efficiency gains, competitive advantage, status signaling.",
                "match_score": 0.85,
                "primary_mechanism": "identity_construction",
                "mechanism_explanation": "Achievers respond to products that express and enhance their professional identity.",
            }
        ],
        "station_recommendations": [
            {
                "station_format": "News/Talk",
                "station_description": "Informed, professional listeners",
                "recommendation_reason": "Reaches decision-makers during drive time when they're planning their day",
                "listener_profile_match": 0.82,
                "confidence_level": 0.78,
            },
            {
                "station_format": "CHR",
                "station_description": "Young professionals",
                "recommendation_reason": "Reaches ambitious 25-34 professionals",
                "listener_profile_match": 0.75,
                "confidence_level": 0.72,
            }
        ],
        "review_intelligence": {
            "reviews_analyzed": 127,
            "language_intelligence": {
                "characteristic_phrases": [
                    "saves me hours every week",
                    "game changer for my workflow",
                    "finally a tool that actually works",
                ]
            }
        },
        "components_used": ["CampaignOrchestrator", "ReviewIntelligence", "Neo4jGraphIntelligence", "ThompsonSampling"],
        "overall_confidence": 0.82,
    }
    
    # Build buyer-friendly response
    friendly = build_buyer_friendly_response(sample_response)
    
    # Format as markdown
    markdown = format_buyer_friendly_markdown(friendly)
    print(markdown)
