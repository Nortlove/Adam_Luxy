#!/usr/bin/env python3
"""
HISTORICAL DATA REPROCESSOR
===========================

Processes the Amazon 2015 review dataset (and other historical data) through
the alignment system to:

1. Pre-compute psychological profiles for all products
2. Extract validated customer-product alignment patterns
3. Create ground truth data for model validation
4. Discover patterns invisible to manual analysis

Staged Processing Approach:
- Stage 1: Category sampling (representative patterns per category)
- Stage 2: High-signal data (reviews with clear conversion signals)
- Stage 3: Full reprocessing (all billion+ records)

Design for Scale:
- Batch processing with checkpointing
- Memory-efficient streaming
- Parallel processing support
- Incremental updates

Expected Benefits:
- Every product gets a pre-computed psychological fingerprint
- O(1) lookup for "best customer for this product" queries
- Empirical validation of alignment matrices
- Self-correcting system that learns from scale
"""

import json
import gzip
import os
from dataclasses import dataclass, field
from typing import Any, Dict, Generator, List, Optional, Tuple, Iterator
from datetime import datetime
from pathlib import Path
import hashlib
import time


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class ReviewRecord:
    """Normalized review record from any source."""
    
    review_id: str
    product_id: str
    user_id: Optional[str]
    review_text: str
    rating: float  # Normalized to 1-5
    helpful_votes: int = 0
    total_votes: int = 0
    verified_purchase: bool = False
    timestamp: Optional[str] = None
    category: Optional[str] = None
    source: str = "unknown"
    
    @property
    def helpfulness_ratio(self) -> float:
        if self.total_votes == 0:
            return 0.5
        return self.helpful_votes / self.total_votes
    
    @property
    def signal_strength(self) -> float:
        """Calculate how strong a signal this review provides."""
        
        # Extreme ratings are stronger signals
        rating_signal = abs(self.rating - 3) / 2  # 0-1, higher for 1 or 5
        
        # More votes = more confidence
        vote_signal = min(1.0, self.total_votes / 100)
        
        # Verified purchases are stronger
        verified_signal = 1.0 if self.verified_purchase else 0.7
        
        # Longer reviews often have more signal
        length_signal = min(1.0, len(self.review_text) / 500)
        
        return (rating_signal * 0.3 + vote_signal * 0.3 + 
                verified_signal * 0.2 + length_signal * 0.2)


@dataclass
class ProductProfile:
    """Pre-computed psychological profile for a product."""
    
    product_id: str
    category: str
    
    # Advertisement psychology dimensions
    persuasion_techniques: Dict[str, float] = field(default_factory=dict)
    emotional_appeals: Dict[str, float] = field(default_factory=dict)
    value_propositions: Dict[str, float] = field(default_factory=dict)
    brand_personality: Dict[str, float] = field(default_factory=dict)
    linguistic_style: Dict[str, float] = field(default_factory=dict)
    
    # Primary characteristics
    primary_persuasion: Optional[str] = None
    primary_emotion: Optional[str] = None
    primary_value: Optional[str] = None
    
    # Target customer segments
    target_motivations: List[str] = field(default_factory=list)
    target_decision_styles: List[str] = field(default_factory=list)
    optimal_archetypes: List[str] = field(default_factory=list)
    
    # Mechanism effectiveness (learned from reviews)
    mechanism_effectiveness: Dict[str, float] = field(default_factory=dict)
    
    # Statistics
    review_count: int = 0
    avg_rating: float = 0.0
    rating_variance: float = 0.0
    
    # Metadata
    created_at: str = ""
    updated_at: str = ""
    confidence: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "product_id": self.product_id,
            "category": self.category,
            "persuasion_techniques": self.persuasion_techniques,
            "emotional_appeals": self.emotional_appeals,
            "value_propositions": self.value_propositions,
            "brand_personality": self.brand_personality,
            "linguistic_style": self.linguistic_style,
            "primary_persuasion": self.primary_persuasion,
            "primary_emotion": self.primary_emotion,
            "primary_value": self.primary_value,
            "target_motivations": self.target_motivations,
            "target_decision_styles": self.target_decision_styles,
            "optimal_archetypes": self.optimal_archetypes,
            "mechanism_effectiveness": self.mechanism_effectiveness,
            "review_count": self.review_count,
            "avg_rating": self.avg_rating,
            "rating_variance": self.rating_variance,
            "confidence": self.confidence,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class AlignmentValidation:
    """Validation record comparing predicted vs actual alignment."""
    
    product_id: str
    customer_motivation: str
    customer_decision_style: str
    
    predicted_alignment: float
    predicted_effectiveness: float
    
    actual_rating: float  # Ground truth
    actual_effectiveness: float  # Derived from rating
    
    discrepancy: float
    
    # Useful for analysis
    review_text_sample: str = ""
    category: str = ""
    signal_strength: float = 0.0


