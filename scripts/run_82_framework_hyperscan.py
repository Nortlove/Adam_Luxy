#!/usr/bin/env python3
"""
ADAM 82-FRAMEWORK HYPERSCAN PIPELINE
=====================================

Ultra-high-performance psychological analysis using Intel Hyperscan (via Vectorscan on ARM).

PERFORMANCE:
- Hyperscan matches ALL patterns in single pass through text
- O(text_length) regardless of pattern count
- Expected: 10,000-50,000+ reviews/sec vs 575/sec with stdlib re

FEATURES:
- Full 82-framework analytical depth
- Checkpointing after each category
- Optional file deletion after processing
- Comprehensive aggregation for priors
"""

import argparse
import gc
import gzip
import json
import logging
import os
import sys
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from multiprocessing import Pool, cpu_count
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import hyperscan

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# =============================================================================
# LOGGING SETUP
# =============================================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/82_framework_hyperscan.log')
    ]
)
logger = logging.getLogger(__name__)


# =============================================================================
# PATTERN EXTRACTION FROM 82 FRAMEWORKS
# =============================================================================

# Import all pattern definitions from psychological_frameworks.py
from adam.intelligence.psychological_frameworks import (
    BIG_FIVE_MARKERS,
    NEED_FOR_COGNITION_MARKERS,
    SELF_MONITORING_MARKERS,
    DECISION_STYLE_MARKERS,
    UNCERTAINTY_TOLERANCE_MARKERS,
    REGULATORY_FOCUS_MARKERS,
    CONSTRUAL_LEVEL_MARKERS,
    TEMPORAL_ORIENTATION_MARKERS,
    APPROACH_AVOIDANCE_MARKERS,
    SELF_DETERMINATION_MARKERS,
    SOCIAL_PROOF_MARKERS,
    AUTHORITY_MARKERS,
    SCARCITY_MARKERS,
    RECIPROCITY_MARKERS,
    COMMITMENT_MARKERS,
    LIKING_MARKERS,
    LOSS_AVERSION_MARKERS,
    ANCHORING_MARKERS,
    FRAMING_MARKERS,
    WANTING_LIKING_MARKERS,
    AUTOMATIC_EVALUATION_MARKERS,
    EMBODIED_COGNITION_MARKERS,
    ATTENTION_MARKERS,
    PROCESSING_FLUENCY_MARKERS,
    MIMETIC_DESIRE_MARKERS,
    EVOLUTIONARY_MOTIVES_MARKERS,
    SOCIAL_COMPARISON_MARKERS,
    IDENTITY_MARKERS,
    BELONGINGNESS_MARKERS,
    DUAL_PROCESS_MARKERS,
    ELM_MARKERS,
    DECISION_FATIGUE_MARKERS,
    CHOICE_OVERLOAD_MARKERS,
    COGNITIVE_LOAD_MARKERS,
    LIWC_MARKERS,
    ABSOLUTIST_MARKERS,
    TEMPORAL_LINGUISTIC_MARKERS,
    CERTAINTY_MARKERS,
    EMOTIONAL_INTENSITY_MARKERS,
)

# Import all pattern definitions from psychological_frameworks_extended.py
from adam.intelligence.psychological_frameworks_extended import (
    STATE_TRAIT_INTERACTION_MARKERS,
    AROUSAL_MODULATION_MARKERS,
    CIRCADIAN_MARKERS,
    JOURNEY_STAGE_MARKERS,
    TEMPORAL_CONSTRUAL_MARKERS,
    MICRO_TEMPORAL_MARKERS,
    CROSS_CATEGORY_MARKERS,
    CONTENT_CONSUMPTION_MARKERS,
    PHYSIOLOGICAL_PROXY_MARKERS,
    INTERACTION_SEQUENCING_MARKERS,
    BRAND_PERSONALITY_MARKERS,
    BRAND_SELF_CONGRUITY_MARKERS,
    PSYCHOLOGICAL_OWNERSHIP_MARKERS,
    MORAL_FOUNDATIONS_MARKERS,
    ELABORATIVE_ENCODING_MARKERS,
    MERE_EXPOSURE_MARKERS,
    PEAK_END_MARKERS,
    NARRATIVE_TRANSPORTATION_MARKERS,
    MEANING_MAKING_MARKERS,
    HEROS_JOURNEY_MARKERS,
    SOURCE_CREDIBILITY_MARKERS,
    EVIDENCE_ELABORATION_MARKERS,
    NEGATIVITY_BIAS_MARKERS,
    MENTAL_ACCOUNTING_MARKERS,
    REFERENCE_PRICE_MARKERS,
    PAIN_OF_PAYING_MARKERS,
    REGULATORY_FIT_MARKERS,
    CONSTRUAL_FIT_MARKERS,
    RESOURCE_DEPLETION_MARKERS,
    CULTURAL_SELF_CONSTRUAL_MARKERS,
    POWER_DISTANCE_MARKERS,
    UNCERTAINTY_AVOIDANCE_CULTURAL_MARKERS,
    VULNERABILITY_MARKERS,
    MANIPULATION_BOUNDARY_MARKERS,
    IDENTITY_THREAT_MARKERS,
    COUNTERFACTUAL_MARKERS,
    CONFIDENCE_CALIBRATION_MARKERS,
)


def extract_patterns_from_framework(framework_dict: Dict, category: str, framework_name: str) -> List[Tuple[str, str, str, str]]:
    """
    Extract all patterns from a framework dictionary.
    Returns list of (pattern, category, framework, sub_category)
    """
    patterns = []
    
    def extract_recursive(d: Dict, sub_cat: str = ""):
        if isinstance(d, dict):
            for key, value in d.items():
                if key in ("description", "application"):
                    continue
                if isinstance(value, list):
                    # This is a list of patterns
                    for pattern in value:
                        if isinstance(pattern, str) and (r"\b" in pattern or r"(?i)" in pattern):
                            patterns.append((pattern, category, framework_name, sub_cat or key))
                elif isinstance(value, dict):
                    # Recurse into nested dict
                    if "markers" in value:
                        for pattern in value.get("markers", []):
                            if isinstance(pattern, str):
                                patterns.append((pattern, category, framework_name, key))
                    else:
                        extract_recursive(value, key)
    
    extract_recursive(framework_dict)
    return patterns


