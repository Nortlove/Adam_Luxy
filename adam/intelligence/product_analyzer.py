# =============================================================================
# Claude-Powered Product Analyzer
# Location: adam/intelligence/product_analyzer.py
# =============================================================================

"""
Claude-Powered Product Understanding

Uses Claude to deeply understand products for optimal ad targeting:
1. Category & subcategory inference
2. Price tier determination (budget/mid/premium/luxury)
3. Purchase type (impulse/considered/major)
4. Geographic relevance (seasonal/regional/universal)
5. Primary psychological drivers
6. Competitive positioning
7. Target customer inference

This replaces the simplistic keyword matching with true AI understanding.

Usage:
    analyzer = ProductAnalyzer()
    intelligence = await analyzer.analyze_product(
        brand="DEWALT",
        product="20V MAX Impact Driver",
        description="Professional-grade cordless impact driver...",
        product_url="https://amazon.com/..."
    )
"""

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Check for Claude/Anthropic API availability
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    logger.warning("Anthropic library not installed. Run: pip install anthropic")


class PriceTier(str, Enum):
    """Product price tier classification."""
    BUDGET = "budget"
    MID_MARKET = "mid_market"
    PREMIUM = "premium"
    LUXURY = "luxury"


class PurchaseType(str, Enum):
    """Purchase decision type."""
    IMPULSE = "impulse"  # < $50, low consideration
    CONSIDERED = "considered"  # $50-$500, moderate research
    MAJOR = "major"  # > $500, extensive research


class GeographicRelevance(str, Enum):
    """Geographic relevance of product."""
    UNIVERSAL = "universal"  # Relevant everywhere
    SEASONAL = "seasonal"  # Weather/holiday dependent
    REGIONAL = "regional"  # Specific regions only


@dataclass
class ProductIntelligence:
    """
    Comprehensive product understanding from Claude analysis.
    
    This object contains everything ADAM needs to know about a product
    to optimize advertising.
    """
    # Basic info
    product_name: str
    brand: str
    
    # Category classification
    primary_category: str = ""
    subcategory: str = ""
    
    # Price and purchase dynamics
    price_tier: PriceTier = PriceTier.MID_MARKET
    estimated_price_range: str = ""
    purchase_type: PurchaseType = PurchaseType.CONSIDERED
    purchase_consideration_factors: List[str] = field(default_factory=list)
    
    # Geographic targeting
    geographic_relevance: GeographicRelevance = GeographicRelevance.UNIVERSAL
    relevant_regions: List[str] = field(default_factory=list)  # e.g., ["cold climates", "urban areas"]
    seasonal_relevance: Optional[str] = None  # e.g., "Winter", "Holiday season"
    exclude_regions: List[str] = field(default_factory=list)  # Regions where product doesn't make sense
    
    # Customer understanding
    primary_buyer_demographics: Dict[str, Any] = field(default_factory=dict)
    buyer_psychographics: Dict[str, Any] = field(default_factory=dict)
    inferred_archetypes: Dict[str, float] = field(default_factory=dict)  # Archetype -> probability
    
    # Psychological drivers
    functional_benefits: List[str] = field(default_factory=list)
    emotional_benefits: List[str] = field(default_factory=list)
    social_benefits: List[str] = field(default_factory=list)
    purchase_motivations: List[str] = field(default_factory=list)
    purchase_barriers: List[str] = field(default_factory=list)
    
    # Competitive context
    competitive_category: str = ""
    key_competitors: List[str] = field(default_factory=list)
    differentiation_factors: List[str] = field(default_factory=list)
    
    # Messaging guidance
    value_proposition: str = ""
    key_claims: List[str] = field(default_factory=list)
    messaging_themes: List[str] = field(default_factory=list)
    tone_recommendations: List[str] = field(default_factory=list)
    
    # Confidence and metadata
    analysis_confidence: float = 0.0
    analysis_timestamp: datetime = field(default_factory=datetime.utcnow)
    claude_model_used: str = ""
    raw_claude_response: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "product_name": self.product_name,
            "brand": self.brand,
            "primary_category": self.primary_category,
            "subcategory": self.subcategory,
            "price_tier": self.price_tier.value,
            "estimated_price_range": self.estimated_price_range,
            "purchase_type": self.purchase_type.value,
            "purchase_consideration_factors": self.purchase_consideration_factors,
            "geographic_relevance": self.geographic_relevance.value,
            "relevant_regions": self.relevant_regions,
            "seasonal_relevance": self.seasonal_relevance,
            "exclude_regions": self.exclude_regions,
            "primary_buyer_demographics": self.primary_buyer_demographics,
            "buyer_psychographics": self.buyer_psychographics,
            "inferred_archetypes": self.inferred_archetypes,
            "functional_benefits": self.functional_benefits,
            "emotional_benefits": self.emotional_benefits,
            "social_benefits": self.social_benefits,
            "purchase_motivations": self.purchase_motivations,
            "purchase_barriers": self.purchase_barriers,
            "competitive_category": self.competitive_category,
            "key_competitors": self.key_competitors,
            "differentiation_factors": self.differentiation_factors,
            "value_proposition": self.value_proposition,
            "key_claims": self.key_claims,
            "messaging_themes": self.messaging_themes,
            "tone_recommendations": self.tone_recommendations,
            "analysis_confidence": self.analysis_confidence,
            "analysis_timestamp": self.analysis_timestamp.isoformat(),
        }


