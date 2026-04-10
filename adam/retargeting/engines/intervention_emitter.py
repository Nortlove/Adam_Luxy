# =============================================================================
# Intervention Record Emitter
# Location: adam/retargeting/engines/intervention_emitter.py
# Unified System Evolution Directive, Section 2.1
# =============================================================================

"""
Emits EnrichedInterventionRecords from the learning pipeline.

Called after Step 13.5 (diagnostic reasoning completes) so it captures
the H1-H5 hypothesis decomposition and next touch plan.

Records accumulate in a buffer and flush to storage periodically.
For pilot: JSONLine file. At scale: Postgres or Kafka.
"""

import json
import logging
import os
import time
from typing import List, Optional

from adam.retargeting.models.intervention_record import EnrichedInterventionRecord

logger = logging.getLogger(__name__)

# Default storage location for pilot
DEFAULT_RECORDS_DIR = "data/intervention_records"
DEFAULT_RECORDS_FILE = "enriched_interventions.jsonl"


class JSONLineStorage:
    """Simple file-based storage for pilot scale.

    Replace with Postgres table or Kafka topic at production scale.
    """

    def __init__(self, filepath: Optional[str] = None):
        if filepath is None:
            os.makedirs(DEFAULT_RECORDS_DIR, exist_ok=True)
            filepath = os.path.join(DEFAULT_RECORDS_DIR, DEFAULT_RECORDS_FILE)
        self.filepath = filepath

    def append_batch(self, records: List[dict]):
        with open(self.filepath, "a") as f:
            for record in records:
                f.write(json.dumps(record, default=str) + "\n")

    @property
    def record_count(self) -> int:
        if not os.path.exists(self.filepath):
            return 0
        with open(self.filepath) as f:
            return sum(1 for _ in f)


class InterventionRecordEmitter:
    """Buffers and flushes EnrichedInterventionRecords to storage.

    Usage:
        emitter = InterventionRecordEmitter()
        emitter.emit(record)
        # Auto-flushes every buffer_size records
        emitter.flush()  # Force flush at shutdown
    """

    def __init__(
        self,
        storage: Optional[JSONLineStorage] = None,
        buffer_size: int = 50,
    ):
        self.storage = storage or JSONLineStorage()
        self.buffer: List[EnrichedInterventionRecord] = []
        self.buffer_size = buffer_size
        self.total_emitted = 0

    def emit(self, record: EnrichedInterventionRecord):
        """Buffer a record for batch writing."""
        self.buffer.append(record)
        self.total_emitted += 1

        if len(self.buffer) >= self.buffer_size:
            self.flush()

    def flush(self):
        """Write buffered records to storage."""
        if not self.buffer:
            return
        records = [r.to_dict() for r in self.buffer]
        try:
            self.storage.append_batch(records)
            logger.debug(
                "Flushed %d intervention records (total: %d)",
                len(records), self.total_emitted,
            )
        except Exception as e:
            logger.warning("Failed to flush intervention records: %s", e)
        self.buffer.clear()

    @property
    def stats(self) -> dict:
        return {
            "total_emitted": self.total_emitted,
            "buffer_size": len(self.buffer),
            "storage_records": self.storage.record_count,
        }


# Singleton
_emitter: Optional[InterventionRecordEmitter] = None


def get_intervention_emitter() -> InterventionRecordEmitter:
    """Get or create the singleton emitter."""
    global _emitter
    if _emitter is None:
        _emitter = InterventionRecordEmitter()
        logger.info("InterventionRecordEmitter initialized (pilot storage)")
    return _emitter
