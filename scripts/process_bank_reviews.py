#!/usr/bin/env python3
"""
ADAM BANK REVIEW PROCESSING & INTEGRATION
==========================================

Processes 19,271 bank customer reviews from HuggingFace and integrates them
into the ADAM psychological intelligence system.

INTEGRATION POINTS:
1. Creates checkpoint file for multi-domain aggregation
2. Extracts 82-framework psychological constructs
3. Adds banking-specific psychological markers
4. Maps to Finance_Banking category
5. Creates Neo4j import data for graph integration
6. Feeds into LangGraph pre-fetch for financial products

UNIQUE VALUE:
- Trust/security psychology (critical for financial decisions)
- Customer service interaction patterns
- Financial anxiety indicators
- Brand loyalty in banking context
- Geographic banking preferences

Author: ADAM Platform
"""

import csv
import json
import logging
import os
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# =============================================================================
# LOGGING SETUP
# =============================================================================
log_dir = Path(__file__).parent.parent / "logs"
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_dir / 'bank_review_processing.log')
    ]
)
logger = logging.getLogger(__name__)


# =============================================================================
# BANKING-SPECIFIC PSYCHOLOGICAL MARKERS
# =============================================================================

BANKING_PSYCHOLOGY_MARKERS = {
    # Trust & Security (Critical for financial decisions)
    "trust_security": {
        "patterns": [
            r"\b(trust|trustworthy|reliable|secure|safe|protected)\b",
            r"\b(peace of mind|confidence|dependable|honest)\b",
            r"\b(fraud protection|security|encryption|verified)\b",
            r"\b(reputation|established|reputable|legitimate)\b",
        ],
        "cialdini_mapping": "authority",
        "weight": 1.3
    },
    
    # Financial Anxiety Indicators
    "financial_anxiety": {
        "patterns": [
            r"\b(worried|anxious|nervous|scared|concerned about)\b",
            r"\b(bankruptcy|debt|struggling|behind on|late payment)\b",
            r"\b(rebuild credit|bad credit|poor credit|credit score)\b",
            r"\b(cant afford|too expensive|fees|charges|interest rate)\b",
        ],
        "cialdini_mapping": "fear_appeal",
        "weight": 1.2
    },
    
    # Customer Service Experience
    "service_experience": {
        "patterns": [
            r"\b(customer service|representative|support|help desk)\b",
            r"\b(wait time|hold|transferred|call center)\b",
            r"\b(helpful|rude|professional|courteous|friendly)\b",
            r"\b(resolved|fixed|handled|addressed|solved)\b",
        ],
        "cialdini_mapping": "liking",
        "weight": 1.1
    },
    
    # Digital Banking Preference
    "digital_preference": {
        "patterns": [
            r"\b(app|website|online|mobile|digital)\b",
            r"\b(easy to use|user friendly|convenient|quick)\b",
            r"\b(login|navigate|interface|dashboard)\b",
            r"\b(transfer|pay bill|check balance|statement)\b",
        ],
        "cialdini_mapping": "ease",
        "weight": 1.0
    },
    
    # Credit Building Focus
    "credit_building": {
        "patterns": [
            r"\b(build credit|improve credit|credit score|credit limit)\b",
            r"\b(increase|approved|starter card|secured card)\b",
            r"\b(fico|credit report|credit bureau|reporting)\b",
            r"\b(on time|payment history|responsible)\b",
        ],
        "cialdini_mapping": "commitment",
        "weight": 1.2
    },
    
    # Reward Sensitivity
    "reward_sensitivity": {
        "patterns": [
            r"\b(reward|cashback|points|miles|benefits)\b",
            r"\b(earn|bonus|incentive|promotion|offer)\b",
            r"\b(no fee|no annual fee|waived|free)\b",
            r"\b(rate|apr|interest|percent)\b",
        ],
        "cialdini_mapping": "reciprocity",
        "weight": 1.1
    },
    
    # Relationship Duration (Loyalty Indicator)
    "relationship_duration": {
        "patterns": [
            r"\b(years|months|long time|since \d{4})\b",
            r"\b(loyal|continue|stay|keep|maintain)\b",
            r"\b(recommend|refer|tell friends|family member)\b",
            r"\b(never had|always been|consistently)\b",
        ],
        "cialdini_mapping": "commitment",
        "weight": 1.0
    },
    
    # Problem Resolution
    "problem_resolution": {
        "patterns": [
            r"\b(problem|issue|dispute|charge|unauthorized)\b",
            r"\b(refund|credit back|reversed|corrected)\b",
            r"\b(fraud|stolen|compromised|hacked)\b",
            r"\b(new card|replacement|cancelled|blocked)\b",
        ],
        "cialdini_mapping": "authority",
        "weight": 1.1
    },
}


