# =============================================================================
# ADAM Embedding Maintenance Jobs
# Location: adam/embeddings/maintenance.py
# =============================================================================

"""
EMBEDDING MAINTENANCE

Background jobs for embedding infrastructure maintenance.

Jobs:
- Vector index compaction
- Stale vector cleanup
- Index rebuilding
- Cache warming
- Quality auditing
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field
from prometheus_client import Counter, Gauge, Histogram

from adam.embeddings.models import EmbeddingNamespace, EmbeddingType

logger = logging.getLogger(__name__)


# =============================================================================
# PROMETHEUS METRICS
# =============================================================================

MAINTENANCE_JOBS = Counter(
    "adam_embedding_maintenance_jobs_total",
    "Maintenance jobs executed",
    ["job_type", "status"],
)

MAINTENANCE_DURATION = Histogram(
    "adam_embedding_maintenance_duration_seconds",
    "Maintenance job duration",
    ["job_type"],
    buckets=[1, 5, 10, 30, 60, 300, 600, 1800],
)

VECTORS_COMPACTED = Counter(
    "adam_embedding_vectors_compacted_total",
    "Vectors compacted",
    ["namespace"],
)

VECTORS_CLEANED = Counter(
    "adam_embedding_vectors_cleaned_total",
    "Stale vectors cleaned",
    ["namespace"],
)


# =============================================================================
# JOB MODELS
# =============================================================================

class JobStatus(str, Enum):
    """Maintenance job status."""
    
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobResult(BaseModel):
    """Result of a maintenance job."""
    
    job_id: str = Field(default_factory=lambda: uuid4().hex[:12])
    job_type: str
    
    status: JobStatus = JobStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: float = 0.0
    
    # Results
    items_processed: int = 0
    items_modified: int = 0
    items_deleted: int = 0
    bytes_freed: int = 0
    
    # Errors
    error: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)


# =============================================================================
# INDEX COMPACTION JOB
# =============================================================================

class IndexCompactionJob:
    """
    Compacts vector indexes by removing deleted entries and rebuilding.
    
    Benefits:
    - Reclaims space from deleted vectors
    - Improves search performance
    - Optimizes index structure
    
    FAISS Note: FAISS doesn't support true deletion. Compaction rebuilds
    the index from scratch with only active vectors.
    """
    
    def __init__(
        self,
        store,  # VectorStore
        batch_size: int = 10000,
    ):
        self.store = store
        self.batch_size = batch_size
    
    async def run(
        self,
        namespaces: Optional[List[EmbeddingNamespace]] = None,
        progress_callback: Optional[Callable] = None,
    ) -> JobResult:
        """
        Run index compaction.
        
        Args:
            namespaces: Specific namespaces to compact (None = all)
            progress_callback: Called with progress updates
            
        Returns:
            Job result with statistics
        """
        result = JobResult(job_type="index_compaction")
        result.status = JobStatus.RUNNING
        result.started_at = datetime.now(timezone.utc)
        
        try:
            # Determine namespaces to process
            if namespaces is None:
                namespaces = list(EmbeddingNamespace)
            
            total_compacted = 0
            total_bytes_freed = 0
            
            for namespace in namespaces:
                logger.info(f"Compacting namespace: {namespace.value}")
                
                # Get current count
                pre_count = await self.store.count(namespace=namespace)
                
                # For FAISS backend, trigger compaction
                if hasattr(self.store._backend, "compact"):
                    compaction_result = await self.store._backend.compact(namespace)
                    compacted = compaction_result.get("vectors_removed", 0)
                    bytes_freed = compaction_result.get("bytes_freed", 0)
                else:
                    # For other backends, may just reorganize
                    compacted = 0
                    bytes_freed = 0
                
                total_compacted += compacted
                total_bytes_freed += bytes_freed
                
                VECTORS_COMPACTED.labels(namespace=namespace.value).inc(compacted)
                
                if progress_callback:
                    progress_callback({
                        "namespace": namespace.value,
                        "pre_count": pre_count,
                        "compacted": compacted,
                    })
            
            result.items_processed = total_compacted
            result.items_modified = total_compacted
            result.bytes_freed = total_bytes_freed
            result.status = JobStatus.COMPLETED
            
            MAINTENANCE_JOBS.labels(
                job_type="index_compaction", status="success"
            ).inc()
            
        except Exception as e:
            result.status = JobStatus.FAILED
            result.error = str(e)
            logger.error(f"Index compaction failed: {e}")
            
            MAINTENANCE_JOBS.labels(
                job_type="index_compaction", status="failed"
            ).inc()
        
        finally:
            result.completed_at = datetime.now(timezone.utc)
            result.duration_seconds = (
                result.completed_at - result.started_at
            ).total_seconds()
            
            MAINTENANCE_DURATION.labels(
                job_type="index_compaction"
            ).observe(result.duration_seconds)
        
        return result


# =============================================================================
# STALE VECTOR CLEANUP JOB
# =============================================================================

class StaleVectorCleanupJob:
    """
    Removes stale vectors that haven't been accessed recently.
    
    Criteria for staleness:
    - Not accessed in X days
    - From deprecated model versions
    - Orphaned (no associated source)
    """
    
    def __init__(
        self,
        store,  # VectorStore
        max_age_days: int = 90,
        batch_size: int = 1000,
    ):
        self.store = store
        self.max_age_days = max_age_days
        self.batch_size = batch_size
    
    async def run(
        self,
        namespaces: Optional[List[EmbeddingNamespace]] = None,
        dry_run: bool = False,
        progress_callback: Optional[Callable] = None,
    ) -> JobResult:
        """
        Run stale vector cleanup.
        
        Args:
            namespaces: Specific namespaces (None = all)
            dry_run: If True, don't actually delete
            progress_callback: Progress updates
            
        Returns:
            Job result
        """
        result = JobResult(job_type="stale_cleanup")
        result.status = JobStatus.RUNNING
        result.started_at = datetime.now(timezone.utc)
        result.metadata["dry_run"] = dry_run
        
        try:
            if namespaces is None:
                namespaces = list(EmbeddingNamespace)
            
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=self.max_age_days)
            
            total_found = 0
            total_deleted = 0
            
            for namespace in namespaces:
                logger.info(f"Checking namespace for stale vectors: {namespace.value}")
                
                # Find stale vectors
                stale_vectors = await self._find_stale_vectors(
                    namespace, cutoff_date
                )
                
                total_found += len(stale_vectors)
                
                if not dry_run:
                    # Delete in batches
                    for i in range(0, len(stale_vectors), self.batch_size):
                        batch = stale_vectors[i:i + self.batch_size]
                        deleted = await self._delete_batch(batch)
                        total_deleted += deleted
                        
                        VECTORS_CLEANED.labels(
                            namespace=namespace.value
                        ).inc(deleted)
                        
                        if progress_callback:
                            progress_callback({
                                "namespace": namespace.value,
                                "processed": i + len(batch),
                                "total": len(stale_vectors),
                            })
                else:
                    total_deleted = total_found  # Would have deleted
            
            result.items_processed = total_found
            result.items_deleted = total_deleted if not dry_run else 0
            result.metadata["stale_found"] = total_found
            result.status = JobStatus.COMPLETED
            
            if dry_run:
                result.warnings.append(
                    f"Dry run: would delete {total_found} vectors"
                )
            
            MAINTENANCE_JOBS.labels(
                job_type="stale_cleanup", status="success"
            ).inc()
            
        except Exception as e:
            result.status = JobStatus.FAILED
            result.error = str(e)
            logger.error(f"Stale cleanup failed: {e}")
            
            MAINTENANCE_JOBS.labels(
                job_type="stale_cleanup", status="failed"
            ).inc()
        
        finally:
            result.completed_at = datetime.now(timezone.utc)
            result.duration_seconds = (
                result.completed_at - result.started_at
            ).total_seconds()
            
            MAINTENANCE_DURATION.labels(
                job_type="stale_cleanup"
            ).observe(result.duration_seconds)
        
        return result
    
    async def _find_stale_vectors(
        self,
        namespace: EmbeddingNamespace,
        cutoff_date: datetime,
    ) -> List[str]:
        """Find stale vector IDs."""
        # For pgvector backend
        if hasattr(self.store._backend, "_pool"):
            async with self.store._backend._pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT vector_id FROM adam_embeddings
                    WHERE namespace = $1
                    AND created_at < $2
                    AND (updated_at IS NULL OR updated_at < $2)
                """, namespace.value, cutoff_date)
                return [row["vector_id"] for row in rows]
        
        # For other backends, return empty (would need iteration)
        return []
    
    async def _delete_batch(self, vector_ids: List[str]) -> int:
        """Delete a batch of vectors."""
        deleted = 0
        for vid in vector_ids:
            if await self.store.delete(vid):
                deleted += 1
        return deleted


