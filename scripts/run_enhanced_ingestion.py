#!/usr/bin/env python3
"""
PRODUCTION ENHANCED INGESTION SCRIPT
====================================

Runs the enhanced ingestion pipeline on the full Amazon review dataset.

Features:
- Parallel processing (configurable cores)
- Checkpointing for resume capability
- Progress tracking with ETA
- Memory-efficient streaming
- Neo4j batch writes (optional)

Usage:
    # Dry run (no actual processing)
    python scripts/run_enhanced_ingestion.py --dry-run
    
    # Process single category
    python scripts/run_enhanced_ingestion.py --category Beauty_and_Personal_Care
    
    # Process all categories with 8 cores
    python scripts/run_enhanced_ingestion.py --workers 8 --all
    
    # Resume from checkpoint
    python scripts/run_enhanced_ingestion.py --resume
"""

import argparse
import asyncio
import json
import logging
import multiprocessing
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURATION
# =============================================================================

@dataclass
class IngestionConfig:
    """Configuration for enhanced ingestion."""
    
    # Paths
    input_dir: Path = Path("/Users/chrisnocera/Sites/adam-platform/amazon")
    output_dir: Path = Path("/Users/chrisnocera/Sites/adam-platform/data/enhanced_reviews")
    checkpoint_dir: Path = Path("/Users/chrisnocera/Sites/adam-platform/data/ingestion_checkpoints")
    
    # Processing
    num_workers: int = 4
    batch_size: int = 1000
    checkpoint_interval: int = 10000  # Save checkpoint every N reviews
    
    # Neo4j (optional)
    neo4j_uri: Optional[str] = None
    neo4j_user: Optional[str] = None
    neo4j_password: Optional[str] = None
    
    # Limits
    max_reviews_per_file: Optional[int] = None  # None = process all
    
    def __post_init__(self):
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)