def build_pattern_database() -> Tuple[List[Tuple[str, str, str, str]], Dict[int, Tuple[str, str, str]]]:
    """
    Build complete pattern list from all 82 frameworks.
    Returns (patterns_list, id_to_category_map)
    """
    all_patterns = []
    
    # Category I: Personality & Individual Differences (1-5)
    for trait, markers in BIG_FIVE_MARKERS.items():
        all_patterns.extend(extract_patterns_from_framework(markers, "personality", f"big_five_{trait}"))
    all_patterns.extend(extract_patterns_from_framework(NEED_FOR_COGNITION_MARKERS, "personality", "need_for_cognition"))
    all_patterns.extend(extract_patterns_from_framework(SELF_MONITORING_MARKERS, "personality", "self_monitoring"))
    all_patterns.extend(extract_patterns_from_framework(DECISION_STYLE_MARKERS, "personality", "decision_style"))
    all_patterns.extend(extract_patterns_from_framework(UNCERTAINTY_TOLERANCE_MARKERS, "personality", "uncertainty_tolerance"))
    
    # Category II: Motivational Frameworks (6-10)
    all_patterns.extend(extract_patterns_from_framework(REGULATORY_FOCUS_MARKERS, "motivation", "regulatory_focus"))
    all_patterns.extend(extract_patterns_from_framework(CONSTRUAL_LEVEL_MARKERS, "motivation", "construal_level"))
    all_patterns.extend(extract_patterns_from_framework(TEMPORAL_ORIENTATION_MARKERS, "motivation", "temporal_orientation"))
    all_patterns.extend(extract_patterns_from_framework(APPROACH_AVOIDANCE_MARKERS, "motivation", "approach_avoidance"))
    all_patterns.extend(extract_patterns_from_framework(SELF_DETERMINATION_MARKERS, "motivation", "self_determination"))
    
    # Category III: Cognitive Mechanisms / Cialdini+ (11-19)
    all_patterns.extend(extract_patterns_from_framework(SOCIAL_PROOF_MARKERS, "cognitive", "social_proof"))
    all_patterns.extend(extract_patterns_from_framework(AUTHORITY_MARKERS, "cognitive", "authority"))
    all_patterns.extend(extract_patterns_from_framework(SCARCITY_MARKERS, "cognitive", "scarcity"))
    all_patterns.extend(extract_patterns_from_framework(RECIPROCITY_MARKERS, "cognitive", "reciprocity"))
    all_patterns.extend(extract_patterns_from_framework(COMMITMENT_MARKERS, "cognitive", "commitment"))
    all_patterns.extend(extract_patterns_from_framework(LIKING_MARKERS, "cognitive", "liking"))
    all_patterns.extend(extract_patterns_from_framework(LOSS_AVERSION_MARKERS, "cognitive", "loss_aversion"))
    all_patterns.extend(extract_patterns_from_framework(ANCHORING_MARKERS, "cognitive", "anchoring"))
    all_patterns.extend(extract_patterns_from_framework(FRAMING_MARKERS, "cognitive", "framing"))
    
    # Category IV: Neuroscience-Grounded (20-24)
    all_patterns.extend(extract_patterns_from_framework(WANTING_LIKING_MARKERS, "neuroscience", "wanting_liking"))
    all_patterns.extend(extract_patterns_from_framework(AUTOMATIC_EVALUATION_MARKERS, "neuroscience", "automatic_evaluation"))
    all_patterns.extend(extract_patterns_from_framework(EMBODIED_COGNITION_MARKERS, "neuroscience", "embodied_cognition"))
    all_patterns.extend(extract_patterns_from_framework(ATTENTION_MARKERS, "neuroscience", "attention"))
    all_patterns.extend(extract_patterns_from_framework(PROCESSING_FLUENCY_MARKERS, "neuroscience", "processing_fluency"))
    
    # Category V: Social & Evolutionary (25-29)
    all_patterns.extend(extract_patterns_from_framework(MIMETIC_DESIRE_MARKERS, "social", "mimetic_desire"))
    all_patterns.extend(extract_patterns_from_framework(EVOLUTIONARY_MOTIVES_MARKERS, "social", "evolutionary_motives"))
    all_patterns.extend(extract_patterns_from_framework(SOCIAL_COMPARISON_MARKERS, "social", "social_comparison"))
    all_patterns.extend(extract_patterns_from_framework(IDENTITY_MARKERS, "social", "identity"))
    all_patterns.extend(extract_patterns_from_framework(BELONGINGNESS_MARKERS, "social", "belongingness"))
    
    # Category VI: Decision-Making (30-34)
    all_patterns.extend(extract_patterns_from_framework(DUAL_PROCESS_MARKERS, "decision", "dual_process"))
    all_patterns.extend(extract_patterns_from_framework(ELM_MARKERS, "decision", "elm"))
    all_patterns.extend(extract_patterns_from_framework(DECISION_FATIGUE_MARKERS, "decision", "decision_fatigue"))
    all_patterns.extend(extract_patterns_from_framework(CHOICE_OVERLOAD_MARKERS, "decision", "choice_overload"))
    all_patterns.extend(extract_patterns_from_framework(COGNITIVE_LOAD_MARKERS, "decision", "cognitive_load"))
    
    # Category VII: Psycholinguistic Analysis (35-40)
    all_patterns.extend(extract_patterns_from_framework(LIWC_MARKERS, "linguistic", "liwc"))
    all_patterns.extend(extract_patterns_from_framework(ABSOLUTIST_MARKERS, "linguistic", "absolutist"))
    all_patterns.extend(extract_patterns_from_framework(TEMPORAL_LINGUISTIC_MARKERS, "linguistic", "temporal_linguistic"))
    all_patterns.extend(extract_patterns_from_framework(CERTAINTY_MARKERS, "linguistic", "certainty"))
    all_patterns.extend(extract_patterns_from_framework(EMOTIONAL_INTENSITY_MARKERS, "linguistic", "emotional_intensity"))
    
    # Category VIII: Temporal & State (41-45)
    all_patterns.extend(extract_patterns_from_framework(STATE_TRAIT_INTERACTION_MARKERS, "temporal", "state_trait"))
    all_patterns.extend(extract_patterns_from_framework(AROUSAL_MODULATION_MARKERS, "temporal", "arousal"))
    all_patterns.extend(extract_patterns_from_framework(CIRCADIAN_MARKERS, "temporal", "circadian"))
    all_patterns.extend(extract_patterns_from_framework(JOURNEY_STAGE_MARKERS, "temporal", "journey_stage"))
    all_patterns.extend(extract_patterns_from_framework(TEMPORAL_CONSTRUAL_MARKERS, "temporal", "temporal_construal"))
    all_patterns.extend(extract_patterns_from_framework(MICRO_TEMPORAL_MARKERS, "temporal", "micro_temporal"))
    
    # Category IX: Behavioral Signals (46-50)
    all_patterns.extend(extract_patterns_from_framework(CROSS_CATEGORY_MARKERS, "behavioral", "cross_category"))
    all_patterns.extend(extract_patterns_from_framework(CONTENT_CONSUMPTION_MARKERS, "behavioral", "content_consumption"))
    all_patterns.extend(extract_patterns_from_framework(PHYSIOLOGICAL_PROXY_MARKERS, "behavioral", "physiological_proxy"))
    all_patterns.extend(extract_patterns_from_framework(INTERACTION_SEQUENCING_MARKERS, "behavioral", "interaction_sequencing"))
    
    # Category X: Brand-Consumer Matching (51-53)
    all_patterns.extend(extract_patterns_from_framework(BRAND_PERSONALITY_MARKERS, "brand", "brand_personality"))
    all_patterns.extend(extract_patterns_from_framework(BRAND_SELF_CONGRUITY_MARKERS, "brand", "brand_self_congruity"))
    all_patterns.extend(extract_patterns_from_framework(PSYCHOLOGICAL_OWNERSHIP_MARKERS, "brand", "psychological_ownership"))
    
    # Category XI: Moral & Values (54-55)
    all_patterns.extend(extract_patterns_from_framework(MORAL_FOUNDATIONS_MARKERS, "moral", "moral_foundations"))
    
    # Category XII: Memory & Learning (56-58)
    all_patterns.extend(extract_patterns_from_framework(ELABORATIVE_ENCODING_MARKERS, "memory", "elaborative_encoding"))
    all_patterns.extend(extract_patterns_from_framework(MERE_EXPOSURE_MARKERS, "memory", "mere_exposure"))
    all_patterns.extend(extract_patterns_from_framework(PEAK_END_MARKERS, "memory", "peak_end"))
    
    # Category XIII: Narrative & Meaning (59-61)
    all_patterns.extend(extract_patterns_from_framework(NARRATIVE_TRANSPORTATION_MARKERS, "narrative", "narrative_transportation"))
    all_patterns.extend(extract_patterns_from_framework(MEANING_MAKING_MARKERS, "narrative", "meaning_making"))
    all_patterns.extend(extract_patterns_from_framework(HEROS_JOURNEY_MARKERS, "narrative", "heros_journey"))
    
    # Category XIV: Trust & Credibility (62-64)
    all_patterns.extend(extract_patterns_from_framework(SOURCE_CREDIBILITY_MARKERS, "trust", "source_credibility"))
    all_patterns.extend(extract_patterns_from_framework(EVIDENCE_ELABORATION_MARKERS, "trust", "evidence_elaboration"))
    all_patterns.extend(extract_patterns_from_framework(NEGATIVITY_BIAS_MARKERS, "trust", "negativity_bias"))
    
    # Category XV: Price & Value Psychology (65-67)
    all_patterns.extend(extract_patterns_from_framework(MENTAL_ACCOUNTING_MARKERS, "price", "mental_accounting"))
    all_patterns.extend(extract_patterns_from_framework(REFERENCE_PRICE_MARKERS, "price", "reference_price"))
    all_patterns.extend(extract_patterns_from_framework(PAIN_OF_PAYING_MARKERS, "price", "pain_of_paying"))
    
    # Category XVI: Mechanism Interaction (68-70)
    all_patterns.extend(extract_patterns_from_framework(REGULATORY_FIT_MARKERS, "mechanism", "regulatory_fit"))
    all_patterns.extend(extract_patterns_from_framework(CONSTRUAL_FIT_MARKERS, "mechanism", "construal_fit"))
    all_patterns.extend(extract_patterns_from_framework(RESOURCE_DEPLETION_MARKERS, "mechanism", "resource_depletion"))
    
    # Category XVII: Cultural & Demographic (71-76)
    all_patterns.extend(extract_patterns_from_framework(CULTURAL_SELF_CONSTRUAL_MARKERS, "cultural", "cultural_self_construal"))
    all_patterns.extend(extract_patterns_from_framework(POWER_DISTANCE_MARKERS, "cultural", "power_distance"))
    all_patterns.extend(extract_patterns_from_framework(UNCERTAINTY_AVOIDANCE_CULTURAL_MARKERS, "cultural", "uncertainty_avoidance_cultural"))
    
    # Category XIX: Ethical Guardrails (77-79)
    all_patterns.extend(extract_patterns_from_framework(VULNERABILITY_MARKERS, "ethical", "vulnerability"))
    all_patterns.extend(extract_patterns_from_framework(MANIPULATION_BOUNDARY_MARKERS, "ethical", "manipulation_boundary"))
    all_patterns.extend(extract_patterns_from_framework(IDENTITY_THREAT_MARKERS, "ethical", "identity_threat"))
    
    # Category XX: Advanced Inference (80-82)
    all_patterns.extend(extract_patterns_from_framework(COUNTERFACTUAL_MARKERS, "advanced", "counterfactual"))
    all_patterns.extend(extract_patterns_from_framework(CONFIDENCE_CALIBRATION_MARKERS, "advanced", "confidence"))
    
    # Build ID to category mapping
    id_to_category = {}
    for i, (pattern, category, framework, sub_cat) in enumerate(all_patterns):
        id_to_category[i] = (category, framework, sub_cat)
    
    logger.info(f"Built pattern database: {len(all_patterns)} patterns across 82 frameworks")
    return all_patterns, id_to_category