@dataclass
class ProcessingCheckpoint:
    """Checkpoint for resumable processing."""
    
    stage: str
    category: str
    last_product_id: str
    processed_count: int
    error_count: int
    timestamp: str
    stats: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# DATA LOADERS
# =============================================================================

class AmazonDataLoader:
    """Load Amazon review data in various formats."""
    
    def __init__(self, data_path: str):
        self.data_path = Path(data_path)
    
    def load_reviews_streaming(
        self,
        category: Optional[str] = None,
        max_records: Optional[int] = None,
    ) -> Generator[ReviewRecord, None, None]:
        """Stream reviews from gzipped JSON files."""
        
        count = 0
        
        for file_path in self._find_review_files(category):
            for review in self._read_file(file_path):
                yield review
                count += 1
                
                if max_records and count >= max_records:
                    return
    
    def load_metadata_streaming(
        self,
        category: Optional[str] = None,
        max_records: Optional[int] = None,
    ) -> Generator[Dict[str, Any], None, None]:
        """Stream product metadata from gzipped JSON files."""
        
        count = 0
        
        for file_path in self._find_metadata_files(category):
            for product in self._read_file(file_path):
                yield product
                count += 1
                
                if max_records and count >= max_records:
                    return
    
    def _find_review_files(self, category: Optional[str]) -> List[Path]:
        """Find review files, optionally filtered by category."""
        
        files = []
        
        # Check for pre-downloaded files
        review_dir = self.data_path / "reviews"
        if review_dir.exists():
            for f in review_dir.glob("*.json.gz"):
                if category is None or category.lower() in f.name.lower():
                    files.append(f)
        
        # Also check root for single files
        for f in self.data_path.glob("reviews_*.json.gz"):
            if category is None or category.lower() in f.name.lower():
                files.append(f)
        
        return sorted(files)
    
    def _find_metadata_files(self, category: Optional[str]) -> List[Path]:
        """Find metadata files."""
        
        files = []
        
        meta_dir = self.data_path / "metadata"
        if meta_dir.exists():
            for f in meta_dir.glob("*.json.gz"):
                if category is None or category.lower() in f.name.lower():
                    files.append(f)
        
        for f in self.data_path.glob("meta_*.json.gz"):
            if category is None or category.lower() in f.name.lower():
                files.append(f)
        
        return sorted(files)
    
    def _read_file(self, file_path: Path) -> Generator[Any, None, None]:
        """Read gzipped JSON line by line."""
        
        try:
            if file_path.suffix == ".gz":
                opener = gzip.open
            else:
                opener = open
            
            with opener(file_path, "rt", encoding="utf-8") as f:
                for line in f:
                    try:
                        data = json.loads(line.strip())
                        
                        # Convert to ReviewRecord if it's a review
                        if "reviewText" in data or "reviewerID" in data:
                            yield self._to_review_record(data, file_path.stem)
                        else:
                            yield data
                    
                    except json.JSONDecodeError:
                        continue
        
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
    
    def _to_review_record(self, data: Dict[str, Any], source: str) -> ReviewRecord:
        """Convert Amazon format to ReviewRecord."""
        
        return ReviewRecord(
            review_id=data.get("reviewerID", "") + "_" + data.get("asin", ""),
            product_id=data.get("asin", ""),
            user_id=data.get("reviewerID"),
            review_text=data.get("reviewText", ""),
            rating=float(data.get("overall", 3)),
            helpful_votes=data.get("helpful", [0, 0])[0] if data.get("helpful") else 0,
            total_votes=data.get("helpful", [0, 0])[1] if data.get("helpful") else 0,
            verified_purchase=data.get("verified", False),
            timestamp=str(data.get("unixReviewTime", "")),
            category=source.replace("reviews_", "").replace("_5", ""),
            source="amazon_2015",
        )


