"""
StackAdapt Outcome Mapper
===========================

Maps StackAdapt conversion events (from their Pixel API) into the
ADAM OutcomeHandler format so all 9 learning systems can update.

StackAdapt Pixel API events arrive with:
    - uid (universal pixel ID)
    - URL, user_agent, user_ip
    - event_args: JSON with action, revenue, order_id, segment_id, etc.

We extract the INFORMATIV segment_id from event_args and map
the conversion to a decision outcome that the OutcomeHandler understands.
"""

from __future__ import annotations

import logging
import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def map_stackadapt_event(event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Map a StackAdapt pixel event to ADAM OutcomeHandler format.

    Args:
        event: Raw StackAdapt pixel event with fields:
            uid, url, user_agent, user_ip, event_args, page_title

    Returns:
        Dict compatible with OutcomeHandler.process_outcome(), or None if
        the event cannot be mapped (e.g., no INFORMATIV segment_id).
    """
    event_args = event.get("event_args", {})
    if isinstance(event_args, str):
        import json
        try:
            event_args = json.loads(event_args)
        except (json.JSONDecodeError, TypeError):
            event_args = {}

    segment_id = (
        event_args.get("informativ_segment_id")
        or event_args.get("segment_id")
        or event_args.get("adam_segment_id")
        or ""
    )
    if not segment_id.startswith("informativ_"):
        return None

    action = event_args.get("action", "conversion")
    revenue = float(event_args.get("revenue", 0))
    order_id = event_args.get("order_id", "")

    outcome_type = _map_action_to_outcome_type(action)
    outcome_value = _compute_outcome_value(outcome_type, revenue)

    # Prefer decision_id echoed back by StackAdapt (links to our decision cache).
    # Fall back to a derived hash if not available.
    decision_id = (
        event_args.get("decision_id")
        or event_args.get("informativ_decision_id")
        or _derive_decision_id(segment_id, event)
    )

    archetype, mechanism, category = _parse_segment_id(segment_id)

    # Extract buyer_id for information value profile updates
    buyer_id = (
        event_args.get("uid")
        or event_args.get("buyer_id")
        or event.get("uid")
        or ""
    )

    return {
        "decision_id": decision_id,
        "outcome_type": outcome_type,
        "outcome_value": outcome_value,
        "metadata": {
            "source": "stackadapt_pixel",
            "segment_id": segment_id,
            "archetype": archetype,
            "mechanism": mechanism,
            "category": category,
            "revenue": revenue,
            "order_id": order_id,
            "url": event.get("url", ""),
            "buyer_id": buyer_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "raw_action": action,
        },
    }


def _map_action_to_outcome_type(action: str) -> str:
    """Map StackAdapt event action to ADAM outcome type."""
    action_lower = action.lower()
    if action_lower in ("purchase", "conversion", "sale", "transaction"):
        return "conversion"
    if action_lower in ("click", "cta_click", "link_click"):
        return "click"
    if action_lower in ("view", "impression", "page_view"):
        return "engagement"
    if action_lower in ("add_to_cart", "cart", "add_to_wishlist"):
        return "engagement"
    if action_lower in ("signup", "register", "subscribe", "lead"):
        return "conversion"
    return "engagement"


def _compute_outcome_value(outcome_type: str, revenue: float) -> float:
    """Compute a 0-1 outcome value for the learning systems."""
    if outcome_type == "conversion":
        if revenue > 0:
            return min(1.0, 0.7 + (revenue / 500.0) * 0.3)
        return 0.8
    if outcome_type == "click":
        return 0.5
    return 0.3


def _derive_decision_id(segment_id: str, event: Dict[str, Any]) -> str:
    """Generate a stable decision ID from segment + event context."""
    uid = event.get("uid", "")
    url = event.get("url", "")
    raw = f"{segment_id}:{uid}:{url}"
    return f"sa_{hashlib.sha256(raw.encode()).hexdigest()[:16]}"


def _parse_segment_id(segment_id: str) -> tuple:
    """Extract archetype, mechanism, category from segment_id."""
    parts = segment_id.replace("informativ_", "").split("_")

    known_archetypes = {
        "explorer", "achiever", "connector", "guardian",
        "analyst", "creator", "nurturer", "pragmatist",
    }
    known_mechanisms = {
        "social_proof", "authority", "scarcity", "reciprocity",
        "commitment", "liking", "fomo", "unity",
    }

    archetype = ""
    mechanism = ""
    category_parts = []

    for part in parts:
        if part in known_archetypes:
            archetype = part
        elif part in known_mechanisms:
            mechanism = part
        else:
            category_parts.append(part)

    category = "_".join(category_parts) if category_parts else ""
    return archetype or "unknown", mechanism, category