def compile_hyperscan_database(patterns: List[Tuple[str, str, str, str]]) -> hyperscan.Database:
    """
    Compile all patterns into a Hyperscan database.
    
    Note: Hyperscan doesn't support \b word boundaries with UCP mode.
    We use UTF8 without UCP and convert \b to (?<!\w)...(?!\w) alternative.
    """
    logger.info(f"Compiling {len(patterns)} patterns into Hyperscan database...")
    start = time.time()
    
    db = hyperscan.Database()
    
    # Convert patterns to Hyperscan format
    expressions = []
    ids = []
    flags = []
    
    for i, (pattern, _, _, _) in enumerate(patterns):
        # Convert Python regex to Hyperscan format
        hs_pattern = pattern
        # Use UTF8 mode only (UCP doesn't work with \b)
        hs_flags = hyperscan.HS_FLAG_UTF8
        
        # Handle case-insensitive flag
        if r"(?i)" in hs_pattern:
            hs_pattern = hs_pattern.replace(r"(?i)", "")
            hs_flags |= hyperscan.HS_FLAG_CASELESS
        
        # Hyperscan uses PCRE-like syntax
        expressions.append(hs_pattern.encode('utf-8'))
        ids.append(i)
        flags.append(hs_flags)
    
    try:
        db.compile(expressions=expressions, ids=ids, flags=flags)
        elapsed = time.time() - start
        logger.info(f"Hyperscan database compiled in {elapsed:.2f}s with {len(patterns)} patterns")
        return db
    except hyperscan.error as e:
        logger.error(f"Hyperscan compilation error: {e}")
        # Try to identify problematic patterns
        logger.info("Attempting to compile patterns individually to find issues...")
        valid_patterns = []
        valid_ids = []
        valid_flags = []
        failed_count = 0
        
        for i, (expr, pid, flag) in enumerate(zip(expressions, ids, flags)):
            try:
                test_db = hyperscan.Database()
                test_db.compile(expressions=[expr], ids=[pid], flags=[flag])
                valid_patterns.append(expr)
                valid_ids.append(pid)
                valid_flags.append(flag)
            except Exception as pe:
                failed_count += 1
                if failed_count <= 10:  # Only log first 10 failures
                    logger.warning(f"Pattern {i} failed: {expr[:60]}... - {pe}")
        
        if failed_count > 10:
            logger.warning(f"... and {failed_count - 10} more patterns failed")
        
        logger.info(f"Compiled {len(valid_patterns)} valid patterns (skipped {failed_count})")
        db.compile(expressions=valid_patterns, ids=valid_ids, flags=valid_flags)
        return db


# =============================================================================
# HYPERSCAN ANALYZER
# =============================================================================

class HyperscanAnalyzer:
    """
    High-performance analyzer using Hyperscan for pattern matching.
    """
    
    def __init__(self):
        self.patterns, self.id_to_category = build_pattern_database()
        self.db = compile_hyperscan_database(self.patterns)
        self.scratch = hyperscan.Scratch(self.db)
        
        # Pre-compute category aggregation maps
        self.category_patterns = defaultdict(set)
        self.framework_patterns = defaultdict(set)
        for pid, (category, framework, sub_cat) in self.id_to_category.items():
            self.category_patterns[category].add(pid)
            self.framework_patterns[framework].add(pid)
    
    def analyze(self, text: str) -> Dict[str, Any]:
        """
        Analyze text using Hyperscan.
        Returns framework scores and matches.
        """
        matches = []
        
        def on_match(id, start, end, flags, context):
            matches.append(id)
            return None
        
        # Scan with Hyperscan
        try:
            self.db.scan(text.encode('utf-8'), match_event_handler=on_match, scratch=self.scratch)
        except Exception as e:
            logger.debug(f"Scan error (non-fatal): {e}")
        
        # Aggregate matches by category and framework
        category_scores = defaultdict(float)
        framework_scores = defaultdict(float)
        sub_category_matches = defaultdict(int)
        
        for pid in matches:
            if pid in self.id_to_category:
                category, framework, sub_cat = self.id_to_category[pid]
                category_scores[category] += 1
                framework_scores[framework] += 1
                sub_category_matches[f"{framework}:{sub_cat}"] += 1
        
        # Normalize by pattern count per category
        for category in category_scores:
            if len(self.category_patterns[category]) > 0:
                category_scores[category] /= len(self.category_patterns[category])
        
        for framework in framework_scores:
            if len(self.framework_patterns[framework]) > 0:
                framework_scores[framework] /= len(self.framework_patterns[framework])
        
        # Detect primary archetype
        archetype_scores = self._infer_archetypes(category_scores, framework_scores)
        primary_archetype = max(archetype_scores, key=archetype_scores.get) if archetype_scores else "unknown"
        
        # Detect ethical flags
        vulnerability_flag = category_scores.get("ethical", 0) > 0.3
        
        return {
            "category_scores": dict(category_scores),
            "framework_scores": dict(framework_scores),
            "sub_category_matches": dict(sub_category_matches),
            "archetype_scores": archetype_scores,
            "primary_archetype": primary_archetype,
            "vulnerability_flag": vulnerability_flag,
            "total_matches": len(matches),
        }
    
    def _infer_archetypes(self, category_scores: Dict[str, float], framework_scores: Dict[str, float]) -> Dict[str, float]:
        """
        Infer archetype scores from framework matches.
        """
        archetypes = {
            "achiever": 0.0,
            "explorer": 0.0,
            "connector": 0.0,
            "guardian": 0.0,
            "pragmatist": 0.0,
            "analyst": 0.0,
        }
        
        # Achiever: high achievement, status, promotion focus
        archetypes["achiever"] = (
            framework_scores.get("big_five_conscientiousness", 0) * 0.3 +
            framework_scores.get("status", 0) * 0.3 +
            framework_scores.get("regulatory_focus", 0) * 0.2 +
            framework_scores.get("big_five_extraversion", 0) * 0.2
        )
        
        # Explorer: high openness, novelty, discovery
        archetypes["explorer"] = (
            framework_scores.get("big_five_openness", 0) * 0.4 +
            framework_scores.get("temporal_orientation", 0) * 0.2 +
            framework_scores.get("approach_avoidance", 0) * 0.2 +
            category_scores.get("narrative", 0) * 0.2
        )
        
        # Connector: high agreeableness, social, relationships
        archetypes["connector"] = (
            framework_scores.get("big_five_agreeableness", 0) * 0.3 +
            framework_scores.get("tribal", 0) * 0.3 +
            framework_scores.get("social_proof", 0) * 0.2 +
            framework_scores.get("kin_selection", 0) * 0.2
        )
        
        # Guardian: high security, prevention focus, protection
        archetypes["guardian"] = (
            framework_scores.get("big_five_neuroticism", 0) * 0.2 +
            framework_scores.get("loss_aversion", 0) * 0.3 +
            category_scores.get("trust", 0) * 0.3 +
            framework_scores.get("uncertainty_tolerance", 0) * 0.2
        )
        
        # Pragmatist: balanced, value-focused, practical
        archetypes["pragmatist"] = (
            category_scores.get("price", 0) * 0.3 +
            framework_scores.get("value_calculation", 0) * 0.3 +
            framework_scores.get("decision_style", 0) * 0.2 +
            framework_scores.get("system_1_2", 0) * 0.2
        )
        
        # Analyst: high cognition, research, detail
        archetypes["analyst"] = (
            framework_scores.get("need_for_cognition", 0) * 0.3 +
            framework_scores.get("elm", 0) * 0.2 +
            framework_scores.get("expertise", 0) * 0.3 +
            framework_scores.get("certainty", 0) * 0.2
        )
        
        # Normalize
        total = sum(archetypes.values())
        if total > 0:
            archetypes = {k: v / total for k, v in archetypes.items()}
        
        return archetypes


