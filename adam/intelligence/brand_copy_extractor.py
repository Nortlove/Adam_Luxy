#!/usr/bin/env python3
"""
BRAND COPY INTELLIGENCE EXTRACTOR
==================================

Extracts persuasion intelligence from Amazon product metadata:
- Titles (primary selling points)
- Features (bullet-point persuasion)
- Descriptions (full brand copy)

This is the "other half" of the persuasion equation:
- Reviews tell us what WORKS on customers
- Brand copy tells us what brands are TRYING

By understanding both, we can match brand persuasion strategies
to customer susceptibilities.

Phase 3: Brand Copy Intelligence
"""

import json
import logging
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS AND TYPES
# =============================================================================

class AakerDimension(str, Enum):
    """Aaker's Brand Personality Dimensions (1997)."""
    SINCERITY = "sincerity"       # Honest, wholesome, cheerful, down-to-earth
    EXCITEMENT = "excitement"     # Daring, spirited, imaginative, up-to-date  
    COMPETENCE = "competence"     # Reliable, intelligent, successful
    SOPHISTICATION = "sophistication"  # Upper class, charming, glamorous
    RUGGEDNESS = "ruggedness"     # Tough, outdoorsy, masculine


class PersuasionTactic(str, Enum):
    """Common persuasion tactics in brand copy."""
    SOCIAL_PROOF = "social_proof"          # "Trusted by millions"
    SCARCITY = "scarcity"                  # "Limited time", "Only X left"
    AUTHORITY = "authority"                # "Expert recommended"
    RECIPROCITY = "reciprocity"            # "Free gift with purchase"
    COMMITMENT = "commitment"              # "Join our community"
    LIKING = "liking"                      # Emotional appeal, relatability
    UNITY = "unity"                        # "Made for people like you"
    FEAR_APPEAL = "fear_appeal"            # Problem-agitation
    ASPIRATION = "aspiration"              # "Be the best version"
    VALUE_PROPOSITION = "value_proposition"  # Benefits over features
    NOVELTY = "novelty"                    # "New", "Revolutionary"
    CONVENIENCE = "convenience"            # "Easy to use", "Simple"
    QUALITY = "quality"                    # "Premium", "High-quality"
    GUARANTEE = "guarantee"                # "100% satisfaction"


# =============================================================================
# DETECTION PATTERNS
# =============================================================================

# Patterns for Cialdini principles
CIALDINI_PATTERNS = {
    "social_proof": [
        r"\b(trusted|loved|recommended)\s+by\s+(millions?|thousands?|customers?)",
        r"#?\d+\s*(best\s*seller|top\s*rated)",
        r"\b(popular|favorite)\s+choice",
        r"\b\d+[\+\*]?\s*(reviews?|customers?|users?|ratings?)",
        r"as\s+seen\s+(on|in)",
    ],
    "scarcity": [
        r"limited\s*(time|edition|supply|stock|offer)",
        r"only\s*\d+\s*left",
        r"while\s+supplies?\s+last",
        r"exclusive\s*(offer|deal|access)",
        r"hurry|act\s+now|don't\s+miss",
    ],
    "authority": [
        r"(doctor|expert|dermatologist|professional)\s*(recommended|approved|tested)",
        r"clinically\s*(proven|tested)",
        r"award[s]?\s*winning",
        r"(certified|registered|licensed)",
        r"years?\s+of\s+experience",
    ],
    "reciprocity": [
        r"free\s+(gift|sample|bonus|shipping)",
        r"complimentary",
        r"included\s+at\s+no\s+(extra\s+)?cost",
    ],
    "commitment": [
        r"join\s+(our|the)\s*(family|community|club)",
        r"become\s+a\s+member",
        r"subscribe\s+(&|and)\s+save",
    ],
    "liking": [
        r"just\s+like\s+you",
        r"made\s+for\s+(people|women|men)\s+like\s+you",
        r"we\s+understand",
        r"your\s+(perfect|ideal)",
    ],
}

