#!/usr/bin/env python3
"""
ENHANCED PATTERN DISCOVERY FOR PERSONALIZED PERSUASION
=======================================================

Analyzes existing learned priors to discover additional predictive patterns
that can improve the strength of persuasive personalized recommendations.

DISCOVERS:
1. Phrase Pattern → Archetype Correlations
2. Cross-Principle Synergy Effects
3. Decision Style → Persuasion Mapping
4. Emotional Intensity Optimization
5. Category-Archetype-Persuasion Chains
6. Temporal Receptivity Patterns
7. Rating Behavior → Persuasion Susceptibility
8. Social Influence Type Targeting
"""

import json
import logging
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DATA_DIR = Path("/Users/chrisnocera/Sites/adam-platform/data/learning")


def load_all_priors() -> Dict[str, Any]:
    """Load all available prior files."""
    priors = {}
    
    files = [
        "language_patterns.json",
        "persuasion_priors.json",
        "enhanced_psycholinguistic_priors.json",
        "complete_coldstart_priors.json",
        "google_enhanced_priors.json",
        "specialty_reviews_priors.json",
        "temporal_patterns.json",
        "brand_loyalty_patterns.json",
    ]
    
    for filename in files:
        path = DATA_DIR / filename
        if path.exists():
            with open(path) as f:
                key = filename.replace('.json', '')
                priors[key] = json.load(f)
                logger.info(f"Loaded {filename}")
    
    return priors


def discover_phrase_persuasion_correlations(priors: Dict) -> Dict[str, Any]:
    """
    Discover correlations between phrase patterns and persuasion susceptibility.
    """
    language = priors.get("language_patterns", {})
    persuasion = priors.get("persuasion_priors", {})
    
    correlations = {}
    
    # Map phrase types to persuasion principles
    phrase_principle_map = {
        "recommendation_phrases": "social_proof",  # Recommendations indicate social influence
        "warning_phrases": "scarcity",  # Warnings often relate to loss/scarcity
        "intensifier_patterns": "liking",  # Intensifiers show emotional engagement
        "comparison_phrases": "authority",  # Comparisons often reference standards
    }
    
    for archetype in ["Connector", "Explorer", "Achiever", "Guardian", "Analyzer"]:
        arch_correlations = {}
        
        # Get persuasion sensitivity for this archetype
        persuasion_sens = persuasion.get("archetype_persuasion_sensitivity", {}).get(archetype, {})
        
        # Count phrase patterns
        for phrase_type, principle in phrase_principle_map.items():
            phrase_key = f"{phrase_type}_by_archetype"
            phrases = language.get(phrase_key, {}).get(archetype, [])
            
            if isinstance(phrases, list):
                phrase_count = len(phrases)
                principle_sensitivity = persuasion_sens.get(principle, {}).get("avg_sensitivity", 0.5)
                
                arch_correlations[phrase_type] = {
                    "phrase_count": phrase_count,
                    "related_principle": principle,
                    "principle_sensitivity": principle_sensitivity,
                    "correlation_strength": phrase_count * principle_sensitivity / 100,
                }
        
        correlations[archetype] = arch_correlations
    
    return correlations