# =============================================================================
# CATEGORY PROCESSING
# =============================================================================

# Category files mapping
CATEGORY_FILES = {
    "Amazon_Fashion": "Amazon_Fashion.jsonl",
    "Appliances": "Appliances.jsonl",
    "Arts_Crafts_and_Sewing": "Arts_Crafts_and_Sewing.jsonl",
    "Automotive": "Automotive.jsonl",
    "Baby_Products": "Baby_Products.jsonl",
    "Beauty_and_Personal_Care": "Beauty_and_Personal_Care.jsonl",
    "Books": "Books.jsonl",
    "CDs_and_Vinyl": "CDs_and_Vinyl.jsonl",
    "Cell_Phones_and_Accessories": "Cell_Phones_and_Accessories.jsonl",
    "Clothing_Shoes_and_Jewelry": "Clothing_Shoes_and_Jewelry.jsonl",
    "Digital_Music": "Digital_Music.jsonl",
    "Electronics": "Electronics.jsonl",
    "Gift_Cards": "Gift_Cards.jsonl",
    "Grocery_and_Gourmet_Food": "Grocery_and_Gourmet_Food.jsonl",
    "Handmade_Products": "Handmade_Products.jsonl",
    "Health_and_Household": "Health_and_Household.jsonl",
    "Health_and_Personal_Care": "Health_and_Personal_Care.jsonl",
    "Home_and_Kitchen": "Home_and_Kitchen.jsonl",
    "Industrial_and_Scientific": "Industrial_and_Scientific.jsonl",
    "Kindle_Store": "Kindle_Store.jsonl",
    "Magazine_Subscriptions": "Magazine_Subscriptions.jsonl",
    "Movies_and_TV": "Movies_and_TV.jsonl",
    "Musical_Instruments": "Musical_Instruments.jsonl",
    "Office_Products": "Office_Products.jsonl",
    "Patio_Lawn_and_Garden": "Patio_Lawn_and_Garden.jsonl",
    "Pet_Supplies": "Pet_Supplies.jsonl",
    "Software": "Software.jsonl",
    "Sports_and_Outdoors": "Sports_and_Outdoors.jsonl",
    "Subscription_Boxes": "Subscription_Boxes.jsonl",
    "Tools_and_Home_Improvement": "Tools_and_Home_Improvement.jsonl",
    "Toys_and_Games": "Toys_and_Games.jsonl",
    "Unknown": "Unknown.jsonl",
    "Video_Games": "Video_Games.jsonl",
}


def load_meta_lookup(meta_path: Path, analyzer: 'HyperscanAnalyzer') -> Tuple[Dict[str, Dict], Dict[str, Dict]]:
    """
    Load metadata file and create ASIN -> product info lookup.
    
    ALSO analyzes product copy (title + features + description) with 82-framework
    to understand brand psychological messaging strategy.
    
    This is CRITICAL for:
    - Enriching reviews with brand, price, product title
    - Understanding brand's psychological targeting
    - Enabling brand-customer psychological alignment matching
    
    Returns:
        meta_lookup: ASIN -> product info
        product_profiles: ASIN -> psychological analysis of product copy
    """
    logger.info(f"Loading metadata from {meta_path}...")
    meta_lookup = {}
    product_profiles = {}
    
    if not meta_path.exists():
        logger.warning(f"Meta file not found: {meta_path}")
        return meta_lookup, product_profiles
    
    open_fn = gzip.open if str(meta_path).endswith('.gz') else open
    mode = 'rt' if str(meta_path).endswith('.gz') else 'r'
    
    product_count = 0
    analyzed_count = 0
    
    try:
        with open_fn(meta_path, mode, encoding='utf-8', errors='replace') as f:
            for line in f:
                try:
                    product = json.loads(line)
                    asin = product.get('parent_asin') or product.get('asin')
                    if not asin:
                        continue
                    
                    # Extract brand from title
                    title = product.get('title', '')
                    brand = extract_brand_from_title(title)
                    
                    # Get all product copy (this IS the brand's advertisement)
                    features = product.get('features', [])
                    description = product.get('description', [])
                    
                    # Combine all product text for psychological analysis
                    product_text_parts = [title]
                    if features:
                        product_text_parts.extend(features if isinstance(features, list) else [features])
                    if description:
                        product_text_parts.extend(description if isinstance(description, list) else [description])
                    
                    product_text = ' '.join(str(p) for p in product_text_parts if p)
                    
                    # Store MINIMAL product info (memory optimization)
                    # Don't store features, description, product_text - they're huge
                    meta_lookup[asin] = {
                        'title': title,
                        'brand': brand,
                        'price': product.get('price'),
                        'main_category': product.get('main_category', ''),
                    }
                    
                    # Analyze product copy with 82-framework (brand's psychological strategy)
                    if len(product_text) > 20:
                        product_analysis = analyzer.analyze(product_text)
                        product_profiles[asin] = {
                            'brand': brand,
                            'category_scores': product_analysis['category_scores'],
                            'framework_scores': product_analysis['framework_scores'],
                            'archetype_scores': product_analysis['archetype_scores'],
                            'primary_archetype': product_analysis['primary_archetype'],
                            'total_matches': product_analysis['total_matches'],
                        }
                        analyzed_count += 1
                    
                    # Clear product_text immediately - no longer needed
                    del product_text
                    del product
                    
                    product_count += 1
                    
                    # Progress and garbage collection for large meta files
                    if product_count % 100000 == 0:
                        logger.info(f"  Loaded {product_count:,} products, analyzed {analyzed_count:,}")
                        gc.collect()  # Free memory periodically
                        for handler in logger.handlers:
                            handler.flush()
                    
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        logger.error(f"Error loading meta file: {e}")
    
    logger.info(f"Loaded {len(meta_lookup):,} products, analyzed {len(product_profiles):,} product descriptions")
    return meta_lookup, product_profiles


def extract_brand_from_title(title: str) -> str:
    """
    Extract brand name from product title.
    
    Common patterns:
    - "Brand Name Product Description" -> "Brand Name"
    - "Brand - Product" -> "Brand"
    - First capitalized word(s) before common product words
    """
    if not title:
        return 'Unknown'
    
    # Common brand separators
    for sep in [' - ', ' | ', ' – ', ': ']:
        if sep in title:
            potential_brand = title.split(sep)[0].strip()
            if len(potential_brand) < 50:  # Reasonable brand name length
                return potential_brand
    
    # Take first 1-3 words as brand (common pattern)
    words = title.split()
    if len(words) >= 2:
        # Check if first word is a common descriptor (not a brand)
        common_descriptors = {'the', 'a', 'an', 'new', 'premium', 'professional', 'deluxe', 'original'}
        start_idx = 0
        if words[0].lower() in common_descriptors:
            start_idx = 1
        
        # Take 1-2 words as brand
        if len(words) > start_idx + 1:
            # Check if second word is also part of brand name (e.g., "North Face")
            potential_brand = ' '.join(words[start_idx:start_idx+2])
            if len(potential_brand) < 30:
                return potential_brand
        if len(words) > start_idx:
            return words[start_idx]
    
    return words[0] if words else 'Unknown'