# Patterns for Aaker brand personality
AAKER_PATTERNS = {
    AakerDimension.SINCERITY: [
        r"honest|genuine|authentic|real|natural|organic",
        r"family[\s-]owned|small\s+business",
        r"wholesome|pure|clean",
        r"down[\s-]to[\s-]earth|simple",
        r"cruelty[\s-]free|eco[\s-]friendly|sustainable",
    ],
    AakerDimension.EXCITEMENT: [
        r"innovative|revolutionary|cutting[\s-]edge",
        r"bold|daring|adventurous",
        r"exciting|fun|playful|vibrant",
        r"new|latest|modern|trendy",
        r"unique|one[\s-]of[\s-]a[\s-]kind",
    ],
    AakerDimension.COMPETENCE: [
        r"professional|expert|precision",
        r"high[\s-]?performance|effective|powerful",
        r"trusted|reliable|dependable",
        r"proven|tested|research[\s-]backed",
        r"intelligent|smart|advanced",
    ],
    AakerDimension.SOPHISTICATION: [
        r"luxury|luxurious|premium|elegant",
        r"sophisticated|refined|exclusive",
        r"glamorous|chic|stylish",
        r"prestige|high[\s-]end|designer",
    ],
    AakerDimension.RUGGEDNESS: [
        r"rugged|tough|durable|strong",
        r"outdoor|nature|adventure",
        r"masculine|manly|for\s+men",
        r"heavy[\s-]?duty|industrial|robust",
    ],
}

# Patterns for persuasion tactics
TACTIC_PATTERNS = {
    PersuasionTactic.FEAR_APPEAL: [
        r"don't\s+(let|risk|suffer|miss)",
        r"protect\s+(yourself|your)",
        r"avoid|prevent|stop",
        r"before\s+it's\s+too\s+late",
    ],
    PersuasionTactic.ASPIRATION: [
        r"(be|become)\s+(the\s+)?best\s+version",
        r"unlock\s+your\s+potential",
        r"achieve|transform|elevate",
        r"dream|goal|success",
    ],
    PersuasionTactic.VALUE_PROPOSITION: [
        r"benefits?\s+include",
        r"(you'll|you\s+will)\s+(get|receive|enjoy)",
        r"designed\s+to",
        r"helps?\s+(you\s+)?(to\s+)?",
    ],
    PersuasionTactic.NOVELTY: [
        r"new(\s+and\s+improved)?",
        r"introducing|now\s+available",
        r"revolutionary|breakthrough|first[\s-]ever",
        r"patent(ed)?",
    ],
    PersuasionTactic.CONVENIENCE: [
        r"easy[\s-]to[\s-]use|simple|effortless",
        r"quick|fast|instant",
        r"hassle[\s-]free|no[\s-]mess",
        r"ready[\s-]to[\s-]use|plug[\s-]and[\s-]play",
    ],
    PersuasionTactic.QUALITY: [
        r"premium|high[\s-]quality|top[\s-]quality",
        r"finest|best[\s-]in[\s-]class",
        r"hand[\s-]crafted|artisan",
        r"superior|exceptional",
    ],
    PersuasionTactic.GUARANTEE: [
        r"\d+[\s-]?(day|month|year)\s*(money[\s-]back\s*)?(guarantee|warranty)",
        r"satisfaction\s+guaranteed",
        r"risk[\s-]free|no[\s-]risk",
        r"100%\s+(satisfaction|guaranteed)",
    ],
}


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class BrandCopyProfile:
    """Complete persuasion profile for a product's brand copy."""
    
    # Product info
    asin: str
    brand: str
    title: str
    category: str = ""
    
    # Persuasion analysis
    cialdini_scores: Dict[str, float] = field(default_factory=dict)
    primary_cialdini: str = ""
    
    aaker_scores: Dict[str, float] = field(default_factory=dict)
    primary_aaker: str = ""
    
    tactic_scores: Dict[str, float] = field(default_factory=dict)
    primary_tactic: str = ""
    
    # Customer fit predictions
    customer_fit: Dict[str, float] = field(default_factory=dict)
    
    # Metadata
    total_copy_length: int = 0
    features_count: int = 0
    has_description: bool = False
    
    # Timestamps
    analyzed_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    def to_compact_json(self) -> str:
        """Compact JSON for storage."""
        data = {
            "asin": self.asin,
            "brand": self.brand,
            "category": self.category,
            "cialdini": self.cialdini_scores,
            "aaker": self.aaker_scores,
            "tactics": self.tactic_scores,
            "customer_fit": self.customer_fit,
            "copy_length": self.total_copy_length,
        }
        return json.dumps(data)


# =============================================================================
# EXTRACTOR
# =============================================================================

