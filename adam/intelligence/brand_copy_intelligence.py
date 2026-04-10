# =============================================================================
# ADAM Brand Copy Intelligence
# Location: adam/intelligence/brand_copy_intelligence.py
# =============================================================================

"""
BRAND COPY INTELLIGENCE

Extracts persuasion intelligence from brand/product descriptions.

The brand's product copy (title, features, description) IS an advertisement.
When a customer buys after reading this copy + reviews, the "ad" worked.

This module extracts:
1. **Cialdini Principles** - Which persuasion tactics the brand is using
2. **Aaker Personality Dimensions** - Brand personality (sincerity, excitement, etc.)
3. **Persuasion Tactics** - Specific language tactics detected
4. **Alignment Analysis** - How well brand copy aligns with customer reviews

CIALDINI'S 7 PRINCIPLES:
- Reciprocity: "Free gift", "Bonus included"
- Commitment/Consistency: "Join the millions who..."
- Social Proof: "Best seller", "#1 rated"
- Authority: "Clinically proven", "Expert recommended"
- Liking: Emotional language, relatability
- Scarcity: "Limited time", "Only X left"
- Unity: "Join our community", "Part of the family"

AAKER'S BRAND PERSONALITY:
- Sincerity: Honest, wholesome, down-to-earth
- Excitement: Daring, spirited, imaginative
- Competence: Reliable, intelligent, successful
- Sophistication: Upper class, charming
- Ruggedness: Outdoorsy, tough

This intelligence flows into:
1. Decision-making (match brand tactics to customer susceptibility)
2. Message crafting (amplify or counter brand messaging)
3. Learning (track which brand tactics convert which archetypes)
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# CIALDINI DETECTION PATTERNS
# =============================================================================

CIALDINI_PATTERNS = {
    "reciprocity": {
        "keywords": [
            "free", "bonus", "gift", "included", "complimentary", "extra",
            "at no additional cost", "value pack", "bundle", "savings",
        ],
        "patterns": [
            r"free\s+\w+",
            r"bonus\s+\w+",
            r"includes?\s+free",
            r"get\s+\w+\s+free",
            r"complimentary\s+\w+",
        ],
        "weight": 1.0,
    },
    
    "commitment": {
        "keywords": [
            "join", "millions", "thousands", "community", "members",
            "subscribers", "customers trust", "people love", "part of",
        ],
        "patterns": [
            r"join\s+(?:the\s+)?(?:\d+|millions?|thousands?)",
            r"(?:\d+|millions?|thousands?)\s+(?:happy\s+)?customers?",
            r"loved\s+by\s+\d+",
            r"trusted\s+by\s+\d+",
        ],
        "weight": 0.9,
    },
    
    "social_proof": {
        "keywords": [
            "best seller", "bestseller", "#1", "number one", "top rated",
            "award winning", "highly rated", "recommended", "favorite",
            "most popular", "customer favorite", "5 star", "five star",
        ],
        "patterns": [
            r"#?\d+\s*(?:best)?seller",
            r"(?:best|top|most)\s+(?:selling|rated|reviewed)",
            r"award[- ]?winning",
            r"(?:\d+|thousands?)\s+(?:\d+[- ]star\s+)?reviews?",
            r"(?:customer|editor|expert)s?\s+choice",
        ],
        "weight": 1.0,
    },
    
    "authority": {
        "keywords": [
            "clinically proven", "dermatologist", "doctor", "expert",
            "professional", "tested", "certified", "approved", "endorsed",
            "recommended by", "used by professionals", "hospital grade",
        ],
        "patterns": [
            r"(?:clinically|scientifically|lab)\s+(?:proven|tested|verified)",
            r"(?:dermatologist|doctor|expert)s?\s+(?:recommended|approved|tested)",
            r"fda\s+(?:approved|cleared)",
            r"certified\s+\w+",
            r"(?:hospital|medical|professional)\s+grade",
        ],
        "weight": 1.1,
    },
    
    "liking": {
        "keywords": [
            "love", "amazing", "beautiful", "gorgeous", "perfect",
            "wonderful", "fantastic", "incredible", "you'll love",
            "feel great", "look great", "your best",
        ],
        "patterns": [
            r"you(?:'ll)?\s+(?:will\s+)?love",
            r"feel\s+(?:your\s+)?(?:best|amazing|great|confident)",
            r"look\s+(?:your\s+)?(?:best|amazing|great|beautiful)",
            r"(?:treat|pamper)\s+yourself",
        ],
        "weight": 0.8,
    },
    
    "scarcity": {
        "keywords": [
            "limited", "exclusive", "only", "last chance", "while supplies",
            "hurry", "don't miss", "running out", "rare", "special edition",
        ],
        "patterns": [
            r"limited\s+(?:time|edition|supply|offer|stock)",
            r"only\s+\d+\s+left",
            r"while\s+(?:supplies|stocks?)\s+last",
            r"(?:hurry|act)\s+(?:now|fast|today)",
            r"(?:exclusive|special)\s+(?:offer|edition)",
        ],
        "weight": 1.0,
    },
    
    "unity": {
        "keywords": [
            "family", "community", "together", "join us", "one of us",
            "our customers", "our community", "belong", "membership",
        ],
        "patterns": [
            r"(?:join|become\s+part\s+of)\s+(?:our|the)\s+(?:family|community)",
            r"for\s+(?:the\s+whole\s+)?family",
            r"(?:our|the)\s+(?:\w+\s+)?(?:community|family|tribe)",
            r"(?:share|bond)\s+with\s+(?:loved\s+ones|family)",
        ],
        "weight": 0.9,
    },
}


# =============================================================================
# AAKER BRAND PERSONALITY PATTERNS
# =============================================================================

AAKER_PATTERNS = {
    "sincerity": {
        "keywords": [
            "honest", "genuine", "real", "authentic", "natural", "wholesome",
            "family", "friendly", "down-to-earth", "simple", "pure", "clean",
        ],
        "patterns": [
            r"(?:100%|all)\s+natural",
            r"(?:honest|genuine|real)\s+\w+",
            r"(?:family|small\s+business)\s+(?:owned|run)",
            r"no\s+(?:artificial|chemicals?|additives?)",
        ],
    },
    
    "excitement": {
        "keywords": [
            "exciting", "daring", "spirited", "imaginative", "bold", "trendy",
            "unique", "innovative", "cutting-edge", "new", "revolutionary",
        ],
        "patterns": [
            r"(?:revolutionary|breakthrough|innovative)\s+\w+",
            r"(?:first|only)\s+(?:of\s+its\s+kind|one)",
            r"(?:new|latest)\s+(?:technology|innovation|design)",
            r"(?:bold|daring|unique)\s+\w+",
        ],
    },
    
    "competence": {
        "keywords": [
            "reliable", "intelligent", "successful", "leader", "trusted",
            "dependable", "efficient", "effective", "performance", "quality",
            "proven", "recommended", "clinically", "dermatologist", "tested",
            "hydration", "moisturizer", "cream", "#1", "brand",
        ],
        "patterns": [
            r"(?:industry|market)\s+(?:leader|leading)",
            r"(?:trusted|relied\s+upon)\s+(?:by|for)",
            r"(?:high|superior|premium)\s+(?:quality|performance)",
            r"(?:proven|tested)\s+(?:results|performance)",
            r"(?:clinically|dermatologist)\s+(?:proven|tested|recommended)",
            r"#?\d+\s*(?:recommended|brand)",
        ],
    },
    
    "sophistication": {
        "keywords": [
            "luxury", "elegant", "glamorous", "charming", "smooth",
            "premium", "exclusive", "refined", "sophisticated", "chic",
        ],
        "patterns": [
            r"(?:luxury|luxurious|premium)\s+\w+",
            r"(?:elegant|sophisticated|refined)\s+\w+",
            r"(?:designer|boutique|artisan)\s+\w+",
            r"(?:handcrafted|hand-?made)\s+\w+",
        ],
    },
    
    "ruggedness": {
        "keywords": [
            "tough", "rugged", "strong", "durable", "outdoor", "adventure",
            "heavy-duty", "built to last", "sturdy", "robust", "powerful",
        ],
        "patterns": [
            r"(?:built|made)\s+(?:to|for)\s+(?:last|endure)",
            r"(?:heavy|industrial)[- ]?duty",
            r"(?:tough|rugged|durable)\s+\w+",
            r"(?:outdoor|all-weather|all-terrain)\s+\w+",
        ],
    },
}


# =============================================================================
# DATA MODELS
# =============================================================================

@dataclass
class CialdiniAnalysis:
    """Results of Cialdini principle detection."""
    scores: Dict[str, float] = field(default_factory=dict)
    primary_principle: str = ""
    secondary_principles: List[str] = field(default_factory=list)
    detected_patterns: Dict[str, List[str]] = field(default_factory=dict)
    total_score: float = 0.0
    
    def get_top_principles(self, n: int = 3) -> List[Tuple[str, float]]:
        """Get top N principles by score."""
        sorted_scores = sorted(
            self.scores.items(),
            key=lambda x: x[1],
            reverse=True,
        )
        return sorted_scores[:n]


@dataclass
class AakerAnalysis:
    """Results of Aaker brand personality detection."""
    scores: Dict[str, float] = field(default_factory=dict)
    primary_personality: str = ""
    personality_blend: List[str] = field(default_factory=list)
    detected_patterns: Dict[str, List[str]] = field(default_factory=dict)
    
    def get_personality_profile(self) -> Dict[str, float]:
        """Get normalized personality profile (sums to 1.0)."""
        total = sum(self.scores.values()) or 1.0
        return {k: v / total for k, v in self.scores.items()}


@dataclass
class BrandCopyIntelligence:
    """Complete brand copy analysis."""
    
    # Source data
    brand: str
    title: str = ""
    features: List[str] = field(default_factory=list)
    description: str = ""
    
    # Analysis results
    cialdini: CialdiniAnalysis = field(default_factory=CialdiniAnalysis)
    aaker: AakerAnalysis = field(default_factory=AakerAnalysis)
    
    # Detected tactics
    tactics_detected: List[str] = field(default_factory=list)
    
    # Alignment with customer archetypes
    archetype_alignment: Dict[str, float] = field(default_factory=dict)
    
    @property
    def full_copy(self) -> str:
        """Get all copy concatenated."""
        parts = [self.title]
        parts.extend(self.features)
        parts.append(self.description)
        return " ".join(filter(None, parts))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage/serialization."""
        return {
            "brand": self.brand,
            "cialdini_scores": self.cialdini.scores,
            "primary_cialdini": self.cialdini.primary_principle,
            "aaker_scores": self.aaker.scores,
            "primary_personality": self.aaker.primary_personality,
            "tactics": self.tactics_detected,
            "archetype_alignment": self.archetype_alignment,
        }