# =============================================================================
# CORE 82-FRAMEWORK PATTERNS (Subset for bank reviews)
# =============================================================================

CORE_FRAMEWORK_PATTERNS = {
    # Big Five Personality
    "openness": [
        r"\b(new feature|try|explore|different|innovative)\b",
        r"\b(curious|interested in|learn about)\b",
    ],
    "conscientiousness": [
        r"\b(organized|schedule|plan|budget|track)\b",
        r"\b(responsible|diligent|careful|precise)\b",
        r"\b(on time|never late|always pay)\b",
    ],
    "extraversion": [
        r"\b(recommend|tell everyone|share|spread)\b",
        r"\b(talk to|call|speak with|contact)\b",
    ],
    "agreeableness": [
        r"\b(understand|patient|helpful|kind|nice)\b",
        r"\b(appreciate|grateful|thank)\b",
    ],
    "neuroticism": [
        r"\b(frustrated|angry|upset|annoyed|hate)\b",
        r"\b(worried|anxious|stressed|nervous)\b",
    ],
    
    # Regulatory Focus
    "promotion_focus": [
        r"\b(gain|earn|reward|benefit|opportunity)\b",
        r"\b(achieve|succeed|advance|grow)\b",
    ],
    "prevention_focus": [
        r"\b(protect|secure|safe|avoid|prevent)\b",
        r"\b(risk|loss|fee|charge|penalty)\b",
    ],
    
    # Decision Style
    "analytical": [
        r"\b(compare|research|evaluate|review|consider)\b",
        r"\b(rate|apr|fee structure|terms)\b",
    ],
    "intuitive": [
        r"\b(feel|sense|gut|impression|vibe)\b",
        r"\b(just know|seems like|felt right)\b",
    ],
    
    # Social Proof
    "social_proof": [
        r"\b(recommend|everyone|popular|many people)\b",
        r"\b(friend|family|colleague|coworker)\b",
        r"\b(reviews|ratings|reputation)\b",
    ],
    
    # Authority
    "authority": [
        r"\b(professional|expert|representative|manager)\b",
        r"\b(policy|regulation|compliance|rules)\b",
    ],
}


# =============================================================================
# ARCHETYPE DETECTION PATTERNS
# =============================================================================

ARCHETYPE_PATTERNS = {
    "achiever": [
        r"\b(goal|achieve|succeed|accomplish|advance)\b",
        r"\b(improve|better|increase|grow|progress)\b",
        r"\b(credit score|limit increase|upgrade)\b",
    ],
    "explorer": [
        r"\b(try|new|different|switch|change)\b",
        r"\b(compare|shop around|options|alternatives)\b",
    ],
    "connector": [
        r"\b(recommend|share|tell|friend|family)\b",
        r"\b(community|together|relationship)\b",
    ],
    "guardian": [
        r"\b(protect|secure|safe|reliable|stable)\b",
        r"\b(trust|dependable|consistent|always)\b",
    ],
    "pragmatist": [
        r"\b(value|cost|fee|price|affordable)\b",
        r"\b(practical|efficient|straightforward)\b",
    ],
    "analyst": [
        r"\b(research|compare|evaluate|analyze|review)\b",
        r"\b(details|fine print|terms|conditions)\b",
    ],
}