class BrandCopyExtractor:
    """
    Extracts persuasion intelligence from Amazon product metadata.
    
    This analyzes:
    1. Product titles (primary selling points)
    2. Feature bullets (key persuasion attempts)
    3. Descriptions (full brand copy)
    
    And produces:
    - Cialdini principle scores
    - Aaker brand personality scores
    - Persuasion tactic inventory
    - Customer type fit predictions
    """
    
    def __init__(self):
        # Compile patterns for efficiency
        self._cialdini_compiled = {
            principle: [re.compile(p, re.IGNORECASE) for p in patterns]
            for principle, patterns in CIALDINI_PATTERNS.items()
        }
        
        self._aaker_compiled = {
            dimension: [re.compile(p, re.IGNORECASE) for p in patterns]
            for dimension, patterns in AAKER_PATTERNS.items()
        }
        
        self._tactic_compiled = {
            tactic: [re.compile(p, re.IGNORECASE) for p in patterns]
            for tactic, patterns in TACTIC_PATTERNS.items()
        }
    
    def analyze(self, product: Dict[str, Any]) -> BrandCopyProfile:
        """
        Analyze a product's brand copy.
        
        Args:
            product: Product metadata dict
            
        Returns:
            BrandCopyProfile with persuasion analysis
        """
        # Extract text content
        asin = product.get("parent_asin", product.get("asin", "unknown"))
        brand = product.get("store", "")
        title = product.get("title", "")
        category = product.get("main_category", "")
        
        features = product.get("features", []) or []
        description = product.get("description", []) or []
        
        # Combine all copy
        all_copy = title + " " + " ".join(features) + " " + " ".join(description)
        
        profile = BrandCopyProfile(
            asin=asin,
            brand=brand,
            title=title[:200],  # Truncate for storage
            category=category,
            total_copy_length=len(all_copy),
            features_count=len(features),
            has_description=len(description) > 0,
        )
        
        # Analyze Cialdini principles
        profile.cialdini_scores = self._score_cialdini(all_copy)
        if profile.cialdini_scores:
            profile.primary_cialdini = max(
                profile.cialdini_scores.items(),
                key=lambda x: x[1]
            )[0]
        
        # Analyze Aaker dimensions
        profile.aaker_scores = self._score_aaker(all_copy)
        if profile.aaker_scores:
            profile.primary_aaker = max(
                profile.aaker_scores.items(),
                key=lambda x: x[1]
            )[0]
        
        # Analyze tactics
        profile.tactic_scores = self._score_tactics(all_copy)
        if profile.tactic_scores:
            profile.primary_tactic = max(
                profile.tactic_scores.items(),
                key=lambda x: x[1]
            )[0]
        
        # Predict customer fit
        profile.customer_fit = self._predict_customer_fit(profile)
        
        return profile
    
    def _score_cialdini(self, text: str) -> Dict[str, float]:
        """Score text against Cialdini principles."""
        scores = {}
        for principle, patterns in self._cialdini_compiled.items():
            matches = sum(1 for p in patterns if p.search(text))
            if matches > 0:
                # Normalize by number of patterns (max 1.0)
                scores[principle] = min(1.0, matches / len(patterns))
        return scores
    
    def _score_aaker(self, text: str) -> Dict[str, float]:
        """Score text against Aaker brand personality dimensions."""
        scores = {}
        for dimension, patterns in self._aaker_compiled.items():
            matches = sum(1 for p in patterns if p.search(text))
            if matches > 0:
                scores[dimension.value] = min(1.0, matches / len(patterns))
        return scores
    
    def _score_tactics(self, text: str) -> Dict[str, float]:
        """Score text against persuasion tactics."""
        scores = {}
        for tactic, patterns in self._tactic_compiled.items():
            matches = sum(1 for p in patterns if p.search(text))
            if matches > 0:
                scores[tactic.value] = min(1.0, matches / len(patterns))
        return scores
    
    def _predict_customer_fit(self, profile: BrandCopyProfile) -> Dict[str, float]:
        """
        Predict which customer types this brand copy appeals to.
        
        Based on:
        - Cialdini principles → Susceptibility match
        - Aaker dimensions → Personality match
        """
        fit = {
            "analytical": 0.0,
            "emotional": 0.0,
            "social": 0.0,
            "impulsive": 0.0,
            "value_conscious": 0.0,
        }
        
        # Cialdini → Customer type mapping
        cialdini_fit = {
            "authority": ("analytical", 0.8),
            "social_proof": ("social", 0.9),
            "scarcity": ("impulsive", 0.85),
            "reciprocity": ("value_conscious", 0.7),
            "liking": ("emotional", 0.8),
            "commitment": ("social", 0.6),
        }
        
        for principle, score in profile.cialdini_scores.items():
            if principle in cialdini_fit:
                customer_type, weight = cialdini_fit[principle]
                fit[customer_type] = max(fit[customer_type], score * weight)
        
        # Aaker → Customer type mapping
        aaker_fit = {
            "competence": ("analytical", 0.7),
            "sincerity": ("emotional", 0.6),
            "excitement": ("impulsive", 0.7),
            "sophistication": ("emotional", 0.5),
            "ruggedness": ("value_conscious", 0.5),
        }
        
        for dimension, score in profile.aaker_scores.items():
            if dimension in aaker_fit:
                customer_type, weight = aaker_fit[dimension]
                fit[customer_type] = max(fit[customer_type], score * weight)
        
        # Tactic → Customer type mapping
        tactic_fit = {
            "value_proposition": ("analytical", 0.7),
            "fear_appeal": ("analytical", 0.5),
            "aspiration": ("emotional", 0.8),
            "novelty": ("impulsive", 0.6),
            "convenience": ("value_conscious", 0.6),
            "quality": ("analytical", 0.6),
            "guarantee": ("value_conscious", 0.8),
        }
        
        for tactic, score in profile.tactic_scores.items():
            if tactic in tactic_fit:
                customer_type, weight = tactic_fit[tactic]
                fit[customer_type] = max(fit[customer_type], score * weight)
        
        return fit