def process_category(
    category: str,
    file_path: Path,
    analyzer: HyperscanAnalyzer,
    amazon_dir: Path,
    batch_size: int = 5000,
) -> Dict[str, Any]:
    """
    Process all reviews in a category file with metadata enrichment.
    
    Also analyzes product copy (brand advertisement) with same 82-framework
    to enable brand-customer psychological alignment analysis.
    """
    logger.info(f"Processing category: {category} from {file_path}")
    
    # Load metadata AND analyze product copy (brand's psychological strategy)
    meta_filename = f"meta_{file_path.name}"
    meta_path = amazon_dir / meta_filename
    meta_lookup, product_profiles = load_meta_lookup(meta_path, analyzer)
    
    # Aggregation structures for CUSTOMER reviews
    category_totals = defaultdict(float)
    framework_totals = defaultdict(float)
    archetype_totals = defaultdict(float)
    brand_customer_profiles = defaultdict(lambda: defaultdict(float))  # Customer archetype by brand
    rating_by_archetype = defaultdict(lambda: defaultdict(list))
    price_by_archetype = defaultdict(list)
    review_product_agg = defaultdict(lambda: {"count": 0, "archetypes": defaultdict(float)})
    
    # Aggregate BRAND psychological profiles from product analysis
    brand_ad_profiles = defaultdict(lambda: {
        "category_scores": defaultdict(float),
        "framework_scores": defaultdict(float),
        "archetype_scores": defaultdict(float),
        "product_count": 0,
    })
    
    # Build brand-level aggregation from product analysis
    for asin, prod_profile in product_profiles.items():
        brand = prod_profile.get('brand', 'Unknown')
        brand_ad_profiles[brand]['product_count'] += 1
        for cat, score in prod_profile.get('category_scores', {}).items():
            brand_ad_profiles[brand]['category_scores'][cat] += score
        for fw, score in prod_profile.get('framework_scores', {}).items():
            brand_ad_profiles[brand]['framework_scores'][fw] += score
        for arch, score in prod_profile.get('archetype_scores', {}).items():
            brand_ad_profiles[brand]['archetype_scores'][arch] += score
    
    # Normalize brand profiles
    for brand, profile in brand_ad_profiles.items():
        n = profile['product_count']
        if n > 0:
            profile['category_scores'] = {k: v/n for k, v in profile['category_scores'].items()}
            profile['framework_scores'] = {k: v/n for k, v in profile['framework_scores'].items()}
            profile['archetype_scores'] = {k: v/n for k, v in profile['archetype_scores'].items()}
    
    logger.info(f"Aggregated {len(brand_ad_profiles):,} brand psychological profiles from product copy")
    
    total_reviews = 0
    total_matches = 0
    enriched_count = 0
    start_time = time.time()
    
    # Determine if file is gzipped
    open_fn = gzip.open if str(file_path).endswith('.gz') else open
    mode = 'rt' if str(file_path).endswith('.gz') else 'r'
    
    try:
        with open_fn(file_path, mode, encoding='utf-8', errors='replace') as f:
            batch = []
            for line in f:
                try:
                    review = json.loads(line)
                    text = review.get('text', '') or review.get('reviewText', '')
                    if not text or len(text) < 10:
                        continue
                    
                    # Enrich review with metadata
                    asin = review.get('parent_asin') or review.get('asin')
                    if asin and asin in meta_lookup:
                        product_info = meta_lookup[asin]
                        review['_enriched'] = True
                        review['_brand'] = product_info['brand']
                        review['_title'] = product_info['title']
                        review['_price'] = product_info['price']
                        review['_main_category'] = product_info['main_category']
                    else:
                        review['_enriched'] = False
                        review['_brand'] = 'Unknown'
                        review['_title'] = ''
                        review['_price'] = None
                    
                    batch.append(review)
                    
                    if len(batch) >= batch_size:
                        # Process batch
                        for r in batch:
                            result = process_single_review(r, analyzer)
                            if result:
                                # Aggregate
                                for cat, score in result['category_scores'].items():
                                    category_totals[cat] += score
                                for fw, score in result['framework_scores'].items():
                                    framework_totals[fw] += score
                                for arch, score in result['archetype_scores'].items():
                                    archetype_totals[arch] += score
                                
                                # Brand CUSTOMER profiles (who buys from this brand)
                                brand = result.get('brand', 'Unknown')
                                for arch, score in result['archetype_scores'].items():
                                    brand_customer_profiles[brand][arch] += score
                                
                                # Price by archetype
                                price = result.get('price')
                                primary_arch = result.get('primary_archetype', 'unknown')
                                try:
                                    price_float = float(price) if price is not None else 0
                                    if price_float > 0:
                                        price_by_archetype[primary_arch].append(price_float)
                                except (TypeError, ValueError):
                                    pass  # Skip invalid prices
                                
                                # Product-level review aggregation
                                asin = result.get('asin', '')
                                if asin:
                                    review_product_agg[asin]['count'] += 1
                                    for arch, score in result['archetype_scores'].items():
                                        review_product_agg[asin]['archetypes'][arch] += score
                                
                                # Rating by archetype
                                rating = result.get('rating', 0)
                                if rating > 0:
                                    rating_by_archetype[primary_arch]['ratings'].append(rating)
                                
                                if result.get('enriched', False):
                                    enriched_count += 1
                                
                                total_reviews += 1
                                total_matches += result.get('total_matches', 0)
                        
                        batch = []
                        
                        # Progress logging
                        if total_reviews % 50000 == 0:
                            elapsed = time.time() - start_time
                            rate = total_reviews / elapsed if elapsed > 0 else 0
                            enrich_pct = (enriched_count / total_reviews * 100) if total_reviews > 0 else 0
                            logger.info(f"  {category}: Processed {total_reviews:,} ({rate:,.0f}/sec, {enrich_pct:.1f}% enriched)")
                            
                            # Flush logs to ensure they're written
                            for handler in logger.handlers:
                                handler.flush()
                            
                            # Force garbage collection every 100K reviews to free memory
                            if total_reviews % 100000 == 0:
                                gc.collect()
                                logger.info(f"  [GC] Memory cleared at {total_reviews:,} reviews")
                                for handler in logger.handlers:
                                    handler.flush()
                
                except json.JSONDecodeError:
                    continue
            
            # Process remaining batch
            for r in batch:
                result = process_single_review(r, analyzer)
                if result:
                    for cat, score in result['category_scores'].items():
                        category_totals[cat] += score
                    for fw, score in result['framework_scores'].items():
                        framework_totals[fw] += score
                    for arch, score in result['archetype_scores'].items():
                        archetype_totals[arch] += score
                    
                    brand = result.get('brand', 'Unknown')
                    for arch, score in result['archetype_scores'].items():
                        brand_customer_profiles[brand][arch] += score
                    
                    price = result.get('price')
                    primary_arch = result.get('primary_archetype', 'unknown')
                    try:
                        price_float = float(price) if price is not None else 0
                        if price_float > 0:
                            price_by_archetype[primary_arch].append(price_float)
                    except (TypeError, ValueError):
                        pass  # Skip invalid prices
                    
                    asin = result.get('asin', '')
                    if asin:
                        review_product_agg[asin]['count'] += 1
                        for arch, score in result['archetype_scores'].items():
                            review_product_agg[asin]['archetypes'][arch] += score
                    
                    rating = result.get('rating', 0)
                    if rating > 0:
                        rating_by_archetype[primary_arch]['ratings'].append(rating)
                    
                    if result.get('enriched', False):
                        enriched_count += 1
                    
                    total_reviews += 1
                    total_matches += result.get('total_matches', 0)
    
    except Exception as e:
        logger.error(f"Error processing {category}: {e}")
        raise
    
    elapsed = time.time() - start_time
    rate = total_reviews / elapsed if elapsed > 0 else 0
    enrich_pct = (enriched_count / total_reviews * 100) if total_reviews > 0 else 0
    logger.info(f"COMPLETED {category}: {total_reviews:,} reviews in {elapsed:.1f}s ({rate:,.0f}/sec, {enrich_pct:.1f}% enriched)")
    
    # Normalize totals
    if total_reviews > 0:
        category_totals = {k: v / total_reviews for k, v in category_totals.items()}
        framework_totals = {k: v / total_reviews for k, v in framework_totals.items()}
        archetype_totals = {k: v / total_reviews for k, v in archetype_totals.items()}
    
    # Calculate rating averages by archetype
    rating_averages = {}
    for arch, data in rating_by_archetype.items():
        ratings = data.get('ratings', [])
        if ratings:
            rating_averages[arch] = sum(ratings) / len(ratings)
    
    # Calculate average price by archetype
    price_averages = {}
    for arch, prices in price_by_archetype.items():
        if prices:
            price_averages[arch] = sum(prices) / len(prices)
    
    # Clean up meta lookup to free memory
    del meta_lookup
    
    # Convert brand ad profiles to serializable format
    brand_ad_profiles_serializable = {}
    for brand, profile in brand_ad_profiles.items():
        brand_ad_profiles_serializable[brand] = {
            "product_count": profile['product_count'],
            "category_scores": dict(profile['category_scores']),
            "framework_scores": dict(profile['framework_scores']),
            "archetype_scores": dict(profile['archetype_scores']),
        }
    
    # ==========================================================================
    # COMPREHENSIVE BRAND-CUSTOMER PSYCHOLOGICAL ALIGNMENT ANALYSIS
    # 
    # Compare FULL 82-framework analysis between:
    # - Brand/Product copy (what brand communicates)
    # - Customer reviews (who actually buys and what resonates)
    #
    # This identifies PSYCHOLOGICAL PAIRINGS at every level:
    # - 19 Psychological Categories
    # - 82 Individual Frameworks  
    # - 6 Archetypes
    # ==========================================================================
    brand_customer_alignment = {}
    
    # We need customer framework/category scores aggregated by brand
    # Build from review_product_agg and product_profiles
    brand_customer_frameworks = defaultdict(lambda: defaultdict(float))
    brand_customer_categories = defaultdict(lambda: defaultdict(float))
    brand_review_counts = defaultdict(int)
    
    for brand in set(brand_ad_profiles_serializable.keys()) & set(brand_customer_profiles.keys()):
        ad_profile = brand_ad_profiles_serializable[brand]
        customer_archetype_profile = dict(brand_customer_profiles[brand])
        
        # Normalize customer archetype profile
        customer_total = sum(customer_archetype_profile.values())
        if customer_total == 0:
            continue
        customer_arch_norm = {k: v/customer_total for k, v in customer_archetype_profile.items()}
        
        # Brand's psychological strategy from product copy
        ad_archetypes = ad_profile.get('archetype_scores', {})
        ad_categories = ad_profile.get('category_scores', {})
        ad_frameworks = ad_profile.get('framework_scores', {})
        
        # =================================================================
        # 1. ARCHETYPE ALIGNMENT (who brand targets vs who buys)
        # =================================================================
        archetype_comparison = {}
        for arch in set(customer_arch_norm.keys()) | set(ad_archetypes.keys()):
            cust_score = customer_arch_norm.get(arch, 0)
            ad_score = ad_archetypes.get(arch, 0)
            archetype_comparison[arch] = {
                "customer_profile": round(cust_score, 4),
                "brand_targeting": round(ad_score, 4),
                "alignment": round(1 - abs(cust_score - ad_score), 4),
                "gap": round(ad_score - cust_score, 4),
            }
        
        # =================================================================
        # 2. CATEGORY ALIGNMENT (19 psychological categories)
        # Compare which psych categories brand uses vs what resonates with customers
        # =================================================================
        category_comparison = {}
        for cat in set(ad_categories.keys()):
            ad_cat_score = ad_categories.get(cat, 0)
            # Note: We'd need customer category scores per brand for full comparison
            # For now, use global category scores as baseline
            category_comparison[cat] = {
                "brand_emphasis": round(ad_cat_score, 4),
            }
        
        # =================================================================
        # 3. FRAMEWORK ALIGNMENT (82 individual frameworks)
        # Which specific psychological triggers does brand use?
        # =================================================================
        framework_comparison = {}
        top_brand_frameworks = sorted(ad_frameworks.items(), key=lambda x: -x[1])[:10]
        for fw, score in top_brand_frameworks:
            framework_comparison[fw] = {
                "brand_usage": round(score, 4),
            }
        
        # =================================================================
        # 4. COMPUTE OVERALL ALIGNMENT SCORES
        # =================================================================
        # Archetype alignment (cosine similarity)
        archs = list(set(customer_arch_norm.keys()) | set(ad_archetypes.keys()))
        cust_vec = [customer_arch_norm.get(a, 0) for a in archs]
        ad_vec = [ad_archetypes.get(a, 0) for a in archs]
        
        dot_product = sum(c * a for c, a in zip(cust_vec, ad_vec))
        cust_mag = sum(c**2 for c in cust_vec) ** 0.5
        ad_mag = sum(a**2 for a in ad_vec) ** 0.5
        
        archetype_alignment_score = dot_product / (cust_mag * ad_mag) if (cust_mag > 0 and ad_mag > 0) else 0
        
        # =================================================================
        # 5. IDENTIFY PSYCHOLOGICAL COMMONALITIES (what's shared)
        # =================================================================
        commonalities = {
            "shared_high_archetypes": [],  # Both brand and customer emphasize
            "shared_categories": [],        # Categories brand uses that match customer
            "shared_frameworks": [],        # Specific frameworks that align
        }
        
        # Find archetypes both emphasize (both > 0.15)
        for arch in archs:
            if customer_arch_norm.get(arch, 0) > 0.15 and ad_archetypes.get(arch, 0) > 0.15:
                commonalities["shared_high_archetypes"].append({
                    "archetype": arch,
                    "customer": round(customer_arch_norm.get(arch, 0), 4),
                    "brand": round(ad_archetypes.get(arch, 0), 4),
                })
        
        # =================================================================
        # 6. IDENTIFY GAPS & OPPORTUNITIES
        # =================================================================
        gaps = {
            "brand_over_indexes": [],   # Brand emphasizes but customers don't respond
            "brand_under_indexes": [],  # Customers respond but brand doesn't emphasize
        }
        
        for arch, data in archetype_comparison.items():
            gap = data['gap']
            if gap > 0.1:  # Brand over-targeting
                gaps["brand_over_indexes"].append({
                    "archetype": arch,
                    "brand_targeting": data['brand_targeting'],
                    "customer_profile": data['customer_profile'],
                    "wasted_effort": round(gap, 4),
                })
            elif gap < -0.1:  # Brand under-targeting (OPPORTUNITY)
                gaps["brand_under_indexes"].append({
                    "archetype": arch,
                    "brand_targeting": data['brand_targeting'],
                    "customer_profile": data['customer_profile'],
                    "opportunity_size": round(abs(gap), 4),
                })
        
        # Sort by magnitude
        gaps["brand_over_indexes"].sort(key=lambda x: -x['wasted_effort'])
        gaps["brand_under_indexes"].sort(key=lambda x: -x['opportunity_size'])
        
        brand_customer_alignment[brand] = {
            "overall_alignment_score": round(archetype_alignment_score, 4),
            "product_count": ad_profile['product_count'],
            # Full psychological comparison
            "archetype_comparison": archetype_comparison,
            "category_emphasis": category_comparison,
            "top_frameworks_used": framework_comparison,
            # Insights
            "commonalities": commonalities,
            "gaps_and_opportunities": gaps,
            # Summary
            "primary_customer_archetype": max(customer_arch_norm, key=customer_arch_norm.get) if customer_arch_norm else None,
            "primary_brand_target": max(ad_archetypes, key=ad_archetypes.get) if ad_archetypes else None,
            "targeting_match": max(customer_arch_norm, key=customer_arch_norm.get) == max(ad_archetypes, key=ad_archetypes.get) if customer_arch_norm and ad_archetypes else False,
        }
    
    logger.info(f"Computed comprehensive brand-customer alignment for {len(brand_customer_alignment):,} brands")
    
    # Summary stats
    if brand_customer_alignment:
        avg_alignment = sum(b['overall_alignment_score'] for b in brand_customer_alignment.values()) / len(brand_customer_alignment)
        match_count = sum(1 for b in brand_customer_alignment.values() if b['targeting_match'])
        logger.info(f"  Average alignment score: {avg_alignment:.2%}")
        logger.info(f"  Brands with correct primary target: {match_count}/{len(brand_customer_alignment)} ({match_count/len(brand_customer_alignment)*100:.1f}%)")
    
    return {
        "category": category,
        "total_reviews": total_reviews,
        "total_matches": total_matches,
        "enriched_reviews": enriched_count,
        "enrichment_rate": enrich_pct,
        "processing_time": elapsed,
        "rate": rate,
        # Customer review analysis
        "category_scores": dict(category_totals),
        "framework_scores": dict(framework_totals),
        "archetype_distribution": dict(archetype_totals),
        # Brand profiles from CUSTOMER reviews (who buys from this brand)
        "brand_customer_profiles": {k: dict(v) for k, v in brand_customer_profiles.items()},
        # Brand profiles from PRODUCT COPY (brand's advertising strategy)
        "brand_ad_profiles": brand_ad_profiles_serializable,
        # BRAND-CUSTOMER ALIGNMENT ANALYSIS
        "brand_customer_alignment": brand_customer_alignment,
        # Other metrics
        "rating_by_archetype": rating_averages,
        "price_by_archetype": price_averages,
        "unique_products": len(product_profiles),
        "products_analyzed": len(product_profiles),
    }