# =============================================================================
# INDEX REBUILD JOB
# =============================================================================

class IndexRebuildJob:
    """
    Rebuilds vector indexes for improved performance.
    
    Use cases:
    - After large bulk imports
    - When search performance degrades
    - When switching index types
    """
    
    def __init__(
        self,
        store,  # VectorStore
    ):
        self.store = store
    
    async def run(
        self,
        namespace: Optional[EmbeddingNamespace] = None,
        index_type: Optional[str] = None,
        progress_callback: Optional[Callable] = None,
    ) -> JobResult:
        """
        Rebuild index.
        
        Args:
            namespace: Specific namespace (None = all)
            index_type: New index type (None = same as current)
            progress_callback: Progress updates
            
        Returns:
            Job result
        """
        result = JobResult(job_type="index_rebuild")
        result.status = JobStatus.RUNNING
        result.started_at = datetime.now(timezone.utc)
        
        try:
            # For pgvector, use REINDEX
            if hasattr(self.store._backend, "reindex"):
                await self.store._backend.reindex(
                    namespace.value if namespace else None
                )
                result.status = JobStatus.COMPLETED
                result.metadata["reindexed"] = True
            
            # For FAISS, would need to rebuild from scratch
            elif hasattr(self.store._backend, "_index"):
                result.warnings.append(
                    "FAISS index rebuild requires full vector export/import"
                )
                result.status = JobStatus.COMPLETED
            
            else:
                result.warnings.append("Index rebuild not supported for this backend")
                result.status = JobStatus.COMPLETED
            
            MAINTENANCE_JOBS.labels(
                job_type="index_rebuild", status="success"
            ).inc()
            
        except Exception as e:
            result.status = JobStatus.FAILED
            result.error = str(e)
            logger.error(f"Index rebuild failed: {e}")
            
            MAINTENANCE_JOBS.labels(
                job_type="index_rebuild", status="failed"
            ).inc()
        
        finally:
            result.completed_at = datetime.now(timezone.utc)
            result.duration_seconds = (
                result.completed_at - result.started_at
            ).total_seconds()
            
            MAINTENANCE_DURATION.labels(
                job_type="index_rebuild"
            ).observe(result.duration_seconds)
        
        return result