# =============================================================================
# BRAND COPY ANALYZER
# =============================================================================

class BrandCopyAnalyzer:
    """
    Analyzes brand copy for persuasion intelligence.
    
    Usage:
        analyzer = BrandCopyAnalyzer()
        intel = analyzer.analyze(
            brand="CeraVe",
            title="CeraVe Moisturizing Cream",
            features=["Developed with dermatologists", "48HR hydration"],
            description="Gentle, fragrance-free moisturizer...",
        )
        
        print(intel.cialdini.primary_principle)  # "authority"
        print(intel.aaker.primary_personality)   # "competence"
    """
    
    def __init__(self):
        """Initialize analyzer with compiled patterns."""
        self._cialdini_compiled = self._compile_patterns(CIALDINI_PATTERNS)
        self._aaker_compiled = self._compile_patterns(AAKER_PATTERNS)
    
    def _compile_patterns(
        self,
        pattern_dict: Dict[str, Dict],
    ) -> Dict[str, List[re.Pattern]]:
        """Pre-compile regex patterns for efficiency."""
        compiled = {}
        for category, config in pattern_dict.items():
            patterns = config.get("patterns", [])
            compiled[category] = [
                re.compile(p, re.IGNORECASE)
                for p in patterns
            ]
        return compiled
    
    def analyze(
        self,
        brand: str,
        title: str = "",
        features: Optional[List[str]] = None,
        description: str = "",
    ) -> BrandCopyIntelligence:
        """
        Analyze brand copy for persuasion intelligence.
        
        Args:
            brand: Brand name
            title: Product title
            features: List of feature bullet points
            description: Full product description
            
        Returns:
            BrandCopyIntelligence with all analysis results
        """
        features = features or []
        
        intel = BrandCopyIntelligence(
            brand=brand,
            title=title,
            features=features,
            description=description,
        )
        
        # Get full copy for analysis
        full_copy = intel.full_copy.lower()
        
        if not full_copy.strip():
            return intel
        
        # Analyze Cialdini principles
        intel.cialdini = self._analyze_cialdini(full_copy)
        
        # Analyze Aaker personality
        intel.aaker = self._analyze_aaker(full_copy)
        
        # Extract tactics
        intel.tactics_detected = self._extract_tactics(full_copy)
        
        # Calculate archetype alignment
        intel.archetype_alignment = self._calculate_archetype_alignment(intel)
        
        return intel
    
    def _analyze_cialdini(self, text: str) -> CialdiniAnalysis:
        """Detect Cialdini principles in text."""
        analysis = CialdiniAnalysis()
        
        for principle, config in CIALDINI_PATTERNS.items():
            score = 0.0
            detected = []
            weight = config.get("weight", 1.0)
            
            # Check keywords
            for keyword in config["keywords"]:
                if keyword.lower() in text:
                    score += 0.5 * weight
                    detected.append(f"keyword:{keyword}")
            
            # Check patterns
            for pattern in self._cialdini_compiled.get(principle, []):
                matches = pattern.findall(text)
                if matches:
                    score += len(matches) * weight
                    detected.extend([f"pattern:{m}" for m in matches[:3]])
            
            if score > 0:
                analysis.scores[principle] = min(score, 5.0)  # Cap at 5.0
                analysis.detected_patterns[principle] = detected
        
        # Determine primary and secondary principles
        if analysis.scores:
            sorted_principles = sorted(
                analysis.scores.items(),
                key=lambda x: x[1],
                reverse=True,
            )
            analysis.primary_principle = sorted_principles[0][0]
            analysis.secondary_principles = [p[0] for p in sorted_principles[1:3]]
            analysis.total_score = sum(analysis.scores.values())
        
        return analysis
    
    def _analyze_aaker(self, text: str) -> AakerAnalysis:
        """Detect Aaker brand personality dimensions."""
        analysis = AakerAnalysis()
        
        for dimension, config in AAKER_PATTERNS.items():
            score = 0.0
            detected = []
            
            # Check keywords
            for keyword in config["keywords"]:
                if keyword.lower() in text:
                    score += 0.5
                    detected.append(f"keyword:{keyword}")
            
            # Check patterns
            for pattern in self._aaker_compiled.get(dimension, []):
                matches = pattern.findall(text)
                if matches:
                    score += len(matches)
                    detected.extend([f"pattern:{m}" for m in matches[:3]])
            
            if score > 0:
                analysis.scores[dimension] = min(score, 5.0)
                analysis.detected_patterns[dimension] = detected
        
        # Determine primary personality
        if analysis.scores:
            sorted_dims = sorted(
                analysis.scores.items(),
                key=lambda x: x[1],
                reverse=True,
            )
            analysis.primary_personality = sorted_dims[0][0]
            analysis.personality_blend = [d[0] for d in sorted_dims[:3]]
        
        return analysis
    
    def _extract_tactics(self, text: str) -> List[str]:
        """Extract specific persuasion tactics detected."""
        tactics = []
        
        # Urgency tactics
        if any(word in text for word in ["now", "today", "hurry", "limited time"]):
            tactics.append("urgency")
        
        # Comparison tactics
        if any(word in text for word in ["vs", "versus", "compared to", "better than"]):
            tactics.append("comparison")
        
        # Guarantee tactics
        if any(word in text for word in ["guarantee", "warranty", "money back", "risk free"]):
            tactics.append("risk_reversal")
        
        # Value stacking
        if any(word in text for word in ["plus", "also includes", "bonus", "additional"]):
            tactics.append("value_stacking")
        
        # Problem-solution
        if any(word in text for word in ["problem", "solution", "fix", "solve", "relief"]):
            tactics.append("problem_solution")
        
        # Transformation promise
        if any(word in text for word in ["transform", "change", "become", "achieve"]):
            tactics.append("transformation")
        
        return tactics
    
    def _calculate_archetype_alignment(
        self,
        intel: BrandCopyIntelligence,
    ) -> Dict[str, float]:
        """
        Calculate how well brand copy aligns with different customer archetypes.
        
        This helps match brand messaging to susceptible customer types.
        """
        alignment = {}
        
        # Archetype → Cialdini susceptibility mapping
        archetype_cialdini = {
            "explorer": ["scarcity", "unity"],
            "sage": ["authority", "commitment"],
            "hero": ["social_proof", "authority"],
            "everyman": ["social_proof", "liking"],
            "rebel": ["scarcity", "unity"],
            "lover": ["liking", "reciprocity"],
            "jester": ["liking", "social_proof"],
            "caregiver": ["reciprocity", "unity"],
            "creator": ["authority", "scarcity"],
            "ruler": ["authority", "social_proof"],
            "magician": ["scarcity", "authority"],
            "innocent": ["liking", "sincerity"],
        }
        
        for archetype, susceptible_to in archetype_cialdini.items():
            score = 0.0
            for principle in susceptible_to:
                score += intel.cialdini.scores.get(principle, 0.0)
            
            # Normalize
            alignment[archetype] = min(score / 4.0, 1.0)
        
        return alignment


