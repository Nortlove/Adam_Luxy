# =============================================================================
# Claude-Powered Review Summarizer
# Location: adam/intelligence/claude_summarizer.py
# =============================================================================

"""
Claude-Powered Review Intelligence Summarization

Uses Claude to extract deep psychological insights from product reviews:
1. Dominant buyer archetype from language patterns
2. Primary purchase motivations
3. Emotional language patterns
4. Big Five personality trait signals
5. Key phrases that resonate
6. Objections and how they were overcome

This transforms raw reviews into actionable customer intelligence.

Usage:
    summarizer = ReviewSummarizer()
    insights = await summarizer.summarize_reviews(
        reviews=[...],
        product_name="DEWALT Impact Driver",
        brand="DEWALT"
    )
"""

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Check for Claude/Anthropic API availability
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


@dataclass
class ReviewInsights:
    """
    Comprehensive insights extracted from reviews.
    
    This represents the "voice of the customer" distilled
    through psychological analysis.
    """
    # Core psychological classification
    dominant_archetype: str = ""
    archetype_confidence: float = 0.0
    archetype_evidence: List[str] = field(default_factory=list)
    
    secondary_archetypes: Dict[str, float] = field(default_factory=dict)
    
    # Big Five personality signals
    personality_profile: Dict[str, float] = field(default_factory=dict)
    # e.g., {"openness": 0.7, "conscientiousness": 0.8, ...}
    
    # Motivations and drivers
    primary_motivations: List[str] = field(default_factory=list)
    secondary_motivations: List[str] = field(default_factory=list)
    
    # Language patterns
    emotional_language: List[str] = field(default_factory=list)
    power_words: List[str] = field(default_factory=list)
    key_phrases: List[str] = field(default_factory=list)
    
    # Objection handling
    common_objections: List[str] = field(default_factory=list)
    how_objections_overcome: List[str] = field(default_factory=list)
    
    # Purchase decision insights
    decision_drivers: List[str] = field(default_factory=list)
    comparison_factors: List[str] = field(default_factory=list)
    
    # Sentiment and satisfaction
    overall_sentiment: str = ""  # positive/mixed/negative
    satisfaction_factors: List[str] = field(default_factory=list)
    dissatisfaction_factors: List[str] = field(default_factory=list)
    
    # Copywriting guidance
    recommended_tone: str = ""
    message_themes: List[str] = field(default_factory=list)
    calls_to_action: List[str] = field(default_factory=list)
    
    # Mechanism recommendations
    recommended_mechanisms: Dict[str, float] = field(default_factory=dict)
    mechanism_evidence: Dict[str, str] = field(default_factory=dict)
    
    # Metadata
    reviews_analyzed: int = 0
    analysis_confidence: float = 0.0
    analysis_timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "dominant_archetype": self.dominant_archetype,
            "archetype_confidence": self.archetype_confidence,
            "archetype_evidence": self.archetype_evidence,
            "secondary_archetypes": self.secondary_archetypes,
            "personality_profile": self.personality_profile,
            "primary_motivations": self.primary_motivations,
            "secondary_motivations": self.secondary_motivations,
            "emotional_language": self.emotional_language,
            "power_words": self.power_words,
            "key_phrases": self.key_phrases,
            "common_objections": self.common_objections,
            "how_objections_overcome": self.how_objections_overcome,
            "decision_drivers": self.decision_drivers,
            "comparison_factors": self.comparison_factors,
            "overall_sentiment": self.overall_sentiment,
            "satisfaction_factors": self.satisfaction_factors,
            "dissatisfaction_factors": self.dissatisfaction_factors,
            "recommended_tone": self.recommended_tone,
            "message_themes": self.message_themes,
            "calls_to_action": self.calls_to_action,
            "recommended_mechanisms": self.recommended_mechanisms,
            "mechanism_evidence": self.mechanism_evidence,
            "reviews_analyzed": self.reviews_analyzed,
            "analysis_confidence": self.analysis_confidence,
        }


