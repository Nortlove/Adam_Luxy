#!/usr/bin/env python3
"""
ENHANCED REVIEW INGESTION PIPELINE
==================================

This is the specification for re-ingesting the 1 billion reviews with
FULL psychological analysis and intelligence extraction.

Key Improvements Over Original Ingestion:
1. Per-review psychological analysis (35 constructs)
2. Persuasive pattern detection per review
3. Helpful vote weighted influence scores
4. Emotional journey extraction
5. Purchase archaeology
6. Brand copy Cialdini analysis

This will enable:
- Pre-computed intelligence (no on-demand analysis)
- Queryable persuasive pattern library
- Weighted learning from validated reviews
- Fast mechanism matching

Estimated Processing:
- 1B reviews at ~50ms each = ~14,000 hours
- With batching + parallelization = ~24-48 hours
- Storage: ~500GB additional for analysis data
"""

import asyncio
import json
import gzip
import logging
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple, Iterator
from pathlib import Path
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor
import multiprocessing

logger = logging.getLogger(__name__)


# =============================================================================
# ENHANCED REVIEW DATA MODEL
# =============================================================================

@dataclass
class EnhancedReviewAnalysis:
    """
    Complete psychological analysis for a single review.
    
    This is what we SHOULD have been storing all along.
    """
    
    # Source identifiers
    asin: str
    review_id: str
    user_id: str
    
    # Original fields
    rating: float
    helpful_vote: int
    verified_purchase: bool
    text_length: int
    
    # === PSYCHOLOGICAL CONSTRUCTS (35 total) ===
    # Big Five
    big5_openness: float = 0.0
    big5_conscientiousness: float = 0.0
    big5_extraversion: float = 0.0
    big5_agreeableness: float = 0.0
    big5_neuroticism: float = 0.0
    
    # Cognitive Processing
    cognitive_nfc: float = 0.0      # Need for cognition
    cognitive_psp: float = 0.0      # Preference for systematic processing
    cognitive_hri: float = 0.0      # Heuristic reliance index
    
    # Self-Regulatory
    selfreg_sm: float = 0.0         # Self-monitoring
    selfreg_rf: float = 0.0         # Regulatory focus (promotion > 0.5, prevention < 0.5)
    selfreg_lam: float = 0.0        # Loss aversion magnitude
    
    # Social
    social_sco: float = 0.0         # Social comparison orientation
    social_conformity: float = 0.0
    social_fairness: float = 0.0
    
    # Information Processing
    info_holistic_analytic: float = 0.0
    info_visualizer_verbalizer: float = 0.0
    info_domain_trans: float = 0.0
    
    # Motivation
    motivation_at: float = 0.0      # Achievement tendency
    motivation_achievement: float = 0.0
    motivation_approach: float = 0.0
    
    # Decision Making
    decision_maximizer: float = 0.0
    decision_sc: float = 0.0        # Self-control
    decision_ti: float = 0.0        # Temporal inconsistency
    
    # Uncertainty
    uncertainty_at: float = 0.0     # Ambiguity tolerance
    uncertainty_ru: float = 0.0     # Risk under uncertainty
    uncertainty_cr: float = 0.0     # Curiosity
    
    # Susceptibility (key for persuasion)
    suscept_social_proof: float = 0.0
    suscept_authority: float = 0.0
    suscept_scarcity: float = 0.0
    suscept_anchoring: float = 0.0
    suscept_delay_discounting: float = 0.0
    
    # Construct confidence (average)
    construct_confidence: float = 0.0
    
    # === PERSUASIVE PATTERNS ===
    # Hook detection
    has_hook_question: bool = False
    has_hook_story: bool = False
    has_hook_contrast: bool = False
    has_hook_authority: bool = False
    has_hook_urgency: bool = False
    
    # Evidence patterns
    has_evidence_specific: bool = False
    has_evidence_comparison: bool = False
    has_evidence_timeline: bool = False
    has_evidence_use_case: bool = False
    has_evidence_durability: bool = False
    
    # Emotional appeals
    has_emotion_joy: bool = False
    has_emotion_relief: bool = False
    has_emotion_belonging: bool = False
    has_emotion_pride: bool = False
    has_emotion_trust: bool = False
    
    # Social proof elements
    has_social_recommendation: bool = False
    has_social_gifting: bool = False
    has_social_repurchase: bool = False
    has_social_convert: bool = False
    
    # Credibility markers
    has_credibility_expertise: bool = False
    has_credibility_balanced: bool = False
    has_credibility_verified: bool = False
    has_credibility_updated: bool = False
    
    # Aggregate persuasion scores
    hook_strength: float = 0.0
    evidence_strength: float = 0.0
    emotion_strength: float = 0.0
    social_proof_strength: float = 0.0
    credibility_strength: float = 0.0
    overall_persuasive_power: float = 0.0
    
    # === INFLUENCE METRICS ===
    influence_score: float = 0.0
    influence_tier: str = "standard"  # standard, medium, high, very_high, viral
    vote_weight: float = 1.0
    
    # === EMOTIONAL JOURNEY ===
    journey_pre_purchase: str = ""    # neutral, anxious, excited, skeptical
    journey_unboxing: str = ""        # disappointed, satisfied, thrilled
    journey_first_use: str = ""
    journey_long_term: str = ""
    expectations_met: str = ""         # exceeded, met, below
    
    # === PURCHASE ARCHAEOLOGY ===
    purchase_motivation: str = ""      # problem_solving, aspirational, social, necessity
    trigger_event: str = ""            # need, desire, recommendation, promotion
    decision_factors: List[str] = field(default_factory=list)
    
    # === ARCHETYPE ===
    primary_archetype: str = ""        # Achiever, Explorer, Connector, Guardian, etc.
    archetype_confidence: float = 0.0
    
    # === METADATA ===
    analyzed_at: str = ""
    analyzer_version: str = "enhanced_v1"
    
    def to_neo4j_properties(self) -> Dict[str, Any]:
        """Convert to Neo4j-compatible property dict."""
        d = asdict(self)
        # Convert lists to JSON strings for Neo4j
        d['decision_factors'] = json.dumps(d['decision_factors'])
        return d
    
    def to_compact_json(self) -> str:
        """Compact JSON for JSONL storage."""
        return json.dumps(asdict(self), separators=(',', ':'))