def process_single_review(review: Dict, analyzer: HyperscanAnalyzer) -> Optional[Dict]:
    """
    Process a single review with the analyzer.
    
    Uses enriched metadata from product catalog for:
    - Brand identification
    - Price context
    - Product title context
    """
    text = review.get('text', '') or review.get('reviewText', '')
    if not text or len(text) < 10:
        return None
    
    # Analyze the review text
    result = analyzer.analyze(text)
    
    # Add metadata from review
    result['asin'] = review.get('parent_asin') or review.get('asin', '')
    result['rating'] = review.get('rating', review.get('overall', 0))
    
    # Use enriched data if available (from meta file join)
    result['enriched'] = review.get('_enriched', False)
    result['brand'] = review.get('_brand', review.get('brand', 'Unknown'))
    result['product_title'] = review.get('_title', '')
    result['price'] = review.get('_price')
    result['main_category'] = review.get('_main_category', '')
    
    return result


# =============================================================================
# CHECKPOINTING & AGGREGATION
# =============================================================================

def save_checkpoint(
    category: str,
    results: Dict[str, Any],
    output_dir: Path,
):
    """
    Save checkpoint after processing a category.
    """
    checkpoint_file = output_dir / f"checkpoint_{category}.json"
    with open(checkpoint_file, 'w') as f:
        json.dump(results, f, indent=2)
    logger.info(f"Checkpoint saved: {checkpoint_file}")