class ReviewSummarizer:
    """
    Claude-powered review summarization for psychological insights.
    
    This is the "voice of the customer" intelligence layer.
    """
    
    SUMMARIZE_PROMPT = '''You are an expert advertising psychologist analyzing customer reviews.
Your goal is to extract deep psychological insights that will help create highly effective advertising.

PRODUCT: {brand} {product}

CUSTOMER REVIEWS ({review_count} total):
{formatted_reviews}

Analyze these reviews and extract psychological intelligence. Return a JSON object:

{{
    "dominant_archetype": "Achiever|Explorer|Guardian|Connector|Pragmatist - based on predominant language patterns",
    "archetype_confidence": 0.0-1.0,
    "archetype_evidence": ["Direct quote or pattern that reveals archetype", "Another example"],
    "secondary_archetypes": {{
        "Achiever": 0.0-1.0,
        "Explorer": 0.0-1.0,
        "Guardian": 0.0-1.0,
        "Connector": 0.0-1.0,
        "Pragmatist": 0.0-1.0
    }},
    "personality_profile": {{
        "openness": 0.0-1.0,
        "conscientiousness": 0.0-1.0,
        "extraversion": 0.0-1.0,
        "agreeableness": 0.0-1.0,
        "neuroticism": 0.0-1.0
    }},
    "primary_motivations": ["What primarily drove people to buy"],
    "secondary_motivations": ["Other reasons mentioned"],
    "emotional_language": ["Emotional words used by reviewers"],
    "power_words": ["High-impact words that appear frequently"],
    "key_phrases": ["Exact phrases from reviews that are compelling and could be used in ads"],
    "common_objections": ["Concerns mentioned before or after purchase"],
    "how_objections_overcome": ["How reviewers describe overcoming hesitation"],
    "decision_drivers": ["What finally made them decide to buy"],
    "comparison_factors": ["What they compared against"],
    "overall_sentiment": "positive|mixed|negative",
    "satisfaction_factors": ["What satisfied customers mention"],
    "dissatisfaction_factors": ["What disappointed customers mention"],
    "recommended_tone": "Description of tone that would resonate",
    "message_themes": ["Themes that would connect based on review language"],
    "calls_to_action": ["CTAs that align with purchase motivations"],
    "recommended_mechanisms": {{
        "authority": 0.0-1.0,
        "social_proof": 0.0-1.0,
        "scarcity": 0.0-1.0,
        "reciprocity": 0.0-1.0,
        "commitment": 0.0-1.0,
        "liking": 0.0-1.0
    }},
    "mechanism_evidence": {{
        "authority": "Why this mechanism would work based on reviews",
        "social_proof": "Evidence for this mechanism"
    }},
    "analysis_confidence": 0.0-1.0
}}

ARCHETYPE DEFINITIONS for classification:
- Achiever: Uses success language ("best", "professional", "worth it"), values quality and status
- Explorer: Uses discovery language ("love trying", "amazing find", "impressed"), values novelty
- Guardian: Uses security language ("reliable", "trust", "safe", "family"), values stability
- Connector: Uses relationship language ("share", "friends love it", "recommend"), values belonging
- Pragmatist: Uses value language ("good deal", "does the job", "practical"), values ROI

MECHANISM SELECTION GUIDANCE:
- Authority: Works when reviewers mention expert recommendations, professional use, or quality standards
- Social Proof: Works when reviewers mention recommendations, popularity, or what others think
- Scarcity: Works when reviewers mention limited availability, exclusivity, or fear of missing out
- Reciprocity: Works when reviewers mention value received, helpfulness, or feeling cared for
- Commitment: Works when reviewers mention loyalty, repeat purchases, or long-term satisfaction
- Liking: Works when reviewers mention brand affinity, personality, or emotional connection

Return ONLY valid JSON, no other text.

JSON Response:'''

    def __init__(self, api_key: Optional[str] = None, model: str = "claude-sonnet-4-20250514"):
        """Initialize the summarizer."""
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.model = model
        self._client = None
    
    def _get_client(self):
        """Get or create Anthropic client."""
        if not ANTHROPIC_AVAILABLE:
            raise ImportError("Anthropic library not installed")
        
        if not self.api_key:
            raise ValueError("Anthropic API key required")
        
        if self._client is None:
            self._client = anthropic.Anthropic(api_key=self.api_key)
        
        return self._client
    
    async def summarize_reviews(
        self,
        reviews: List[Dict[str, Any]],
        product_name: str,
        brand: str,
        max_reviews: int = 50,
    ) -> ReviewInsights:
        """
        Summarize reviews using Claude for psychological insights.
        
        Args:
            reviews: List of review dicts with 'review_text' and 'rating'
            product_name: Product name
            brand: Brand name
            max_reviews: Maximum reviews to include (for token management)
            
        Returns:
            ReviewInsights with comprehensive analysis
        """
        if not reviews:
            return ReviewInsights(analysis_confidence=0.0)
        
        logger.info(f"Summarizing {len(reviews)} reviews for {brand} {product_name}")
        
        # Sample reviews if too many (prefer high-rated and low-rated)
        sampled = self._sample_reviews(reviews, max_reviews)
        
        # Format reviews for prompt
        formatted = self._format_reviews_for_prompt(sampled)
        
        # Build prompt
        prompt = self.SUMMARIZE_PROMPT.format(
            brand=brand,
            product=product_name,
            review_count=len(sampled),
            formatted_reviews=formatted,
        )
        
        try:
            client = self._get_client()
            response = client.messages.create(
                model=self.model,
                max_tokens=2500,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            raw_response = response.content[0].text
            
            # Parse JSON
            try:
                analysis = json.loads(raw_response)
            except json.JSONDecodeError:
                import re
                json_match = re.search(r'\{[\s\S]*\}', raw_response)
                if json_match:
                    analysis = json.loads(json_match.group())
                else:
                    logger.error(f"Failed to parse JSON from review summary")
                    return self._create_fallback_insights(sampled)
            
            # Build insights
            insights = self._build_insights(analysis, len(sampled))
            
            logger.info(
                f"Review analysis complete: {insights.dominant_archetype} archetype "
                f"({insights.archetype_confidence:.0%} confidence)"
            )
            
            return insights
            
        except Exception as e:
            logger.error(f"Error summarizing reviews with Claude: {e}")
            return self._create_fallback_insights(sampled)
    
    def _sample_reviews(
        self,
        reviews: List[Dict[str, Any]],
        max_count: int,
    ) -> List[Dict[str, Any]]:
        """Sample reviews, preferring high and low ratings for diversity."""
        if len(reviews) <= max_count:
            return reviews
        
        # Sort by rating
        sorted_reviews = sorted(reviews, key=lambda r: r.get("rating", 3))
        
        # Take from both ends plus middle
        high_rated = sorted_reviews[-max_count//3:]
        low_rated = sorted_reviews[:max_count//6]
        mid_rated = sorted_reviews[len(sorted_reviews)//3:2*len(sorted_reviews)//3][:max_count//2]
        
        sampled = high_rated + mid_rated + low_rated
        return sampled[:max_count]
    
    def _format_reviews_for_prompt(self, reviews: List[Dict[str, Any]]) -> str:
        """Format reviews for the prompt."""
        formatted = []
        for i, review in enumerate(reviews, 1):
            rating = review.get("rating", "N/A")
            text = review.get("review_text", "")[:500]  # Truncate long reviews
            formatted.append(f"[Review {i}] Rating: {rating}/5\n{text}\n")
        
        return "\n".join(formatted)
    
    def _build_insights(self, analysis: Dict[str, Any], review_count: int) -> ReviewInsights:
        """Build ReviewInsights from Claude's analysis."""
        return ReviewInsights(
            dominant_archetype=analysis.get("dominant_archetype", ""),
            archetype_confidence=analysis.get("archetype_confidence", 0.5),
            archetype_evidence=analysis.get("archetype_evidence", []),
            secondary_archetypes=analysis.get("secondary_archetypes", {}),
            personality_profile=analysis.get("personality_profile", {}),
            primary_motivations=analysis.get("primary_motivations", []),
            secondary_motivations=analysis.get("secondary_motivations", []),
            emotional_language=analysis.get("emotional_language", []),
            power_words=analysis.get("power_words", []),
            key_phrases=analysis.get("key_phrases", []),
            common_objections=analysis.get("common_objections", []),
            how_objections_overcome=analysis.get("how_objections_overcome", []),
            decision_drivers=analysis.get("decision_drivers", []),
            comparison_factors=analysis.get("comparison_factors", []),
            overall_sentiment=analysis.get("overall_sentiment", "mixed"),
            satisfaction_factors=analysis.get("satisfaction_factors", []),
            dissatisfaction_factors=analysis.get("dissatisfaction_factors", []),
            recommended_tone=analysis.get("recommended_tone", ""),
            message_themes=analysis.get("message_themes", []),
            calls_to_action=analysis.get("calls_to_action", []),
            recommended_mechanisms=analysis.get("recommended_mechanisms", {}),
            mechanism_evidence=analysis.get("mechanism_evidence", {}),
            reviews_analyzed=review_count,
            analysis_confidence=analysis.get("analysis_confidence", 0.7),
        )
    
    def _create_fallback_insights(self, reviews: List[Dict[str, Any]]) -> ReviewInsights:
        """Create basic insights when Claude is unavailable."""
        logger.warning("Using fallback review insights (Claude unavailable)")
        
        # Basic sentiment from ratings
        ratings = [r.get("rating", 3) for r in reviews if r.get("rating")]
        avg_rating = sum(ratings) / len(ratings) if ratings else 3.0
        
        sentiment = "positive" if avg_rating >= 4 else "mixed" if avg_rating >= 3 else "negative"
        
        return ReviewInsights(
            dominant_archetype="Pragmatist",  # Default assumption
            archetype_confidence=0.3,
            overall_sentiment=sentiment,
            reviews_analyzed=len(reviews),
            analysis_confidence=0.2,
        )


# =============================================================================
# SINGLETON
# =============================================================================

_summarizer: Optional[ReviewSummarizer] = None


def get_review_summarizer() -> ReviewSummarizer:
    """Get singleton ReviewSummarizer."""
    global _summarizer
    if _summarizer is None:
        _summarizer = ReviewSummarizer()
    return _summarizer
