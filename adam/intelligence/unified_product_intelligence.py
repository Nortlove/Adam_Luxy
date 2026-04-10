#!/usr/bin/env python3
"""
UNIFIED PRODUCT INTELLIGENCE
============================

The complete intelligence picture from Amazon data by properly linking:

1. **Brand Copy** (meta_*.jsonl via ASIN):
   - Product title (headline persuasion)
   - Bullet features (key selling points)
   - Description (full brand narrative)
   - Images (visual persuasion - referenced)
   = THE BRAND'S "ADVERTISEMENT"

2. **Customer Reviews** (*.jsonl via ASIN):
   - Review text (customer voice)
   - Rating (satisfaction signal)
   - Helpful votes (influence validation)
   - Verified purchase (authenticity signal)
   = CUSTOMER RESPONSE TO THE "AD"

3. **Purchase Validation**:
   When someone buys, they've been persuaded by BOTH:
   - The brand's copy
   - Other customer reviews
   
4. **Helpful Vote Meta-Validation**:
   When someone marks a review helpful, they're saying:
   "This review influenced MY decision to buy/not buy"
   = PROOF THAT PERSUASIVE LANGUAGE WORKED

The ASIN links all these together into a complete persuasion picture.

This module:
- Loads and joins meta + reviews via ASIN
- Extracts brand persuasion intent from copy
- Extracts customer persuasion patterns from reviews
- Computes brand-customer alignment
- Identifies what language actually converted customers
"""

import gzip
import json
import logging
import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURATION
# =============================================================================

AMAZON_DATA_DIR = Path("/Volumes/Sped/Nocera Models/Review Data/Amazon")


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class BrandCopy:
    """
    The brand's persuasion attempt from product metadata.
    
    Amazon Product Metadata Schema:
    - main_category (str): Domain of the product
    - title (str): Product name - PRIMARY HEADLINE
    - features (list): Bullet-point persuasion - KEY SELLING POINTS
    - description (list): Full narrative persuasion
    - price (float): USD price
    - images (list): Product images (thumb, large, hi_res, variant)
    - videos (list): Promotional videos (title, url)
    - store (str): Store/brand name
    - categories (list): Hierarchical categories
    - details (dict): Rich structured data (materials, brand, sizes)
    - parent_asin (str): LINKING KEY to reviews
    - bought_together (list): Co-purchase bundles - JOURNEY DATA
    - average_rating (float): Overall product rating
    - rating_number (int): Total ratings count
    """
    
    # Identifiers
    asin: str
    parent_asin: str  # THE KEY for linking to reviews
    
    # Brand info
    brand: str  # From 'store' or 'details.brand'
    store: str = ""
    
    # The "Ad Copy" - What brand is TRYING to persuade with
    title: str = ""  # Primary headline
    features: List[str] = field(default_factory=list)  # Bullet points
    description: List[str] = field(default_factory=list)  # Full narrative (now a list per schema)
    
    # Product context
    price: Optional[float] = None
    main_category: str = ""
    categories: List[str] = field(default_factory=list)  # Hierarchical
    
    # Rich structured data
    details: Dict[str, Any] = field(default_factory=dict)  # Materials, sizes, specs
    
    # Media
    images: List[Dict[str, str]] = field(default_factory=list)  # thumb, large, hi_res, variant
    videos: List[Dict[str, str]] = field(default_factory=list)  # title, url
    
    # Social proof from Amazon
    average_rating: float = 0.0
    rating_number: int = 0
    
    # Journey intelligence
    bought_together: List[str] = field(default_factory=list)  # Bundle ASINs - CO-PURCHASE DATA
    
    # Extracted intelligence
    cialdini_scores: Dict[str, float] = field(default_factory=dict)
    aaker_scores: Dict[str, float] = field(default_factory=dict)
    tactics_detected: List[str] = field(default_factory=list)
    primary_personality: str = ""
    
    @property
    def full_copy(self) -> str:
        """Concatenate all brand copy for analysis."""
        parts = [self.title]
        if self.features:
            parts.extend(self.features)
        if self.description:
            # description is a list per schema
            parts.extend(self.description if isinstance(self.description, list) else [self.description])
        return " ".join(parts)
    
    @property
    def has_strong_social_proof(self) -> bool:
        """Check if product has strong Amazon social proof."""
        return self.rating_number >= 100 and self.average_rating >= 4.0
    
    @property
    def has_video(self) -> bool:
        """Check if product has promotional video."""
        return len(self.videos) > 0


