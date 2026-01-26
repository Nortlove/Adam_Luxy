# ADAM Amazon Dataset Processing Specification
## Transforming 1.2B+ Verified Purchase Reviews into Psychological Intelligence Priors

**Document Purpose**: Define the complete data pipeline for ingesting, processing, and operationalizing Amazon's verified purchase review corpus as the foundational psychological intelligence layer for ADAM.

**Version**: 1.0  
**Date**: January 2026  
**Status**: Production Specification  
**Classification**: Core Data Infrastructure  
**Priority**: P0 - Foundational

---

# EXECUTIVE SUMMARY

## Why This Dataset Is Foundational

The Amazon review corpus is unique in the world of consumer psychology data because it provides:

| Property | Why It Matters | Alternative Sources (And Why They're Inferior) |
|----------|---------------|----------------------------------------------|
| **Verified Purchase** | We KNOW this person actually bought the product | Social media: no purchase verification |
| **Unstructured Language** | Natural expression reveals personality | Surveys: prompted, not natural |
| **Cross-Category Behavior** | Same customer across 100+ categories | Single-retailer: narrow view |
| **Temporal Patterns** | Review timing, purchase frequency | Static datasets: no time dimension |
| **Scale** | 1.2B+ reviews, 100M+ reviewers | Academic studies: thousands of participants |

**The Core Insight**: This is the only dataset where **verified economic behavior** meets **unstructured psychological expression** at scale. Every review is simultaneously:
- A **purchase signal** (they bought this)
- A **satisfaction signal** (they cared enough to review)
- A **personality signal** (how they express themselves)
- A **values signal** (what they prioritize in products)

## What ADAM Extracts From This Data

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                    AMAZON DATA → PSYCHOLOGICAL INTELLIGENCE                     │
│                                                                                 │
│   RAW DATA                    EXTRACTION                    OPERATIONALIZATION  │
│   ════════                    ══════════                    ═══════════════════ │
│                                                                                 │
│   Review Text ─────────────→ Linguistic Features ────────→ Big Five Inference  │
│   ├─ Word choice             ├─ Self-reference             ├─ Openness score   │
│   ├─ Sentence structure      ├─ Analytical markers         ├─ Conscientiousness│
│   ├─ Emotional expression    ├─ Social orientation         ├─ Extraversion     │
│   └─ Detail level            └─ Certainty language         └─ Neuroticism      │
│                                                                                 │
│   Rating + Text ───────────→ Satisfaction Drivers ───────→ Mechanism Priors    │
│   ├─ 5★ = what delights      ├─ Quality focus             ├─ Loss aversion     │
│   ├─ 1★ = what disappoints   ├─ Value focus               ├─ Social proof     │
│   └─ 3★ = trade-offs         └─ Social validation need    └─ Scarcity response│
│                                                                                 │
│   Purchase History ────────→ Cross-Category Patterns ────→ Archetype Clusters │
│   ├─ Categories purchased    ├─ Lifestyle inference       ├─ Cold Start priors│
│   ├─ Price tier patterns     ├─ Values hierarchy          ├─ Format priors    │
│   └─ Brand loyalty           └─ Decision style            └─ Station priors   │
│                                                                                 │
│   Timing Patterns ─────────→ Temporal Signatures ────────→ Journey Priors     │
│   ├─ Review delay            ├─ Reflection tendency       ├─ Decision stage   │
│   ├─ Review frequency        ├─ Engagement level          ├─ Urgency signals  │
│   └─ Update behavior         └─ Consideration depth       └─ Timing optima    │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

# PART 1: DATA SCHEMA AND STRUCTURE

## 1.1 Expected Raw Data Format

The Amazon review corpus is expected in the following format (standard Amazon product review dataset structure):

```python
# =============================================================================
# RAW AMAZON REVIEW SCHEMA
# =============================================================================

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class RawAmazonReview(BaseModel):
    """
    Raw review record from Amazon corpus.
    
    This schema represents the expected input format from the dataset.
    """
    # Core identifiers
    review_id: str                          # Unique review identifier
    reviewer_id: str                        # Amazon customer ID (anonymized)
    asin: str                               # Amazon Standard Identification Number
    
    # Review content
    review_text: str                        # Full review text
    summary: Optional[str] = None           # Review title/summary
    overall: float                          # Star rating (1.0-5.0)
    
    # Temporal
    unix_review_time: int                   # Unix timestamp
    review_time: str                        # Human-readable date
    
    # Metadata
    verified: bool = True                   # Verified purchase flag
    vote: Optional[int] = None              # Helpful votes
    
    # Product context (may be in separate file)
    category: Optional[str] = None
    brand: Optional[str] = None
    price: Optional[float] = None
    
    @property
    def review_datetime(self) -> datetime:
        return datetime.fromtimestamp(self.unix_review_time)


class AmazonProductMetadata(BaseModel):
    """
    Product metadata (typically in separate file).
    """
    asin: str
    title: str
    brand: Optional[str] = None
    price: Optional[float] = None
    
    # Category hierarchy
    categories: List[List[str]] = Field(default_factory=list)
    main_category: Optional[str] = None
    
    # Product characteristics
    description: Optional[str] = None
    features: List[str] = Field(default_factory=list)
    
    # Images (for multimodal if needed)
    image_urls: List[str] = Field(default_factory=list)


class ReviewerProfile(BaseModel):
    """
    Aggregated profile for a single Amazon reviewer.
    
    Built from all their reviews across categories.
    """
    reviewer_id: str
    
    # Review statistics
    total_reviews: int
    verified_reviews: int
    
    # Category spread
    categories_reviewed: List[str]
    primary_categories: List[str]  # Top 3 by count
    
    # Rating patterns
    avg_rating: float
    rating_distribution: Dict[int, int]  # {1: count, 2: count, ...}
    rating_std: float
    
    # Temporal patterns
    first_review_date: datetime
    last_review_date: datetime
    avg_days_between_reviews: float
    review_velocity_trend: str  # "increasing", "decreasing", "stable"
    
    # Language patterns (aggregated)
    avg_review_length: float
    vocabulary_richness: float
    
    # Inferred traits (to be computed)
    inferred_big_five: Optional[Dict[str, float]] = None
    inferred_regulatory_focus: Optional[str] = None
    inferred_construal_level: Optional[str] = None
```

## 1.2 Category Taxonomy

Amazon categories must be mapped to ADAM's psychological category model:

```python
# =============================================================================
# AMAZON CATEGORY → ADAM PSYCHOLOGICAL CATEGORY MAPPING
# =============================================================================

class ADAMProductCategory(str, Enum):
    """ADAM's standardized product categories with psychological profiles."""
    
    # Technology
    ELECTRONICS_CONSUMER = "electronics_consumer"
    ELECTRONICS_PROFESSIONAL = "electronics_professional"
    COMPUTING = "computing"
    MOBILE = "mobile"
    GAMING = "gaming"
    
    # Home & Living
    HOME_FURNITURE = "home_furniture"
    HOME_DECOR = "home_decor"
    KITCHEN = "kitchen"
    APPLIANCES = "appliances"
    
    # Personal Care
    BEAUTY = "beauty"
    HEALTH = "health"
    PERSONAL_CARE = "personal_care"
    FITNESS = "fitness"
    
    # Fashion
    FASHION_APPAREL = "fashion_apparel"
    FASHION_ACCESSORIES = "fashion_accessories"
    FASHION_LUXURY = "fashion_luxury"
    
    # Media & Entertainment
    BOOKS = "books"
    MUSIC = "music"
    MOVIES = "movies"
    GAMES = "games"
    
    # Automotive
    AUTOMOTIVE = "automotive"
    
    # Food & Beverage
    GROCERY = "grocery"
    GOURMET = "gourmet"
    
    # Baby & Family
    BABY = "baby"
    TOYS = "toys"
    
    # Outdoor & Sports
    SPORTS = "sports"
    OUTDOOR = "outdoor"
    
    # Other
    OFFICE = "office"
    PET = "pet"
    CRAFTS = "crafts"


# Mapping from Amazon categories to ADAM categories
AMAZON_TO_ADAM_CATEGORY = {
    "Electronics": ADAMProductCategory.ELECTRONICS_CONSUMER,
    "Computers": ADAMProductCategory.COMPUTING,
    "Cell Phones & Accessories": ADAMProductCategory.MOBILE,
    "Video Games": ADAMProductCategory.GAMING,
    "Home & Kitchen": ADAMProductCategory.KITCHEN,
    "Furniture": ADAMProductCategory.HOME_FURNITURE,
    "Beauty": ADAMProductCategory.BEAUTY,
    "Health & Personal Care": ADAMProductCategory.HEALTH,
    "Sports & Outdoors": ADAMProductCategory.SPORTS,
    "Clothing, Shoes & Jewelry": ADAMProductCategory.FASHION_APPAREL,
    "Books": ADAMProductCategory.BOOKS,
    "Movies & TV": ADAMProductCategory.MOVIES,
    "Grocery & Gourmet Food": ADAMProductCategory.GROCERY,
    "Baby": ADAMProductCategory.BABY,
    "Toys & Games": ADAMProductCategory.TOYS,
    "Automotive": ADAMProductCategory.AUTOMOTIVE,
    "Pet Supplies": ADAMProductCategory.PET,
    "Office Products": ADAMProductCategory.OFFICE,
    # ... complete mapping
}


# Psychological profiles by category (used as priors)
CATEGORY_PSYCHOLOGICAL_PROFILES = {
    ADAMProductCategory.ELECTRONICS_CONSUMER: {
        "big_five_skew": {
            "openness": 0.62,        # Tech enthusiasts tend higher
            "conscientiousness": 0.55,
            "extraversion": 0.48,
            "agreeableness": 0.50,
            "neuroticism": 0.48
        },
        "regulatory_focus": "promotion",  # Seeking new features
        "construal_level": "concrete",    # Spec-focused
        "decision_style": "analytical",
        "primary_mechanisms": ["novelty", "competence", "social_proof"],
        "review_characteristics": {
            "avg_length": 180,
            "detail_level": "high",
            "comparison_frequency": "high"
        }
    },
    
    ADAMProductCategory.BEAUTY: {
        "big_five_skew": {
            "openness": 0.58,
            "conscientiousness": 0.52,
            "extraversion": 0.62,       # Higher social orientation
            "agreeableness": 0.58,
            "neuroticism": 0.55
        },
        "regulatory_focus": "mixed",
        "construal_level": "mixed",
        "decision_style": "experiential",
        "primary_mechanisms": ["identity_expression", "social_proof", "authenticity"],
        "review_characteristics": {
            "avg_length": 120,
            "detail_level": "medium",
            "emotional_expression": "high"
        }
    },
    
    ADAMProductCategory.BOOKS: {
        "big_five_skew": {
            "openness": 0.72,           # Highest openness
            "conscientiousness": 0.55,
            "extraversion": 0.45,       # Lower extraversion
            "agreeableness": 0.55,
            "neuroticism": 0.50
        },
        "regulatory_focus": "promotion",
        "construal_level": "abstract",  # Ideas over details
        "decision_style": "reflective",
        "primary_mechanisms": ["curiosity", "identity_expression", "narrative_transport"],
        "review_characteristics": {
            "avg_length": 200,
            "detail_level": "high",
            "emotional_expression": "high"
        }
    },
    
    # ... profiles for all categories
}
```

---

# PART 2: INGESTION PIPELINE

## 2.1 Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                    AMAZON DATA INGESTION PIPELINE                               │
│                                                                                 │
│   ┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐  │
│   │   Raw JSON  │     │   Validate  │     │   Enrich    │     │   Extract   │  │
│   │   Files     │────►│   & Parse   │────►│   Metadata  │────►│   Features  │  │
│   │             │     │             │     │             │     │             │  │
│   └─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘  │
│                                                                     │          │
│                                                                     ▼          │
│   ┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐  │
│   │   Neo4j     │     │   Build     │     │   Cluster   │     │   Compute   │  │
│   │   Storage   │◄────│   Priors    │◄────│   Reviewers │◄────│   Profiles  │  │
│   │             │     │             │     │             │     │             │  │
│   └─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘  │
│         │                                                                       │
│         ▼                                                                       │
│   ┌─────────────────────────────────────────────────────────────────────────┐  │
│   │                     ADAM LEARNING SYSTEMS                               │  │
│   │   ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐      │  │
│   │   │Cold     │  │Mechanism│  │Category │  │Archetype│  │WPP/     │      │  │
│   │   │Start    │  │Priors   │  │Priors   │  │Clusters │  │iHeart   │      │  │
│   │   └─────────┘  └─────────┘  └─────────┘  └─────────┘  └─────────┘      │  │
│   └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 2.2 Ingestion Service Implementation

```python
# =============================================================================
# AMAZON DATA INGESTION SERVICE
# =============================================================================

import asyncio
import logging
from pathlib import Path
from typing import AsyncIterator, Dict, List, Optional, Any
from datetime import datetime
import json
import gzip
from dataclasses import dataclass, field

from neo4j import AsyncDriver
from pydantic import ValidationError

logger = logging.getLogger(__name__)


@dataclass
class IngestionConfig:
    """Configuration for Amazon data ingestion."""
    
    # Data paths
    reviews_path: Path                      # Path to reviews JSON/JSONL files
    metadata_path: Optional[Path] = None    # Path to product metadata
    
    # Processing settings
    batch_size: int = 10000                 # Reviews per batch
    parallel_workers: int = 8               # Concurrent processing workers
    
    # Filtering
    min_review_length: int = 20             # Skip very short reviews
    verified_only: bool = True              # Only verified purchases
    min_helpful_votes: int = 0              # Minimum helpful votes
    
    # Language processing
    extract_features_inline: bool = False   # Extract linguistic features during ingestion
    use_claude_for_features: bool = True    # Use Claude vs. rule-based
    
    # Output
    store_raw_text: bool = False            # Store full review text in Neo4j
    neo4j_database: str = "neo4j"


class AmazonDataIngestionService:
    """
    Ingest and process Amazon review data into ADAM's knowledge graph.
    
    This is a BATCH process run periodically to update priors, not
    a real-time service.
    """
    
    def __init__(
        self,
        neo4j_driver: AsyncDriver,
        config: IngestionConfig,
        claude_client: Optional[Any] = None
    ):
        self.neo4j = neo4j_driver
        self.config = config
        self.claude = claude_client
        
        # Statistics
        self.stats = {
            "reviews_processed": 0,
            "reviews_skipped": 0,
            "reviewers_created": 0,
            "products_created": 0,
            "features_extracted": 0,
            "errors": 0
        }
    
    async def run_full_ingestion(self) -> Dict[str, Any]:
        """
        Run complete ingestion pipeline.
        
        This is the main entry point for initial data load or refresh.
        """
        logger.info("Starting Amazon data ingestion")
        start_time = datetime.utcnow()
        
        try:
            # Phase 1: Load and validate raw reviews
            logger.info("Phase 1: Loading and validating reviews")
            async for batch in self._load_reviews_batched():
                await self._process_review_batch(batch)
            
            # Phase 2: Build reviewer profiles
            logger.info("Phase 2: Building reviewer profiles")
            await self._build_reviewer_profiles()
            
            # Phase 3: Extract psychological features
            logger.info("Phase 3: Extracting psychological features")
            await self._extract_psychological_features()
            
            # Phase 4: Cluster reviewers into archetypes
            logger.info("Phase 4: Clustering into archetypes")
            await self._cluster_reviewers()
            
            # Phase 5: Build category priors
            logger.info("Phase 5: Building category priors")
            await self._build_category_priors()
            
            # Phase 6: Build mechanism priors
            logger.info("Phase 6: Building mechanism priors")
            await self._build_mechanism_priors()
            
            elapsed = (datetime.utcnow() - start_time).total_seconds()
            
            return {
                "status": "success",
                "elapsed_seconds": elapsed,
                "statistics": self.stats
            }
            
        except Exception as e:
            logger.error(f"Ingestion failed: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "statistics": self.stats
            }
    
    async def _load_reviews_batched(self) -> AsyncIterator[List[RawAmazonReview]]:
        """
        Load reviews from files in batches.
        
        Handles both .json and .json.gz files.
        """
        files = list(self.config.reviews_path.glob("*.json*"))
        logger.info(f"Found {len(files)} review files")
        
        batch = []
        
        for file_path in files:
            logger.info(f"Processing file: {file_path.name}")
            
            # Handle gzipped files
            if file_path.suffix == '.gz':
                opener = gzip.open
            else:
                opener = open
            
            with opener(file_path, 'rt', encoding='utf-8') as f:
                for line in f:
                    try:
                        data = json.loads(line.strip())
                        review = RawAmazonReview(**data)
                        
                        # Apply filters
                        if self._should_skip_review(review):
                            self.stats["reviews_skipped"] += 1
                            continue
                        
                        batch.append(review)
                        
                        if len(batch) >= self.config.batch_size:
                            yield batch
                            batch = []
                            
                    except (json.JSONDecodeError, ValidationError) as e:
                        self.stats["errors"] += 1
                        continue
        
        # Yield remaining
        if batch:
            yield batch
    
    def _should_skip_review(self, review: RawAmazonReview) -> bool:
        """Apply filtering rules."""
        if self.config.verified_only and not review.verified:
            return True
        if len(review.review_text) < self.config.min_review_length:
            return True
        if review.vote is not None and review.vote < self.config.min_helpful_votes:
            return True
        return False
    
    async def _process_review_batch(self, batch: List[RawAmazonReview]):
        """
        Process a batch of reviews into Neo4j.
        """
        async with self.neo4j.session(database=self.config.neo4j_database) as session:
            # Create/update reviewer nodes
            reviewer_data = self._aggregate_reviewer_data(batch)
            await session.execute_write(
                self._write_reviewers, reviewer_data
            )
            
            # Create/update product nodes
            product_data = self._aggregate_product_data(batch)
            await session.execute_write(
                self._write_products, product_data
            )
            
            # Create review relationships
            await session.execute_write(
                self._write_reviews, batch
            )
        
        self.stats["reviews_processed"] += len(batch)
        
        if self.stats["reviews_processed"] % 100000 == 0:
            logger.info(f"Processed {self.stats['reviews_processed']:,} reviews")
    
    @staticmethod
    async def _write_reviewers(tx, reviewer_data: List[Dict]):
        """Write reviewer nodes to Neo4j."""
        query = """
        UNWIND $reviewers AS reviewer
        MERGE (r:AmazonReviewer {reviewer_id: reviewer.reviewer_id})
        ON CREATE SET
            r.created_at = datetime(),
            r.review_count = 1
        ON MATCH SET
            r.review_count = r.review_count + 1,
            r.updated_at = datetime()
        """
        await tx.run(query, reviewers=reviewer_data)
    
    @staticmethod
    async def _write_products(tx, product_data: List[Dict]):
        """Write product nodes to Neo4j."""
        query = """
        UNWIND $products AS product
        MERGE (p:AmazonProduct {asin: product.asin})
        ON CREATE SET
            p.category = product.category,
            p.adam_category = product.adam_category,
            p.created_at = datetime()
        """
        await tx.run(query, products=product_data)
    
    @staticmethod
    async def _write_reviews(tx, reviews: List[RawAmazonReview]):
        """Write review relationships."""
        review_data = [
            {
                "reviewer_id": r.reviewer_id,
                "asin": r.asin,
                "rating": r.overall,
                "review_length": len(r.review_text),
                "timestamp": r.unix_review_time
            }
            for r in reviews
        ]
        
        query = """
        UNWIND $reviews AS review
        MATCH (r:AmazonReviewer {reviewer_id: review.reviewer_id})
        MATCH (p:AmazonProduct {asin: review.asin})
        MERGE (r)-[rev:REVIEWED {timestamp: review.timestamp}]->(p)
        SET rev.rating = review.rating,
            rev.review_length = review.review_length
        """
        await tx.run(query, reviews=review_data)
```

---

# PART 3: LINGUISTIC FEATURE EXTRACTION

## 3.1 Feature Extraction Pipeline

```python
# =============================================================================
# LINGUISTIC FEATURE EXTRACTION
# =============================================================================

from dataclasses import dataclass
from typing import Dict, List, Any, Optional
import re
from collections import Counter


@dataclass
class LinguisticFeatures:
    """
    Extracted linguistic features from review text.
    
    These features map to psychological constructs.
    """
    # Self-reference (I, me, my) - correlates with neuroticism, depression
    self_reference_rate: float
    
    # Social reference (we, us, they) - correlates with extraversion
    social_reference_rate: float
    
    # Analytical language (because, therefore, thus) - correlates with conscientiousness
    analytical_marker_rate: float
    
    # Certainty language (definitely, always, never) - correlates with dogmatism
    certainty_rate: float
    tentative_rate: float  # maybe, perhaps, possibly
    
    # Emotional expression
    positive_emotion_rate: float
    negative_emotion_rate: float
    emotional_intensity: float
    
    # Cognitive complexity
    avg_sentence_length: float
    vocabulary_richness: float  # Type-token ratio
    subordinate_clause_rate: float
    
    # Specificity
    number_usage_rate: float     # Concrete numbers
    detail_marker_rate: float    # Specific descriptions
    
    # Temporal orientation
    past_tense_rate: float
    present_tense_rate: float
    future_tense_rate: float
    
    # Review-specific
    comparison_language_rate: float   # "compared to", "better than"
    recommendation_rate: float        # "recommend", "suggest", "worth"
    
    # Confidence in extraction
    extraction_confidence: float


class LinguisticFeatureExtractor:
    """
    Extract psycholinguistic features from review text.
    
    Uses rule-based extraction for speed with Claude augmentation
    for nuanced understanding.
    """
    
    # Word lists for feature detection
    SELF_REFERENCE = {'i', 'me', 'my', 'mine', 'myself'}
    SOCIAL_REFERENCE = {'we', 'us', 'our', 'they', 'them', 'their', 'people'}
    ANALYTICAL_MARKERS = {
        'because', 'therefore', 'thus', 'hence', 'consequently',
        'since', 'reason', 'result', 'cause', 'effect', 'due to'
    }
    CERTAINTY_MARKERS = {
        'definitely', 'certainly', 'absolutely', 'always', 'never',
        'must', 'obvious', 'clearly', 'undoubtedly', 'surely'
    }
    TENTATIVE_MARKERS = {
        'maybe', 'perhaps', 'possibly', 'might', 'could',
        'seems', 'appears', 'somewhat', 'kind of', 'sort of'
    }
    POSITIVE_EMOTIONS = {
        'love', 'great', 'excellent', 'amazing', 'wonderful',
        'perfect', 'fantastic', 'awesome', 'happy', 'pleased',
        'satisfied', 'impressed', 'recommend', 'best', 'favorite'
    }
    NEGATIVE_EMOTIONS = {
        'hate', 'terrible', 'awful', 'horrible', 'worst',
        'disappointed', 'frustrating', 'annoying', 'waste',
        'broke', 'cheap', 'poor', 'useless', 'defective'
    }
    COMPARISON_MARKERS = {
        'compared', 'versus', 'vs', 'better', 'worse',
        'than', 'unlike', 'similar', 'different', 'prefer'
    }
    RECOMMENDATION_MARKERS = {
        'recommend', 'suggest', 'worth', 'buy', 'get',
        'try', 'must have', 'essential', 'skip', 'avoid'
    }
    
    def extract(self, text: str) -> LinguisticFeatures:
        """Extract all linguistic features from text."""
        
        # Tokenize
        words = self._tokenize(text)
        sentences = self._split_sentences(text)
        word_count = len(words)
        
        if word_count < 5:
            return self._default_features()
        
        word_set = set(w.lower() for w in words)
        word_lower = [w.lower() for w in words]
        
        # Calculate rates
        return LinguisticFeatures(
            self_reference_rate=self._count_matches(word_lower, self.SELF_REFERENCE) / word_count,
            social_reference_rate=self._count_matches(word_lower, self.SOCIAL_REFERENCE) / word_count,
            analytical_marker_rate=self._count_phrase_matches(text.lower(), self.ANALYTICAL_MARKERS) / word_count,
            certainty_rate=self._count_matches(word_lower, self.CERTAINTY_MARKERS) / word_count,
            tentative_rate=self._count_matches(word_lower, self.TENTATIVE_MARKERS) / word_count,
            positive_emotion_rate=self._count_matches(word_lower, self.POSITIVE_EMOTIONS) / word_count,
            negative_emotion_rate=self._count_matches(word_lower, self.NEGATIVE_EMOTIONS) / word_count,
            emotional_intensity=self._calculate_emotional_intensity(text),
            avg_sentence_length=word_count / max(1, len(sentences)),
            vocabulary_richness=len(word_set) / word_count,
            subordinate_clause_rate=self._count_subordinate_clauses(text) / max(1, len(sentences)),
            number_usage_rate=len(re.findall(r'\d+', text)) / word_count,
            detail_marker_rate=self._count_detail_markers(text) / word_count,
            past_tense_rate=self._estimate_tense(words, 'past'),
            present_tense_rate=self._estimate_tense(words, 'present'),
            future_tense_rate=self._estimate_tense(words, 'future'),
            comparison_language_rate=self._count_matches(word_lower, self.COMPARISON_MARKERS) / word_count,
            recommendation_rate=self._count_matches(word_lower, self.RECOMMENDATION_MARKERS) / word_count,
            extraction_confidence=0.8 if word_count > 50 else 0.5
        )
    
    def _tokenize(self, text: str) -> List[str]:
        """Simple word tokenization."""
        return re.findall(r'\b\w+\b', text)
    
    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        return re.split(r'[.!?]+', text)
    
    def _count_matches(self, words: List[str], word_set: set) -> int:
        """Count how many words match the given set."""
        return sum(1 for w in words if w in word_set)
    
    def _count_phrase_matches(self, text: str, phrase_set: set) -> int:
        """Count phrase matches in text."""
        count = 0
        for phrase in phrase_set:
            count += text.count(phrase)
        return count
    
    def _calculate_emotional_intensity(self, text: str) -> float:
        """
        Calculate emotional intensity from punctuation and capitalization.
        """
        exclamation_count = text.count('!')
        caps_ratio = sum(1 for c in text if c.isupper()) / max(1, len(text))
        
        intensity = min(1.0, (exclamation_count * 0.2) + (caps_ratio * 2))
        return intensity
    
    def _count_subordinate_clauses(self, text: str) -> int:
        """Count subordinate clause markers."""
        markers = {'which', 'that', 'who', 'whom', 'whose', 'where', 'when', 'while', 'although', 'because', 'if'}
        words = self._tokenize(text.lower())
        return sum(1 for w in words if w in markers)
    
    def _count_detail_markers(self, text: str) -> int:
        """Count specific detail indicators."""
        # Look for specific measurements, colors, materials, etc.
        patterns = [
            r'\d+\s*(inch|cm|mm|oz|lb|gram)',  # Measurements
            r'(black|white|red|blue|green|gray)',  # Colors
            r'(plastic|metal|leather|cotton|wood)',  # Materials
        ]
        count = 0
        for pattern in patterns:
            count += len(re.findall(pattern, text.lower()))
        return count
    
    def _estimate_tense(self, words: List[str], tense: str) -> float:
        """Estimate tense usage rate."""
        past_markers = {'was', 'were', 'had', 'did', 'bought', 'used', 'worked', 'tried'}
        present_markers = {'is', 'are', 'am', 'have', 'has', 'works', 'looks', 'feels'}
        future_markers = {'will', 'going', 'gonna', 'plan', 'expect', 'hope'}
        
        markers = {
            'past': past_markers,
            'present': present_markers,
            'future': future_markers
        }[tense]
        
        return self._count_matches([w.lower() for w in words], markers) / max(1, len(words))
    
    def _default_features(self) -> LinguisticFeatures:
        """Return default features for very short text."""
        return LinguisticFeatures(
            self_reference_rate=0.0,
            social_reference_rate=0.0,
            analytical_marker_rate=0.0,
            certainty_rate=0.0,
            tentative_rate=0.0,
            positive_emotion_rate=0.0,
            negative_emotion_rate=0.0,
            emotional_intensity=0.0,
            avg_sentence_length=0.0,
            vocabulary_richness=0.0,
            subordinate_clause_rate=0.0,
            number_usage_rate=0.0,
            detail_marker_rate=0.0,
            past_tense_rate=0.0,
            present_tense_rate=0.0,
            future_tense_rate=0.0,
            comparison_language_rate=0.0,
            recommendation_rate=0.0,
            extraction_confidence=0.0
        )
```

---

# PART 4: PSYCHOLOGICAL PROFILE INFERENCE

## 4.1 Big Five Inference from Linguistic Features

```python
# =============================================================================
# BIG FIVE INFERENCE FROM LINGUISTIC FEATURES
# =============================================================================

from dataclasses import dataclass
from typing import Dict, Optional
import numpy as np


@dataclass
class BigFiveInference:
    """Inferred Big Five personality scores with confidence."""
    openness: float              # 0-1
    conscientiousness: float     # 0-1
    extraversion: float          # 0-1
    agreeableness: float         # 0-1
    neuroticism: float           # 0-1
    
    # Confidence per trait
    openness_confidence: float
    conscientiousness_confidence: float
    extraversion_confidence: float
    agreeableness_confidence: float
    neuroticism_confidence: float
    
    # Overall confidence
    overall_confidence: float


class BigFiveInferenceEngine:
    """
    Infer Big Five personality traits from linguistic features.
    
    Based on research:
    - Pennebaker & King (1999): Linguistic markers of personality
    - Yarkoni (2010): Personality in 100,000 words
    - Schwartz et al. (2013): Personality from social media language
    """
    
    # Feature → Trait correlations (from literature)
    # Positive values = positive correlation, negative = negative correlation
    FEATURE_TRAIT_CORRELATIONS = {
        "openness": {
            "vocabulary_richness": 0.35,
            "subordinate_clause_rate": 0.25,
            "avg_sentence_length": 0.20,
            "analytical_marker_rate": 0.15,
            "certainty_rate": -0.15,  # Open people are less certain
            "tentative_rate": 0.10,
        },
        "conscientiousness": {
            "analytical_marker_rate": 0.30,
            "detail_marker_rate": 0.25,
            "number_usage_rate": 0.20,
            "certainty_rate": 0.15,
            "negative_emotion_rate": -0.20,
            "tentative_rate": -0.10,
        },
        "extraversion": {
            "social_reference_rate": 0.30,
            "positive_emotion_rate": 0.25,
            "emotional_intensity": 0.20,
            "self_reference_rate": -0.15,  # Extraverts focus on others
            "avg_sentence_length": -0.10,  # More concise
        },
        "agreeableness": {
            "positive_emotion_rate": 0.30,
            "social_reference_rate": 0.20,
            "negative_emotion_rate": -0.35,
            "certainty_rate": -0.15,  # Less dogmatic
            "recommendation_rate": 0.15,
        },
        "neuroticism": {
            "negative_emotion_rate": 0.35,
            "self_reference_rate": 0.25,
            "tentative_rate": 0.15,
            "certainty_rate": -0.10,
            "positive_emotion_rate": -0.25,
        }
    }
    
    def infer(
        self,
        features: LinguisticFeatures,
        category_prior: Optional[Dict[str, float]] = None
    ) -> BigFiveInference:
        """
        Infer Big Five from linguistic features.
        
        Args:
            features: Extracted linguistic features
            category_prior: Optional category-based priors (e.g., from product category)
        """
        trait_scores = {}
        trait_confidences = {}
        
        for trait in ["openness", "conscientiousness", "extraversion", 
                      "agreeableness", "neuroticism"]:
            
            score, confidence = self._infer_single_trait(
                trait, features, category_prior
            )
            trait_scores[trait] = score
            trait_confidences[trait] = confidence
        
        overall_confidence = np.mean(list(trait_confidences.values())) * features.extraction_confidence
        
        return BigFiveInference(
            openness=trait_scores["openness"],
            conscientiousness=trait_scores["conscientiousness"],
            extraversion=trait_scores["extraversion"],
            agreeableness=trait_scores["agreeableness"],
            neuroticism=trait_scores["neuroticism"],
            openness_confidence=trait_confidences["openness"],
            conscientiousness_confidence=trait_confidences["conscientiousness"],
            extraversion_confidence=trait_confidences["extraversion"],
            agreeableness_confidence=trait_confidences["agreeableness"],
            neuroticism_confidence=trait_confidences["neuroticism"],
            overall_confidence=overall_confidence
        )
    
    def _infer_single_trait(
        self,
        trait: str,
        features: LinguisticFeatures,
        category_prior: Optional[Dict[str, float]]
    ) -> tuple[float, float]:
        """
        Infer a single trait score.
        
        Returns (score, confidence).
        """
        correlations = self.FEATURE_TRAIT_CORRELATIONS.get(trait, {})
        
        # Calculate weighted sum of feature contributions
        contributions = []
        weights = []
        
        for feature_name, correlation in correlations.items():
            feature_value = getattr(features, feature_name, None)
            if feature_value is not None:
                # Transform feature to contribution
                if correlation > 0:
                    contribution = feature_value * correlation
                else:
                    contribution = (1 - feature_value) * abs(correlation)
                
                contributions.append(contribution)
                weights.append(abs(correlation))
        
        if not contributions:
            # Use prior if available, else population mean
            if category_prior and trait in category_prior:
                return category_prior[trait], 0.4
            return 0.5, 0.3
        
        # Weighted average
        score = np.average(contributions) / np.average(weights)
        
        # Normalize to 0-1
        score = max(0.0, min(1.0, 0.5 + score))
        
        # Blend with prior if available
        if category_prior and trait in category_prior:
            prior = category_prior[trait]
            # Weight prior less as we have more evidence
            prior_weight = 0.3
            score = score * (1 - prior_weight) + prior * prior_weight
        
        # Confidence based on number of features used
        confidence = min(0.9, 0.4 + 0.1 * len(contributions))
        
        return score, confidence
```

## 4.2 Mechanism Prior Inference

```python
# =============================================================================
# MECHANISM PRIOR INFERENCE
# =============================================================================

@dataclass
class MechanismPriors:
    """Inferred mechanism susceptibility priors."""
    
    # Each mechanism: (susceptibility 0-1, confidence 0-1)
    loss_aversion: tuple[float, float]
    social_proof: tuple[float, float]
    scarcity: tuple[float, float]
    authority: tuple[float, float]
    reciprocity: tuple[float, float]
    commitment_consistency: tuple[float, float]
    liking: tuple[float, float]
    novelty: tuple[float, float]
    identity_expression: tuple[float, float]


class MechanismPriorInferenceEngine:
    """
    Infer mechanism susceptibility from Big Five + linguistic features.
    
    Based on research connecting personality to persuasion susceptibility:
    - Cialdini's principles × personality research
    - Kaptein et al. (2015): Personalizing persuasive technologies
    """
    
    # Big Five → Mechanism susceptibility mappings
    TRAIT_MECHANISM_MAP = {
        "loss_aversion": {
            "neuroticism": 0.4,
            "conscientiousness": 0.2,
            "openness": -0.2,
        },
        "social_proof": {
            "extraversion": 0.3,
            "agreeableness": 0.3,
            "openness": -0.1,
        },
        "scarcity": {
            "neuroticism": 0.3,
            "conscientiousness": 0.2,
        },
        "authority": {
            "conscientiousness": 0.3,
            "agreeableness": 0.2,
            "openness": -0.2,
        },
        "novelty": {
            "openness": 0.5,
            "extraversion": 0.2,
            "conscientiousness": -0.2,
        },
        "identity_expression": {
            "openness": 0.3,
            "extraversion": 0.2,
            "agreeableness": 0.1,
        }
    }
    
    # Linguistic feature → Mechanism susceptibility
    LINGUISTIC_MECHANISM_MAP = {
        "loss_aversion": {
            "negative_emotion_rate": 0.3,
            "certainty_rate": 0.2,
        },
        "social_proof": {
            "social_reference_rate": 0.4,
            "comparison_language_rate": 0.3,
        },
        "authority": {
            "analytical_marker_rate": 0.3,
            "detail_marker_rate": 0.2,
        },
        "novelty": {
            "vocabulary_richness": 0.3,
            "positive_emotion_rate": 0.2,
        }
    }
    
    def infer(
        self,
        big_five: BigFiveInference,
        features: LinguisticFeatures
    ) -> MechanismPriors:
        """
        Infer mechanism priors from personality and language.
        """
        mechanisms = {}
        
        for mechanism in ["loss_aversion", "social_proof", "scarcity",
                         "authority", "reciprocity", "commitment_consistency",
                         "liking", "novelty", "identity_expression"]:
            
            susceptibility, confidence = self._infer_mechanism(
                mechanism, big_five, features
            )
            mechanisms[mechanism] = (susceptibility, confidence)
        
        return MechanismPriors(**mechanisms)
    
    def _infer_mechanism(
        self,
        mechanism: str,
        big_five: BigFiveInference,
        features: LinguisticFeatures
    ) -> tuple[float, float]:
        """Infer single mechanism susceptibility."""
        
        contributions = []
        weights = []
        
        # Trait-based contribution
        trait_map = self.TRAIT_MECHANISM_MAP.get(mechanism, {})
        for trait, weight in trait_map.items():
            trait_value = getattr(big_five, trait, 0.5)
            trait_confidence = getattr(big_five, f"{trait}_confidence", 0.5)
            
            if weight > 0:
                contribution = trait_value * weight
            else:
                contribution = (1 - trait_value) * abs(weight)
            
            contributions.append(contribution * trait_confidence)
            weights.append(abs(weight))
        
        # Linguistic feature contribution
        ling_map = self.LINGUISTIC_MECHANISM_MAP.get(mechanism, {})
        for feature, weight in ling_map.items():
            feature_value = getattr(features, feature, 0.0)
            contributions.append(feature_value * weight)
            weights.append(abs(weight))
        
        if not contributions:
            return 0.5, 0.3
        
        susceptibility = np.sum(contributions) / np.sum(weights)
        susceptibility = max(0.1, min(0.9, 0.5 + susceptibility))
        
        confidence = min(0.85, 0.4 + 0.05 * len(contributions))
        
        return susceptibility, confidence
```

---

# PART 5: ARCHETYPE CLUSTERING

## 5.1 Building Psychological Archetypes

```python
# =============================================================================
# ARCHETYPE CLUSTERING FROM AMAZON REVIEWERS
# =============================================================================

from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import numpy as np
from typing import List, Dict, Any
from dataclasses import dataclass


@dataclass
class AmazonArchetype:
    """
    Psychological archetype derived from Amazon reviewer clustering.
    
    Used by Cold Start to initialize new users.
    """
    archetype_id: str
    name: str
    description: str
    
    # Psychological centroid
    big_five_centroid: Dict[str, float]
    regulatory_focus: str
    construal_level: str
    
    # Mechanism priors
    mechanism_priors: Dict[str, float]
    
    # Behavioral patterns
    typical_categories: List[str]
    avg_rating_given: float
    review_length_tendency: str  # "short", "medium", "long"
    
    # Matching signals
    linguistic_signature: Dict[str, float]
    
    # Statistics
    cluster_size: int
    cohesion_score: float


class ArchetypeClusteringService:
    """
    Cluster Amazon reviewers into psychological archetypes.
    
    These archetypes become the initialization priors for Cold Start (#13).
    """
    
    def __init__(
        self,
        neo4j_driver: AsyncDriver,
        n_clusters: int = 12,  # ~12 primary archetypes
        min_reviews_per_reviewer: int = 5
    ):
        self.neo4j = neo4j_driver
        self.n_clusters = n_clusters
        self.min_reviews = min_reviews_per_reviewer
    
    async def build_archetypes(self) -> List[AmazonArchetype]:
        """
        Build archetypes from all reviewers with sufficient data.
        """
        # Get reviewer profiles
        profiles = await self._get_reviewer_profiles()
        
        # Create feature matrix
        feature_matrix, reviewer_ids = self._build_feature_matrix(profiles)
        
        # Cluster
        clusters = self._cluster_reviewers(feature_matrix)
        
        # Build archetype definitions
        archetypes = self._build_archetype_definitions(
            clusters, feature_matrix, reviewer_ids, profiles
        )
        
        # Store archetypes
        await self._store_archetypes(archetypes)
        
        return archetypes
    
    async def _get_reviewer_profiles(self) -> List[Dict[str, Any]]:
        """Get all reviewer profiles with Big Five and features."""
        query = """
        MATCH (r:AmazonReviewer)
        WHERE r.review_count >= $min_reviews
          AND r.big_five IS NOT NULL
        RETURN r {
            .reviewer_id,
            .big_five,
            .linguistic_features,
            .mechanism_priors,
            .categories_reviewed,
            .avg_rating,
            .avg_review_length
        } as profile
        """
        async with self.neo4j.session() as session:
            result = await session.run(query, min_reviews=self.min_reviews)
            return [record["profile"] async for record in result]
    
    def _build_feature_matrix(
        self,
        profiles: List[Dict]
    ) -> tuple[np.ndarray, List[str]]:
        """Build feature matrix for clustering."""
        features = []
        reviewer_ids = []
        
        for profile in profiles:
            big_five = profile.get("big_five", {})
            ling = profile.get("linguistic_features", {})
            
            feature_vector = [
                big_five.get("openness", 0.5),
                big_five.get("conscientiousness", 0.5),
                big_five.get("extraversion", 0.5),
                big_five.get("agreeableness", 0.5),
                big_five.get("neuroticism", 0.5),
                ling.get("self_reference_rate", 0.0),
                ling.get("analytical_marker_rate", 0.0),
                ling.get("emotional_intensity", 0.0),
                ling.get("vocabulary_richness", 0.0),
                profile.get("avg_rating", 3.0) / 5.0,
            ]
            
            features.append(feature_vector)
            reviewer_ids.append(profile["reviewer_id"])
        
        return np.array(features), reviewer_ids
    
    def _cluster_reviewers(self, features: np.ndarray) -> np.ndarray:
        """Perform K-means clustering."""
        scaler = StandardScaler()
        scaled_features = scaler.fit_transform(features)
        
        kmeans = KMeans(
            n_clusters=self.n_clusters,
            random_state=42,
            n_init=10
        )
        
        return kmeans.fit_predict(scaled_features)
    
    def _build_archetype_definitions(
        self,
        clusters: np.ndarray,
        features: np.ndarray,
        reviewer_ids: List[str],
        profiles: List[Dict]
    ) -> List[AmazonArchetype]:
        """Build archetype definitions from clusters."""
        
        archetypes = []
        
        for cluster_id in range(self.n_clusters):
            mask = clusters == cluster_id
            cluster_features = features[mask]
            cluster_profiles = [p for i, p in enumerate(profiles) if mask[i]]
            
            if len(cluster_profiles) < 10:
                continue
            
            # Calculate centroid
            centroid = cluster_features.mean(axis=0)
            
            # Determine characteristics
            big_five_centroid = {
                "openness": float(centroid[0]),
                "conscientiousness": float(centroid[1]),
                "extraversion": float(centroid[2]),
                "agreeableness": float(centroid[3]),
                "neuroticism": float(centroid[4])
            }
            
            # Determine regulatory focus
            if centroid[0] > 0.6 and centroid[2] > 0.5:  # High O, high E
                regulatory_focus = "promotion"
            elif centroid[1] > 0.6 and centroid[4] > 0.5:  # High C, high N
                regulatory_focus = "prevention"
            else:
                regulatory_focus = "mixed"
            
            # Name the archetype
            archetype_name = self._generate_archetype_name(big_five_centroid)
            
            archetype = AmazonArchetype(
                archetype_id=f"amazon_archetype_{cluster_id}",
                name=archetype_name,
                description=self._generate_description(big_five_centroid),
                big_five_centroid=big_five_centroid,
                regulatory_focus=regulatory_focus,
                construal_level="abstract" if centroid[0] > 0.6 else "concrete",
                mechanism_priors=self._derive_mechanism_priors(big_five_centroid),
                typical_categories=self._find_typical_categories(cluster_profiles),
                avg_rating_given=float(centroid[9] * 5),
                review_length_tendency="long" if centroid[8] > 0.6 else "short",
                linguistic_signature={
                    "self_reference_rate": float(centroid[5]),
                    "analytical_marker_rate": float(centroid[6]),
                    "emotional_intensity": float(centroid[7]),
                    "vocabulary_richness": float(centroid[8])
                },
                cluster_size=int(mask.sum()),
                cohesion_score=self._calculate_cohesion(cluster_features)
            )
            
            archetypes.append(archetype)
        
        return archetypes
    
    def _generate_archetype_name(self, big_five: Dict[str, float]) -> str:
        """Generate human-readable archetype name."""
        
        # Primary trait
        traits = sorted(big_five.items(), key=lambda x: abs(x[1] - 0.5), reverse=True)
        primary_trait, primary_value = traits[0]
        
        trait_labels = {
            "openness": ("Curious Explorer", "Practical Traditionalist"),
            "conscientiousness": ("Meticulous Planner", "Flexible Improviser"),
            "extraversion": ("Social Connector", "Thoughtful Observer"),
            "agreeableness": ("Warm Collaborator", "Direct Challenger"),
            "neuroticism": ("Sensitive Responder", "Calm Analyst")
        }
        
        if primary_value > 0.5:
            return trait_labels[primary_trait][0]
        else:
            return trait_labels[primary_trait][1]
    
    def _derive_mechanism_priors(self, big_five: Dict[str, float]) -> Dict[str, float]:
        """Derive mechanism priors from Big Five centroid."""
        return {
            "loss_aversion": 0.3 + big_five["neuroticism"] * 0.4,
            "social_proof": 0.3 + big_five["extraversion"] * 0.3 + big_five["agreeableness"] * 0.2,
            "scarcity": 0.3 + big_five["neuroticism"] * 0.3,
            "authority": 0.3 + big_five["conscientiousness"] * 0.3,
            "novelty": 0.3 + big_five["openness"] * 0.5,
            "identity_expression": 0.3 + big_five["openness"] * 0.3 + big_five["extraversion"] * 0.2
        }
```

---

# PART 6: NEO4J SCHEMA FOR AMAZON DATA

```cypher
// =============================================================================
// AMAZON DATA NEO4J SCHEMA
// =============================================================================

// Reviewer Node
CREATE CONSTRAINT amazon_reviewer_id IF NOT EXISTS
FOR (r:AmazonReviewer) REQUIRE r.reviewer_id IS UNIQUE;

// Product Node
CREATE CONSTRAINT amazon_product_asin IF NOT EXISTS
FOR (p:AmazonProduct) REQUIRE p.asin IS UNIQUE;

// Archetype Node
CREATE CONSTRAINT amazon_archetype_id IF NOT EXISTS
FOR (a:AmazonArchetype) REQUIRE a.archetype_id IS UNIQUE;

// Indexes
CREATE INDEX amazon_reviewer_big_five IF NOT EXISTS
FOR (r:AmazonReviewer) ON (r.big_five_openness);

CREATE INDEX amazon_product_category IF NOT EXISTS
FOR (p:AmazonProduct) ON (p.adam_category);

// Relationships
// (r:AmazonReviewer)-[:REVIEWED {rating, timestamp}]->(p:AmazonProduct)
// (r:AmazonReviewer)-[:BELONGS_TO_ARCHETYPE {confidence}]->(a:AmazonArchetype)
// (a:AmazonArchetype)-[:HAS_MECHANISM_PRIOR {susceptibility}]->(m:CognitiveMechanism)
// (p:AmazonProduct)-[:IN_CATEGORY]->(c:ProductCategory)
```

---

# PART 7: INTEGRATION WITH ADAM COMPONENTS

## 7.1 Cold Start Integration

```python
# Cold Start uses Amazon archetypes
async def initialize_from_amazon_archetype(
    self,
    archetype_id: str
) -> UserProfile:
    """Initialize user from Amazon archetype."""
    archetype = await self.graph.get_amazon_archetype(archetype_id)
    
    return UserProfile(
        big_five=BigFiveProfile(**archetype.big_five_centroid),
        regulatory_focus=RegulatoryFocusState(
            promotion_strength=0.6 if archetype.regulatory_focus == "promotion" else 0.4,
            prevention_strength=0.6 if archetype.regulatory_focus == "prevention" else 0.4
        ),
        mechanism_receptivity=archetype.mechanism_priors,
        profile_source="amazon_archetype",
        profile_confidence=0.5  # Moderate confidence for archetype-based
    )
```

## 7.2 WPP Ad Desk Integration

The WPP spec already references `AmazonCorpusClient` - this specification provides that implementation:

```python
# The AmazonCorpusClient referenced in WPP Enhancement #28
class AmazonCorpusClient:
    """Client for accessing Amazon review data."""
    
    def __init__(self, neo4j_driver: AsyncDriver):
        self.neo4j = neo4j_driver
    
    async def get_reviews_by_product_name(
        self,
        product_name: str,
        limit: int = 100
    ) -> List[Dict]:
        """Get reviews matching product name."""
        # Implementation using Neo4j
        pass
    
    async def get_reviews_by_category(
        self,
        category: str,
        price_tier: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """Get reviews in category."""
        pass
    
    async def get_reviewer_profile(
        self,
        reviewer_id: str
    ) -> Optional[ReviewerProfile]:
        """Get aggregated reviewer profile."""
        pass
```

## 7.3 iHeart Integration

Amazon priors provide the foundational personality models that iHeart listening refines:

```
Amazon Data → Archetypes → Cold Start Initialization
                              ↓
iHeart Listening → Refinement → Personalized Profile
```

---

# PART 8: IMPLEMENTATION TIMELINE

| Phase | Duration | Deliverables |
|-------|----------|--------------|
| **Phase 1: Data Ingestion** | 2 weeks | Raw data loading, validation, Neo4j storage |
| **Phase 2: Feature Extraction** | 2 weeks | Linguistic features, Big Five inference |
| **Phase 3: Archetype Clustering** | 1 week | K-means clustering, archetype definitions |
| **Phase 4: Integration** | 2 weeks | Cold Start, WPP, iHeart connections |
| **Phase 5: Validation** | 1 week | Cross-validation, accuracy testing |

---

# PART 9: SUCCESS METRICS

| Metric | Target | Measurement |
|--------|--------|-------------|
| Reviews Processed | 1.2B+ | Count |
| Reviewer Profiles Built | 100M+ | Count |
| Archetype Coverage | >90% of new users matchable | Cold Start hit rate |
| Big Five Inference Accuracy | >70% correlation with surveys | Validation study |
| Mechanism Prior Accuracy | >60% prediction of response | A/B testing |

---

**END OF AMAZON DATASET PROCESSING SPECIFICATION**