# =============================================================================
# PROCESSING FUNCTIONS
# =============================================================================

def compile_patterns():
    """Compile all regex patterns for efficiency."""
    compiled = {
        "banking": {},
        "framework": {},
        "archetype": {},
    }
    
    # Banking patterns
    for category, data in BANKING_PSYCHOLOGY_MARKERS.items():
        patterns = data["patterns"]
        compiled["banking"][category] = {
            "regex": [re.compile(p, re.IGNORECASE) for p in patterns],
            "cialdini": data["cialdini_mapping"],
            "weight": data["weight"],
        }
    
    # Framework patterns
    for category, patterns in CORE_FRAMEWORK_PATTERNS.items():
        compiled["framework"][category] = [
            re.compile(p, re.IGNORECASE) for p in patterns
        ]
    
    # Archetype patterns
    for archetype, patterns in ARCHETYPE_PATTERNS.items():
        compiled["archetype"][archetype] = [
            re.compile(p, re.IGNORECASE) for p in patterns
        ]
    
    return compiled


def analyze_review(text: str, compiled_patterns: Dict) -> Dict[str, Any]:
    """
    Analyze a single review for psychological constructs.
    
    Returns:
        Dict with framework scores, banking scores, archetype scores
    """
    if not text or not isinstance(text, str):
        return None
    
    text_lower = text.lower()
    
    # Banking psychology scores
    banking_scores = {}
    cialdini_scores = defaultdict(float)
    
    for category, data in compiled_patterns["banking"].items():
        matches = sum(1 for regex in data["regex"] if regex.search(text_lower))
        if matches > 0:
            score = min(matches * data["weight"] * 0.2, 1.0)
            banking_scores[category] = score
            cialdini_scores[data["cialdini"]] += score * 0.5
    
    # Framework scores
    framework_scores = {}
    for category, regexes in compiled_patterns["framework"].items():
        matches = sum(1 for regex in regexes if regex.search(text_lower))
        if matches > 0:
            framework_scores[category] = min(matches * 0.25, 1.0)
    
    # Archetype scores
    archetype_scores = {}
    for archetype, regexes in compiled_patterns["archetype"].items():
        matches = sum(1 for regex in regexes if regex.search(text_lower))
        if matches > 0:
            archetype_scores[archetype] = min(matches * 0.3, 1.0)
    
    # Normalize archetype scores
    total_arch = sum(archetype_scores.values())
    if total_arch > 0:
        archetype_scores = {k: v/total_arch for k, v in archetype_scores.items()}
    
    return {
        "banking_psychology": banking_scores,
        "cialdini_principles": dict(cialdini_scores),
        "framework_scores": framework_scores,
        "archetype_scores": archetype_scores,
        "text_length": len(text),
    }