# =============================================================================
# SINGLETON AND CONVENIENCE FUNCTIONS
# =============================================================================

_analyzer: Optional[BrandCopyAnalyzer] = None


def get_brand_copy_analyzer() -> BrandCopyAnalyzer:
    """Get singleton analyzer."""
    global _analyzer
    if _analyzer is None:
        _analyzer = BrandCopyAnalyzer()
    return _analyzer


def analyze_brand_copy(
    brand: str,
    title: str = "",
    features: Optional[List[str]] = None,
    description: str = "",
) -> BrandCopyIntelligence:
    """
    Convenience function to analyze brand copy.
    
    Usage:
        intel = analyze_brand_copy(
            brand="Nike",
            title="Nike Air Max 90",
            features=["Iconic design", "Max Air cushioning"],
            description="The Nike Air Max 90 stays true to its OG roots...",
        )
    """
    analyzer = get_brand_copy_analyzer()
    return analyzer.analyze(brand, title, features, description)


# =============================================================================
# BATCH PROCESSING
# =============================================================================

async def analyze_metadata_batch(
    metadata_records: List[Dict[str, Any]],
) -> List[BrandCopyIntelligence]:
    """
    Analyze a batch of product metadata records.
    
    Args:
        metadata_records: List of dicts with title, features, description, store
        
    Returns:
        List of BrandCopyIntelligence objects
    """
    analyzer = get_brand_copy_analyzer()
    results = []
    
    for record in metadata_records:
        brand = record.get("store") or record.get("details", {}).get("brand", "")
        title = record.get("title", "")
        features = record.get("features", [])
        
        # Description can be string or list
        desc = record.get("description", "")
        if isinstance(desc, list):
            desc = " ".join(desc)
        
        intel = analyzer.analyze(
            brand=brand,
            title=title,
            features=features,
            description=desc,
        )
        results.append(intel)
    
    return results
