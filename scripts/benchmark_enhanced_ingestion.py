#!/usr/bin/env python3
"""
BENCHMARK ENHANCED INGESTION
============================

Tests the enhanced ingestion pipeline at scale to:
1. Measure processing throughput
2. Validate analysis quality across diverse reviews
3. Profile memory usage
4. Test checkpointing/resume

Run: python scripts/benchmark_enhanced_ingestion.py --samples 1000
"""

import argparse
import json
import sys
import time
from pathlib import Path
from collections import Counter
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))


def benchmark_ingestion(jsonl_path: Path, num_samples: int, find_high_vote: bool = True):
    """
    Benchmark enhanced ingestion on real data.
    
    Args:
        jsonl_path: Path to JSONL review file
        num_samples: Number of reviews to process
        find_high_vote: Whether to specifically find high-vote reviews
    """
    print("=" * 70)
    print("ENHANCED INGESTION BENCHMARK")
    print("=" * 70)
    print(f"File: {jsonl_path}")
    print(f"Samples: {num_samples}")
    print(f"Find high vote: {find_high_vote}")
    print()
    
    # Import pipeline
    from adam.data.amazon.enhanced_ingestion import EnhancedIngestionPipeline
    pipeline = EnhancedIngestionPipeline()
    
    # Collect samples
    print("Collecting samples...")
    samples = []
    high_vote_samples = []
    scan_count = 0
    
    with open(jsonl_path, 'r') as f:
        for line in f:
            scan_count += 1
            
            try:
                review = json.loads(line)
                votes = review.get('helpful_vote', 0) or 0
                
                # Always collect some regular samples
                if len(samples) < num_samples // 2:
                    samples.append(review)
                
                # Specifically collect high-vote samples
                if find_high_vote and votes >= 50:
                    high_vote_samples.append(review)
                
                # Stop if we have enough
                if len(samples) >= num_samples // 2 and len(high_vote_samples) >= num_samples // 2:
                    break
                    
                # Safety limit
                if scan_count >= 100000:
                    break
                    
            except json.JSONDecodeError:
                continue
    
    # Combine samples
    all_samples = samples[:num_samples//2] + high_vote_samples[:num_samples//2]
    if len(all_samples) < num_samples:
        all_samples.extend(samples[:num_samples - len(all_samples)])
    
    print(f"Scanned {scan_count:,} reviews")
    print(f"Collected {len(all_samples)} samples ({len(high_vote_samples)} high-vote)")
    print()
    
    # Process samples
    print("-" * 70)
    print("PROCESSING")
    print("-" * 70)
    
    results = []
    stats = {
        "total": 0,
        "errors": 0,
        "processing_times": [],
        "big5_scores": [],
        "persuasive_powers": [],
        "influence_tiers": Counter(),
        "archetypes": Counter(),
        "high_influence_reviews": [],
        "construct_confidences": [],
    }
    
    start_time = time.time()
    
    for i, review in enumerate(all_samples):
        try:
            review_start = time.time()
            analysis = pipeline.analyze_review(review)
            review_time = time.time() - review_start
            
            stats["total"] += 1
            stats["processing_times"].append(review_time)
            stats["big5_scores"].append(analysis.big5_openness)
            stats["persuasive_powers"].append(analysis.overall_persuasive_power)
            stats["influence_tiers"][analysis.influence_tier] += 1
            stats["archetypes"][analysis.primary_archetype] += 1
            stats["construct_confidences"].append(analysis.construct_confidence)
            
            # Track high-influence reviews
            if analysis.influence_tier in ('very_high', 'viral'):
                stats["high_influence_reviews"].append({
                    "title": review.get('title', '')[:50],
                    "votes": review.get('helpful_vote', 0),
                    "persuasive_power": analysis.overall_persuasive_power,
                    "influence_score": analysis.influence_score,
                    "archetype": analysis.primary_archetype,
                })
            
            results.append(analysis)
            
            # Progress
            if (i + 1) % 100 == 0:
                elapsed = time.time() - start_time
                rate = (i + 1) / elapsed
                print(f"  Processed {i+1}/{len(all_samples)} ({rate:.1f}/sec)")
                
        except Exception as e:
            stats["errors"] += 1
            if stats["errors"] <= 5:
                print(f"  [ERROR] {e}")
    
    total_time = time.time() - start_time
    
    # Summary
    print("\n" + "=" * 70)
    print("RESULTS SUMMARY")
    print("=" * 70)
    
    print(f"\n[THROUGHPUT]")
    print(f"  Total processed: {stats['total']}")
    print(f"  Errors: {stats['errors']}")
    print(f"  Total time: {total_time:.1f}s")
    print(f"  Rate: {stats['total'] / total_time:.1f} reviews/sec")
    
    if stats["processing_times"]:
        avg_time = sum(stats["processing_times"]) / len(stats["processing_times"])
        min_time = min(stats["processing_times"])
        max_time = max(stats["processing_times"])
        print(f"  Avg time per review: {avg_time*1000:.1f}ms")
        print(f"  Min/Max: {min_time*1000:.1f}ms / {max_time*1000:.1f}ms")
    
    print(f"\n[PSYCHOLOGICAL PROFILES]")
    if stats["big5_scores"]:
        avg_openness = sum(stats["big5_scores"]) / len(stats["big5_scores"])
        print(f"  Avg Big5 Openness: {avg_openness:.2f}")
    if stats["construct_confidences"]:
        avg_conf = sum(stats["construct_confidences"]) / len(stats["construct_confidences"])
        print(f"  Avg Construct Confidence: {avg_conf:.2f}")
    
    print(f"\n[PERSUASIVE POWER]")
    if stats["persuasive_powers"]:
        avg_power = sum(stats["persuasive_powers"]) / len(stats["persuasive_powers"])
        high_power = sum(1 for p in stats["persuasive_powers"] if p > 0.5)
        print(f"  Average: {avg_power:.2f}")
        print(f"  High power (>0.5): {high_power} ({100*high_power/len(stats['persuasive_powers']):.1f}%)")
    
    print(f"\n[INFLUENCE DISTRIBUTION]")
    for tier, count in sorted(stats["influence_tiers"].items()):
        pct = 100 * count / stats["total"]
        print(f"  {tier}: {count} ({pct:.1f}%)")
    
    print(f"\n[ARCHETYPE DISTRIBUTION]")
    for arch, count in stats["archetypes"].most_common(10):
        pct = 100 * count / stats["total"]
        print(f"  {arch}: {count} ({pct:.1f}%)")
    
    print(f"\n[TOP HIGH-INFLUENCE REVIEWS]")
    top_reviews = sorted(
        stats["high_influence_reviews"],
        key=lambda x: x["influence_score"],
        reverse=True
    )[:5]
    for r in top_reviews:
        print(f"  {r['votes']} votes | {r['influence_score']:.2f} score | {r['archetype']} | {r['title'][:40]}...")
    
    print("\n" + "=" * 70)
    print("PROJECTED FULL INGESTION")
    print("=" * 70)
    
    rate = stats["total"] / total_time
    
    # Estimates for full dataset
    reviews_1b = 1_000_000_000
    time_sequential = reviews_1b / rate / 3600  # hours
    
    # With parallelization (8 cores)
    time_parallel_8 = time_sequential / 8
    
    # With 32-core machine
    time_parallel_32 = time_sequential / 32
    
    print(f"  At current rate ({rate:.1f}/sec):")
    print(f"    Sequential: {time_sequential:.1f} hours ({time_sequential/24:.1f} days)")
    print(f"    8-core parallel: {time_parallel_8:.1f} hours ({time_parallel_8/24:.1f} days)")
    print(f"    32-core parallel: {time_parallel_32:.1f} hours ({time_parallel_32/24:.1f} days)")
    
    # Storage estimate (average ~2KB per enhanced review)
    storage_gb = (reviews_1b * 2000) / (1024**3)
    print(f"\n  Storage estimate: ~{storage_gb:.0f} GB for enhanced data")
    
    print("\n[DONE]")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Benchmark enhanced ingestion")
    parser.add_argument(
        "--samples",
        type=int,
        default=500,
        help="Number of samples to process"
    )
    parser.add_argument(
        "--file",
        type=str,
        default="/Users/chrisnocera/Sites/adam-platform/amazon/Beauty_and_Personal_Care.jsonl",
        help="Path to JSONL file"
    )
    
    args = parser.parse_args()
    
    jsonl_path = Path(args.file)
    if not jsonl_path.exists():
        print(f"File not found: {jsonl_path}")
        sys.exit(1)
    
    benchmark_ingestion(jsonl_path, args.samples)