@dataclass
class CustomerReview:
    """
    A customer's response to the brand's product.
    
    Amazon Review Schema:
    - rating (float): 1.0 to 5.0
    - title (str): Review title
    - text (str): Review body
    - images (list): User-posted images (small, medium, large URLs) - VALIDATION PHOTOS
    - asin (str): Product ID
    - parent_asin (str): Parent ID - LINKING KEY (use this!)
    - user_id (str): Reviewer ID
    - timestamp (int): Unix timestamp
    - verified_purchase (bool): Purchase verification - AUTHENTICITY SIGNAL
    - helpful_vote (int): How many found this helpful - META-VALIDATION
    """
    
    # Identifiers
    asin: str
    parent_asin: str = ""  # THE KEY for linking - products with different colors/sizes share this
    user_id: str = ""
    
    # Review content
    rating: float = 0.0  # 1.0 to 5.0
    title: str = ""  # Review headline
    text: str = ""  # Review body - THE CUSTOMER'S VOICE
    
    # User-posted images - Strong social proof (they actually used it)
    images: List[Dict[str, str]] = field(default_factory=list)  # small_image_url, medium_image_url, large_image_url
    
    # Validation signals
    helpful_vote: int = 0  # META-VALIDATION - others found this influential
    verified_purchase: bool = False  # AUTHENTICITY - they actually bought it
    timestamp: Optional[int] = None  # When reviewed (for temporal analysis)
    
    # Extracted intelligence
    mechanisms_detected: List[str] = field(default_factory=list)
    sentiment: float = 0.0  # -1 to 1
    persuasion_effectiveness: float = 0.0  # How influential (based on helpful votes)
    
    @property
    def has_images(self) -> bool:
        """Check if reviewer posted images - strong validation."""
        return len(self.images) > 0
    
    @property
    def is_high_influence(self) -> bool:
        """Check if this is a high-influence review."""
        return self.helpful_vote >= 10 and self.verified_purchase
    
    @property
    def influence_tier(self) -> str:
        """Classify influence tier."""
        votes = self.helpful_vote
        if votes >= 200:
            return "viral"
        elif votes >= 51:
            return "very_high"
        elif votes >= 11:
            return "high"
        elif votes >= 3:
            return "moderate"
        else:
            return "low"


@dataclass 
class PersuasionAlignment:
    """
    Alignment between brand intent and customer response.
    
    The key insight: When brand intent aligns with what customers 
    respond to, conversion is higher.
    """
    
    parent_asin: str
    
    # Brand's persuasion strategy (from meta)
    brand_personality: str  # Aaker dimension
    brand_cialdini_emphasis: List[str]  # What principles brand is using in copy
    brand_features_count: int = 0  # How many bullet points
    brand_has_video: bool = False  # Video = higher investment
    
    # Customer response patterns (from reviews)
    customer_archetype_match: Dict[str, float] = field(default_factory=dict)  # Which archetypes respond
    effective_mechanisms: List[str] = field(default_factory=list)  # What actually persuaded (high-vote)
    
    # Validation signals
    verified_purchase_rate: float = 0.0  # What % verified - authenticity
    reviews_with_images_rate: float = 0.0  # What % posted photos - validation
    
    # Alignment metrics
    intent_response_alignment: float = 0.0  # Brand intent matches customer response
    conversion_language_patterns: List[str] = field(default_factory=list)  # Language that converted
    
    # Co-purchase intelligence (from bought_together)
    co_purchase_patterns: List[str] = field(default_factory=list)  # What else they buy
    
    # Strength metrics
    brand_copy_strength: float = 0.0  # How persuasive is the brand copy
    social_proof_strength: float = 0.0  # How persuasive are the reviews
    combined_conversion_power: float = 0.0  # Overall persuasion effectiveness
    
    @property
    def is_well_aligned(self) -> bool:
        """Check if brand and customer are well aligned."""
        return self.intent_response_alignment >= 0.6