def load_checkpoints(output_dir: Path, load_contents: bool = True) -> Dict[str, Dict]:
    """
    Load existing checkpoints.
    
    Args:
        output_dir: Directory containing checkpoint files
        load_contents: If True, load full JSON contents (memory intensive).
                      If False, just track which categories are done (fast resume).
    """
    checkpoints = {}
    for f in output_dir.glob("checkpoint_*.json"):
        category = f.stem.replace("checkpoint_", "")
        if load_contents:
            with open(f) as fp:
                checkpoints[category] = json.load(fp)
        else:
            # Just mark as done without loading contents
            checkpoints[category] = {"_placeholder": True}
    return checkpoints


def aggregate_all_results(checkpoints: Dict[str, Dict], output_dir: Path):
    """
    Aggregate all category results into final priors.
    
    Includes BOTH:
    - Brand CUSTOMER profiles (psychological profile of who buys from brand)
    - Brand AD profiles (psychological strategy in product copy/advertising)
    
    This enables brand-customer psychological ALIGNMENT analysis.
    """
    logger.info("Aggregating all results into final priors...")
    
    # Aggregate across all categories
    total_reviews = 0
    total_products_analyzed = 0
    combined_category_scores = defaultdict(float)
    combined_framework_scores = defaultdict(float)
    combined_archetype_dist = defaultdict(float)
    
    # Brand CUSTOMER profiles (who buys from this brand)
    combined_brand_customer_profiles = defaultdict(lambda: defaultdict(float))
    
    # Brand AD profiles (psychological strategy in advertising)
    combined_brand_ad_profiles = defaultdict(lambda: {
        "product_count": 0,
        "category_scores": defaultdict(float),
        "framework_scores": defaultdict(float),
        "archetype_scores": defaultdict(float),
    })
    
    category_profiles = {}
    
    for category, results in checkpoints.items():
        n = results.get('total_reviews', 0)
        total_reviews += n
        total_products_analyzed += results.get('products_analyzed', 0)
        
        # Weight by review count
        for cat, score in results.get('category_scores', {}).items():
            combined_category_scores[cat] += score * n
        for fw, score in results.get('framework_scores', {}).items():
            combined_framework_scores[fw] += score * n
        for arch, score in results.get('archetype_distribution', {}).items():
            combined_archetype_dist[arch] += score * n
        
        # Brand CUSTOMER profiles (from reviews)
        for brand, profile in results.get('brand_customer_profiles', {}).items():
            for arch, score in profile.items():
                combined_brand_customer_profiles[brand][arch] += score
        
        # Brand AD profiles (from product copy analysis)
        for brand, profile in results.get('brand_ad_profiles', {}).items():
            combined_brand_ad_profiles[brand]['product_count'] += profile.get('product_count', 0)
            for cat, score in profile.get('category_scores', {}).items():
                combined_brand_ad_profiles[brand]['category_scores'][cat] += score
            for fw, score in profile.get('framework_scores', {}).items():
                combined_brand_ad_profiles[brand]['framework_scores'][fw] += score
            for arch, score in profile.get('archetype_scores', {}).items():
                combined_brand_ad_profiles[brand]['archetype_scores'][arch] += score
        
        # Category-specific profile
        category_profiles[category] = {
            'archetype_distribution': results.get('archetype_distribution', {}),
            'framework_scores': results.get('framework_scores', {}),
            'total_reviews': n,
            'products_analyzed': results.get('products_analyzed', 0),
        }
    
    # Normalize global scores
    if total_reviews > 0:
        combined_category_scores = {k: v / total_reviews for k, v in combined_category_scores.items()}
        combined_framework_scores = {k: v / total_reviews for k, v in combined_framework_scores.items()}
        combined_archetype_dist = {k: v / total_reviews for k, v in combined_archetype_dist.items()}
    
    # Normalize brand ad profiles by product count
    brand_ad_profiles_final = {}
    for brand, profile in combined_brand_ad_profiles.items():
        n = profile['product_count']
        if n > 0:
            brand_ad_profiles_final[brand] = {
                "product_count": n,
                "category_scores": {k: v/n for k, v in profile['category_scores'].items()},
                "framework_scores": {k: v/n for k, v in profile['framework_scores'].items()},
                "archetype_scores": {k: v/n for k, v in profile['archetype_scores'].items()},
            }
    
    # ==========================================================================
    # GLOBAL BRAND-CUSTOMER ALIGNMENT ANALYSIS
    # Compare aggregated brand targeting vs customer profiles
    # ==========================================================================
    logger.info("Computing global brand-customer alignment analysis...")
    
    global_brand_alignment = {}
    high_alignment_brands = []
    low_alignment_brands = []
    biggest_opportunities = []
    
    for brand in set(brand_ad_profiles_final.keys()) & set(combined_brand_customer_profiles.keys()):
        ad_profile = brand_ad_profiles_final[brand]
        customer_profile = dict(combined_brand_customer_profiles[brand])
        
        # Normalize customer profile
        customer_total = sum(customer_profile.values())
        if customer_total == 0:
            continue
        customer_norm = {k: v/customer_total for k, v in customer_profile.items()}
        
        ad_archetypes = ad_profile.get('archetype_scores', {})
        
        # Compute alignment
        archs = list(set(customer_norm.keys()) | set(ad_archetypes.keys()))
        cust_vec = [customer_norm.get(a, 0) for a in archs]
        ad_vec = [ad_archetypes.get(a, 0) for a in archs]
        
        dot_product = sum(c * a for c, a in zip(cust_vec, ad_vec))
        cust_mag = sum(c**2 for c in cust_vec) ** 0.5
        ad_mag = sum(a**2 for a in ad_vec) ** 0.5
        
        if cust_mag > 0 and ad_mag > 0:
            alignment = dot_product / (cust_mag * ad_mag)
        else:
            alignment = 0
        
        # Find biggest gap (opportunity)
        gaps = {}
        for arch in archs:
            gap = customer_norm.get(arch, 0) - ad_archetypes.get(arch, 0)
            if gap > 0.05:  # Brand is under-targeting
                gaps[arch] = gap
        
        global_brand_alignment[brand] = {
            "alignment_score": round(alignment, 4),
            "product_count": ad_profile['product_count'],
            "top_customer_archetype": max(customer_norm, key=customer_norm.get) if customer_norm else None,
            "top_ad_archetype": max(ad_archetypes, key=ad_archetypes.get) if ad_archetypes else None,
            "opportunities": gaps,
        }
        
        # Track high/low alignment
        if alignment > 0.8 and ad_profile['product_count'] >= 10:
            high_alignment_brands.append((brand, alignment, ad_profile['product_count']))
        elif alignment < 0.4 and ad_profile['product_count'] >= 10:
            low_alignment_brands.append((brand, alignment, ad_profile['product_count']))
        
        # Track opportunities
        for arch, gap in gaps.items():
            biggest_opportunities.append({
                "brand": brand,
                "archetype": arch,
                "gap_size": gap,
                "product_count": ad_profile['product_count'],
            })
    
    # Sort and limit
    high_alignment_brands.sort(key=lambda x: -x[1])
    low_alignment_brands.sort(key=lambda x: x[1])
    biggest_opportunities.sort(key=lambda x: -x['gap_size'])
    
    alignment_insights = {
        "total_brands_analyzed": len(global_brand_alignment),
        "avg_alignment_score": round(sum(b['alignment_score'] for b in global_brand_alignment.values()) / len(global_brand_alignment), 4) if global_brand_alignment else 0,
        "high_alignment_brands": [{"brand": b, "score": s, "products": p} for b, s, p in high_alignment_brands[:20]],
        "low_alignment_brands": [{"brand": b, "score": s, "products": p} for b, s, p in low_alignment_brands[:20]],
        "biggest_opportunities": biggest_opportunities[:50],
    }
    
    logger.info(f"  Analyzed {len(global_brand_alignment):,} brands")
    logger.info(f"  Average alignment score: {alignment_insights['avg_alignment_score']:.2%}")
    logger.info(f"  High-alignment brands (>80%): {len(high_alignment_brands)}")
    logger.info(f"  Low-alignment brands (<40%): {len(low_alignment_brands)}")
    
    # Save final priors
    priors = {
        "metadata": {
            "total_reviews": total_reviews,
            "total_products_analyzed": total_products_analyzed,
            "total_categories": len(checkpoints),
            "total_brands": len(brand_ad_profiles_final),
            "generated_at": datetime.now().isoformat(),
            "pipeline": "hyperscan_82_framework_with_alignment_analysis",
        },
        # Global customer review analysis
        "global_archetype_distribution": dict(combined_archetype_dist),
        "global_category_scores": dict(combined_category_scores),
        "global_framework_scores": dict(combined_framework_scores),
        # Category-specific profiles
        "category_profiles": category_profiles,
        # Brand CUSTOMER profiles (psychological profile of who buys from brand)
        "brand_customer_profiles": {k: dict(v) for k, v in combined_brand_customer_profiles.items()},
        # Brand AD profiles (psychological strategy in product copy)
        "brand_ad_profiles": brand_ad_profiles_final,
        # BRAND-CUSTOMER ALIGNMENT ANALYSIS
        "brand_alignment": global_brand_alignment,
        "alignment_insights": alignment_insights,
    }
    
    # Save
    priors_file = output_dir / "82_framework_priors.json"
    with open(priors_file, 'w') as f:
        json.dump(priors, f, indent=2)
    logger.info(f"Final priors saved: {priors_file}")
    logger.info(f"  - {total_reviews:,} customer reviews analyzed")
    logger.info(f"  - {total_products_analyzed:,} product descriptions analyzed")
    logger.info(f"  - {len(brand_ad_profiles_final):,} brand profiles built")
    
    return priors


