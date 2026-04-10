# =============================================================================
# ADAM Brand Positioning Analyzer
# Location: adam/intelligence/scrapers/brand_positioning_analyzer.py
# =============================================================================

"""
BRAND POSITIONING ANALYZER

Extracts brand self-definition language from product pages for relationship intelligence.

This provides Channel 4 (Brand Positioning) for the 5-Channel Observation Framework:
- Channel 1: Customer Reviews (how customers talk about brand)
- Channel 2: Social Signals (how customers signal to others)
- Channel 3: Self-Expression (identity statements from channels 1-2)
- Channel 4: Brand Positioning (THIS FILE - how brand defines itself)
- Channel 5: Advertising (output)

Brand positioning language reveals:
- How the brand sees itself (archetype, personality)
- What relationship the brand seeks with customers
- Value propositions and positioning statements
- Emotional vs functional emphasis
- Target audience signals

This is crucial for matching brand voice with customer relationship expectations.
"""

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# =============================================================================
# DATA MODELS
# =============================================================================

@dataclass
class BrandPositioningSignal:
    """A signal extracted from brand positioning language."""
    signal_type: str  # "value_prop", "emotional_appeal", "personality", "relationship_cue"
    text: str
    confidence: float = 0.7
    source: str = "product_page"  # "about_page", "tagline", "description"


@dataclass
class BrandPositioningAnalysis:
    """Analysis of brand positioning from product/brand page."""
    brand: str
    product: Optional[str] = None
    
    # Core positioning
    primary_value_proposition: str = ""
    emotional_appeals: List[str] = field(default_factory=list)
    functional_benefits: List[str] = field(default_factory=list)
    
    # Brand personality signals
    personality_traits: List[str] = field(default_factory=list)
    brand_archetype: Optional[str] = None
    brand_archetype_confidence: float = 0.0
    
    # Relationship signals
    desired_relationship_type: Optional[str] = None
    relationship_signals: List[str] = field(default_factory=list)
    
    # Voice characteristics
    voice_formality: float = 0.5  # 0 = casual, 1 = formal
    voice_energy: float = 0.5  # 0 = calm, 1 = energetic
    voice_warmth: float = 0.5  # 0 = distant, 1 = warm
    
    # Raw signals
    signals: List[BrandPositioningSignal] = field(default_factory=list)
    
    # Source texts
    description_text: str = ""
    tagline: str = ""
    bullet_points: List[str] = field(default_factory=list)
    
    # Metadata
    analyzed_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    confidence: float = 0.5


# =============================================================================
# BRAND POSITIONING ANALYZER
# =============================================================================