# =============================================================================
# BATCH PROCESSING
# =============================================================================

class BrandCopyIngestionPipeline:
    """
    Pipeline for processing Amazon product metadata at scale.
    """
    
    def __init__(self, output_dir: Optional[Path] = None):
        self.extractor = BrandCopyExtractor()
        self.output_dir = output_dir or Path("data/brand_copy")
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def process_file(
        self,
        meta_file: Path,
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Process a metadata JSONL file.
        
        Args:
            meta_file: Path to meta_*.jsonl file
            limit: Maximum products to process (for testing)
            
        Returns:
            Dict with processing stats
        """
        import time
        
        category = meta_file.stem.replace("meta_", "")
        output_path = self.output_dir / f"brand_copy_{category}.jsonl"
        
        stats = {
            "category": category,
            "total": 0,
            "processed": 0,
            "errors": 0,
            "with_social_proof": 0,
            "with_authority": 0,
            "with_scarcity": 0,
        }
        
        start = time.time()
        
        with open(meta_file, "r") as f_in, open(output_path, "w") as f_out:
            for line in f_in:
                stats["total"] += 1
                
                if limit and stats["total"] > limit:
                    break
                
                try:
                    product = json.loads(line)
                    profile = self.extractor.analyze(product)
                    f_out.write(profile.to_compact_json() + "\n")
                    
                    stats["processed"] += 1
                    
                    # Track principle usage
                    if profile.cialdini_scores.get("social_proof", 0) > 0.3:
                        stats["with_social_proof"] += 1
                    if profile.cialdini_scores.get("authority", 0) > 0.3:
                        stats["with_authority"] += 1
                    if profile.cialdini_scores.get("scarcity", 0) > 0.3:
                        stats["with_scarcity"] += 1
                        
                except Exception as e:
                    stats["errors"] += 1
                    if stats["errors"] <= 5:
                        logger.debug(f"Error processing product: {e}")
                
                # Progress
                if stats["total"] % 10000 == 0:
                    elapsed = time.time() - start
                    rate = stats["total"] / max(elapsed, 0.001)
                    print(f"\r[{category}] {stats['total']:,} products, {rate:.0f}/sec", end="", flush=True)
        
        print()  # New line
        
        elapsed = time.time() - start
        stats["elapsed_sec"] = elapsed
        stats["rate"] = stats["total"] / max(elapsed, 0.001)
        
        logger.info(
            f"[{category}] Processed {stats['processed']:,} products in {elapsed:.1f}s "
            f"({stats['rate']:.0f}/sec)"
        )
        
        return stats


# =============================================================================
# SINGLETON
# =============================================================================

_extractor: Optional[BrandCopyExtractor] = None


def get_brand_copy_extractor() -> BrandCopyExtractor:
    """Get singleton brand copy extractor."""
    global _extractor
    if _extractor is None:
        _extractor = BrandCopyExtractor()
    return _extractor


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Extract brand copy intelligence")
    parser.add_argument("--input", type=str, required=True, help="Input meta file")
    parser.add_argument("--limit", type=int, help="Limit products for testing")
    
    args = parser.parse_args()
    
    logging.basicConfig(level=logging.INFO)
    
    pipeline = BrandCopyIngestionPipeline()
    stats = pipeline.process_file(Path(args.input), limit=args.limit)
    
    print("\nStats:", json.dumps(stats, indent=2))