def discover_cross_principle_synergies(priors: Dict) -> Dict[str, Any]:
    """
    Discover which persuasion principles work well together for each archetype.
    """
    persuasion = priors.get("persuasion_priors", {})
    
    synergies = {}
    
    principles = ["social_proof", "authority", "scarcity", "reciprocity", "commitment", "liking"]
    
    for archetype in ["Connector", "Explorer", "Achiever", "Guardian", "Analyzer"]:
        persuasion_sens = persuasion.get("archetype_persuasion_sensitivity", {}).get(archetype, {})
        
        # Get sensitivities
        sensitivities = {}
        for principle in principles:
            sens_data = persuasion_sens.get(principle, {})
            sensitivities[principle] = sens_data.get("avg_sensitivity", 0.5)
        
        # Find top principles
        sorted_principles = sorted(sensitivities.items(), key=lambda x: x[1], reverse=True)
        
        # Calculate synergy scores (multiply top principles)
        top_2 = sorted_principles[:2]
        top_3 = sorted_principles[:3]
        
        synergy_2 = top_2[0][1] * top_2[1][1] if len(top_2) >= 2 else 0
        synergy_3 = np.prod([p[1] for p in top_3]) ** (1/3) if len(top_3) >= 3 else 0
        
        synergies[archetype] = {
            "ranked_principles": [
                {"principle": p, "sensitivity": round(s, 4)} 
                for p, s in sorted_principles
            ],
            "recommended_combination": {
                "primary": top_2[0][0] if top_2 else "social_proof",
                "secondary": top_2[1][0] if len(top_2) > 1 else "liking",
                "synergy_score": round(synergy_2, 4),
            },
            "triple_combination": {
                "principles": [p[0] for p in top_3],
                "geometric_mean": round(synergy_3, 4),
            },
        }
    
    return synergies


def discover_decision_persuasion_mapping(priors: Dict) -> Dict[str, Any]:
    """
    Map decision styles to optimal persuasion strategies.
    """
    persuasion = priors.get("persuasion_priors", {})
    
    mapping = {}
    
    # Decision style to CTA mapping
    style_cta_map = {
        "analytical": {
            "cta_phrases": [
                "Compare options",
                "See the details",
                "Learn more",
                "View specifications",
                "Read reviews",
            ],
            "message_style": "factual",
            "recommended_length": "long",
            "use_statistics": True,
        },
        "impulsive": {
            "cta_phrases": [
                "Buy now",
                "Get it today",
                "Limited time",
                "Don't miss out",
                "Act fast",
            ],
            "message_style": "urgent",
            "recommended_length": "short",
            "use_statistics": False,
        },
        "social": {
            "cta_phrases": [
                "Join thousands",
                "See what others say",
                "Share with friends",
                "Most popular choice",
                "Trending now",
            ],
            "message_style": "social_proof_heavy",
            "recommended_length": "medium",
            "use_statistics": True,  # Social numbers
        },
        "balanced": {
            "cta_phrases": [
                "Discover now",
                "Find out more",
                "Start here",
                "Try it today",
                "See for yourself",
            ],
            "message_style": "balanced",
            "recommended_length": "medium",
            "use_statistics": True,
        },
    }
    
    for archetype in ["Connector", "Explorer", "Achiever", "Guardian", "Analyzer"]:
        decision_styles = persuasion.get("archetype_decision_styles", {}).get(archetype, {})
        
        # Find dominant style
        style_probs = {}
        for style in ["analytical", "impulsive", "social", "balanced"]:
            style_probs[style] = decision_styles.get(style, 0.25)
        
        dominant_style = max(style_probs.items(), key=lambda x: x[1])
        
        mapping[archetype] = {
            "style_distribution": {k: round(v, 4) for k, v in style_probs.items()},
            "dominant_style": dominant_style[0],
            "dominant_confidence": round(dominant_style[1], 4),
            "recommended_strategy": style_cta_map.get(dominant_style[0], style_cta_map["balanced"]),
        }
    
    return mapping


