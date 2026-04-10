"""
Anthropic Message Batches API wrapper.

Submits up to 100K requests per batch, polls for completion,
and streams results back. 50% cost discount vs real-time API.

Uses claude-haiku-4-5 for maximum speed and cost efficiency.
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Iterator

import anthropic

logger = logging.getLogger("adam.corpus.batch_api")

# Model preference: try Haiku 4.5 first (cheapest), fall back to Sonnet 4
# Set via environment variable ADAM_BATCH_MODEL to override
DEFAULT_MODEL = "claude-sonnet-4-20250514"
MAX_TOKENS = 2048
# Each review prompt ~2-3KB → 50K requests ≈ 150MB, well under 256MB limit
MAX_BATCH_SIZE = 50_000


def _get_model() -> str:
    import os
    return os.environ.get("ADAM_BATCH_MODEL", DEFAULT_MODEL)


def create_batch(
    client: anthropic.Anthropic,
    requests: list[dict],
    description: str = "",
    max_retries: int = 10,
) -> str:
    """
    Submit a batch of requests. Returns batch_id.
    Handles rate limits with exponential backoff.

    Each request dict must have:
      - custom_id: str
      - system: str
      - user_prompt: str
    """
    model = _get_model()
    batch_requests = []
    for req in requests:
        batch_requests.append({
            "custom_id": req["custom_id"],
            "params": {
                "model": model,
                "max_tokens": MAX_TOKENS,
                "system": req["system"],
                "messages": [{"role": "user", "content": req["user_prompt"]}],
            },
        })

    logger.info(f"Submitting batch: {len(batch_requests)} requests, model={model}, desc='{description}'")

    for attempt in range(max_retries):
        try:
            batch = client.messages.batches.create(requests=batch_requests)
            logger.info(f"Batch created: id={batch.id}, status={batch.processing_status}")
            return batch.id
        except anthropic.RateLimitError as e:
            wait = min(30 * (attempt + 1), 120)
            logger.warning(f"Rate limit on batch create (attempt {attempt+1}), waiting {wait}s...")
            time.sleep(wait)
        except anthropic.APIStatusError as e:
            if e.status_code == 413 or "too_large" in str(e) or "256MB" in str(e):
                # Batch too large — halve it
                mid = len(batch_requests) // 2
                logger.warning(f"Batch too large ({len(batch_requests)} reqs), halving to {mid}")
                batch_requests = batch_requests[:mid]
            else:
                logger.error(f"API error: {e}")
                if attempt < max_retries - 1:
                    time.sleep(15)
                else:
                    raise
        except Exception as e:
            logger.error(f"Batch create error: {e}")
            if attempt < max_retries - 1:
                time.sleep(15)
            else:
                raise
    raise RuntimeError(f"Failed to create batch after {max_retries} attempts")


def poll_batch(
    client: anthropic.Anthropic,
    batch_id: str,
    poll_interval: int = 30,
    max_wait: int = 86400,
) -> dict:
    """
    Poll until batch completes. Returns batch status dict.
    """
    start = time.time()
    while True:
        batch = client.messages.batches.retrieve(batch_id)
        status = batch.processing_status
        counts = batch.request_counts

        elapsed = time.time() - start
        logger.info(
            f"Batch {batch_id}: status={status}, "
            f"succeeded={counts.succeeded}/{counts.processing + counts.succeeded + counts.errored + counts.canceled + counts.expired}, "
            f"errored={counts.errored}, elapsed={elapsed:.0f}s"
        )

        if status == "ended":
            return {
                "batch_id": batch_id,
                "succeeded": counts.succeeded,
                "errored": counts.errored,
                "expired": counts.expired,
                "canceled": counts.canceled,
                "elapsed_s": elapsed,
            }

        if elapsed > max_wait:
            logger.error(f"Batch {batch_id} did not complete within {max_wait}s")
            return {"batch_id": batch_id, "error": "timeout", "elapsed_s": elapsed}

        # Adaptive polling: start at poll_interval, increase as we wait longer
        wait = min(poll_interval + int(elapsed / 300) * 10, 120)
        time.sleep(wait)


def stream_results(
    client: anthropic.Anthropic,
    batch_id: str,
) -> Iterator[tuple[str, dict | None]]:
    """
    Stream results from a completed batch.

    Yields (custom_id, parsed_json_or_None) tuples.
    """
    count = 0
    errors = 0
    for result in client.messages.batches.results(batch_id):
        custom_id = result.custom_id

        if result.result.type == "succeeded":
            try:
                text = result.result.message.content[0].text.strip()
                # Strip markdown code fences if present
                if text.startswith("```"):
                    lines = text.split("\n")
                    text = "\n".join(l for l in lines if not l.strip().startswith("```"))
                parsed = json.loads(text)
                count += 1
                yield custom_id, parsed
            except (json.JSONDecodeError, IndexError, AttributeError) as e:
                errors += 1
                logger.warning(f"Parse error for {custom_id}: {e}")
                yield custom_id, None
        else:
            errors += 1
            error_type = result.result.type
            logger.warning(f"Request {custom_id} failed: {error_type}")
            yield custom_id, None

    logger.info(f"Batch {batch_id} results: {count} parsed, {errors} errors")


def submit_and_wait(
    client: anthropic.Anthropic,
    requests: list[dict],
    description: str = "",
    poll_interval: int = 30,
) -> Iterator[tuple[str, dict | None]]:
    """
    Convenience: submit batch, poll until done, stream results.

    Handles chunking into MAX_BATCH_SIZE automatically.
    """
    if not requests:
        return

    # Chunk if needed
    chunks = []
    for i in range(0, len(requests), MAX_BATCH_SIZE):
        chunks.append(requests[i:i + MAX_BATCH_SIZE])

    logger.info(f"Total requests: {len(requests)}, split into {len(chunks)} batch(es)")

    for chunk_idx, chunk in enumerate(chunks):
        desc = f"{description} [chunk {chunk_idx+1}/{len(chunks)}]" if len(chunks) > 1 else description
        batch_id = create_batch(client, chunk, desc)

        status = poll_batch(client, batch_id, poll_interval)
        if "error" in status:
            logger.error(f"Batch chunk {chunk_idx+1} failed: {status}")
            continue

        logger.info(
            f"Batch chunk {chunk_idx+1} done: "
            f"succeeded={status['succeeded']}, errored={status['errored']}, "
            f"elapsed={status['elapsed_s']:.0f}s"
        )

        yield from stream_results(client, batch_id)