class BrandPositioningAnalyzer:
    """
    Analyzes product/brand page content to extract brand positioning signals.
    
    Uses Claude to understand:
    - Value propositions and positioning statements
    - Emotional vs functional emphasis
    - Brand personality and archetype signals
    - Relationship type the brand is seeking
    """
    
    # Mapping of positioning language to relationship types
    POSITIONING_RELATIONSHIP_MAP = {
        # Identity-focused positioning
        "express yourself": "self_expression_vehicle",
        "who you are": "self_identity_core",
        "define your": "self_identity_core",
        "be yourself": "self_expression_vehicle",
        "authentic": "self_expression_vehicle",
        "unique": "self_expression_vehicle",
        
        # Status positioning
        "luxury": "status_marker",
        "premium": "status_marker",
        "exclusive": "status_marker",
        "elite": "status_marker",
        "distinguished": "status_marker",
        "prestige": "status_marker",
        
        # Tribal/community positioning
        "community": "tribal_badge",
        "tribe": "tribal_badge",
        "belong": "tribal_badge",
        "together": "tribal_badge",
        "join": "tribal_badge",
        "family": "tribal_badge",
        
        # Functional positioning
        "reliable": "reliable_tool",
        "dependable": "reliable_tool",
        "trust": "trusted_ally",
        "quality": "reliable_tool",
        "performance": "reliable_tool",
        "built to last": "reliable_tool",
        
        # Comfort positioning
        "comfort": "comfort_companion",
        "cozy": "comfort_companion",
        "relax": "comfort_companion",
        "soothing": "comfort_companion",
        "peace": "comfort_companion",
        
        # Adventure positioning
        "adventure": "adventure_partner",
        "explore": "adventure_partner",
        "discover": "adventure_partner",
        "journey": "adventure_partner",
        "experience": "adventure_partner",
        
        # Expert positioning
        "expert": "mentor",
        "guide": "mentor",
        "professional": "mentor",
        "knowledge": "mentor",
        
        # Care positioning
        "protect": "caregiver",
        "care": "caregiver",
        "nurture": "caregiver",
        "safe": "caregiver",
        
        # Nostalgia positioning
        "heritage": "childhood_friend",
        "tradition": "childhood_friend",
        "since": "childhood_friend",
        "classic": "childhood_friend",
        "generations": "inherited_legacy",
        
        # Innovation positioning
        "innovative": "innovation_partner",
        "cutting-edge": "innovation_partner",
        "future": "innovation_partner",
        "next generation": "innovation_partner",
        
        # Value positioning
        "value": "value_champion",
        "affordable": "value_champion",
        "smart choice": "competence_validator",
    }
    
    def __init__(self):
        self._anthropic_client = None
    
    def _get_anthropic_client(self):
        """Lazy initialization of Anthropic client."""
        if self._anthropic_client is None:
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if api_key:
                try:
                    import anthropic
                    self._anthropic_client = anthropic.Anthropic(api_key=api_key)
                    logger.info("Anthropic client initialized for brand positioning")
                except ImportError:
                    logger.warning("anthropic package not installed")
        return self._anthropic_client
    
    def analyze_product_page(
        self,
        brand: str,
        product: Optional[str] = None,
        description: str = "",
        bullet_points: Optional[List[str]] = None,
        tagline: Optional[str] = None,
    ) -> BrandPositioningAnalysis:
        """
        Analyze product page content for brand positioning signals.
        
        Args:
            brand: Brand name
            product: Product name
            description: Product description text
            bullet_points: Product feature bullet points
            tagline: Brand/product tagline
            
        Returns:
            BrandPositioningAnalysis with extracted signals
        """
        analysis = BrandPositioningAnalysis(
            brand=brand,
            product=product,
            description_text=description,
            tagline=tagline or "",
            bullet_points=bullet_points or [],
        )
        
        # Combine all text for analysis
        all_text = f"{tagline or ''}\n{description}\n" + "\n".join(bullet_points or [])
        
        if not all_text.strip():
            logger.warning("No text provided for brand positioning analysis")
            return analysis
        
        # Extract signals using pattern matching
        self._extract_pattern_signals(analysis, all_text)
        
        # Use Claude for deeper analysis if available
        client = self._get_anthropic_client()
        if client:
            self._analyze_with_claude(analysis, all_text, client)
        
        # Determine primary relationship type
        self._determine_desired_relationship(analysis)
        
        return analysis
    
    def _extract_pattern_signals(
        self,
        analysis: BrandPositioningAnalysis,
        text: str,
    ) -> None:
        """Extract signals using pattern matching."""
        text_lower = text.lower()
        
        # Track relationship signal counts
        relationship_counts: Dict[str, int] = {}
        
        for pattern, relationship_type in self.POSITIONING_RELATIONSHIP_MAP.items():
            if pattern in text_lower:
                analysis.signals.append(BrandPositioningSignal(
                    signal_type="relationship_cue",
                    text=pattern,
                    confidence=0.7,
                ))
                relationship_counts[relationship_type] = relationship_counts.get(relationship_type, 0) + 1
        
        # Determine primary relationship from counts
        if relationship_counts:
            primary_rel = max(relationship_counts, key=relationship_counts.get)
            analysis.relationship_signals = list(relationship_counts.keys())
            analysis.desired_relationship_type = primary_rel
            analysis.confidence = min(0.8, 0.5 + len(relationship_counts) * 0.1)
    
    def _analyze_with_claude(
        self,
        analysis: BrandPositioningAnalysis,
        text: str,
        client,
    ) -> None:
        """Use Claude for deeper positioning analysis."""
        prompt = f"""Analyze this product/brand text for positioning signals. Be concise.

TEXT:
{text[:2000]}

Return a JSON object with:
{{
    "primary_value_proposition": "one sentence",
    "emotional_appeals": ["list of emotional appeals used"],
    "functional_benefits": ["list of functional benefits mentioned"],
    "personality_traits": ["brand personality traits detected"],
    "brand_archetype": "one of: Hero, Sage, Explorer, Outlaw, Magician, Lover, Jester, Everyman, Caregiver, Ruler, Creator, Innocent",
    "voice_formality": 0.0-1.0,
    "voice_energy": 0.0-1.0,
    "voice_warmth": 0.0-1.0,
    "desired_customer_relationship": "one of: identity_partner, status_symbol, reliable_tool, trusted_ally, adventure_companion, comfort_provider, expert_guide, tribe_badge"
}}

Only return valid JSON, nothing else."""

        try:
            response = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}]
            )
            
            import json
            result_text = response.content[0].text.strip()
            
            # Try to parse JSON
            if result_text.startswith("{"):
                result = json.loads(result_text)
                
                analysis.primary_value_proposition = result.get("primary_value_proposition", "")
                analysis.emotional_appeals = result.get("emotional_appeals", [])
                analysis.functional_benefits = result.get("functional_benefits", [])
                analysis.personality_traits = result.get("personality_traits", [])
                analysis.brand_archetype = result.get("brand_archetype")
                analysis.voice_formality = result.get("voice_formality", 0.5)
                analysis.voice_energy = result.get("voice_energy", 0.5)
                analysis.voice_warmth = result.get("voice_warmth", 0.5)
                
                # Map Claude's relationship type to our types
                claude_rel = result.get("desired_customer_relationship", "")
                if claude_rel:
                    rel_mapping = {
                        "identity_partner": "self_identity_core",
                        "status_symbol": "status_marker",
                        "reliable_tool": "reliable_tool",
                        "trusted_ally": "trusted_ally",
                        "adventure_companion": "adventure_partner",
                        "comfort_provider": "comfort_companion",
                        "expert_guide": "mentor",
                        "tribe_badge": "tribal_badge",
                    }
                    if claude_rel in rel_mapping:
                        analysis.desired_relationship_type = rel_mapping[claude_rel]
                
                analysis.confidence = 0.85
                logger.info(f"Claude brand positioning analysis complete: {analysis.brand_archetype}")
                
        except Exception as e:
            logger.warning(f"Claude positioning analysis failed: {e}")
    
    def _determine_desired_relationship(
        self,
        analysis: BrandPositioningAnalysis,
    ) -> None:
        """Determine the relationship type the brand is seeking."""
        if analysis.desired_relationship_type:
            return
        
        # Infer from personality and appeals
        if analysis.emotional_appeals:
            emotions = " ".join(analysis.emotional_appeals).lower()
            if any(w in emotions for w in ["luxury", "premium", "exclusive"]):
                analysis.desired_relationship_type = "status_marker"
            elif any(w in emotions for w in ["comfort", "peace", "relax"]):
                analysis.desired_relationship_type = "comfort_companion"
            elif any(w in emotions for w in ["trust", "reliable", "depend"]):
                analysis.desired_relationship_type = "trusted_ally"
            elif any(w in emotions for w in ["adventure", "explore", "discover"]):
                analysis.desired_relationship_type = "adventure_partner"
        
        # Infer from functional benefits
        if not analysis.desired_relationship_type and analysis.functional_benefits:
            funcs = " ".join(analysis.functional_benefits).lower()
            if any(w in funcs for w in ["performance", "quality", "durable"]):
                analysis.desired_relationship_type = "reliable_tool"
            elif any(w in funcs for w in ["value", "affordable", "budget"]):
                analysis.desired_relationship_type = "value_champion"
        
        # Default based on brand archetype
        if not analysis.desired_relationship_type and analysis.brand_archetype:
            archetype_rel_map = {
                "Hero": "aspiration_anchor",
                "Sage": "mentor",
                "Explorer": "adventure_partner",
                "Outlaw": "identity_negation",
                "Magician": "transformation_agent",
                "Lover": "committed_partnership",
                "Jester": "fling",
                "Everyman": "best_friend_utility",
                "Caregiver": "caregiver",
                "Ruler": "status_marker",
                "Creator": "co_creator",
                "Innocent": "comfort_companion",
            }
            analysis.desired_relationship_type = archetype_rel_map.get(
                analysis.brand_archetype,
                "reliable_tool"
            )
        
        # Final default
        if not analysis.desired_relationship_type:
            analysis.desired_relationship_type = "reliable_tool"
    
    def get_texts_for_relationship_analysis(
        self,
        analysis: BrandPositioningAnalysis,
    ) -> List[Dict[str, Any]]:
        """
        Convert brand positioning analysis to format for relationship detection.
        
        Returns list of dicts with 'text' and 'channel' keys.
        """
        from adam.intelligence.relationship import ObservationChannel
        
        texts = []
        
        # Add description as brand positioning text
        if analysis.description_text:
            texts.append({
                "text": analysis.description_text,
                "channel": ObservationChannel.BRAND_POSITIONING,
                "source_id": f"brand_desc:{analysis.brand}",
            })
        
        # Add tagline
        if analysis.tagline:
            texts.append({
                "text": analysis.tagline,
                "channel": ObservationChannel.BRAND_POSITIONING,
                "source_id": f"brand_tagline:{analysis.brand}",
            })
        
        # Add bullet points combined
        if analysis.bullet_points:
            combined_bullets = " | ".join(analysis.bullet_points)
            texts.append({
                "text": combined_bullets,
                "channel": ObservationChannel.BRAND_POSITIONING,
                "source_id": f"brand_bullets:{analysis.brand}",
            })
        
        # Add value proposition
        if analysis.primary_value_proposition:
            texts.append({
                "text": analysis.primary_value_proposition,
                "channel": ObservationChannel.BRAND_POSITIONING,
                "source_id": f"brand_value_prop:{analysis.brand}",
            })
        
        return texts


# =============================================================================
# FACTORY FUNCTION
# =============================================================================

def get_brand_positioning_analyzer() -> BrandPositioningAnalyzer:
    """Get the brand positioning analyzer instance."""
    return BrandPositioningAnalyzer()
