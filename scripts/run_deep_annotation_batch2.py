"""
Run deep bilateral annotation on the 974 new unique reviews.
Uses the refined annotation engine with anchored scoring and contrastive framing.
Synchronous with threading for parallelism.
"""

import json
import logging
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from adam.intelligence.annotation_engine import (
    build_annotation_prompt,
    compute_composite_alignment,
    ANNOTATION_DIMENSIONS,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

REVIEWS_DIR = os.path.join(os.path.dirname(__file__), "..", "reviews")
INPUT_FILE = os.path.join(REVIEWS_DIR, "new_reviews_for_annotation.json")
OUTPUT_FILE = os.path.join(REVIEWS_DIR, "new_reviews_deep_annotated.json")
CHECKPOINT_FILE = os.path.join(REVIEWS_DIR, "annotation_checkpoint_batch2.json")

WORKERS = 10
CHECKPOINT_INTERVAL = 50


def annotate_single(client, review, idx):
    """Annotate a single review synchronously."""
    text = review["review_text"]
    rating = review["rating"]
    company = review["company"]
    prompt = build_annotation_prompt(text, rating, company)

    for attempt in range(3):
        try:
            response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=800,
                messages=[{"role": "user", "content": prompt}],
            )

            resp_text = response.content[0].text.strip()
            if resp_text.startswith("```"):
                resp_text = resp_text.split("\n", 1)[1].rsplit("```", 1)[0]

            result = json.loads(resp_text)

            # Validate dimensions
            for prop_name in ANNOTATION_DIMENSIONS:
                val = result.get(prop_name)
                if val is None or not isinstance(val, (int, float)):
                    result[prop_name] = 0.5
                else:
                    result[prop_name] = max(0.0, min(1.0, float(val)))

            # Attach metadata
            result["_review_id"] = idx
            result["_company"] = company
            result["_rating"] = rating
            result["_text"] = text
            result["_source"] = review.get("source", "Unknown")
            result["_data_source"] = review.get("data_source", "Unknown")
            result["composite_alignment"] = compute_composite_alignment(result)
            return result

        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse error for review {idx} (attempt {attempt+1}): {e}")
            time.sleep(1.0)
        except Exception as e:
            logger.warning(f"Error for review {idx} (attempt {attempt+1}): {e}")
            time.sleep(2.0 * (attempt + 1))

    return {"_review_id": idx, "_company": company, "_error": True, "_text": text}


def load_checkpoint():
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE) as f:
            return json.load(f)
    return {"completed_ids": set(), "completed": [], "errors": []}


def save_checkpoint(completed, errors, completed_ids):
    with open(CHECKPOINT_FILE, "w") as f:
        json.dump({
            "completed_ids": list(completed_ids),
            "completed_count": len(completed),
            "error_count": len(errors),
        }, f)
    # Save partial results
    with open(OUTPUT_FILE, "w") as f:
        json.dump({
            "metadata": {"status": "in_progress", "count": len(completed)},
            "annotated_reviews": completed,
        }, f, indent=2)


def main():
    import anthropic
    client = anthropic.Anthropic()

    # Quick test
    try:
        test = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=50,
            messages=[{"role": "user", "content": "Say 'ok'"}],
        )
        print(f"API test: {test.content[0].text}")
    except Exception as e:
        print(f"API test failed: {e}")
        return

    # Load reviews
    with open(INPUT_FILE) as f:
        data = json.load(f)
    reviews = data["reviews"]
    total = len(reviews)
    print(f"Total reviews to annotate: {total}")

    # Check for existing partial results
    completed = []
    errors = []
    completed_ids = set()

    if os.path.exists(OUTPUT_FILE):
        try:
            with open(OUTPUT_FILE) as f:
                existing = json.load(f)
            if existing.get("metadata", {}).get("status") == "in_progress":
                completed = existing.get("annotated_reviews", [])
                completed_ids = {r["_review_id"] for r in completed}
                print(f"Resuming: {len(completed)} already done")
        except Exception:
            pass

    remaining = [(i, r) for i, r in enumerate(reviews) if i not in completed_ids]
    print(f"Remaining: {len(remaining)}")

    t_start = time.time()
    processed = 0

    with ThreadPoolExecutor(max_workers=WORKERS) as executor:
        # Submit in chunks to allow checkpointing
        chunk_size = 50
        for chunk_start in range(0, len(remaining), chunk_size):
            chunk = remaining[chunk_start:chunk_start + chunk_size]

            futures = {}
            for idx, review in chunk:
                f = executor.submit(annotate_single, client, review, idx)
                futures[f] = idx

            for future in as_completed(futures):
                result = future.result()
                if result.get("_error"):
                    errors.append(result)
                else:
                    completed.append(result)
                    completed_ids.add(result["_review_id"])

                processed += 1

            elapsed = time.time() - t_start
            rate = processed / elapsed if elapsed > 0 else 0
            eta = (len(remaining) - processed) / rate if rate > 0 else 0
            print(
                f"  [{len(completed_ids)}/{total}] "
                f"{len(completed)} ok, {len(errors)} err, "
                f"{rate:.1f}/s, ETA {eta/60:.1f}min"
            )

            # Checkpoint
            save_checkpoint(completed, errors, completed_ids)

    elapsed = time.time() - t_start
    print(f"\nDone in {elapsed/60:.1f} minutes")
    print(f"Annotated: {len(completed)}, Errors: {len(errors)}")

    # Stats
    from collections import Counter
    import statistics

    if completed:
        mechanisms = Counter(r.get("primary_mechanism", "?") for r in completed)
        archetypes = Counter(r.get("buyer_archetype", "?") for r in completed)
        reg_focus = Counter(r.get("regulatory_focus", "?") for r in completed)

        print("\nPrimary mechanisms:")
        for m, c in mechanisms.most_common():
            print(f"  {m}: {c} ({100*c/len(completed):.1f}%)")

        print("\nArchetypes:")
        for a, c in archetypes.most_common():
            print(f"  {a}: {c} ({100*c/len(completed):.1f}%)")

        print("\nRegulatory focus:")
        for r, c in reg_focus.most_common():
            print(f"  {r}: {c} ({100*c/len(completed):.1f}%)")

        print("\nDimension variance (top 5):")
        for dim in ANNOTATION_DIMENSIONS:
            vals = [r.get(dim, 0.5) for r in completed]
            if len(vals) > 1:
                std = statistics.stdev(vals)
                mean = statistics.mean(vals)
                print(f"  {dim}: μ={mean:.3f}, σ={std:.3f}")

    # Final save
    output = {
        "metadata": {
            "source": "batch2_new_reviews",
            "status": "complete",
            "total_annotated": len(completed),
            "errors": len(errors),
            "annotation_time_minutes": round(elapsed / 60, 1),
        },
        "annotated_reviews": completed,
    }
    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nSaved to {OUTPUT_FILE}")

    # Cleanup
    if os.path.exists(CHECKPOINT_FILE):
        os.remove(CHECKPOINT_FILE)


if __name__ == "__main__":
    main()