# =============================================================================
# CACHE WARMING JOB
# =============================================================================

class CacheWarmingJob:
    """
    Warms embedding cache with frequently accessed vectors.
    
    Strategies:
    - Most recently accessed
    - Most frequently accessed
    - Popular source IDs
    """
    
    def __init__(
        self,
        generator,  # EmbeddingGenerator
        cache,  # Redis cache
        batch_size: int = 100,
    ):
        self.generator = generator
        self.cache = cache
        self.batch_size = batch_size
    
    async def run(
        self,
        texts: List[str],
        progress_callback: Optional[Callable] = None,
    ) -> JobResult:
        """
        Warm cache with specific texts.
        
        Args:
            texts: Texts to pre-embed and cache
            progress_callback: Progress updates
            
        Returns:
            Job result
        """
        result = JobResult(job_type="cache_warming")
        result.status = JobStatus.RUNNING
        result.started_at = datetime.now(timezone.utc)
        
        try:
            total_warmed = 0
            
            for i in range(0, len(texts), self.batch_size):
                batch = texts[i:i + self.batch_size]
                
                # Generate embeddings (will cache automatically)
                await self.generator.embed_batch(batch)
                total_warmed += len(batch)
                
                if progress_callback:
                    progress_callback({
                        "processed": total_warmed,
                        "total": len(texts),
                    })
            
            result.items_processed = total_warmed
            result.status = JobStatus.COMPLETED
            
            MAINTENANCE_JOBS.labels(
                job_type="cache_warming", status="success"
            ).inc()
            
        except Exception as e:
            result.status = JobStatus.FAILED
            result.error = str(e)
            logger.error(f"Cache warming failed: {e}")
            
            MAINTENANCE_JOBS.labels(
                job_type="cache_warming", status="failed"
            ).inc()
        
        finally:
            result.completed_at = datetime.now(timezone.utc)
            result.duration_seconds = (
                result.completed_at - result.started_at
            ).total_seconds()
            
            MAINTENANCE_DURATION.labels(
                job_type="cache_warming"
            ).observe(result.duration_seconds)
        
        return result