def process_bank_reviews(input_path: Path) -> Dict[str, Any]:
    """
    Process all bank reviews and aggregate psychological profiles.
    
    Returns:
        Aggregated checkpoint data ready for integration
    """
    logger.info(f"Processing bank reviews from {input_path}")
    
    compiled = compile_patterns()
    
    # Aggregation structures
    bank_profiles = defaultdict(lambda: {
        "total_reviews": 0,
        "avg_rating": 0,
        "rating_sum": 0,
        "banking_psychology": defaultdict(float),
        "cialdini_principles": defaultdict(float),
        "framework_scores": defaultdict(float),
        "archetype_distribution": defaultdict(float),
        "locations": defaultdict(int),
    })
    
    total_reviews = 0
    total_analyzed = 0
    
    # Global aggregations
    global_banking = defaultdict(float)
    global_cialdini = defaultdict(float)
    global_framework = defaultdict(float)
    global_archetype = defaultdict(float)
    
    with open(input_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            total_reviews += 1
            
            bank = row.get('bank', 'unknown')
            text = row.get('text', '')
            rating = int(row.get('star', 3))
            location = row.get('location', 'Unknown')
            
            # Analyze review
            analysis = analyze_review(text, compiled)
            
            if analysis:
                total_analyzed += 1
                
                # Update bank profile
                profile = bank_profiles[bank]
                profile["total_reviews"] += 1
                profile["rating_sum"] += rating
                
                # Aggregate banking psychology
                for cat, score in analysis["banking_psychology"].items():
                    profile["banking_psychology"][cat] += score
                    global_banking[cat] += score
                
                # Aggregate Cialdini
                for principle, score in analysis["cialdini_principles"].items():
                    profile["cialdini_principles"][principle] += score
                    global_cialdini[principle] += score
                
                # Aggregate framework
                for fw, score in analysis["framework_scores"].items():
                    profile["framework_scores"][fw] += score
                    global_framework[fw] += score
                
                # Aggregate archetype
                for arch, score in analysis["archetype_scores"].items():
                    profile["archetype_distribution"][arch] += score
                    global_archetype[arch] += score
                
                # Track location
                if location:
                    state = location.split(',')[-1].strip() if ',' in location else location
                    profile["locations"][state] += 1
            
            if total_reviews % 5000 == 0:
                logger.info(f"  Processed {total_reviews:,} reviews...")
    
    logger.info(f"Processed {total_reviews:,} reviews, analyzed {total_analyzed:,}")
    
    # Normalize bank profiles
    for bank, profile in bank_profiles.items():
        count = profile["total_reviews"]
        if count > 0:
            profile["avg_rating"] = profile["rating_sum"] / count
            del profile["rating_sum"]
            
            # Normalize scores
            for cat in profile["banking_psychology"]:
                profile["banking_psychology"][cat] /= count
            for cat in profile["cialdini_principles"]:
                profile["cialdini_principles"][cat] /= count
            for cat in profile["framework_scores"]:
                profile["framework_scores"][cat] /= count
            for arch in profile["archetype_distribution"]:
                profile["archetype_distribution"][arch] /= count
            
            # Convert defaultdicts to regular dicts
            profile["banking_psychology"] = dict(profile["banking_psychology"])
            profile["cialdini_principles"] = dict(profile["cialdini_principles"])
            profile["framework_scores"] = dict(profile["framework_scores"])
            profile["archetype_distribution"] = dict(profile["archetype_distribution"])
            profile["locations"] = dict(profile["locations"])
    
    # Normalize global scores
    if total_analyzed > 0:
        global_banking = {k: v/total_analyzed for k, v in global_banking.items()}
        global_cialdini = {k: v/total_analyzed for k, v in global_cialdini.items()}
        global_framework = {k: v/total_analyzed for k, v in global_framework.items()}
        global_archetype = {k: v/total_analyzed for k, v in global_archetype.items()}
    
    # Build checkpoint structure
    checkpoint = {
        "source": "bank_reviews_huggingface",
        "category": "Finance_Banking",
        "total_reviews": total_reviews,
        "analyzed_reviews": total_analyzed,
        "total_banks": len(bank_profiles),
        "processed_at": datetime.now().isoformat(),
        
        # Global aggregations
        "banking_psychology_global": dict(global_banking),
        "cialdini_principles_global": dict(global_cialdini),
        "framework_totals": dict(global_framework),
        "archetype_totals": dict(global_archetype),
        
        # Per-bank profiles
        "profiles": {k: dict(v) for k, v in bank_profiles.items()},
        
        # Metadata for integration
        "integration_metadata": {
            "domain_category": "Finance_Banking",
            "persuasion_weight": 1.2,  # Higher weight for financial decisions
            "trust_critical": True,
            "anxiety_sensitive": True,
        }
    }
    
    return checkpoint


def create_neo4j_import(checkpoint: Dict) -> List[Dict]:
    """
    Create Neo4j import data for graph integration.
    
    Creates:
    - Bank nodes with psychological profiles
    - BankReviewProfile nodes
    - Mechanism effectiveness edges
    """
    neo4j_data = []
    
    # Create bank nodes
    for bank_name, profile in checkpoint["profiles"].items():
        bank_node = {
            "type": "Bank",
            "name": bank_name,
            "category": "Finance_Banking",
            "total_reviews": profile["total_reviews"],
            "avg_rating": profile["avg_rating"],
            "dominant_archetype": max(profile["archetype_distribution"].items(), 
                                      key=lambda x: x[1])[0] if profile["archetype_distribution"] else "guardian",
            "trust_score": profile["banking_psychology"].get("trust_security", 0),
            "anxiety_sensitivity": profile["banking_psychology"].get("financial_anxiety", 0),
            "digital_preference": profile["banking_psychology"].get("digital_preference", 0),
        }
        neo4j_data.append(bank_node)
        
        # Create mechanism effectiveness edges
        for principle, score in profile["cialdini_principles"].items():
            if score > 0.1:
                edge = {
                    "type": "MECHANISM_EFFECTIVENESS",
                    "from_type": "Bank",
                    "from_name": bank_name,
                    "to_type": "CognitiveMechanism",
                    "to_name": principle,
                    "effectiveness": score,
                    "source": "bank_reviews",
                }
                neo4j_data.append(edge)
    
    return neo4j_data


def main():
    """Main processing pipeline."""
    project_root = Path(__file__).parent.parent
    
    # Input/output paths
    input_path = project_root / "data" / "external_reviews" / "bank_reviews_huggingface.csv"
    output_dir = project_root / "data" / "learning" / "multi_domain"
    neo4j_dir = project_root / "data" / "neo4j_import"
    
    output_dir.mkdir(parents=True, exist_ok=True)
    neo4j_dir.mkdir(parents=True, exist_ok=True)
    
    if not input_path.exists():
        logger.error(f"Input file not found: {input_path}")
        sys.exit(1)
    
    # Process reviews
    logger.info("=" * 70)
    logger.info("ADAM BANK REVIEW PROCESSING")
    logger.info("=" * 70)
    
    checkpoint = process_bank_reviews(input_path)
    
    # Save checkpoint
    checkpoint_path = output_dir / "checkpoint_bank_reviews.json"
    with open(checkpoint_path, 'w') as f:
        json.dump(checkpoint, f, indent=2)
    logger.info(f"Saved checkpoint to {checkpoint_path}")
    
    # Create Neo4j import data
    neo4j_data = create_neo4j_import(checkpoint)
    neo4j_path = neo4j_dir / "bank_reviews_import.json"
    with open(neo4j_path, 'w') as f:
        json.dump(neo4j_data, f, indent=2)
    logger.info(f"Saved Neo4j import data to {neo4j_path}")
    
    # Print summary
    logger.info("")
    logger.info("=" * 70)
    logger.info("PROCESSING COMPLETE")
    logger.info("=" * 70)
    logger.info(f"Total reviews: {checkpoint['total_reviews']:,}")
    logger.info(f"Banks covered: {checkpoint['total_banks']}")
    logger.info(f"Category: {checkpoint['category']}")
    logger.info("")
    logger.info("Global Archetype Distribution:")
    for arch, score in sorted(checkpoint['archetype_totals'].items(), 
                               key=lambda x: -x[1]):
        logger.info(f"  {arch}: {score:.3f}")
    logger.info("")
    logger.info("Banking Psychology Insights:")
    for cat, score in sorted(checkpoint['banking_psychology_global'].items(),
                              key=lambda x: -x[1]):
        logger.info(f"  {cat}: {score:.3f}")
    logger.info("")
    logger.info("Top Cialdini Principles:")
    for principle, score in sorted(checkpoint['cialdini_principles_global'].items(),
                                    key=lambda x: -x[1])[:5]:
        logger.info(f"  {principle}: {score:.3f}")
    
    logger.info("")
    logger.info("NEXT STEPS:")
    logger.info("1. Run: python scripts/integrate_all_review_sources.py")
    logger.info("2. Run: python scripts/import_reingestion_to_neo4j.py --include-banks")
    logger.info("3. Verify: Bank intelligence available in ReviewIntelligenceAtom")
    
    return checkpoint


if __name__ == "__main__":
    main()