@dataclass
class UnifiedProductIntelligence:
    """
    Complete intelligence for a product (brand + customers).
    
    Links brand copy (from meta) with customer reviews via parent_asin.
    """
    
    # Identifier - use parent_asin as the key
    parent_asin: str
    
    # The two halves of persuasion
    brand_copy: BrandCopy  # What brand is TRYING
    reviews: List[CustomerReview] = field(default_factory=list)  # How customers RESPONDED
    
    # Alignment analysis
    alignment: Optional[PersuasionAlignment] = None
    
    # Aggregated review metrics
    total_reviews: int = 0
    avg_rating: float = 0.0
    total_helpful_votes: int = 0
    verified_purchase_rate: float = 0.0
    
    # Validation signal counts
    reviews_with_images: int = 0  # Users who posted photos
    viral_reviews: int = 0        # 200+ helpful votes
    very_high_influence: int = 0  # 51-200 helpful votes
    high_influence: int = 0       # 11-50 helpful votes
    
    # High-influence reviews (the proven persuaders)
    high_influence_reviews: List[CustomerReview] = field(default_factory=list)
    
    # Journey intelligence from bought_together
    co_purchase_asins: List[str] = field(default_factory=list)
    
    def compute_metrics(self):
        """Compute aggregated metrics from reviews."""
        if not self.reviews:
            return
        
        self.total_reviews = len(self.reviews)
        self.avg_rating = sum(r.rating for r in self.reviews) / len(self.reviews)
        self.total_helpful_votes = sum(r.helpful_vote for r in self.reviews)
        self.verified_purchase_rate = sum(
            1 for r in self.reviews if r.verified_purchase
        ) / len(self.reviews)
        
        # Count validation signals
        self.reviews_with_images = sum(1 for r in self.reviews if r.has_images)
        
        # Count by influence tier
        for r in self.reviews:
            tier = r.influence_tier
            if tier == "viral":
                self.viral_reviews += 1
            elif tier == "very_high":
                self.very_high_influence += 1
            elif tier == "high":
                self.high_influence += 1
        
        # Identify high-influence reviews (the proven persuaders)
        sorted_reviews = sorted(
            self.reviews, 
            key=lambda r: r.helpful_vote, 
            reverse=True
        )
        self.high_influence_reviews = [
            r for r in sorted_reviews[:50] if r.helpful_vote >= 3
        ]
        
        # Journey intelligence from bought_together
        if self.brand_copy.bought_together:
            self.co_purchase_asins = self.brand_copy.bought_together
    
    @property
    def total_social_proof_signals(self) -> int:
        """Total validation signals (votes + images + verified)."""
        return (
            self.total_helpful_votes + 
            self.reviews_with_images * 5 +  # Images worth more
            int(self.verified_purchase_rate * self.total_reviews * 2)
        )
    
    @property
    def influence_distribution(self) -> Dict[str, int]:
        """Distribution of reviews by influence tier."""
        return {
            "viral": self.viral_reviews,
            "very_high": self.very_high_influence,
            "high": self.high_influence,
            "moderate_low": self.total_reviews - self.viral_reviews - self.very_high_influence - self.high_influence,
        }


# =============================================================================
# UNIFIED PRODUCT ANALYZER
# =============================================================================