# =============================================================================
# MAINTENANCE SCHEDULER
# =============================================================================

class MaintenanceScheduler:
    """
    Schedules and runs maintenance jobs.
    
    Can be run as a background task or triggered manually.
    """
    
    def __init__(
        self,
        store,  # VectorStore
        generator=None,  # EmbeddingGenerator
        cache=None,  # Redis cache
    ):
        self.store = store
        self.generator = generator
        self.cache = cache
        
        # Job history
        self._job_history: List[JobResult] = []
        
        # Running
        self._running = False
        self._task = None
    
    async def start_scheduled(
        self,
        compaction_interval_hours: int = 24,
        cleanup_interval_hours: int = 168,  # Weekly
    ) -> None:
        """Start scheduled maintenance."""
        if self._running:
            return
        
        self._running = True
        self._task = asyncio.create_task(
            self._schedule_loop(compaction_interval_hours, cleanup_interval_hours)
        )
        logger.info("Maintenance scheduler started")
    
    async def stop(self) -> None:
        """Stop scheduled maintenance."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Maintenance scheduler stopped")
    
    async def _schedule_loop(
        self,
        compaction_hours: int,
        cleanup_hours: int,
    ) -> None:
        """Background scheduling loop."""
        last_compaction = datetime.now(timezone.utc)
        last_cleanup = datetime.now(timezone.utc)
        
        while self._running:
            try:
                now = datetime.now(timezone.utc)
                
                # Check compaction
                if (now - last_compaction).total_seconds() >= compaction_hours * 3600:
                    result = await self.run_compaction()
                    self._job_history.append(result)
                    last_compaction = now
                
                # Check cleanup
                if (now - last_cleanup).total_seconds() >= cleanup_hours * 3600:
                    result = await self.run_cleanup()
                    self._job_history.append(result)
                    last_cleanup = now
                
                # Sleep for 1 hour
                await asyncio.sleep(3600)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                await asyncio.sleep(3600)
    
    async def run_compaction(
        self,
        namespaces: Optional[List[EmbeddingNamespace]] = None,
    ) -> JobResult:
        """Run index compaction job."""
        job = IndexCompactionJob(self.store)
        result = await job.run(namespaces)
        self._job_history.append(result)
        return result
    
    async def run_cleanup(
        self,
        namespaces: Optional[List[EmbeddingNamespace]] = None,
        dry_run: bool = False,
    ) -> JobResult:
        """Run stale vector cleanup job."""
        job = StaleVectorCleanupJob(self.store)
        result = await job.run(namespaces, dry_run)
        self._job_history.append(result)
        return result
    
    async def run_rebuild(
        self,
        namespace: Optional[EmbeddingNamespace] = None,
    ) -> JobResult:
        """Run index rebuild job."""
        job = IndexRebuildJob(self.store)
        result = await job.run(namespace)
        self._job_history.append(result)
        return result
    
    async def run_cache_warming(
        self,
        texts: List[str],
    ) -> JobResult:
        """Run cache warming job."""
        if not self.generator:
            result = JobResult(job_type="cache_warming")
            result.status = JobStatus.FAILED
            result.error = "Generator not configured"
            return result
        
        job = CacheWarmingJob(self.generator, self.cache)
        result = await job.run(texts)
        self._job_history.append(result)
        return result
    
    def get_history(
        self,
        limit: int = 100,
        job_type: Optional[str] = None,
    ) -> List[JobResult]:
        """Get job history."""
        history = self._job_history
        
        if job_type:
            history = [j for j in history if j.job_type == job_type]
        
        return history[-limit:]
