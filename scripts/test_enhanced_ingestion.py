#!/usr/bin/env python3
"""
TEST ENHANCED INGESTION PIPELINE
================================

Tests the enhanced review analysis on a small sample to validate:
1. Psychological construct extraction
2. Persuasive pattern detection  
3. Influence scoring
4. Emotional journey extraction
5. Archetype detection

Run: python scripts/test_enhanced_ingestion.py
"""

import json
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Sample reviews with different characteristics for testing
SAMPLE_REVIEWS = [
    # High helpful vote, detailed positive review
    {
        "rating": 5.0,
        "title": "Life changing skincare - I've tried everything!",
        "text": """After 15 years of struggling with sensitive skin, I was skeptical about trying yet another product. But WOW. Within the first week, I noticed a difference. The redness that had plagued me for years started to fade. By week three, my skin looked better than it had in a decade.

Here's what makes this different:
1. The formula is gentle but effective - no burning, no irritation
2. A little goes a long way - I've been using the same bottle for 3 months
3. It works under makeup beautifully

I've now recommended this to 5 friends and they're all converts. My dermatologist even asked what I was using! 

If you're on the fence, just try it. The 30-day guarantee means you have nothing to lose. I only wish I had found this sooner.""",
        "helpful_vote": 347,
        "verified_purchase": True,
        "asin": "B001TEST01",
        "user_id": "TEST_USER_1",
        "timestamp": 1699999999999,
    },
    # Low vote, negative emotional review
    {
        "rating": 1.0,
        "title": "Complete waste of money",
        "text": """I'm so frustrated. This product did absolutely nothing for me. I used it exactly as directed for 6 weeks and saw zero improvement. In fact, my skin seemed to get worse!

The packaging was also damaged when it arrived, which should have been a warning sign. Customer service was no help at all.

Save your money and buy literally anything else.""",
        "helpful_vote": 2,
        "verified_purchase": True,
        "asin": "B001TEST02",
        "user_id": "TEST_USER_2",
        "timestamp": 1699999999998,
    },
    # Medium vote, analytical review with comparisons
    {
        "rating": 4.0,
        "title": "Good but not the best I've tried",
        "text": """I've tested dozens of serums over the years, so I can offer some perspective.

PROS:
- Lightweight texture absorbs quickly
- No sticky residue
- Slight improvement in fine lines after 8 weeks
- Good price point compared to competitors

CONS:
- Pump dispenser is inconsistent
- Fragrance is noticeable (though pleasant)
- Results are gradual, not dramatic

COMPARISON TO ALTERNATIVES:
- Cheaper than Brand X but similar results
- Not as effective as Brand Y but half the price
- Better packaging than Brand Z

BOTTOM LINE: A solid mid-range option. I'd repurchase but would also consider alternatives.""",
        "helpful_vote": 89,
        "verified_purchase": True,
        "asin": "B001TEST03",
        "user_id": "TEST_USER_3",
        "timestamp": 1699999999997,
    },
    # Gift review with social proof
    {
        "rating": 5.0,
        "title": "Bought for my mom, now everyone wants one",
        "text": """I got this as a birthday gift for my mom based on the reviews here. She LOVED it so much that she won't stop talking about it.

Now my aunt wants one for Christmas, my sister is buying one, and my grandmother asked about it too! It's become the family favorite.

The quality is impressive for the price. Even my dad, who never notices anything, commented on how nice mom's skin looks.""",
        "helpful_vote": 23,
        "verified_purchase": True,
        "asin": "B001TEST04",
        "user_id": "TEST_USER_4",
        "timestamp": 1699999999996,
    },
    # Urgency/scarcity review
    {
        "rating": 5.0,
        "title": "GET THIS BEFORE IT SELLS OUT AGAIN",
        "text": """I waited 3 weeks for this to come back in stock. Don't make my mistake - order it NOW if you see it available!

This is the third time I've repurchased. It's become my holy grail product. I literally cannot live without it anymore. The results are immediate and long-lasting.

UPDATE: Just saw they're running low again. Seriously, stock up!""",
        "helpful_vote": 156,
        "verified_purchase": True,
        "asin": "B001TEST05",
        "user_id": "TEST_USER_5",
        "timestamp": 1699999999995,
    },
]