def discover_emotional_optimization(priors: Dict) -> Dict[str, Any]:
    """
    Discover optimal emotional intensity and triggers for each archetype.
    """
    persuasion = priors.get("persuasion_priors", {})
    enhanced = priors.get("enhanced_psycholinguistic_priors", {})
    
    optimization = {}
    
    emotions = ["fear_anxiety", "excitement", "trust", "nostalgia", "status", "value"]
    
    for archetype in ["Connector", "Explorer", "Achiever", "Guardian", "Analyzer"]:
        emotion_sens = persuasion.get("archetype_emotion_sensitivity", {}).get(archetype, {})
        
        # Get emotion sensitivities
        sensitivities = {}
        for emotion in emotions:
            sens_data = emotion_sens.get(emotion, {})
            sensitivities[emotion] = sens_data.get("avg_sensitivity", 0.5)
        
        # Sort by sensitivity
        sorted_emotions = sorted(sensitivities.items(), key=lambda x: x[1], reverse=True)
        
        # Get linguistic patterns for emotional messaging
        linguistic = enhanced.get(archetype, {})
        
        # Determine intensity level
        exclamation_rate = linguistic.get("exclamation_rate", 0.5)
        superlative_rate = linguistic.get("superlative_rate", 0.3)
        
        if exclamation_rate > 0.7 and superlative_rate > 0.4:
            intensity = "high"
        elif exclamation_rate > 0.4 or superlative_rate > 0.25:
            intensity = "medium"
        else:
            intensity = "low"
        
        # Emotional messaging recommendations
        emotion_phrases = {
            "fear_anxiety": ["Don't miss out", "Protect yourself", "Avoid problems"],
            "excitement": ["Discover", "Experience", "Unlock amazing"],
            "trust": ["Guaranteed", "Trusted by thousands", "Reliable"],
            "nostalgia": ["Remember when", "Classic quality", "Timeless"],
            "status": ["Exclusive", "Premium", "VIP access"],
            "value": ["Best deal", "Save big", "Unbeatable price"],
        }
        
        top_emotion = sorted_emotions[0][0] if sorted_emotions else "excitement"
        
        optimization[archetype] = {
            "emotion_sensitivities": {k: round(v, 4) for k, v in sorted_emotions},
            "primary_emotion": top_emotion,
            "secondary_emotion": sorted_emotions[1][0] if len(sorted_emotions) > 1 else "trust",
            "recommended_intensity": intensity,
            "emotional_phrases": emotion_phrases.get(top_emotion, []),
            "avoid_emotions": [e[0] for e in sorted_emotions[-2:]] if len(sorted_emotions) > 2 else [],
        }
    
    return optimization


def discover_category_chains(priors: Dict) -> Dict[str, Any]:
    """
    Discover Category → Archetype → Persuasion chains.
    """
    complete = priors.get("complete_coldstart_priors", {})
    persuasion = priors.get("persuasion_priors", {})
    
    chains = {}
    
    category_priors = complete.get("category_archetype_priors", {})
    
    # Sample important categories
    important_categories = [
        "Electronics", "Fashion", "Food_Grocery", "Home_Improvement", 
        "Automotive", "Books", "Pet_Care", "Health_Personal_Care",
        "Toys_Games", "Movies_TV",
    ]
    
    for category in important_categories:
        if category not in category_priors:
            continue
        
        arch_dist = category_priors[category]
        
        # Find dominant archetype
        dominant_arch = max(arch_dist.items(), key=lambda x: x[1])
        
        # Get persuasion strategy for dominant archetype
        arch_persuasion = persuasion.get("archetype_persuasion_sensitivity", {}).get(dominant_arch[0], {})
        
        # Find best principle for this archetype
        best_principle = None
        best_sens = 0
        for principle in ["social_proof", "authority", "scarcity", "reciprocity", "commitment", "liking"]:
            sens = arch_persuasion.get(principle, {}).get("avg_sensitivity", 0)
            if sens > best_sens:
                best_sens = sens
                best_principle = principle
        
        chains[category] = {
            "dominant_archetype": dominant_arch[0],
            "archetype_confidence": round(dominant_arch[1], 4),
            "best_persuasion_principle": best_principle,
            "principle_effectiveness": round(best_sens, 4),
            "recommendation": f"For {category}, target {dominant_arch[0]}s with {best_principle} messaging",
        }
    
    return chains