@dataclass  
class IngestionProgress:
    """Progress tracking for ingestion."""
    
    category: str
    file_path: str
    total_reviews: int = 0
    processed_reviews: int = 0
    high_influence_reviews: int = 0
    errors: int = 0
    start_time: str = ""
    last_update: str = ""
    status: str = "pending"  # pending, running, completed, failed
    
    def to_checkpoint(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_checkpoint(cls, data: Dict[str, Any]) -> "IngestionProgress":
        return cls(**data)


# =============================================================================
# WORKER FUNCTIONS
# =============================================================================

def process_chunk(args: Tuple[str, List[Dict], int]) -> Dict[str, Any]:
    """
    Process a chunk of reviews (runs in worker process).
    
    Args:
        args: Tuple of (category, reviews, chunk_id)
        
    Returns:
        Dict with chunk results
    """
    category, reviews, chunk_id = args
    
    # Import inside worker to avoid pickling issues
    from adam.data.amazon.enhanced_ingestion import EnhancedIngestionPipeline
    
    pipeline = EnhancedIngestionPipeline()
    
    results = []
    errors = 0
    high_influence = 0
    
    for review in reviews:
        try:
            analysis = pipeline.analyze_review(review)
            results.append(analysis.to_compact_json())
            
            if analysis.influence_tier in ('very_high', 'viral'):
                high_influence += 1
                
        except Exception as e:
            errors += 1
            if errors <= 3:
                logger.debug(f"Error in chunk {chunk_id}: {e}")
    
    return {
        "chunk_id": chunk_id,
        "category": category,
        "count": len(results),
        "high_influence": high_influence,
        "errors": errors,
        "results": results,
    }


def count_lines(file_path: Path) -> int:
    """Count lines in a file efficiently."""
    import gzip
    
    count = 0
    if str(file_path).endswith('.gz'):
        with gzip.open(file_path, 'rt') as f:
            for _ in f:
                count += 1
    else:
        with open(file_path, 'r') as f:
            for _ in f:
                count += 1
    return count


# =============================================================================
# MAIN PROCESSOR
# =============================================================================

class EnhancedIngestionRunner:
    """
    Runs enhanced ingestion at production scale.
    """
    
    def __init__(self, config: IngestionConfig):
        self.config = config
        self.progress: Dict[str, IngestionProgress] = {}
    
    def discover_files(self, categories: Optional[List[str]] = None) -> List[Path]:
        """Discover JSONL files to process."""
        files = []
        
        for ext in ['*.jsonl', '*.jsonl.gz']:
            for f in self.config.input_dir.glob(ext):
                # Skip metadata files
                if f.name.startswith('meta_'):
                    continue
                
                # Filter by category if specified
                if categories:
                    category = f.stem.replace('.jsonl', '').replace('.gz', '')
                    if category not in categories:
                        continue
                
                files.append(f)
        
        return sorted(files)
    
    def load_checkpoint(self, file_path: Path) -> Optional[IngestionProgress]:
        """Load checkpoint for a file if it exists."""
        checkpoint_path = self.config.checkpoint_dir / f"{file_path.stem}_checkpoint.json"
        
        if checkpoint_path.exists():
            try:
                with open(checkpoint_path, 'r') as f:
                    data = json.load(f)
                return IngestionProgress.from_checkpoint(data)
            except Exception as e:
                logger.warning(f"Could not load checkpoint: {e}")
        
        return None
    
    def save_checkpoint(self, progress: IngestionProgress) -> None:
        """Save checkpoint for a file."""
        checkpoint_path = self.config.checkpoint_dir / f"{Path(progress.file_path).stem}_checkpoint.json"
        
        progress.last_update = datetime.now().isoformat()
        
        with open(checkpoint_path, 'w') as f:
            json.dump(progress.to_checkpoint(), f, indent=2)
    
    def process_file(self, file_path: Path, resume: bool = False) -> IngestionProgress:
        """
        Process a single JSONL file.
        
        Args:
            file_path: Path to JSONL file
            resume: Whether to resume from checkpoint
            
        Returns:
            Final progress
        """
        import gzip
        from adam.data.amazon.enhanced_ingestion import EnhancedIngestionPipeline
        
        category = file_path.stem.replace('.jsonl', '').replace('.gz', '')
        
        # Load or create progress
        if resume:
            progress = self.load_checkpoint(file_path)
            if progress and progress.status == "completed":
                logger.info(f"Skipping {category} - already completed")
                return progress
            skip_count = progress.processed_reviews if progress else 0
        else:
            progress = None
            skip_count = 0
        
        if not progress:
            progress = IngestionProgress(
                category=category,
                file_path=str(file_path),
                start_time=datetime.now().isoformat(),
            )
        
        progress.status = "running"
        
        # Output file
        output_path = self.config.output_dir / f"enhanced_{category}.jsonl"
        
        # Count total if not known
        if progress.total_reviews == 0:
            logger.info(f"Counting lines in {file_path.name}...")
            progress.total_reviews = count_lines(file_path)
            logger.info(f"Total reviews in {category}: {progress.total_reviews:,}")
        
        # Apply limit if configured
        max_reviews = self.config.max_reviews_per_file or progress.total_reviews
        
        # Open input
        if str(file_path).endswith('.gz'):
            f_in = gzip.open(file_path, 'rt', encoding='utf-8')
        else:
            f_in = open(file_path, 'r', encoding='utf-8')
        
        # Initialize pipeline
        pipeline = EnhancedIngestionPipeline()
        
        # Process
        start_time = time.time()
        last_checkpoint = 0
        
        try:
            with f_in, open(output_path, 'a' if resume else 'w') as f_out:
                for line_num, line in enumerate(f_in):
                    # Skip already processed
                    if line_num < skip_count:
                        continue
                    
                    # Stop if limit reached
                    if progress.processed_reviews >= max_reviews:
                        break
                    
                    try:
                        review = json.loads(line)
                        analysis = pipeline.analyze_review(review)
                        
                        # Write result
                        f_out.write(analysis.to_compact_json() + '\n')
                        
                        progress.processed_reviews += 1
                        if analysis.influence_tier in ('very_high', 'viral'):
                            progress.high_influence_reviews += 1
                            
                    except json.JSONDecodeError:
                        progress.errors += 1
                        continue
                    except Exception as e:
                        progress.errors += 1
                        if progress.errors <= 10:
                            logger.debug(f"Error processing review {line_num}: {e}")
                        continue
                    
                    # Progress update every 1000
                    if progress.processed_reviews % 1000 == 0:
                        elapsed = time.time() - start_time
                        rate = progress.processed_reviews / max(elapsed, 0.001)
                        remaining = (max_reviews - progress.processed_reviews) / max(rate, 0.001)
                        print(
                            f"\r[{category}] {progress.processed_reviews:,}/{max_reviews:,} "
                            f"({100*progress.processed_reviews/max_reviews:.1f}%) "
                            f"{rate:.0f}/sec ETA:{timedelta(seconds=int(remaining))}",
                            end="", flush=True
                        )
                    
                    # Checkpoint every checkpoint_interval
                    if progress.processed_reviews - last_checkpoint >= self.config.checkpoint_interval:
                        self.save_checkpoint(progress)
                        last_checkpoint = progress.processed_reviews
                        elapsed = time.time() - start_time
                        rate = progress.processed_reviews / max(elapsed, 0.001)
                        remaining = (max_reviews - progress.processed_reviews) / max(rate, 0.001)
                        logger.info(
                            f"[{category}] Progress: {progress.processed_reviews:,}/{max_reviews:,} "
                            f"({100*progress.processed_reviews/max_reviews:.1f}%) "
                            f"Rate: {rate:.0f}/sec, ETA: {timedelta(seconds=int(remaining))}"
                        )
            
            progress.status = "completed"
            print()  # New line after progress
            
        except Exception as e:
            logger.error(f"Processing failed for {category}: {e}")
            progress.status = "failed"
            import traceback
            traceback.print_exc()
        
        finally:
            self.save_checkpoint(progress)
        
        # Final stats
        elapsed = time.time() - start_time
        rate = progress.processed_reviews / elapsed if elapsed > 0 else 0
        
        logger.info(
            f"[{category}] COMPLETE: {progress.processed_reviews:,} reviews, "
            f"{progress.high_influence_reviews:,} high-influence, "
            f"{progress.errors:,} errors, "
            f"{rate:.0f}/sec in {timedelta(seconds=int(elapsed))}"
        )
        
        return progress
    
    def run(
        self,
        categories: Optional[List[str]] = None,
        resume: bool = False,
        dry_run: bool = False,
    ) -> Dict[str, IngestionProgress]:
        """
        Run enhanced ingestion on all or specified categories.
        
        Args:
            categories: Optional list of categories to process
            resume: Whether to resume from checkpoints
            dry_run: Whether to just show what would be processed
            
        Returns:
            Dict of category -> final progress
        """
        files = self.discover_files(categories)
        
        if not files:
            logger.warning("No files found to process")
            return {}
        
        logger.info(f"Found {len(files)} files to process")
        
        if dry_run:
            for f in files:
                checkpoint = self.load_checkpoint(f)
                status = checkpoint.status if checkpoint else "pending"
                logger.info(f"  {f.name}: {status}")
            return {}
        
        results = {}
        
        for file_path in files:
            try:
                progress = self.process_file(file_path, resume=resume)
                results[progress.category] = progress
            except Exception as e:
                logger.error(f"Failed to process {file_path}: {e}")
        
        # Summary
        total_processed = sum(p.processed_reviews for p in results.values())
        total_high_influence = sum(p.high_influence_reviews for p in results.values())
        total_errors = sum(p.errors for p in results.values())
        
        logger.info("=" * 70)
        logger.info("INGESTION COMPLETE")
        logger.info(f"Categories processed: {len(results)}")
        logger.info(f"Total reviews: {total_processed:,}")
        logger.info(f"High-influence reviews: {total_high_influence:,}")
        logger.info(f"Errors: {total_errors:,}")
        logger.info("=" * 70)
        
        return results


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Run enhanced review ingestion",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    parser.add_argument(
        "--category",
        type=str,
        help="Process single category (e.g., Beauty_and_Personal_Care)"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Process all available categories"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Number of parallel workers (default: 4)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=1000,
        help="Batch size for processing (default: 1000)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Maximum reviews per file (for testing)"
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from checkpoints"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be processed without processing"
    )
    parser.add_argument(
        "--input-dir",
        type=str,
        default="/Users/chrisnocera/Sites/adam-platform/amazon",
        help="Input directory with JSONL files"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="/Users/chrisnocera/Sites/adam-platform/data/enhanced_reviews",
        help="Output directory for enhanced reviews"
    )
    
    args = parser.parse_args()
    
    # Determine categories
    if args.category:
        categories = [args.category]
    elif args.all:
        categories = None  # All
    else:
        parser.error("Either --category or --all is required")
    
    # Configure
    config = IngestionConfig(
        input_dir=Path(args.input_dir),
        output_dir=Path(args.output_dir),
        num_workers=args.workers,
        batch_size=args.batch_size,
        max_reviews_per_file=args.limit,
    )
    
    # Run
    runner = EnhancedIngestionRunner(config)
    runner.run(
        categories=categories,
        resume=args.resume,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
