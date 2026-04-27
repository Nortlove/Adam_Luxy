"""Process-singleton MRT decision producer.

The bilateral cascade and any other live decision path call into this
module to emit logged decision records. The producer is the wire to
durable storage — Kafka in production (handoff §1.2), in-memory in
dev/test/pilot.

Design:
    - Single process-singleton accessor: get_mrt_producer()
    - First call: choose backend based on env config (KAFKA_BOOTSTRAP_
      SERVERS present → Kafka; otherwise in-memory)
    - Subsequent calls: return cached instance
    - Soft-fail: if Kafka init throws, fall back to in-memory rather
      than crash the cascade
    - reset_for_tests() to swap in a controlled producer between cases

The Kafka path is intentionally NOT implemented in this commit — the
KAFKA_BOOTSTRAP_SERVERS check exists so production can wire without
touching this file's interface, but the actual kafka-python producer
build is a follow-up. Today's pilot uses the in-memory path; records
accumulate in process memory and can be flushed via dump_to_jsonl().
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from dataclasses import asdict
from pathlib import Path
from typing import Callable, List, Optional

from adam.intelligence.mrt_logging import (
    InMemoryDecisionLog,
    MRTDecisionRecord,
)

logger = logging.getLogger(__name__)


_PRODUCER_LOCK = threading.Lock()
_PRODUCER: Optional[InMemoryDecisionLog] = None
_INIT_ATTEMPTED = False


def get_mrt_producer() -> InMemoryDecisionLog:
    """Return the process-singleton MRT decision producer.

    Currently always returns InMemoryDecisionLog. A KAFKA_BOOTSTRAP_
    SERVERS env var will (in a follow-up) trigger Kafka producer
    construction; for now the function logs an info message and
    returns the in-memory log either way.
    """
    global _PRODUCER, _INIT_ATTEMPTED

    if _PRODUCER is not None:
        return _PRODUCER

    with _PRODUCER_LOCK:
        if _PRODUCER is not None:  # double-check under lock
            return _PRODUCER

        _INIT_ATTEMPTED = True

        kafka_bootstrap = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "")
        if kafka_bootstrap:
            # Future: build kafka-python producer wired to mrt.decisions.v1
            # using MRT_DECISIONS_V1_AVRO_SCHEMA. For now, log and fall
            # through to in-memory so the cascade keeps logging.
            logger.info(
                "MRT producer: KAFKA_BOOTSTRAP_SERVERS=%s detected; Kafka path "
                "not yet wired — using in-memory log for now.",
                kafka_bootstrap,
            )

        _PRODUCER = InMemoryDecisionLog()
        logger.info("MRT producer: in-memory log initialized")
        return _PRODUCER


def emit(record: MRTDecisionRecord) -> None:
    """Convenience: emit a record via the singleton producer.

    Soft-fails: any exception is logged and swallowed. The bid path
    must NEVER break because logging is offline (handoff §1.10).
    """
    try:
        producer = get_mrt_producer()
        producer.emit(record)
    except Exception as exc:
        logger.warning("MRT emit failed: %s", exc)


def dump_to_jsonl(path: Path) -> int:
    """Flush the in-memory log to a JSONL file. Returns rows written.

    Each row is one MRTDecisionRecord serialized as JSON. The order is
    insertion order (chronological by decision-time epoch). Use this
    for offline-batch ingestion into the WCLS pipeline before Kafka is
    deployed.

    Soft-fails: if no producer or no records, writes an empty file and
    returns 0. If writing fails, returns -1 and logs.
    """
    if _PRODUCER is None:
        try:
            path.write_text("")
        except Exception:
            return -1
        return 0

    try:
        with open(path, "w") as f:
            for rec in _PRODUCER.records:
                f.write(json.dumps(asdict(rec), default=str))
                f.write("\n")
    except Exception as exc:
        logger.warning("MRT dump_to_jsonl failed: %s", exc)
        return -1

    return len(_PRODUCER.records)


def reset_for_tests(producer: Optional[InMemoryDecisionLog] = None) -> None:
    """Swap in a controlled producer for test cases. Without arg,
    restores the singleton to a fresh in-memory log."""
    global _PRODUCER, _INIT_ATTEMPTED
    with _PRODUCER_LOCK:
        _PRODUCER = producer if producer is not None else InMemoryDecisionLog()
        _INIT_ATTEMPTED = True