# =============================================================================
# ENHANCED INGESTION PIPELINE
# =============================================================================

class EnhancedIngestionPipeline:
    """
    Pipeline for re-ingesting reviews with full psychological analysis.
    
    Designed for:
    - Parallel processing across CPU cores
    - Batch writes to Neo4j
    - Checkpoint/resume capability
    - Progress tracking
    """
    
    def __init__(
        self,
        neo4j_driver=None,
        output_dir: Optional[Path] = None,
        batch_size: int = 1000,
        num_workers: int = None,
    ):
        self.driver = neo4j_driver
        self.output_dir = output_dir or Path("data/enhanced_reviews")
        self.batch_size = batch_size
        self.num_workers = num_workers or max(1, multiprocessing.cpu_count() - 2)
        
        # Statistics
        self.total_processed = 0
        self.total_errors = 0
        self.start_time = None
        
        # Lazy load analyzers
        self._construct_analyzer = None
        self._persuasive_extractor = None
        self._vote_weighter = None
    
    def _get_construct_analyzer(self):
        """Get or create construct analyzer."""
        if self._construct_analyzer is None:
            try:
                # CORRECT path: adam.intelligence.enhanced_review_analyzer
                from adam.intelligence.enhanced_review_analyzer import get_enhanced_analyzer
                self._construct_analyzer = get_enhanced_analyzer()
            except ImportError as e:
                logger.warning(f"EnhancedReviewAnalyzer not available: {e}")
                self._construct_analyzer = None
        return self._construct_analyzer
    
    def _get_persuasive_extractor(self):
        """Get or create persuasive pattern extractor."""
        if self._persuasive_extractor is None:
            from adam.intelligence.persuasive_patterns import get_persuasive_pattern_extractor
            self._persuasive_extractor = get_persuasive_pattern_extractor()
        return self._persuasive_extractor
    
    def _get_vote_weighter(self):
        """Get or create vote weighter."""
        if self._vote_weighter is None:
            from adam.intelligence.helpful_vote_weighting import get_helpful_vote_weighter
            self._vote_weighter = get_helpful_vote_weighter()
        return self._vote_weighter
    
    def analyze_review(self, review: Dict[str, Any]) -> EnhancedReviewAnalysis:
        """
        Perform full psychological analysis on a single review.
        
        This is the core function that extracts all intelligence.
        """
        text = review.get('text', '') or review.get('reviewText', '')
        helpful_votes = review.get('helpful_vote', 0) or 0
        
        # Initialize result
        result = EnhancedReviewAnalysis(
            asin=review.get('asin', '') or review.get('parent_asin', ''),
            review_id=review.get('review_id', f"r_{hash(text)%10000000}"),
            user_id=review.get('user_id', '') or review.get('reviewerID', ''),
            rating=float(review.get('rating', review.get('overall', 3))),
            helpful_vote=helpful_votes,
            verified_purchase=review.get('verified_purchase', False),
            text_length=len(text),
            analyzed_at=datetime.now().isoformat(),
        )
        
        if not text or len(text) < 20:
            return result
        
        # 1. Psychological Construct Analysis (35 constructs)
        analyzer = self._get_construct_analyzer()
        rating = float(review.get('rating', review.get('overall', 3)))
        if analyzer:
            try:
                # Analyzer returns a ConstructProfile object
                profile = analyzer.analyze_review(text, rating)
                
                # Map all 35 constructs to result fields
                # Field name mapping from construct_id to our dataclass fields
                CONSTRUCT_FIELD_MAP = {
                    # Big Five
                    "big5_openness": "big5_openness",
                    "big5_conscientiousness": "big5_conscientiousness", 
                    "big5_extraversion": "big5_extraversion",
                    "big5_agreeableness": "big5_agreeableness",
                    "big5_neuroticism": "big5_neuroticism",
                    # Cognitive Processing
                    "cognitive_nfc": "cognitive_nfc",
                    "cognitive_psp": "cognitive_psp",
                    "cognitive_hri": "cognitive_hri",
                    # Self-Regulatory
                    "selfreg_sm": "selfreg_sm",
                    "selfreg_rf": "selfreg_rf",
                    "selfreg_lam": "selfreg_lam",
                    # Social
                    "social_sco": "social_sco",
                    "social_conformity": "social_conformity",
                    "social_fairness": "social_fairness",
                    # Information Processing
                    "info_holistic": "info_holistic_analytic",
                    "info_visualizer": "info_visualizer_verbalizer",
                    "info_domain_trans": "info_domain_trans",
                    # Motivation
                    "motivation_at": "motivation_at",
                    "motivation_achievement": "motivation_achievement",
                    "motivation_approach": "motivation_approach",
                    # Decision Making
                    "decision_maximizer": "decision_maximizer",
                    "decision_sc": "decision_sc",
                    "decision_ti": "decision_ti",
                    # Uncertainty
                    "uncertainty_at": "uncertainty_at",
                    "uncertainty_ru": "uncertainty_ru",
                    "uncertainty_cr": "uncertainty_cr",
                    # Susceptibility
                    "suscept_social_proof": "suscept_social_proof",
                    "suscept_authority": "suscept_authority",
                    "suscept_scarcity": "suscept_scarcity",
                    "suscept_anchoring": "suscept_anchoring",
                    "suscept_delay_discounting": "suscept_delay_discounting",
                }
                
                # Extract scores from profile
                total_confidence = 0.0
                n_constructs = 0
                for construct_id, field_name in CONSTRUCT_FIELD_MAP.items():
                    score = profile.get_construct(construct_id)
                    if score and hasattr(result, field_name):
                        setattr(result, field_name, score.score)
                        total_confidence += score.confidence
                        n_constructs += 1
                
                # Average confidence across all constructs
                if n_constructs > 0:
                    result.construct_confidence = total_confidence / n_constructs
                    
            except Exception as e:
                logger.debug(f"Construct analysis failed: {e}")
        
        # 2. Persuasive Pattern Extraction
        extractor = self._get_persuasive_extractor()
        if extractor:
            try:
                profile = extractor.analyze_review(text, helpful_votes)
                
                # Map pattern detections
                for pattern in profile.patterns:
                    field_name = f"has_{pattern.element.value}"
                    if hasattr(result, field_name):
                        setattr(result, field_name, True)
                
                # Copy strength scores
                result.hook_strength = profile.hook_strength
                result.evidence_strength = profile.evidence_strength
                result.emotion_strength = profile.emotion_strength
                result.social_proof_strength = profile.social_proof_strength
                result.credibility_strength = profile.credibility_strength
                result.overall_persuasive_power = profile.overall_persuasive_power
            except Exception as e:
                logger.debug(f"Persuasive pattern extraction failed: {e}")
        
        # 3. Influence Score Calculation
        weighter = self._get_vote_weighter()
        if weighter:
            try:
                result.vote_weight = weighter.calculate_weight(helpful_votes)
                result.influence_score = result.vote_weight * result.overall_persuasive_power
                result.influence_tier = weighter.get_vote_tier(helpful_votes)
            except Exception as e:
                logger.debug(f"Vote weighting failed: {e}")
        
        # 4. Archetype Detection (simple heuristic)
        result.primary_archetype = self._detect_archetype(result)
        result.archetype_confidence = 0.7 if result.primary_archetype else 0.0
        
        return result
    
    def _detect_archetype(self, analysis: EnhancedReviewAnalysis) -> str:
        """Simple archetype detection from constructs."""
        scores = {
            "Achiever": analysis.motivation_achievement + analysis.decision_maximizer,
            "Explorer": analysis.big5_openness + analysis.uncertainty_cr,
            "Connector": analysis.big5_extraversion + analysis.social_sco,
            "Guardian": analysis.big5_conscientiousness + analysis.selfreg_lam,
            "Pragmatist": analysis.cognitive_psp + analysis.decision_sc,
            "Innovator": analysis.big5_openness + analysis.uncertainty_at,
        }
        return max(scores, key=scores.get)
    
    def process_file(
        self,
        input_file: Path,
        output_file: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """
        Process a single JSONL file with full analysis.
        
        Args:
            input_file: Path to JSONL (or JSONL.gz) file
            output_file: Optional output path for enhanced JSONL
            
        Returns:
            Statistics dict
        """
        if output_file is None:
            output_file = self.output_dir / f"enhanced_{input_file.stem}.jsonl"
        
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        stats = {
            "input_file": str(input_file),
            "output_file": str(output_file),
            "total": 0,
            "processed": 0,
            "errors": 0,
            "high_influence": 0,  # 200+ votes
            "with_hooks": 0,
            "start_time": datetime.now().isoformat(),
        }
        
        # Open input
        if str(input_file).endswith('.gz'):
            f_in = gzip.open(input_file, 'rt', encoding='utf-8')
        else:
            f_in = open(input_file, 'r', encoding='utf-8')
        
        # Process in batches
        with f_in, open(output_file, 'w', encoding='utf-8') as f_out:
            for line in f_in:
                stats['total'] += 1
                
                try:
                    review = json.loads(line)
                    analysis = self.analyze_review(review)
                    
                    # Write enhanced review
                    f_out.write(analysis.to_compact_json() + '\n')
                    
                    stats['processed'] += 1
                    
                    # Track interesting cases
                    if analysis.influence_tier in ('very_high', 'viral'):
                        stats['high_influence'] += 1
                    if analysis.hook_strength > 0.5:
                        stats['with_hooks'] += 1
                    
                except Exception as e:
                    stats['errors'] += 1
                    if stats['errors'] <= 10:
                        logger.warning(f"Error processing review: {e}")
                
                # Progress logging
                if stats['total'] % 10000 == 0:
                    logger.info(f"Processed {stats['total']} reviews...")
        
        stats['end_time'] = datetime.now().isoformat()
        stats['success_rate'] = stats['processed'] / max(1, stats['total'])
        
        return stats
    
    def process_directory(
        self,
        input_dir: Path,
        pattern: str = "*.jsonl*",
    ) -> Dict[str, Any]:
        """
        Process all JSONL files in a directory.
        
        Args:
            input_dir: Directory containing JSONL files
            pattern: Glob pattern for files
            
        Returns:
            Aggregate statistics
        """
        input_dir = Path(input_dir)
        files = list(input_dir.glob(pattern))
        
        logger.info(f"Found {len(files)} files to process")
        
        aggregate_stats = {
            "files_processed": 0,
            "total_reviews": 0,
            "total_processed": 0,
            "total_errors": 0,
            "total_high_influence": 0,
            "file_stats": [],
        }
        
        for file_path in files:
            logger.info(f"Processing {file_path.name}...")
            
            try:
                stats = self.process_file(file_path)
                aggregate_stats['file_stats'].append(stats)
                aggregate_stats['files_processed'] += 1
                aggregate_stats['total_reviews'] += stats['total']
                aggregate_stats['total_processed'] += stats['processed']
                aggregate_stats['total_errors'] += stats['errors']
                aggregate_stats['total_high_influence'] += stats['high_influence']
            except Exception as e:
                logger.error(f"Failed to process {file_path}: {e}")
        
        return aggregate_stats
    
    async def store_to_neo4j(
        self,
        analyses: List[EnhancedReviewAnalysis],
    ) -> int:
        """
        Store enhanced analyses to Neo4j.
        
        Creates/updates nodes with full psychological properties.
        """
        if not self.driver:
            logger.warning("No Neo4j driver, skipping storage")
            return 0
        
        query = """
        UNWIND $analyses AS a
        MERGE (r:EnhancedReview {review_id: a.review_id})
        SET r += a
        WITH r, a
        MERGE (u:Reviewer {user_id: a.user_id})
        MERGE (r)-[:WRITTEN_BY]->(u)
        WITH r, a
        WHERE a.influence_tier IN ['very_high', 'viral']
        SET r:SuperInfluencer
        RETURN count(r) as stored
        """
        
        async with self.driver.session() as session:
            result = await session.run(
                query,
                analyses=[a.to_neo4j_properties() for a in analyses]
            )
            record = await result.single()
            return record['stored'] if record else 0


# =============================================================================
# ENTRY POINT
# =============================================================================

def run_enhanced_ingestion(
    input_dir: str,
    output_dir: str = "data/enhanced_reviews",
    neo4j_uri: str = None,
    neo4j_user: str = None,
    neo4j_password: str = None,
):
    """
    Run enhanced ingestion pipeline.
    
    Args:
        input_dir: Directory with original JSONL review files
        output_dir: Output directory for enhanced JSONL
        neo4j_*: Optional Neo4j connection params
    """
    logger.info("="*60)
    logger.info("ENHANCED REVIEW INGESTION PIPELINE")
    logger.info("="*60)
    
    # Initialize driver if credentials provided
    driver = None
    if neo4j_uri and neo4j_user and neo4j_password:
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
    
    # Create pipeline
    pipeline = EnhancedIngestionPipeline(
        neo4j_driver=driver,
        output_dir=Path(output_dir),
    )
    
    # Process
    stats = pipeline.process_directory(Path(input_dir))
    
    # Report
    logger.info("="*60)
    logger.info("INGESTION COMPLETE")
    logger.info(f"Files processed: {stats['files_processed']}")
    logger.info(f"Total reviews: {stats['total_reviews']}")
    logger.info(f"Successfully processed: {stats['total_processed']}")
    logger.info(f"Errors: {stats['total_errors']}")
    logger.info(f"High-influence reviews: {stats['total_high_influence']}")
    logger.info("="*60)
    
    return stats


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Enhanced Review Ingestion")
    parser.add_argument("input_dir", help="Input directory with JSONL files")
    parser.add_argument("--output-dir", default="data/enhanced_reviews")
    parser.add_argument("--neo4j-uri", default=None)
    parser.add_argument("--neo4j-user", default=None)
    parser.add_argument("--neo4j-password", default=None)
    
    args = parser.parse_args()
    
    logging.basicConfig(level=logging.INFO)
    
    run_enhanced_ingestion(
        args.input_dir,
        args.output_dir,
        args.neo4j_uri,
        args.neo4j_user,
        args.neo4j_password,
    )