def discover_social_influence_targeting(priors: Dict) -> Dict[str, Any]:
    """
    Discover social influence type targeting strategies.
    """
    persuasion = priors.get("persuasion_priors", {})
    
    targeting = {}
    
    influence_messaging = {
        "information_seeker": {
            "proof_type": "Expert testimonials",
            "content_focus": "Detailed information",
            "social_signals": "Expert reviews, professional endorsements",
            "cta_style": "Learn from experts",
        },
        "entertainment_seeker": {
            "proof_type": "Fun testimonials",
            "content_focus": "Entertaining content",
            "social_signals": "Fun reviews, viral content",
            "cta_style": "Join the fun",
        },
        "status_seeker": {
            "proof_type": "Celebrity/influencer",
            "content_focus": "Exclusivity, prestige",
            "social_signals": "Elite status, VIP access",
            "cta_style": "Join the elite",
        },
        "validation_seeker": {
            "proof_type": "Customer testimonials",
            "content_focus": "Social validation",
            "social_signals": "User reviews, community",
            "cta_style": "Join thousands of happy customers",
        },
    }
    
    for archetype in ["Connector", "Explorer", "Achiever", "Guardian", "Analyzer"]:
        influence_data = persuasion.get("archetype_social_influence_type", {}).get(archetype, {})
        
        influence_type = influence_data.get("influence_type", "validation_seeker")
        
        targeting[archetype] = {
            "social_influence_type": influence_type,
            "avg_useful_votes": influence_data.get("avg_useful_votes", 0),
            "avg_funny_votes": influence_data.get("avg_funny_votes", 0),
            "avg_cool_votes": influence_data.get("avg_cool_votes", 0),
            "targeting_strategy": influence_messaging.get(influence_type, influence_messaging["validation_seeker"]),
        }
    
    return targeting


def discover_rating_behavior_patterns(priors: Dict) -> Dict[str, Any]:
    """
    Discover how rating behavior correlates with persuasion susceptibility.
    """
    persuasion = priors.get("persuasion_priors", {})
    
    patterns = {}
    
    for archetype in ["Connector", "Explorer", "Achiever", "Guardian", "Analyzer"]:
        rating_data = persuasion.get("archetype_rating_patterns", {}).get(archetype, {})
        engagement_data = persuasion.get("archetype_engagement_depth", {}).get(archetype, {})
        
        # Calculate rating behavior metrics
        avg_rating = rating_data.get("avg_rating", 4.0)
        rating_variance = rating_data.get("rating_variance", 0.5)
        extreme_positive_rate = rating_data.get("extreme_positive_rate", 0.3)
        extreme_negative_rate = rating_data.get("extreme_negative_rate", 0.1)
        
        # Determine if easy or hard to please
        if avg_rating > 4.2 and extreme_negative_rate < 0.1:
            persuasion_difficulty = "easy"
            recommended_approach = "Positive messaging, focus on benefits"
        elif avg_rating < 3.5 or extreme_negative_rate > 0.2:
            persuasion_difficulty = "hard"
            recommended_approach = "Evidence-heavy messaging, address concerns"
        else:
            persuasion_difficulty = "moderate"
            recommended_approach = "Balanced messaging with social proof"
        
        patterns[archetype] = {
            "avg_rating": round(avg_rating, 2),
            "rating_variance": round(rating_variance, 3),
            "extreme_positive_rate": round(extreme_positive_rate, 3),
            "extreme_negative_rate": round(extreme_negative_rate, 3),
            "persuasion_difficulty": persuasion_difficulty,
            "recommended_approach": recommended_approach,
            "engagement_depth": engagement_data.get("avg_review_length", 0),
        }
    
    return patterns