class ProductAnalyzer:
    """
    Claude-powered product analysis for advertising optimization.
    
    Uses Claude to deeply understand products beyond simple keyword matching.
    """
    
    # Prompt template for product analysis
    ANALYSIS_PROMPT = '''You are an expert advertising psychologist and market researcher. 
Analyze the following product for advertising optimization.

PRODUCT INFORMATION:
- Brand: {brand}
- Product: {product}
- Description: {description}
{url_context}

Analyze this product and return a JSON object with the following structure:

{{
    "primary_category": "Main product category (e.g., 'Power Tools', 'Beauty', 'Electronics')",
    "subcategory": "Specific subcategory (e.g., 'Cordless Drills', 'Anti-Aging Skincare')",
    "price_tier": "budget|mid_market|premium|luxury",
    "estimated_price_range": "e.g., '$150-300'",
    "purchase_type": "impulse|considered|major",
    "purchase_consideration_factors": ["Factor 1", "Factor 2"],
    "geographic_relevance": "universal|seasonal|regional",
    "relevant_regions": ["Region types where product is most relevant"],
    "seasonal_relevance": "Season if applicable, null otherwise",
    "exclude_regions": ["Regions where product doesn't make sense, e.g., 'warm climates' for snow boots"],
    "primary_buyer_demographics": {{
        "age_range": "e.g., 25-54",
        "gender_skew": "male|female|balanced",
        "income_level": "e.g., middle to upper-middle",
        "occupation_types": ["Relevant occupations"]
    }},
    "buyer_psychographics": {{
        "lifestyle": "Description of buyer lifestyle",
        "values": ["Value 1", "Value 2"],
        "interests": ["Interest 1", "Interest 2"]
    }},
    "inferred_archetypes": {{
        "Achiever": 0.0-1.0,
        "Explorer": 0.0-1.0,
        "Guardian": 0.0-1.0,
        "Connector": 0.0-1.0,
        "Pragmatist": 0.0-1.0
    }},
    "functional_benefits": ["Benefit 1", "Benefit 2"],
    "emotional_benefits": ["Emotional benefit 1"],
    "social_benefits": ["Social benefit 1"],
    "purchase_motivations": ["What drives someone to buy this"],
    "purchase_barriers": ["What might prevent purchase"],
    "competitive_category": "How buyers think about the competitive set",
    "key_competitors": ["Brand/Product 1", "Brand/Product 2"],
    "differentiation_factors": ["What makes this product different"],
    "value_proposition": "One sentence capturing the core value",
    "key_claims": ["Main marketing claims"],
    "messaging_themes": ["Themes that would resonate"],
    "tone_recommendations": ["Recommended tone attributes"],
    "analysis_confidence": 0.0-1.0
}}

IMPORTANT RULES:
1. For geographic_relevance: Think about WHERE this product makes sense. Snow boots don't make sense in Phoenix. Beach products don't make sense in Denver.
2. For inferred_archetypes: Provide probabilities that sum to approximately 1.0
3. For exclude_regions: Be specific about regions where advertising would be wasteful
4. Be specific and actionable in all fields
5. Return ONLY valid JSON, no other text

CRITICAL ARCHETYPE GUIDANCE:
- Achiever: Buys premium/luxury/designer products for status, quality, success signaling. High price = Achiever.
- Explorer: Buys innovative, adventurous, outdoor, unique products. Seeks new experiences.
- Guardian: Buys reliable, safe, protective products. Values security and trust.
- Connector: Buys social, fashionable, trendy products that help them connect with others.
- Pragmatist: ONLY for budget/value products. Someone buying $180+ designer boots is NOT a Pragmatist.

PRICE-ARCHETYPE CORRELATION:
- $150+ products: Achiever should be dominant (0.35-0.55) - these buyers value quality over price
- "Designer", "Premium", "Luxury", "Ultimate" keywords: STRONGLY boost Achiever, SUPPRESS Pragmatist
- Budget/value keywords: Pragmatist dominant
- Pragmatist archetype should be VERY LOW (< 0.10) for any premium-priced or designer product

JSON Response:'''

    def __init__(self, api_key: Optional[str] = None, model: str = "claude-sonnet-4-20250514"):
        """
        Initialize the product analyzer.
        
        Args:
            api_key: Anthropic API key (or uses ANTHROPIC_API_KEY env var)
            model: Claude model to use
        """
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.model = model
        self._client = None
    
    def _get_client(self):
        """Get or create Anthropic client."""
        if not ANTHROPIC_AVAILABLE:
            raise ImportError("Anthropic library not installed")
        
        if not self.api_key:
            raise ValueError("Anthropic API key required. Set ANTHROPIC_API_KEY environment variable.")
        
        if self._client is None:
            self._client = anthropic.Anthropic(api_key=self.api_key)
        
        return self._client
    
    async def analyze_product(
        self,
        brand: str,
        product: str,
        description: str,
        product_url: Optional[str] = None,
    ) -> ProductIntelligence:
        """
        Analyze a product using Claude.
        
        Args:
            brand: Brand name
            product: Product name
            description: Product description
            product_url: Optional product URL for context
            
        Returns:
            ProductIntelligence with comprehensive analysis
        """
        logger.info(f"Analyzing product: {brand} {product}")
        
        # Build URL context if provided
        url_context = f"- Product URL: {product_url}" if product_url else ""
        
        # Format prompt
        prompt = self.ANALYSIS_PROMPT.format(
            brand=brand,
            product=product,
            description=description,
            url_context=url_context,
        )
        
        try:
            # Call Claude API
            client = self._get_client()
            response = client.messages.create(
                model=self.model,
                max_tokens=2000,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            # Extract text response
            raw_response = response.content[0].text
            
            # Parse JSON response
            try:
                analysis = json.loads(raw_response)
            except json.JSONDecodeError:
                # Try to extract JSON from response
                import re
                json_match = re.search(r'\{[\s\S]*\}', raw_response)
                if json_match:
                    analysis = json.loads(json_match.group())
                else:
                    logger.error(f"Failed to parse JSON from Claude response: {raw_response[:500]}")
                    return self._create_fallback_intelligence(brand, product, description)
            
            # Build ProductIntelligence from parsed response
            intelligence = self._build_intelligence(
                brand=brand,
                product=product,
                analysis=analysis,
                raw_response=raw_response,
            )
            
            # VALIDATION: Check for obviously wrong archetype assignments
            intelligence = self._validate_and_correct_archetypes(
                intelligence=intelligence,
                description=description,
            )
            
            logger.info(
                f"Product analysis complete: {intelligence.primary_category}/{intelligence.subcategory}, "
                f"confidence: {intelligence.analysis_confidence:.0%}"
            )
            
            return intelligence
            
        except Exception as e:
            logger.error(f"Error analyzing product with Claude: {e}")
            return self._create_fallback_intelligence(brand, product, description)
    
    def _build_intelligence(
        self,
        brand: str,
        product: str,
        analysis: Dict[str, Any],
        raw_response: str,
    ) -> ProductIntelligence:
        """Build ProductIntelligence from Claude's analysis."""
        
        # Parse price tier
        price_tier_str = analysis.get("price_tier", "mid_market")
        try:
            price_tier = PriceTier(price_tier_str)
        except ValueError:
            price_tier = PriceTier.MID_MARKET
        
        # Parse purchase type
        purchase_type_str = analysis.get("purchase_type", "considered")
        try:
            purchase_type = PurchaseType(purchase_type_str)
        except ValueError:
            purchase_type = PurchaseType.CONSIDERED
        
        # Parse geographic relevance
        geo_str = analysis.get("geographic_relevance", "universal")
        try:
            geographic_relevance = GeographicRelevance(geo_str)
        except ValueError:
            geographic_relevance = GeographicRelevance.UNIVERSAL
        
        return ProductIntelligence(
            product_name=product,
            brand=brand,
            primary_category=analysis.get("primary_category", ""),
            subcategory=analysis.get("subcategory", ""),
            price_tier=price_tier,
            estimated_price_range=analysis.get("estimated_price_range", ""),
            purchase_type=purchase_type,
            purchase_consideration_factors=analysis.get("purchase_consideration_factors", []),
            geographic_relevance=geographic_relevance,
            relevant_regions=analysis.get("relevant_regions", []),
            seasonal_relevance=analysis.get("seasonal_relevance"),
            exclude_regions=analysis.get("exclude_regions", []),
            primary_buyer_demographics=analysis.get("primary_buyer_demographics", {}),
            buyer_psychographics=analysis.get("buyer_psychographics", {}),
            inferred_archetypes=analysis.get("inferred_archetypes", {}),
            functional_benefits=analysis.get("functional_benefits", []),
            emotional_benefits=analysis.get("emotional_benefits", []),
            social_benefits=analysis.get("social_benefits", []),
            purchase_motivations=analysis.get("purchase_motivations", []),
            purchase_barriers=analysis.get("purchase_barriers", []),
            competitive_category=analysis.get("competitive_category", ""),
            key_competitors=analysis.get("key_competitors", []),
            differentiation_factors=analysis.get("differentiation_factors", []),
            value_proposition=analysis.get("value_proposition", ""),
            key_claims=analysis.get("key_claims", []),
            messaging_themes=analysis.get("messaging_themes", []),
            tone_recommendations=analysis.get("tone_recommendations", []),
            analysis_confidence=analysis.get("analysis_confidence", 0.7),
            claude_model_used=self.model,
            raw_claude_response=raw_response,
        )
    
    def _validate_and_correct_archetypes(
        self,
        intelligence: ProductIntelligence,
        description: str,
    ) -> ProductIntelligence:
        """
        Validate Claude's archetype assignments and correct obvious errors.
        
        This catches cases where Claude returns "Pragmatist" for luxury/designer products.
        """
        archetypes = intelligence.inferred_archetypes.copy()
        desc_lower = description.lower()
        
        # Premium/designer indicators
        premium_signals = [
            "designer", "luxury", "premium", "ultimate", "exclusive", 
            "high-end", "upscale", "finest", "superior", "elite",
            "couture", "artisan", "handcrafted", "signature"
        ]
        
        has_premium_signals = any(signal in desc_lower for signal in premium_signals)
        is_premium_price = intelligence.price_tier in [PriceTier.PREMIUM, PriceTier.LUXURY]
        
        # Check if Pragmatist is dominant when it shouldn't be
        pragmatist_score = archetypes.get("Pragmatist", 0)
        top_archetype = max(archetypes, key=archetypes.get) if archetypes else "Unknown"
        
        if (has_premium_signals or is_premium_price) and top_archetype == "Pragmatist":
            logger.warning(
                f"VALIDATION CORRECTION: Claude returned Pragmatist as top archetype for "
                f"premium/designer product. Correcting..."
            )
            
            # Suppress Pragmatist and boost Achiever
            archetypes["Pragmatist"] = 0.05
            archetypes["Achiever"] = max(archetypes.get("Achiever", 0.3), 0.45)
            
            # Normalize
            total = sum(archetypes.values())
            archetypes = {k: v/total for k, v in archetypes.items()}
            
            intelligence.inferred_archetypes = archetypes
            
            new_top = max(archetypes, key=archetypes.get)
            logger.info(f"Corrected top archetype: {new_top} ({archetypes[new_top]:.2%})")
        
        # Also correct if Pragmatist is very high (>30%) for premium products
        elif (has_premium_signals or is_premium_price) and pragmatist_score > 0.30:
            logger.warning(
                f"VALIDATION CORRECTION: Pragmatist score too high ({pragmatist_score:.2%}) "
                f"for premium product. Reducing..."
            )
            
            # Reduce Pragmatist, boost others proportionally
            reduction = pragmatist_score - 0.08
            archetypes["Pragmatist"] = 0.08
            archetypes["Achiever"] = archetypes.get("Achiever", 0.2) + (reduction * 0.5)
            archetypes["Explorer"] = archetypes.get("Explorer", 0.2) + (reduction * 0.3)
            archetypes["Connector"] = archetypes.get("Connector", 0.2) + (reduction * 0.2)
            
            # Normalize
            total = sum(archetypes.values())
            archetypes = {k: v/total for k, v in archetypes.items()}
            
            intelligence.inferred_archetypes = archetypes
        
        return intelligence
    
    def _create_fallback_intelligence(
        self,
        brand: str,
        product: str,
        description: str,
    ) -> ProductIntelligence:
        """Create basic intelligence when Claude is unavailable."""
        logger.warning("Using fallback product intelligence (Claude unavailable)")
        
        # Combined text for analysis
        full_text = f"{brand} {product} {description}".lower()
        desc_lower = description.lower()
        brand_lower = brand.lower()
        product_lower = product.lower()
        
        # =====================================================================
        # BRAND RECOGNITION: Premium/Luxury brands get automatic elevation
        # =====================================================================
        PREMIUM_BRANDS = {
            # Tech
            "apple", "dyson", "bang & olufsen", "bose", "sonos", "tesla", 
            "porsche", "ferrari", "lamborghini", "maserati", "bentley",
            # Fashion & Luxury Fashion
            "gucci", "prada", "louis vuitton", "hermes", "chanel", "dior",
            "burberry", "versace", "armani", "balenciaga", "fendi",
            "stuart weitzman", "manolo blahnik", "jimmy choo", "louboutin",
            "valentino", "givenchy", "celine", "bottega veneta", "loewe",
            "saint laurent", "tom ford", "alexander mcqueen",
            # Watch
            "rolex", "omega", "patek philippe", "audemars piguet", "cartier",
            "tag heuer", "breitling", "iwc",
            # Other
            "tiffany", "montblanc", "leica", "hasselblad"
        }
        
        ASPIRATIONAL_BRANDS = {
            # Tech
            "samsung", "sony", "lg", "microsoft", "google", 
            # Athletic/Sportswear
            "nike", "adidas", "under armour", "lululemon", "peloton",
            # Footwear (Premium/Designer)
            "sorel", "ugg", "timberland", "hunter", "blundstone", "cole haan",
            "allbirds", "doc martens", "dr. martens", "clarks", "ecco",
            "birkenstock", "tods", "sperry", "merrell", "keen",
            # Fashion (Aspirational)
            "coach", "kate spade", "michael kors", "tory burch", "ralph lauren",
            "calvin klein", "tommy hilfiger", "hugo boss", "ted baker",
            "canada goose", "moncler", "patagonia", "arc'teryx", "north face",
            # Home
            "vitamix", "kitchenaid", "le creuset", "staub", "all-clad",
            # Beauty
            "la mer", "sk-ii", "estee lauder", "lancome", "clinique",
        }
        
        is_premium_brand = brand_lower in PREMIUM_BRANDS
        is_aspirational_brand = brand_lower in ASPIRATIONAL_BRANDS
        
        # =====================================================================
        # PRICE SIGNALS: Detect price tier from multiple sources
        # =====================================================================
        price_tier = PriceTier.MID_MARKET
        
        # Check for price in description (e.g., "$200", "$1500")
        import re
        price_match = re.search(r'\$\s*(\d+(?:,\d{3})*(?:\.\d{2})?)', full_text)
        if price_match:
            price_val = float(price_match.group(1).replace(',', ''))
            if price_val >= 500:
                price_tier = PriceTier.LUXURY
            elif price_val >= 150:
                price_tier = PriceTier.PREMIUM
            elif price_val >= 50:
                price_tier = PriceTier.MID_MARKET
            else:
                price_tier = PriceTier.BUDGET
        
        # Brand-based price tier override
        if is_premium_brand:
            price_tier = PriceTier.LUXURY
        elif is_aspirational_brand and price_tier == PriceTier.MID_MARKET:
            price_tier = PriceTier.PREMIUM
        
        # Keyword-based price tier detection
        if any(w in full_text for w in ["luxury", "premium", "elite", "exclusive", "finest", "artisan"]):
            price_tier = max(price_tier, PriceTier.PREMIUM, key=lambda x: ["budget", "mid_market", "premium", "luxury"].index(x.value))
        elif any(w in desc_lower for w in ["budget", "affordable", "value", "cheap", "economy"]):
            price_tier = PriceTier.BUDGET
        
        # Product-specific luxury signals
        luxury_product_signals = [
            "milanese", "stainless steel", "titanium", "sapphire", "ceramic", 
            "gold", "platinum", "diamond", "leather", "cashmere", "silk",
            "handcrafted", "hand-made", "artisan"
        ]
        if any(signal in full_text for signal in luxury_product_signals):
            if price_tier == PriceTier.MID_MARKET:
                price_tier = PriceTier.PREMIUM
        
        # =====================================================================
        # ARCHETYPE INFERENCE: Much smarter inference
        # =====================================================================
        archetypes = {
            "Achiever": 0.2,
            "Explorer": 0.2,
            "Guardian": 0.2,
            "Connector": 0.2,
            "Pragmatist": 0.2
        }
        
        # Premium/Luxury → Achiever boost
        if price_tier in [PriceTier.PREMIUM, PriceTier.LUXURY] or is_premium_brand:
            archetypes["Achiever"] = 0.55
            archetypes["Pragmatist"] = 0.05  # Pragmatists don't buy luxury
        
        # Keyword-based archetype boosting
        achiever_signals = ["professional", "success", "premium", "elite", "exclusive", 
                          "sophisticated", "refined", "executive", "prestige", "status",
                          "designer", "ultimate", "luxury", "finest", "superior", 
                          "high-end", "high end", "upscale", "deluxe", "signature",
                          "crafted", "artisan", "bespoke", "couture", "iconic"]
        explorer_signals = ["new", "innovative", "discover", "adventure", "unique", 
                          "first", "revolutionary", "cutting-edge", "breakthrough",
                          "outdoor", "wilderness", "trail", "expedition", "explore",
                          "arctic", "alpine", "waterproof", "all-terrain"]
        guardian_signals = ["safe", "secure", "protect", "reliable", "trusted", 
                          "proven", "family", "peace of mind", "warranty",
                          "durable", "long-lasting", "dependable", "sturdy"]
        connector_signals = ["share", "together", "community", "friends", "social", 
                           "connect", "belong", "group", "team",
                           "stylish", "fashion", "trendy", "chic", "vogue"]
        # NOTE: Pragmatist signals are WEAK signals - only trigger if NO premium indicators
        pragmatist_signals = ["value", "save", "deal", "affordable", "practical", 
                            "efficient", "smart buy", "best price", "economical",
                            "budget", "cheap", "basic", "no frills"]
        
        # Track if premium/luxury signals are present
        has_premium_signals = False
        
        for signal in achiever_signals:
            if signal in full_text:
                archetypes["Achiever"] += 0.15
                has_premium_signals = True
        for signal in explorer_signals:
            if signal in full_text:
                archetypes["Explorer"] += 0.12
        for signal in guardian_signals:
            if signal in full_text:
                archetypes["Guardian"] += 0.12
        for signal in connector_signals:
            if signal in full_text:
                archetypes["Connector"] += 0.12
        
        # IMPORTANT: Only boost Pragmatist if NO premium/luxury indicators
        # Pragmatist is fundamentally incompatible with designer/luxury products
        if not has_premium_signals and price_tier in [PriceTier.BUDGET, PriceTier.MID_MARKET]:
            for signal in pragmatist_signals:
                if signal in full_text:
                    archetypes["Pragmatist"] += 0.12
        
        # If product is clearly premium/designer, suppress Pragmatist
        if has_premium_signals or price_tier in [PriceTier.PREMIUM, PriceTier.LUXURY]:
            archetypes["Pragmatist"] = min(archetypes["Pragmatist"], 0.05)
        
        # Normalize archetypes
        total = sum(archetypes.values())
        archetypes = {k: v/total for k, v in archetypes.items()}
        
        # Determine category
        category = "General"
        subcategory = ""
        
        # Footwear (check first - specific)
        if any(w in full_text for w in ["boot", "boots", "shoe", "shoes", "sneaker", "sneakers", 
                                        "loafer", "sandal", "heel", "flat", "slipper", "footwear"]):
            category = "Footwear"
            if any(w in full_text for w in ["boot", "boots"]):
                if any(w in full_text for w in ["winter", "snow", "arctic", "cold", "warm"]):
                    subcategory = "Winter Boots"
                elif any(w in full_text for w in ["rain", "waterproof"]):
                    subcategory = "Rain Boots"
                elif any(w in full_text for w in ["hiking", "trail", "outdoor"]):
                    subcategory = "Outdoor Boots"
                else:
                    subcategory = "Fashion Boots"
            # Footwear → Connector/Explorer archetype boost
            archetypes["Connector"] += 0.15  # Fashion-forward
            if "outdoor" in full_text or "winter" in full_text or "arctic" in full_text:
                archetypes["Explorer"] += 0.15
        # Fashion/Apparel
        elif any(w in full_text for w in ["jacket", "coat", "dress", "shirt", "pants", "jeans",
                                          "sweater", "hoodie", "outerwear", "apparel", "clothing"]):
            category = "Fashion & Apparel"
            archetypes["Connector"] += 0.12
        # Accessories
        elif any(w in full_text for w in ["watch", "band", "strap", "bracelet", "bag", "handbag",
                                          "purse", "wallet", "belt", "scarf", "hat", "sunglasses"]):
            category = "Fashion Accessories"
        elif any(w in full_text for w in ["earbuds", "headphones", "speaker", "audio"]):
            category = "Audio Electronics"
        elif any(w in full_text for w in ["phone", "tablet", "laptop", "computer"]):
            category = "Consumer Electronics"
        
        # If we detected subcategory, use it
        if not subcategory:
            subcategory = category
        
        confidence = 0.4 if is_premium_brand else 0.3
        
        logger.info(f"Fallback analysis: brand={brand}, price_tier={price_tier.value}, "
                   f"top_archetype={max(archetypes, key=archetypes.get)}")
        
        return ProductIntelligence(
            product_name=product,
            brand=brand,
            primary_category=category,
            price_tier=price_tier,
            purchase_type=PurchaseType.CONSIDERED,
            geographic_relevance=GeographicRelevance.UNIVERSAL,
            inferred_archetypes=archetypes,
            analysis_confidence=confidence,
        )


# =============================================================================
# SINGLETON
# =============================================================================

_analyzer: Optional[ProductAnalyzer] = None


def get_product_analyzer() -> ProductAnalyzer:
    """Get singleton ProductAnalyzer."""
    global _analyzer
    if _analyzer is None:
        _analyzer = ProductAnalyzer()
    return _analyzer