class UnifiedProductAnalyzer:
    """
    Analyzes products by joining brand copy + customer reviews via ASIN.
    
    The key insight: ASIN is the relational key that links:
    - What the brand is TRYING (meta_*.jsonl)
    - How customers RESPONDED (*.jsonl)
    - Whether it WORKED (purchase + rating)
    - Whether it INFLUENCED OTHERS (helpful votes)
    """
    
    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or AMAZON_DATA_DIR
        self._meta_cache: Dict[str, Dict[str, Any]] = {}  # category -> {asin -> metadata}
        
        # Cialdini patterns
        self._cialdini_patterns = self._compile_cialdini_patterns()
        
        # Aaker patterns
        self._aaker_patterns = self._compile_aaker_patterns()
    
    def get_unified_intelligence(
        self,
        brand: str,
        product_name: str,
        category: str,
        max_reviews: int = 1000,
    ) -> Optional[UnifiedProductIntelligence]:
        """
        Get complete intelligence for a product.
        
        IMPORTANT: Uses parent_asin as the linking key!
        Products with different colors/sizes share the same parent_asin.
        
        Flow:
        1. Search meta for matching products → get parent_asin
        2. Load brand copy from meta (the "ad")
        3. Load reviews via parent_asin (customer responses)
        4. Analyze both and compute alignment
        """
        logger.info(f"Getting unified intelligence: {brand} - {product_name}")
        
        # Step 1: Find matching products in metadata
        products = self._search_metadata(category, brand, product_name)
        
        if not products:
            logger.warning(f"No products found for {brand} - {product_name}")
            return None
        
        # Use best match
        best_match = products[0]
        
        # Step 2: Build BrandCopy from metadata
        brand_copy = self._build_brand_copy(best_match)
        
        # Use parent_asin as THE KEY for linking
        parent_asin = brand_copy.parent_asin
        logger.info(f"Using parent_asin: {parent_asin} for review linking")
        
        # Step 3: Analyze brand copy (the brand's persuasion attempt)
        self._analyze_brand_copy(brand_copy)
        
        # Step 4: Load reviews using parent_asin
        reviews = self._load_reviews_for_asin(category, parent_asin, max_reviews)
        logger.info(f"Loaded {len(reviews)} reviews for parent_asin {parent_asin}")
        
        # Step 5: Analyze reviews (customer responses)
        for review in reviews:
            self._analyze_review(review)
        
        # Step 6: Build unified intelligence
        intelligence = UnifiedProductIntelligence(
            parent_asin=parent_asin,
            brand_copy=brand_copy,
            reviews=reviews,
        )
        intelligence.compute_metrics()
        
        # Step 7: Compute alignment (brand intent vs customer response)
        intelligence.alignment = self._compute_alignment(brand_copy, reviews)
        
        logger.info(
            f"Unified intelligence complete: {intelligence.total_reviews} reviews, "
            f"{intelligence.total_helpful_votes} helpful votes, "
            f"{intelligence.viral_reviews} viral reviews"
        )
        
        return intelligence
    
    def stream_asin_pairs(
        self,
        category: str,
        batch_size: int = 1000,
    ) -> Iterator[Tuple[Dict[str, Any], List[Dict[str, Any]]]]:
        """
        Stream ASIN-linked pairs of (metadata, reviews).
        
        Efficiently processes large datasets by:
        1. Loading metadata index
        2. Streaming reviews
        3. Yielding when we have reviews for an ASIN
        
        Yields:
            Tuple of (product_metadata, [reviews])
        """
        # Load all metadata for category
        metadata = self._load_metadata(category)
        
        # Collect reviews by ASIN
        reviews_by_asin: Dict[str, List[Dict]] = defaultdict(list)
        
        # Stream reviews
        review_path = self.data_dir / f"{category}.jsonl"
        if not review_path.exists():
            review_path = self.data_dir / f"{category}.jsonl.gz"
        
        if not review_path.exists():
            logger.error(f"Review file not found: {review_path}")
            return
        
        opener = gzip.open if review_path.suffix == '.gz' else open
        
        with opener(review_path, 'rt', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                try:
                    review = json.loads(line)
                    asin = review.get("parent_asin") or review.get("asin")
                    
                    if asin and asin in metadata:
                        reviews_by_asin[asin].append(review)
                        
                        # Yield batch when we have enough
                        if len(reviews_by_asin[asin]) >= batch_size:
                            yield metadata[asin], reviews_by_asin.pop(asin)
                
                except json.JSONDecodeError:
                    continue
                
                if line_num % 1000000 == 0:
                    logger.info(f"Processed {line_num:,} reviews")
        
        # Yield remaining
        for asin, reviews in reviews_by_asin.items():
            if reviews and asin in metadata:
                yield metadata[asin], reviews
    
    # =========================================================================
    # METADATA OPERATIONS
    # =========================================================================
    
    def _search_metadata(
        self,
        category: str,
        brand: str,
        product_name: str,
    ) -> List[Dict[str, Any]]:
        """Search metadata for matching products."""
        metadata = self._load_metadata(category)
        brand_lower = brand.lower()
        
        # Extract keywords
        keywords = self._extract_keywords(product_name)
        
        matches = []
        for asin, info in metadata.items():
            product_brand = (info.get("brand") or info.get("store") or "").lower()
            product_title = (info.get("title") or "").lower()
            
            # Check brand match
            if brand_lower not in product_brand and brand_lower not in product_title:
                continue
            
            # Score keyword match
            keyword_matches = sum(1 for kw in keywords if kw in product_title)
            score = keyword_matches / len(keywords) if keywords else 0.5
            
            matches.append({
                **info,
                "asin": asin,
                "match_score": score,
            })
        
        # Sort by match score
        matches.sort(key=lambda m: m["match_score"], reverse=True)
        return matches[:100]
    
    def _load_metadata(self, category: str) -> Dict[str, Dict]:
        """Load metadata file into ASIN-indexed dict."""
        if category in self._meta_cache:
            return self._meta_cache[category]
        
        metadata = {}
        meta_path = self.data_dir / f"meta_{category}.jsonl"
        
        if not meta_path.exists():
            meta_path = self.data_dir / f"meta_{category}.jsonl.gz"
        
        if not meta_path.exists():
            logger.error(f"Metadata file not found: {meta_path}")
            return metadata
        
        logger.info(f"Loading metadata from {meta_path}")
        opener = gzip.open if meta_path.suffix == '.gz' else open
        
        with opener(meta_path, 'rt', encoding='utf-8') as f:
            for line in f:
                try:
                    item = json.loads(line)
                    asin = item.get("parent_asin") or item.get("asin")
                    if asin:
                        metadata[asin] = item
                except json.JSONDecodeError:
                    continue
        
        logger.info(f"Loaded {len(metadata):,} products")
        self._meta_cache[category] = metadata
        return metadata
    
    def _build_brand_copy(self, meta: Dict[str, Any]) -> BrandCopy:
        """
        Build BrandCopy from metadata.
        
        Uses the full Amazon metadata schema:
        - parent_asin: THE LINKING KEY
        - title: Primary headline
        - features: Bullet-point persuasion
        - description: Full narrative (list)
        - details: Rich structured data
        - bought_together: Co-purchase journey data
        """
        # Parse price
        price = None
        if meta.get("price"):
            try:
                price_str = str(meta["price"]).replace("$", "").replace(",", "")
                price = float(price_str.split("-")[0].strip())
            except (ValueError, TypeError):
                pass
        
        # Get brand from multiple possible sources
        brand = (
            meta.get("store") or 
            meta.get("details", {}).get("brand") or 
            meta.get("details", {}).get("Brand") or
            ""
        )
        
        # Handle description - can be string or list
        description = meta.get("description", [])
        if isinstance(description, str):
            description = [description] if description else []
        
        return BrandCopy(
            # Identifiers - parent_asin is THE KEY
            asin=meta.get("asin", ""),
            parent_asin=meta.get("parent_asin") or meta.get("asin", ""),
            
            # Brand info
            brand=brand,
            store=meta.get("store", ""),
            
            # The "Ad Copy" 
            title=meta.get("title", ""),
            features=meta.get("features", []) or [],
            description=description,
            
            # Product context
            price=price,
            main_category=meta.get("main_category", ""),
            categories=meta.get("categories", []) or [],
            
            # Rich structured data
            details=meta.get("details", {}) or {},
            
            # Media
            images=meta.get("images", []) or [],
            videos=meta.get("videos", []) or [],
            
            # Social proof from Amazon
            average_rating=meta.get("average_rating", 0.0) or 0.0,
            rating_number=meta.get("rating_number", 0) or 0,
            
            # Journey intelligence - CO-PURCHASE DATA
            bought_together=meta.get("bought_together", []) or [],
        )
    
    # =========================================================================
    # REVIEW OPERATIONS  
    # =========================================================================
    
    def _load_reviews_for_asin(
        self,
        category: str,
        parent_asin: str,
        max_reviews: int,
    ) -> List[CustomerReview]:
        """
        Load reviews for a specific parent_asin.
        
        IMPORTANT: Use parent_asin for linking!
        Products with different colors/sizes share the same parent_asin.
        
        Full review schema:
        - rating (float): 1.0 to 5.0
        - title (str): Review title
        - text (str): Review body
        - images (list): User-posted images (validation photos)
        - asin (str): Product variant ID
        - parent_asin (str): LINKING KEY
        - user_id (str): Reviewer ID
        - timestamp (int): Unix time
        - verified_purchase (bool): Authenticity signal
        - helpful_vote (int): Meta-validation
        """
        reviews = []
        
        review_path = self.data_dir / f"{category}.jsonl"
        if not review_path.exists():
            review_path = self.data_dir / f"{category}.jsonl.gz"
        
        if not review_path.exists():
            return reviews
        
        opener = gzip.open if review_path.suffix == '.gz' else open
        
        with opener(review_path, 'rt', encoding='utf-8') as f:
            for line in f:
                try:
                    data = json.loads(line)
                    
                    # Use parent_asin as the primary linking key
                    review_parent_asin = data.get("parent_asin", "")
                    
                    if review_parent_asin == parent_asin:
                        reviews.append(CustomerReview(
                            # Identifiers
                            asin=data.get("asin", ""),
                            parent_asin=review_parent_asin,
                            user_id=data.get("user_id", ""),
                            
                            # Content
                            rating=data.get("rating", 0.0),
                            title=data.get("title", ""),
                            text=data.get("text", ""),
                            
                            # User-posted images - strong validation
                            images=data.get("images", []) or [],
                            
                            # Validation signals
                            helpful_vote=data.get("helpful_vote", 0),
                            verified_purchase=data.get("verified_purchase", False),
                            timestamp=data.get("timestamp"),
                        ))
                        
                        if len(reviews) >= max_reviews:
                            break
                
                except json.JSONDecodeError:
                    continue
        
        return reviews
    
    # =========================================================================
    # ANALYSIS
    # =========================================================================
    
    def _analyze_brand_copy(self, brand_copy: BrandCopy) -> None:
        """Analyze brand copy for persuasion patterns."""
        text = brand_copy.full_copy.lower()
        
        # Cialdini scores
        for principle, patterns in self._cialdini_patterns.items():
            matches = sum(1 for p in patterns if p.search(text))
            brand_copy.cialdini_scores[principle] = min(1.0, matches * 0.25)
        
        # Aaker personality scores
        for dimension, patterns in self._aaker_patterns.items():
            matches = sum(1 for p in patterns if p.search(text))
            brand_copy.aaker_scores[dimension] = min(1.0, matches * 0.2)
        
        # Determine primary personality
        if brand_copy.aaker_scores:
            brand_copy.primary_personality = max(
                brand_copy.aaker_scores.items(),
                key=lambda x: x[1]
            )[0]
        
        # Track tactics detected
        brand_copy.tactics_detected = [
            k for k, v in brand_copy.cialdini_scores.items() if v > 0.25
        ]
    
    def _analyze_review(self, review: CustomerReview) -> None:
        """Analyze review for persuasion patterns."""
        text = review.text.lower()
        
        # Detect mechanisms from our helpful_vote_intelligence patterns
        mechanisms = []
        
        # Social proof
        if re.search(r"(recommend|everyone|husband|wife|family|friends)", text):
            mechanisms.append("social_proof")
        
        # Authority
        if re.search(r"(professional|expert|years|experience|tested)", text):
            mechanisms.append("authority")
        
        # Scarcity/urgency
        if re.search(r"(grab|hurry|before|limited|wish.*sooner)", text):
            mechanisms.append("scarcity")
        
        # Commitment
        if re.search(r"(use|using|every|daily|always|will always)", text):
            mechanisms.append("commitment")
        
        # Liking
        if re.search(r"(love|adore|obsessed|game.?changer|holy grail)", text):
            mechanisms.append("liking")
        
        review.mechanisms_detected = mechanisms
        
        # Compute persuasion effectiveness based on helpful votes
        # Log scale: 0 votes = 0, 10 votes = 0.5, 100 votes = 0.75, 1000 votes = 1.0
        import math
        review.persuasion_effectiveness = min(
            1.0,
            math.log10(review.helpful_vote + 1) / 3
        ) if review.helpful_vote > 0 else 0.0
    
    def _compute_alignment(
        self,
        brand_copy: BrandCopy,
        reviews: List[CustomerReview],
    ) -> PersuasionAlignment:
        """
        Compute alignment between brand intent and customer response.
        
        Analyzes:
        - What brand is TRYING (from meta)
        - What actually WORKS (from high-helpful-vote reviews)
        - How well they ALIGN
        """
        
        # What principles is brand emphasizing in their copy?
        brand_emphasis = [
            k for k, v in sorted(
                brand_copy.cialdini_scores.items(),
                key=lambda x: x[1],
                reverse=True
            )[:3]
            if v > 0.2
        ]
        
        # What mechanisms are actually working? (from high-vote reviews = PROOF it worked)
        high_vote_reviews = [r for r in reviews if r.helpful_vote >= 10]
        mechanism_counts = defaultdict(int)
        for review in high_vote_reviews:
            for mech in review.mechanisms_detected:
                mechanism_counts[mech] += 1
        
        effective_mechanisms = [
            m for m, c in sorted(
                mechanism_counts.items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]
        ]
        
        # Compute intent-response alignment
        if brand_emphasis and effective_mechanisms:
            overlap = len(set(brand_emphasis) & set(effective_mechanisms))
            alignment = overlap / max(len(brand_emphasis), len(effective_mechanisms))
        else:
            alignment = 0.5
        
        # Extract conversion language patterns from high-vote reviews
        conversion_patterns = []
        for review in high_vote_reviews[:20]:
            if review.rating >= 4:
                # Extract phrases that appear in influential reviews
                phrases = re.findall(
                    r'(absolutely \w+|highly recommend|best \w+ ever|game ?changer|'
                    r'life.?saver|can\'t live without|must have|worth every|'
                    r'exceeded expectations|better than expected|love this|'
                    r'perfect for|exactly what|would buy again)',
                    review.text.lower()
                )
                conversion_patterns.extend(phrases)
        
        # Compute validation rates
        verified_rate = sum(1 for r in reviews if r.verified_purchase) / max(len(reviews), 1)
        image_rate = sum(1 for r in reviews if r.has_images) / max(len(reviews), 1)
        
        # Compute strengths
        brand_copy_strength = sum(brand_copy.cialdini_scores.values()) / 6
        
        # Social proof strength considers:
        # - High-vote reviews
        # - Total helpful votes
        # - Reviews with images
        # - Verified purchases
        social_proof_strength = min(1.0, (
            len(high_vote_reviews) / max(len(reviews), 1) * 0.4 +
            (sum(r.helpful_vote for r in reviews) / max(len(reviews) * 10, 1)) * 0.3 +
            image_rate * 0.15 +
            verified_rate * 0.15
        )) if reviews else 0
        
        return PersuasionAlignment(
            parent_asin=brand_copy.parent_asin,
            
            # Brand's strategy
            brand_personality=brand_copy.primary_personality,
            brand_cialdini_emphasis=brand_emphasis,
            brand_features_count=len(brand_copy.features),
            brand_has_video=brand_copy.has_video,
            
            # Customer response
            customer_archetype_match={},  # Would need archetype detection
            effective_mechanisms=effective_mechanisms,
            
            # Validation signals
            verified_purchase_rate=verified_rate,
            reviews_with_images_rate=image_rate,
            
            # Alignment
            intent_response_alignment=alignment,
            conversion_language_patterns=list(set(conversion_patterns))[:15],
            
            # Co-purchase (from bought_together)
            co_purchase_patterns=brand_copy.bought_together[:5],
            
            # Strengths
            brand_copy_strength=brand_copy_strength,
            social_proof_strength=social_proof_strength,
            combined_conversion_power=(brand_copy_strength + social_proof_strength) / 2,
        )
    
    # =========================================================================
    # HELPERS
    # =========================================================================
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text."""
        stop_words = {
            "the", "a", "an", "and", "or", "for", "of", "with", "in", "on",
            "to", "by", "is", "are", "was", "were", "size", "color",
        }
        text_clean = re.sub(r'[^\w\s-]', ' ', text.lower())
        return [w for w in text_clean.split() if w not in stop_words and len(w) > 2]
    
    def _compile_cialdini_patterns(self) -> Dict[str, List[re.Pattern]]:
        """Compile Cialdini detection patterns."""
        from adam.intelligence.brand_copy_extractor import CIALDINI_PATTERNS
        return {
            principle: [re.compile(p, re.IGNORECASE) for p in patterns]
            for principle, patterns in CIALDINI_PATTERNS.items()
        }
    
    def _compile_aaker_patterns(self) -> Dict[str, List[re.Pattern]]:
        """Compile Aaker detection patterns."""
        from adam.intelligence.brand_copy_extractor import AAKER_PATTERNS, AakerDimension
        return {
            dim.value: [re.compile(p, re.IGNORECASE) for p in patterns]
            for dim, patterns in AAKER_PATTERNS.items()
        }


# =============================================================================
# SINGLETON
# =============================================================================

_analyzer: Optional[UnifiedProductAnalyzer] = None


def get_unified_product_analyzer() -> UnifiedProductAnalyzer:
    """Get singleton analyzer."""
    global _analyzer
    if _analyzer is None:
        _analyzer = UnifiedProductAnalyzer()
    return _analyzer


# =============================================================================
# TEST
# =============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("=" * 70)
    print("UNIFIED PRODUCT INTELLIGENCE TEST")
    print("Using Amazon Data Schema: parent_asin as linking key")
    print("=" * 70)
    
    analyzer = get_unified_product_analyzer()
    
    intel = analyzer.get_unified_intelligence(
        brand="SOREL",
        product_name="Joan of Arctic Boots",
        category="Clothing_Shoes_and_Jewelry",
        max_reviews=500,
    )
    
    if intel:
        print(f"\n📦 PRODUCT IDENTIFICATION:")
        print(f"   Brand: {intel.brand_copy.brand}")
        print(f"   Title: {intel.brand_copy.title[:60]}...")
        print(f"   parent_asin (LINKING KEY): {intel.parent_asin}")
        print(f"   Main Category: {intel.brand_copy.main_category}")
        print(f"   Price: ${intel.brand_copy.price:.2f}" if intel.brand_copy.price else "   Price: N/A")
        
        print(f"\n🎯 BRAND COPY ANALYSIS (The 'Ad'):")
        print(f"   Title (headline): {intel.brand_copy.title[:80]}...")
        print(f"   Features (bullet points): {len(intel.brand_copy.features)}")
        for i, f in enumerate(intel.brand_copy.features[:3], 1):
            print(f"      {i}. {f[:60]}...")
        print(f"   Description sections: {len(intel.brand_copy.description)}")
        print(f"   Has Video: {intel.brand_copy.has_video}")
        print(f"   Amazon Rating: {intel.brand_copy.average_rating:.1f} ({intel.brand_copy.rating_number:,} ratings)")
        print(f"   Primary Personality: {intel.brand_copy.primary_personality}")
        print(f"   Cialdini Scores: {intel.brand_copy.cialdini_scores}")
        print(f"   Tactics Detected: {intel.brand_copy.tactics_detected}")
        
        print(f"\n👥 CUSTOMER RESPONSE (Reviews linked via parent_asin):")
        print(f"   Total Reviews: {intel.total_reviews:,}")
        print(f"   Avg Rating: {intel.avg_rating:.2f}")
        print(f"   Total Helpful Votes: {intel.total_helpful_votes:,}")
        print(f"   Verified Purchase Rate: {intel.verified_purchase_rate:.1%}")
        print(f"   Reviews with Images: {intel.reviews_with_images}")
        print(f"   Influence Distribution: {intel.influence_distribution}")
        
        print(f"\n⭐ HIGH-INFLUENCE REVIEWS (Proven Persuaders):")
        for i, r in enumerate(intel.high_influence_reviews[:3], 1):
            print(f"   {i}. [{r.influence_tier}] {r.helpful_vote} votes, {r.rating}★ - {r.title[:40]}...")
            print(f"      Mechanisms: {r.mechanisms_detected}")
            print(f"      Has images: {r.has_images}, Verified: {r.verified_purchase}")
        
        if intel.alignment:
            print(f"\n🔗 PERSUASION ALIGNMENT (Intent vs Response):")
            print(f"   Brand Personality: {intel.alignment.brand_personality}")
            print(f"   Brand Emphasis: {intel.alignment.brand_cialdini_emphasis}")
            print(f"   What Actually Works: {intel.alignment.effective_mechanisms}")
            print(f"   Alignment Score: {intel.alignment.intent_response_alignment:.2f}")
            print(f"   Well Aligned: {intel.alignment.is_well_aligned}")
            print(f"   Conversion Language: {intel.alignment.conversion_language_patterns[:5]}")
            print(f"   Brand Copy Strength: {intel.alignment.brand_copy_strength:.2f}")
            print(f"   Social Proof Strength: {intel.alignment.social_proof_strength:.2f}")
            print(f"   Combined Power: {intel.alignment.combined_conversion_power:.2f}")
        
        if intel.co_purchase_asins:
            print(f"\n🛒 CO-PURCHASE PATTERNS (bought_together):")
            print(f"   Related ASINs: {intel.co_purchase_asins[:5]}")
    else:
        print("No intelligence found")