# =============================================================================
# HISTORICAL DATA PROCESSOR
# =============================================================================

class HistoricalDataReprocessor:
    """
    Main processor for historical review data.
    """
    
    def __init__(
        self,
        data_path: str,
        output_path: str,
        checkpoint_path: Optional[str] = None,
    ):
        self.data_loader = AmazonDataLoader(data_path)
        self.output_path = Path(output_path)
        self.checkpoint_path = Path(checkpoint_path) if checkpoint_path else self.output_path / "checkpoints"
        
        # Initialize services
        from .customer_ad_alignment import CustomerAdAlignmentService
        from .advertisement_psychology_framework import create_advertisement_profile
        from .expanded_type_integration import ExpandedTypeIntegrationService
        
        self.alignment_service = CustomerAdAlignmentService()
        self.type_service = ExpandedTypeIntegrationService()
        self.create_ad_profile = create_advertisement_profile
        
        # Create output directories
        self.output_path.mkdir(parents=True, exist_ok=True)
        self.checkpoint_path.mkdir(parents=True, exist_ok=True)
        
        # Statistics
        self.stats = {
            "products_profiled": 0,
            "reviews_processed": 0,
            "alignments_validated": 0,
            "patterns_discovered": 0,
            "errors": 0,
        }
    
    # =========================================================================
    # STAGE 1: Category Sampling
    # =========================================================================
    
    def process_category_sample(
        self,
        category: str,
        sample_size: int = 10000,
    ) -> Dict[str, Any]:
        """
        Process a representative sample from one category.
        
        This creates:
        - Product profiles for sampled products
        - Alignment validation data
        - Category-specific patterns
        """
        
        print(f"\n{'='*70}")
        print(f"STAGE 1: Processing category sample - {category}")
        print(f"{'='*70}")
        
        # Load checkpoint if exists
        checkpoint = self._load_checkpoint(f"stage1_{category}")
        start_count = checkpoint.processed_count if checkpoint else 0
        
        # Collect reviews by product
        product_reviews: Dict[str, List[ReviewRecord]] = {}
        
        print(f"\nLoading reviews (sample size: {sample_size})...")
        
        for review in self.data_loader.load_reviews_streaming(
            category=category,
            max_records=sample_size,
        ):
            if review.product_id not in product_reviews:
                product_reviews[review.product_id] = []
            product_reviews[review.product_id].append(review)
        
        print(f"Loaded {len(product_reviews)} unique products")
        
        # Process each product
        product_profiles = []
        validation_records = []
        
        for i, (product_id, reviews) in enumerate(product_reviews.items()):
            if i < start_count:
                continue
            
            try:
                # Create product profile from review aggregation
                profile = self._create_product_profile(product_id, reviews, category)
                product_profiles.append(profile)
                
                # Validate alignments using reviews as ground truth
                validations = self._validate_alignments(profile, reviews)
                validation_records.extend(validations)
                
                self.stats["products_profiled"] += 1
                self.stats["reviews_processed"] += len(reviews)
                self.stats["alignments_validated"] += len(validations)
                
                if (i + 1) % 100 == 0:
                    print(f"  Processed {i + 1}/{len(product_reviews)} products...")
                    self._save_checkpoint(f"stage1_{category}", {
                        "processed_count": i + 1,
                        "products_profiled": len(product_profiles),
                    })
            
            except Exception as e:
                self.stats["errors"] += 1
                print(f"  Error processing {product_id}: {e}")
        
        # Save results
        results = {
            "category": category,
            "sample_size": sample_size,
            "products_profiled": len(product_profiles),
            "validation_records": len(validation_records),
            "stats": self.stats.copy(),
        }
        
        self._save_product_profiles(product_profiles, f"profiles_{category}.json")
        self._save_validation_data(validation_records, f"validation_{category}.json")
        self._analyze_patterns(validation_records, f"patterns_{category}.json")
        
        print(f"\nStage 1 complete for {category}")
        print(f"  Products profiled: {len(product_profiles)}")
        print(f"  Alignments validated: {len(validation_records)}")
        
        return results
    
    # =========================================================================
    # STAGE 2: High-Signal Data
    # =========================================================================
    
    def process_high_signal_data(
        self,
        min_votes: int = 10,
        min_signal_strength: float = 0.7,
        max_records: int = 100000,
    ) -> Dict[str, Any]:
        """
        Process reviews with strong signals (lots of votes, verified, extreme ratings).
        
        These provide the most reliable ground truth for learning.
        """
        
        print(f"\n{'='*70}")
        print(f"STAGE 2: Processing high-signal data")
        print(f"{'='*70}")
        
        high_signal_reviews = []
        
        print(f"\nScanning for high-signal reviews...")
        
        for review in self.data_loader.load_reviews_streaming(max_records=max_records * 10):
            if (review.total_votes >= min_votes and 
                review.signal_strength >= min_signal_strength):
                high_signal_reviews.append(review)
                
                if len(high_signal_reviews) >= max_records:
                    break
        
        print(f"Found {len(high_signal_reviews)} high-signal reviews")
        
        # Group by product and process
        product_reviews: Dict[str, List[ReviewRecord]] = {}
        
        for review in high_signal_reviews:
            if review.product_id not in product_reviews:
                product_reviews[review.product_id] = []
            product_reviews[review.product_id].append(review)
        
        # Process and validate
        validation_records = []
        
        for product_id, reviews in product_reviews.items():
            try:
                # Use aggregated review text as product description
                profile = self._create_product_profile(product_id, reviews, "high_signal")
                validations = self._validate_alignments(profile, reviews)
                validation_records.extend(validations)
                
                self.stats["products_profiled"] += 1
                self.stats["reviews_processed"] += len(reviews)
                self.stats["alignments_validated"] += len(validations)
            
            except Exception as e:
                self.stats["errors"] += 1
        
        # Save results
        self._save_validation_data(validation_records, "validation_high_signal.json")
        
        # Analyze and report
        analysis = self._analyze_patterns(validation_records, "patterns_high_signal.json")
        
        print(f"\nStage 2 complete")
        print(f"  High-signal reviews: {len(high_signal_reviews)}")
        print(f"  Products analyzed: {len(product_reviews)}")
        print(f"  Patterns discovered: {analysis.get('patterns_count', 0)}")
        
        return {
            "high_signal_reviews": len(high_signal_reviews),
            "products_analyzed": len(product_reviews),
            "validation_records": len(validation_records),
            "stats": self.stats.copy(),
        }
    
    # =========================================================================
    # STAGE 3: Full Reprocessing (Parallel/Distributed)
    # =========================================================================
    
    def generate_batch_jobs(
        self,
        batch_size: int = 10000,
    ) -> List[Dict[str, Any]]:
        """
        Generate batch job specifications for distributed processing.
        
        Each job can be processed independently by a worker.
        """
        
        jobs = []
        
        # Get all categories
        categories = self._discover_categories()
        
        for category in categories:
            # Estimate record count (would need actual counting in production)
            estimated_records = 1000000  # Placeholder
            num_batches = (estimated_records + batch_size - 1) // batch_size
            
            for batch_idx in range(num_batches):
                jobs.append({
                    "job_id": f"{category}_batch_{batch_idx:05d}",
                    "category": category,
                    "batch_idx": batch_idx,
                    "batch_size": batch_size,
                    "skip_records": batch_idx * batch_size,
                })
        
        return jobs
    
    def process_batch(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single batch job.
        
        Designed to be called by distributed workers.
        """
        
        category = job["category"]
        batch_size = job["batch_size"]
        skip_records = job["skip_records"]
        
        # Stream and process
        product_profiles = []
        validation_records = []
        product_reviews: Dict[str, List[ReviewRecord]] = {}
        
        count = 0
        for review in self.data_loader.load_reviews_streaming(category=category):
            if count < skip_records:
                count += 1
                continue
            
            if count >= skip_records + batch_size:
                break
            
            if review.product_id not in product_reviews:
                product_reviews[review.product_id] = []
            product_reviews[review.product_id].append(review)
            count += 1
        
        # Process products
        for product_id, reviews in product_reviews.items():
            try:
                profile = self._create_product_profile(product_id, reviews, category)
                product_profiles.append(profile)
                
                validations = self._validate_alignments(profile, reviews)
                validation_records.extend(validations)
            except Exception:
                pass
        
        return {
            "job_id": job["job_id"],
            "products_profiled": len(product_profiles),
            "validation_records": len(validation_records),
            "profiles": [p.to_dict() for p in product_profiles],
        }
    
    # =========================================================================
    # INTERNAL METHODS
    # =========================================================================
    
    def _create_product_profile(
        self,
        product_id: str,
        reviews: List[ReviewRecord],
        category: str,
    ) -> ProductProfile:
        """Create psychological profile for a product from its reviews."""
        
        # Aggregate review texts for analysis
        # Use positive reviews to understand what the product promises
        positive_texts = [r.review_text for r in reviews if r.rating >= 4]
        all_texts = [r.review_text for r in reviews]
        
        # Create pseudo product description from positive reviews
        product_description = " ".join(positive_texts[:5])
        
        if len(product_description) < 50 and all_texts:
            product_description = " ".join(all_texts[:5])
        
        # Analyze as advertisement
        ad_profile = self.create_ad_profile(product_description, product_id)
        
        # Calculate statistics
        ratings = [r.rating for r in reviews]
        avg_rating = sum(ratings) / len(ratings) if ratings else 0
        variance = sum((r - avg_rating) ** 2 for r in ratings) / len(ratings) if ratings else 0
        
        # Determine optimal customer segments from review analysis
        target_motivations = ad_profile.target_motivations
        target_decision_styles = ad_profile.target_decision_styles
        
        return ProductProfile(
            product_id=product_id,
            category=category,
            persuasion_techniques=ad_profile.persuasion_techniques_used,
            emotional_appeals=ad_profile.emotional_appeals_used,
            value_propositions=ad_profile.value_propositions_used,
            brand_personality=ad_profile.personality_traits,
            linguistic_style={ad_profile.linguistic_style: 1.0},
            primary_persuasion=ad_profile.primary_persuasion_technique,
            primary_emotion=ad_profile.primary_emotional_appeal,
            primary_value=ad_profile.primary_value_proposition,
            target_motivations=target_motivations,
            target_decision_styles=target_decision_styles,
            optimal_archetypes=self._infer_optimal_archetypes(ad_profile),
            mechanism_effectiveness=ad_profile.mechanism_emphasis,
            review_count=len(reviews),
            avg_rating=avg_rating,
            rating_variance=variance,
            confidence=min(1.0, len(reviews) / 20),  # More reviews = more confidence
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
        )
    
    def _validate_alignments(
        self,
        profile: ProductProfile,
        reviews: List[ReviewRecord],
    ) -> List[AlignmentValidation]:
        """
        Validate alignment predictions against actual review ratings.
        """
        
        validations = []
        
        # Sample reviews for validation (to avoid over-processing)
        sample_reviews = reviews[:10] if len(reviews) > 10 else reviews
        
        # Create ad profile for alignment calculation
        ad_profile = self.create_ad_profile(
            " ".join([r.review_text for r in reviews[:3]]),
            profile.product_id
        )
        
        for review in sample_reviews:
            if len(review.review_text) < 20:
                continue
            
            try:
                # Infer customer type from review
                customer = self.type_service.infer_type_from_text(
                    review.review_text,
                    "pragmatist"  # Default archetype
                )
                
                # Calculate alignment
                alignment = self.alignment_service.calculate_alignment(customer, ad_profile)
                
                # Compare to actual
                actual_effectiveness = review.rating / 5.0
                discrepancy = actual_effectiveness - alignment.predicted_effectiveness
                
                validations.append(AlignmentValidation(
                    product_id=profile.product_id,
                    customer_motivation=customer.expanded_motivation,
                    customer_decision_style=customer.expanded_decision_style,
                    predicted_alignment=alignment.overall_alignment,
                    predicted_effectiveness=alignment.predicted_effectiveness,
                    actual_rating=review.rating,
                    actual_effectiveness=actual_effectiveness,
                    discrepancy=discrepancy,
                    review_text_sample=review.review_text[:200],
                    category=profile.category,
                    signal_strength=review.signal_strength,
                ))
            
            except Exception:
                continue
        
        return validations
    
    def _analyze_patterns(
        self,
        validations: List[AlignmentValidation],
        output_file: str,
    ) -> Dict[str, Any]:
        """
        Analyze validation data to discover patterns.
        """
        
        if not validations:
            return {"patterns_count": 0}
        
        # Group by motivation-decision combination
        patterns: Dict[str, List[float]] = {}
        
        for v in validations:
            key = f"{v.customer_motivation}_{v.customer_decision_style}"
            if key not in patterns:
                patterns[key] = []
            patterns[key].append(v.discrepancy)
        
        # Analyze each pattern
        pattern_analysis = []
        
        for key, discrepancies in patterns.items():
            if len(discrepancies) < 5:
                continue
            
            avg_discrepancy = sum(discrepancies) / len(discrepancies)
            
            pattern_analysis.append({
                "pattern": key,
                "sample_count": len(discrepancies),
                "avg_discrepancy": avg_discrepancy,
                "direction": "under_predicted" if avg_discrepancy > 0 else "over_predicted",
                "correction_suggested": avg_discrepancy * 0.5,  # Conservative correction
            })
        
        # Save analysis
        output_path = self.output_path / output_file
        with open(output_path, "w") as f:
            json.dump(pattern_analysis, f, indent=2)
        
        self.stats["patterns_discovered"] += len(pattern_analysis)
        
        return {
            "patterns_count": len(pattern_analysis),
            "patterns": pattern_analysis,
        }
    
    def _infer_optimal_archetypes(self, ad_profile) -> List[str]:
        """Infer which archetypes would respond best to this product."""
        
        archetypes = []
        
        # Based on value propositions and emotional appeals
        if ad_profile.primary_value_proposition in ["quality_craftsmanship", "expertise_mastery"]:
            archetypes.append("perfectionist")
        
        if ad_profile.primary_value_proposition in ["value_savings", "risk_reduction"]:
            archetypes.append("guardian")
        
        if ad_profile.primary_emotional_appeal in ["excitement", "adventure_thrill"]:
            archetypes.append("explorer")
        
        if ad_profile.primary_emotional_appeal in ["trust", "contentment"]:
            archetypes.append("pragmatist")
        
        # Default to pragmatist if nothing specific
        if not archetypes:
            archetypes.append("pragmatist")
        
        return archetypes
    
    def _discover_categories(self) -> List[str]:
        """Discover available categories from data files."""
        
        categories = set()
        
        # Look for category-specific files
        for f in self.data_loader._find_review_files(None):
            # Extract category from filename
            name = f.stem.replace("reviews_", "").replace("_5", "")
            categories.add(name)
        
        return sorted(categories)
    
    def _save_checkpoint(self, name: str, data: Dict[str, Any]) -> None:
        """Save processing checkpoint."""
        
        checkpoint = ProcessingCheckpoint(
            stage=name.split("_")[0],
            category=name.split("_", 1)[1] if "_" in name else "",
            last_product_id=data.get("last_product_id", ""),
            processed_count=data.get("processed_count", 0),
            error_count=self.stats.get("errors", 0),
            timestamp=datetime.now().isoformat(),
            stats=data,
        )
        
        path = self.checkpoint_path / f"{name}.json"
        with open(path, "w") as f:
            json.dump({
                "stage": checkpoint.stage,
                "category": checkpoint.category,
                "last_product_id": checkpoint.last_product_id,
                "processed_count": checkpoint.processed_count,
                "error_count": checkpoint.error_count,
                "timestamp": checkpoint.timestamp,
                "stats": checkpoint.stats,
            }, f, indent=2)
    
    def _load_checkpoint(self, name: str) -> Optional[ProcessingCheckpoint]:
        """Load processing checkpoint if exists."""
        
        path = self.checkpoint_path / f"{name}.json"
        
        if not path.exists():
            return None
        
        try:
            with open(path) as f:
                data = json.load(f)
            
            return ProcessingCheckpoint(**data)
        except Exception:
            return None
    
    def _save_product_profiles(self, profiles: List[ProductProfile], filename: str) -> None:
        """Save product profiles."""
        
        path = self.output_path / filename
        
        with open(path, "w") as f:
            json.dump([p.to_dict() for p in profiles], f, indent=2)
    
    def _save_validation_data(self, validations: List[AlignmentValidation], filename: str) -> None:
        """Save validation data."""
        
        path = self.output_path / filename
        
        data = [
            {
                "product_id": v.product_id,
                "customer_motivation": v.customer_motivation,
                "customer_decision_style": v.customer_decision_style,
                "predicted_alignment": v.predicted_alignment,
                "predicted_effectiveness": v.predicted_effectiveness,
                "actual_rating": v.actual_rating,
                "actual_effectiveness": v.actual_effectiveness,
                "discrepancy": v.discrepancy,
                "category": v.category,
                "signal_strength": v.signal_strength,
            }
            for v in validations
        ]
        
        with open(path, "w") as f:
            json.dump(data, f, indent=2)


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def run_stage1_sampling(
    data_path: str,
    output_path: str,
    categories: Optional[List[str]] = None,
    sample_size: int = 10000,
) -> Dict[str, Any]:
    """
    Run Stage 1: Category Sampling.
    
    Quick start:
    >>> run_stage1_sampling(
    ...     data_path="/path/to/amazon/data",
    ...     output_path="/path/to/output",
    ...     categories=["Electronics", "Books"],
    ... )
    """
    
    processor = HistoricalDataReprocessor(
        data_path=data_path,
        output_path=output_path,
    )
    
    if categories is None:
        categories = processor._discover_categories()
    
    results = {}
    
    for category in categories:
        result = processor.process_category_sample(category, sample_size)
        results[category] = result
    
    return results


def run_stage2_high_signal(
    data_path: str,
    output_path: str,
    min_votes: int = 10,
    max_records: int = 100000,
) -> Dict[str, Any]:
    """
    Run Stage 2: High-Signal Processing.
    """
    
    processor = HistoricalDataReprocessor(
        data_path=data_path,
        output_path=output_path,
    )
    
    return processor.process_high_signal_data(
        min_votes=min_votes,
        max_records=max_records,
    )


# =============================================================================
# TESTING
# =============================================================================

if __name__ == "__main__":
    print("\n" + "="*70)
    print("HISTORICAL DATA REPROCESSOR TEST")
    print("="*70)
    
    # Test with mock data
    print("\n=== Testing Data Structures ===")
    
    # Create sample review
    review = ReviewRecord(
        review_id="test_001",
        product_id="B00001",
        user_id="user_001",
        review_text="This product is amazing! Exactly what I needed. Fast shipping and great quality.",
        rating=5.0,
        helpful_votes=15,
        total_votes=18,
        verified_purchase=True,
        category="Electronics",
    )
    
    print(f"\nSample Review:")
    print(f"  Product: {review.product_id}")
    print(f"  Rating: {review.rating}/5")
    print(f"  Signal Strength: {review.signal_strength:.2f}")
    print(f"  Helpfulness: {review.helpfulness_ratio:.2f}")
    
    # Create sample product profile
    profile = ProductProfile(
        product_id="B00001",
        category="Electronics",
        primary_persuasion="social_proof",
        primary_emotion="trust",
        primary_value="quality_craftsmanship",
        target_motivations=["quality_assurance", "functional_need"],
        target_decision_styles=["analytical_systematic", "satisficing"],
        review_count=50,
        avg_rating=4.5,
        confidence=0.9,
    )
    
    print(f"\nSample Product Profile:")
    print(f"  Product: {profile.product_id}")
    print(f"  Persuasion: {profile.primary_persuasion}")
    print(f"  Emotion: {profile.primary_emotion}")
    print(f"  Value: {profile.primary_value}")
    print(f"  Target Motivations: {profile.target_motivations}")
    
    # Create sample validation
    validation = AlignmentValidation(
        product_id="B00001",
        customer_motivation="quality_assurance",
        customer_decision_style="analytical_systematic",
        predicted_alignment=0.72,
        predicted_effectiveness=0.68,
        actual_rating=4.5,
        actual_effectiveness=0.9,
        discrepancy=0.22,
    )
    
    print(f"\nSample Validation:")
    print(f"  Predicted Effectiveness: {validation.predicted_effectiveness:.0%}")
    print(f"  Actual Effectiveness: {validation.actual_effectiveness:.0%}")
    print(f"  Discrepancy: {validation.discrepancy:+.0%}")
    print(f"  (System under-predicted by {validation.discrepancy:.0%})")
    
    print("\n=== Test Complete ===")
    print("\nTo process real data, use:")
    print("  run_stage1_sampling('/path/to/data', '/path/to/output')")