def test_enhanced_analysis():
    """Run enhanced analysis on sample reviews."""
    print("=" * 70)
    print("ENHANCED INGESTION PIPELINE TEST")
    print("=" * 70)
    print(f"Testing {len(SAMPLE_REVIEWS)} sample reviews\n")
    
    # Import the pipeline
    try:
        from adam.data.amazon.enhanced_ingestion import (
            EnhancedIngestionPipeline,
            EnhancedReviewAnalysis,
        )
        print("[OK] Enhanced ingestion module imported")
    except ImportError as e:
        print(f"[FAIL] Could not import enhanced ingestion: {e}")
        return False
    
    # Import analyzers
    try:
        from adam.intelligence.persuasive_patterns import get_persuasive_pattern_extractor
        extractor = get_persuasive_pattern_extractor()
        print("[OK] Persuasive pattern extractor loaded")
    except ImportError as e:
        print(f"[WARN] Persuasive pattern extractor not available: {e}")
        extractor = None
    
    try:
        from adam.intelligence.helpful_vote_weighting import get_helpful_vote_weighter
        weighter = get_helpful_vote_weighter()
        print("[OK] Helpful vote weighter loaded")
    except ImportError as e:
        print(f"[WARN] Helpful vote weighter not available: {e}")
        weighter = None
    
    print("\n" + "-" * 70)
    print("ANALYZING REVIEWS")
    print("-" * 70)
    
    # Create pipeline
    pipeline = EnhancedIngestionPipeline()
    
    results = []
    for i, review in enumerate(SAMPLE_REVIEWS, 1):
        print(f"\n[Review {i}] {review['title'][:50]}...")
        print(f"  Helpful votes: {review['helpful_vote']}")
        print(f"  Rating: {review['rating']}")
        
        # Analyze
        analysis = pipeline.analyze_review(review)
        results.append(analysis)
        
        # Display key findings
        print(f"\n  PSYCHOLOGICAL PROFILE:")
        print(f"    Big5 Openness: {analysis.big5_openness:.2f}")
        print(f"    Big5 Conscientiousness: {analysis.big5_conscientiousness:.2f}")
        print(f"    Big5 Extraversion: {analysis.big5_extraversion:.2f}")
        
        print(f"\n  PERSUASIVE POWER:")
        print(f"    Hook strength: {analysis.hook_strength:.2f}")
        print(f"    Evidence strength: {analysis.evidence_strength:.2f}")
        print(f"    Emotion strength: {analysis.emotion_strength:.2f}")
        print(f"    Social proof: {analysis.social_proof_strength:.2f}")
        print(f"    Overall persuasive power: {analysis.overall_persuasive_power:.2f}")
        
        print(f"\n  INFLUENCE:")
        print(f"    Influence tier: {analysis.influence_tier}")
        print(f"    Vote weight: {analysis.vote_weight:.2f}x")
        print(f"    Influence score: {analysis.influence_score:.2f}")
        
        print(f"\n  ARCHETYPE: {analysis.primary_archetype}")
    
    print("\n" + "=" * 70)
    print("ANALYSIS SUMMARY")
    print("=" * 70)
    
    # Summary statistics
    avg_persuasive = sum(r.overall_persuasive_power for r in results) / len(results)
    high_influence = sum(1 for r in results if r.influence_tier in ('very_high', 'viral'))
    
    print(f"\nTotal reviews analyzed: {len(results)}")
    print(f"Average persuasive power: {avg_persuasive:.2f}")
    print(f"High-influence reviews: {high_influence}")
    
    # Influence distribution
    tiers = {}
    for r in results:
        tiers[r.influence_tier] = tiers.get(r.influence_tier, 0) + 1
    
    print(f"\nInfluence tier distribution:")
    for tier, count in sorted(tiers.items()):
        print(f"  {tier}: {count}")
    
    # Archetype distribution
    archetypes = {}
    for r in results:
        archetypes[r.primary_archetype] = archetypes.get(r.primary_archetype, 0) + 1
    
    print(f"\nArchetype distribution:")
    for arch, count in sorted(archetypes.items(), key=lambda x: -x[1]):
        print(f"  {arch}: {count}")
    
    print("\n" + "=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)
    
    return True


def test_real_file_sample():
    """Test on actual JSONL file data."""
    print("\n" + "=" * 70)
    print("TESTING ON REAL DATA FILE")
    print("=" * 70)
    
    jsonl_path = Path("/Users/chrisnocera/Sites/adam-platform/amazon/Beauty_and_Personal_Care.jsonl")
    
    if not jsonl_path.exists():
        print(f"[SKIP] JSONL file not found: {jsonl_path}")
        return True
    
    try:
        from adam.data.amazon.enhanced_ingestion import EnhancedIngestionPipeline
        pipeline = EnhancedIngestionPipeline()
    except ImportError as e:
        print(f"[FAIL] Could not import pipeline: {e}")
        return False
    
    print(f"Reading sample from: {jsonl_path}")
    
    # Read first 20 reviews
    reviews = []
    high_vote_reviews = []
    
    with open(jsonl_path, 'r') as f:
        for i, line in enumerate(f):
            if i >= 1000:  # Scan first 1000 to find high-vote reviews
                break
            try:
                review = json.loads(line)
                if i < 10:  # Keep first 10 regardless
                    reviews.append(review)
                if review.get('helpful_vote', 0) >= 50:
                    high_vote_reviews.append(review)
            except json.JSONDecodeError:
                continue
    
    # Add some high-vote reviews to our sample
    reviews.extend(high_vote_reviews[:5])
    
    print(f"Sampled {len(reviews)} reviews ({len(high_vote_reviews)} with 50+ votes in first 1000)")
    
    # Analyze
    stats = {
        "total": 0,
        "with_hooks": 0,
        "high_influence": 0,
        "archetypes": {},
    }
    
    for review in reviews[:20]:  # Analyze up to 20
        try:
            analysis = pipeline.analyze_review(review)
            stats["total"] += 1
            
            if analysis.hook_strength > 0.3:
                stats["with_hooks"] += 1
            if analysis.influence_tier in ('very_high', 'viral'):
                stats["high_influence"] += 1
            
            arch = analysis.primary_archetype
            stats["archetypes"][arch] = stats["archetypes"].get(arch, 0) + 1
            
        except Exception as e:
            print(f"  [WARN] Failed to analyze review: {e}")
    
    print(f"\n[RESULTS]")
    print(f"  Analyzed: {stats['total']}")
    print(f"  With hooks: {stats['with_hooks']}")
    print(f"  High influence: {stats['high_influence']}")
    print(f"  Archetypes: {stats['archetypes']}")
    
    return True


if __name__ == "__main__":
    success = test_enhanced_analysis()
    
    if success:
        test_real_file_sample()
    
    print("\n[DONE]")