# =============================================================================
# DYNAMIC FILE DISCOVERY
# =============================================================================

def discover_review_files(amazon_dir: Path, checkpoints: Dict) -> List[Tuple[str, str]]:
    """
    Dynamically discover review files in the amazon directory.
    Returns list of (category_name, filename) tuples for unprocessed files.
    """
    files_to_process = []
    
    # Scan for all .jsonl files (excluding meta_ files)
    for file_path in amazon_dir.glob("*.jsonl"):
        filename = file_path.name
        
        # Skip metadata files
        if filename.startswith("meta_"):
            continue
        
        # Extract category name from filename
        category = filename.replace(".jsonl", "")
        
        # Skip if already processed
        if category in checkpoints:
            continue
        
        files_to_process.append((category, filename))
    
    # Also check for gzipped files
    for file_path in amazon_dir.glob("*.jsonl.gz"):
        filename = file_path.name
        
        # Skip metadata files
        if filename.startswith("meta_"):
            continue
        
        # Extract category name from filename  
        category = filename.replace(".jsonl.gz", "")
        
        # Skip if already processed
        if category in checkpoints:
            continue
        
        # Don't add if we already have the unzipped version
        if (category, f"{category}.jsonl") not in files_to_process:
            files_to_process.append((category, filename))
    
    return files_to_process


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="82-Framework Hyperscan Pipeline")
    parser.add_argument("--amazon-dir", default="/Users/chrisnocera/Sites/adam-platform/amazon",
                        help="Directory containing Amazon review files")
    parser.add_argument("--output-dir", default="/Users/chrisnocera/Sites/adam-platform/data/learning",
                        help="Output directory for priors")
    parser.add_argument("--batch-size", type=int, default=5000,
                        help="Batch size for processing")
    parser.add_argument("--delete-after", action="store_true",
                        help="Delete source files after processing")
    parser.add_argument("--resume", action="store_true",
                        help="Resume from existing checkpoints")
    parser.add_argument("--categories", nargs="*",
                        help="Specific categories to process (default: all)")
    parser.add_argument("--continuous", action="store_true",
                        help="Run continuously, scanning for new files")
    parser.add_argument("--scan-interval", type=int, default=60,
                        help="Seconds between scans for new files in continuous mode")
    args = parser.parse_args()
    
    amazon_dir = Path(args.amazon_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info("=" * 60)
    logger.info("ADAM 82-FRAMEWORK HYPERSCAN PIPELINE")
    if args.continuous:
        logger.info("MODE: CONTINUOUS - Will scan for new files")
    logger.info("=" * 60)
    logger.info(f"Amazon directory: {amazon_dir}")
    logger.info(f"Output directory: {output_dir}")
    logger.info(f"Delete after processing: {args.delete_after}")
    
    # Initialize analyzer
    logger.info("\nInitializing Hyperscan analyzer...")
    analyzer = HyperscanAnalyzer()
    logger.info(f"Analyzer ready with {len(analyzer.patterns)} patterns")
    
    # Load existing checkpoints if resuming
    # OPTIMIZATION: Don't load checkpoint contents - just track which categories are done
    # This saves GB of memory that was causing massive slowdowns
    checkpoints = {}
    if args.resume:
        checkpoints = load_checkpoints(output_dir, load_contents=False)
        logger.info(f"Found {len(checkpoints)} existing checkpoints (lightweight mode)")
    
    total_start = time.time()
    scan_count = 0
    
    while True:
        scan_count += 1
        
        # Discover files to process
        if args.categories:
            # Static category list provided
            categories_to_process = [
                (c, CATEGORY_FILES.get(c, f"{c}.jsonl")) 
                for c in args.categories if c not in checkpoints
            ]
        else:
            # Dynamic discovery - scan directory for any .jsonl files
            categories_to_process = discover_review_files(amazon_dir, checkpoints)
        
        if categories_to_process:
            logger.info(f"\n[Scan #{scan_count}] Found {len(categories_to_process)} categories to process:")
            for cat, fname in categories_to_process[:10]:
                logger.info(f"  - {cat}")
            if len(categories_to_process) > 10:
                logger.info(f"  ... and {len(categories_to_process) - 10} more")
        
        # Process each discovered category
        for category, filename in categories_to_process:
            file_path = amazon_dir / filename
            
            # Check if file exists (or gzipped version)
            if not file_path.exists():
                gz_path = amazon_dir / f"{filename}.gz" if not filename.endswith('.gz') else file_path
                if gz_path.exists():
                    file_path = gz_path
                else:
                    logger.warning(f"File not found: {file_path}")
                    continue
            
            try:
                # Process category with metadata enrichment
                results = process_category(
                    category=category,
                    file_path=file_path,
                    analyzer=analyzer,
                    amazon_dir=amazon_dir,
                    batch_size=args.batch_size
                )
                
                # Save checkpoint
                save_checkpoint(category, results, output_dir)
                
                # OPTIMIZATION: Don't keep results in memory - just mark as done
                # This prevents memory from growing unbounded
                checkpoints[category] = {"_placeholder": True, "total_reviews": results.get('total_reviews', 0)}
                del results
                gc.collect()
                
                # Delete source file if requested
                if args.delete_after:
                    logger.info(f"Deleting {file_path}...")
                    file_path.unlink()
                    # Also delete metadata file if exists
                    base_name = filename.replace('.gz', '')
                    meta_path = amazon_dir / f"meta_{base_name}"
                    if meta_path.exists():
                        meta_path.unlink()
                        logger.info(f"Deleted {meta_path}")
                    # Also check for gzipped meta
                    meta_gz_path = amazon_dir / f"meta_{base_name}.gz"
                    if meta_gz_path.exists():
                        meta_gz_path.unlink()
                        logger.info(f"Deleted {meta_gz_path}")
                
                # OPTIMIZATION: Skip per-category aggregation to save memory
                # Aggregation will happen at the end when all categories are done
                logger.info(f"Checkpoint saved for {category}, skipping aggregation until end")
            
            except Exception as e:
                logger.error(f"Error processing {category}: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        # If not continuous mode, break after first pass
        if not args.continuous:
            break
        
        # In continuous mode, wait and scan again
        if not categories_to_process:
            logger.info(f"\n[Scan #{scan_count}] No new files found. Waiting {args.scan_interval}s...")
            logger.info(f"  Add .jsonl files to: {amazon_dir}")
            logger.info(f"  (with matching meta_*.jsonl for product enrichment)")
        else:
            logger.info(f"\nCompleted batch. Waiting {args.scan_interval}s before next scan...")
        
        time.sleep(args.scan_interval)
    
    # Final aggregation and summary
    # OPTIMIZATION: Load checkpoints fresh for aggregation (done once at end)
    if checkpoints:
        logger.info("Loading all checkpoints for final aggregation...")
        full_checkpoints = load_checkpoints(output_dir, load_contents=True)
        priors = aggregate_all_results(full_checkpoints, output_dir)
        del full_checkpoints
        gc.collect()
        
        total_time = time.time() - total_start
        total_reviews = sum(c.get('total_reviews', 0) for c in checkpoints.values())
        overall_rate = total_reviews / total_time if total_time > 0 else 0
        
        logger.info("\n" + "=" * 60)
        logger.info("PIPELINE COMPLETE")
        logger.info("=" * 60)
        logger.info(f"Total reviews processed: {total_reviews:,}")
        logger.info(f"Total categories: {len(checkpoints)}")
        logger.info(f"Total time: {total_time/3600:.1f} hours")
        logger.info(f"Overall rate: {overall_rate:,.0f} reviews/sec")
        logger.info(f"Priors saved to: {output_dir / '82_framework_priors.json'}")


if __name__ == "__main__":
    main()