def generate_comprehensive_recommendations(
    phrase_correlations: Dict,
    synergies: Dict,
    decision_mapping: Dict,
    emotional_opt: Dict,
    category_chains: Dict,
    social_targeting: Dict,
    rating_patterns: Dict,
) -> Dict[str, Any]:
    """
    Generate comprehensive persuasion recommendations by archetype.
    """
    recommendations = {}
    
    for archetype in ["Connector", "Explorer", "Achiever", "Guardian", "Analyzer"]:
        # Gather all insights
        synergy = synergies.get(archetype, {})
        decision = decision_mapping.get(archetype, {})
        emotion = emotional_opt.get(archetype, {})
        social = social_targeting.get(archetype, {})
        rating = rating_patterns.get(archetype, {})
        
        # Build comprehensive recommendation
        rec = {
            "archetype": archetype,
            
            # Persuasion Principles
            "persuasion_strategy": {
                "primary_principle": synergy.get("recommended_combination", {}).get("primary", "social_proof"),
                "secondary_principle": synergy.get("recommended_combination", {}).get("secondary", "liking"),
                "synergy_score": synergy.get("recommended_combination", {}).get("synergy_score", 0.5),
            },
            
            # Messaging Style
            "messaging_style": {
                "decision_style": decision.get("dominant_style", "balanced"),
                "emotional_intensity": emotion.get("recommended_intensity", "medium"),
                "primary_emotion": emotion.get("primary_emotion", "excitement"),
                "cta_phrases": decision.get("recommended_strategy", {}).get("cta_phrases", []),
            },
            
            # Social Proof Type
            "social_proof_strategy": {
                "influence_type": social.get("social_influence_type", "validation_seeker"),
                "proof_type": social.get("targeting_strategy", {}).get("proof_type", "Customer testimonials"),
                "social_signals": social.get("targeting_strategy", {}).get("social_signals", "User reviews"),
            },
            
            # Difficulty & Approach
            "persuasion_approach": {
                "difficulty": rating.get("persuasion_difficulty", "moderate"),
                "approach": rating.get("recommended_approach", "Balanced messaging"),
                "avg_rating_tendency": rating.get("avg_rating", 4.0),
            },
            
            # Emotional Triggers
            "emotional_triggers": {
                "use": emotion.get("emotional_phrases", []),
                "avoid_emotions": emotion.get("avoid_emotions", []),
            },
            
            # Message Construction Template
            "message_template": {
                "opening": _get_opening(synergy, emotion),
                "body": _get_body(decision, social),
                "cta": _get_cta(decision),
            },
        }
        
        recommendations[archetype] = rec
    
    return recommendations


def _get_opening(synergy: Dict, emotion: Dict) -> str:
    """Generate recommended opening based on primary principle."""
    principle = synergy.get("recommended_combination", {}).get("primary", "social_proof")
    emotion_type = emotion.get("primary_emotion", "excitement")
    
    openings = {
        "social_proof": "Join thousands who have discovered...",
        "authority": "Experts recommend...",
        "scarcity": "Limited time opportunity...",
        "reciprocity": "Here's a special gift for you...",
        "commitment": "Take the first step to...",
        "liking": "We think you'll love...",
    }
    return openings.get(principle, "Discover something special...")


def _get_body(decision: Dict, social: Dict) -> str:
    """Generate recommended body style."""
    style = decision.get("dominant_style", "balanced")
    influence = social.get("social_influence_type", "validation_seeker")
    
    if style == "analytical":
        return "Include detailed specs, comparisons, and data points"
    elif style == "impulsive":
        return "Keep it short, focus on immediate benefits and urgency"
    elif style == "social":
        return f"Emphasize {influence} with testimonials and social signals"
    else:
        return "Balance information with emotional appeal"


def _get_cta(decision: Dict) -> str:
    """Generate recommended CTA."""
    phrases = decision.get("recommended_strategy", {}).get("cta_phrases", ["Discover now"])
    return phrases[0] if phrases else "Learn more"


def main():
    """Run the complete enhanced pattern discovery."""
    
    logger.info("=" * 70)
    logger.info("ENHANCED PATTERN DISCOVERY FOR PERSONALIZED PERSUASION")
    logger.info("=" * 70)
    
    # Load all priors
    priors = load_all_priors()
    
    # Run all discoveries
    logger.info("\n1. Discovering phrase-persuasion correlations...")
    phrase_correlations = discover_phrase_persuasion_correlations(priors)
    
    logger.info("2. Discovering cross-principle synergies...")
    synergies = discover_cross_principle_synergies(priors)
    
    logger.info("3. Discovering decision-persuasion mapping...")
    decision_mapping = discover_decision_persuasion_mapping(priors)
    
    logger.info("4. Discovering emotional optimization patterns...")
    emotional_opt = discover_emotional_optimization(priors)
    
    logger.info("5. Discovering category-archetype-persuasion chains...")
    category_chains = discover_category_chains(priors)
    
    logger.info("6. Discovering social influence targeting...")
    social_targeting = discover_social_influence_targeting(priors)
    
    logger.info("7. Discovering rating behavior patterns...")
    rating_patterns = discover_rating_behavior_patterns(priors)
    
    logger.info("8. Generating comprehensive recommendations...")
    recommendations = generate_comprehensive_recommendations(
        phrase_correlations, synergies, decision_mapping,
        emotional_opt, category_chains, social_targeting, rating_patterns
    )
    
    # Build output
    output = {
        "analysis_timestamp": datetime.now().isoformat(),
        "phrase_persuasion_correlations": phrase_correlations,
        "principle_synergies": synergies,
        "decision_persuasion_mapping": decision_mapping,
        "emotional_optimization": emotional_opt,
        "category_persuasion_chains": category_chains,
        "social_influence_targeting": social_targeting,
        "rating_behavior_patterns": rating_patterns,
        "comprehensive_recommendations": recommendations,
    }
    
    # Save
    output_path = DATA_DIR / "enhanced_persuasion_discovery.json"
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)
    
    logger.info(f"\nSaved enhanced patterns to {output_path}")
    
    # Print summary
    print("\n" + "=" * 70)
    print("ENHANCED PATTERN DISCOVERY RESULTS")
    print("=" * 70)
    
    print("\n--- PRINCIPLE SYNERGIES BY ARCHETYPE ---")
    for arch, data in synergies.items():
        combo = data["recommended_combination"]
        print(f"\n{arch}:")
        print(f"  Best combo: {combo['primary']} + {combo['secondary']}")
        print(f"  Synergy score: {combo['synergy_score']:.3f}")
    
    print("\n--- DECISION STYLE → PERSUASION MAPPING ---")
    for arch, data in decision_mapping.items():
        print(f"\n{arch}: {data['dominant_style']} ({data['dominant_confidence']:.1%})")
        print(f"  CTA style: {data['recommended_strategy']['cta_phrases'][0]}")
    
    print("\n--- EMOTIONAL OPTIMIZATION ---")
    for arch, data in emotional_opt.items():
        print(f"\n{arch}:")
        print(f"  Primary emotion: {data['primary_emotion']}")
        print(f"  Intensity: {data['recommended_intensity']}")
        print(f"  Avoid: {data['avoid_emotions']}")
    
    print("\n--- SOCIAL INFLUENCE TARGETING ---")
    for arch, data in social_targeting.items():
        print(f"\n{arch}: {data['social_influence_type']}")
        print(f"  Proof type: {data['targeting_strategy']['proof_type']}")
    
    print("\n--- PERSUASION DIFFICULTY ---")
    for arch, data in rating_patterns.items():
        print(f"\n{arch}: {data['persuasion_difficulty']} (avg rating: {data['avg_rating']})")
        print(f"  Approach: {data['recommended_approach']}")
    
    print("\n--- CATEGORY → PERSUASION CHAINS (Sample) ---")
    for cat, data in list(category_chains.items())[:5]:
        print(f"\n{cat}:")
        print(f"  {data['recommendation']}")
    
    print("\n" + "=" * 70)
    print("COMPREHENSIVE RECOMMENDATIONS GENERATED")
    print("=" * 70)
    
    for arch, rec in recommendations.items():
        print(f"\n{arch}:")
        print(f"  Principle: {rec['persuasion_strategy']['primary_principle']} + {rec['persuasion_strategy']['secondary_principle']}")
        print(f"  Style: {rec['messaging_style']['decision_style']}, {rec['messaging_style']['emotional_intensity']} intensity")
        print(f"  Social: {rec['social_proof_strategy']['influence_type']}")
        print(f"  Template: \"{rec['message_template']['opening'][:50]}...\"")
    
    return output


if __name__ == "__main__":
    results = main()
