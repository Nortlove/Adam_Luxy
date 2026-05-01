# =============================================================================
# Spine #5 — Claude API Goal-State Label Generator
# Location: adam/intelligence/goal_state_label_generator.py
# =============================================================================
"""Claude-API-driven multi-label goal-state labeling for Spine #5 training.

Slice 18 — closes the data-side gap from Slices 17b/c. Both
LogisticGoalStateModel (Option B) and HierarchicalGoalStateModel
(Option C) need labeled (page_features, active_goal_state_set) tuples
to be more than passthrough fallbacks. Without labels, the
DualEvalContext primary stays at PassthroughGoalStateModel and the
B-vs-C empirical comparison is uninformative.

Per directive Section 6.2 (offline learning engine — Claude API as the
slow brain): this is the offline label-generation pipeline. Run
nightly / weekly over the page corpus + new pages from production
DecisionTraces; persist labels to Neo4j; trigger model retrain when
the labeled-pair count crosses thresholds.

WHY THIS EXISTS — DECISION-TIME PATH

  Page corpus (page_intelligence cache) + new pages from prod
      ↓ (this slice)
  GoalStateLabelGenerator.generate_labels_bulk via Claude API
      ↓ (multi-label JSON: which of 14 goals is the user pursuing?)
  :GoalStateLabel nodes persisted to Neo4j
      ↓ (sibling slice — train_models_from_labels)
  Trained LogisticGoalStateModel (B) + HierarchicalGoalStateModel (C)
      ↓ register_dual_eval_context at FastAPI startup
  Decision-time cascade integration (Slice 17d) computes F() per
  candidate via the trained models; both posteriors logged in
  DecisionTrace for offline B-vs-C comparison (Slice 19).

PROMPT CACHING DISCIPLINE

The system prompt embeds the entire 14-goal inventory with
descriptions, posture compatibilities, and keyword markers. It's
static across requests (cache key invariant). With ``cache_control``
on the system block + 1h TTL, ~95%+ of input tokens are served
from cache after the first call:

  request 1: ~2K input tokens (full price; cache write at 2x)
  request 2..N: ~50 input tokens (uncached question) + ~2K cache read (0.1x)

The ``ANTHROPIC_API_KEY`` env var is the same one ``claude_summarizer``
uses — no new key plumbing.

STRUCTURED OUTPUT VALIDATION

Uses ``client.messages.parse()`` with a Pydantic model
(``GoalStateLabelResponse``). The schema constrains the response
to ``{active_goal_state_ids: list[str], confidence: float,
reasoning: str}``. Active goal IDs are validated against the
inventory; invalid IDs are dropped with a warning.

DISCIPLINE (B3-LUXY a/b/c/d)
----------------------------

(a) Citations: directive Section 6.2 (Claude API as offline slow
    brain); SKILL_CLAUDE_API.md prompt-caching pattern (frozen system
    prefix + ephemeral TTL); Pydantic structured-output validation
    via ``client.messages.parse()``. Multi-label format matches
    the directive Spine #5 line 216 framing ("which of the ~12-15
    active goal states the user is in" — read as multi-label, since
    a page can prime multiple goals).

(b) Tests pin: API-key-missing soft-fail; library-missing soft-fail;
    successful generate produces valid label; invalid goal_state_ids
    in response filtered out; multi-page bulk generation accumulates
    correctly; persist + load round-trip via Neo4j; cache_control
    set on the system block; rate-limit retries handled by SDK
    automatically.

(c) calibration_pending=True. The MIN_CONFIDENCE_THRESHOLD default
    0.50 filters low-confidence labels from training data; pilot
    data + held-out evaluation will calibrate. A14 flag:
    SPINE_5_LABEL_CONFIDENCE_THRESHOLD_PILOT_PENDING.

(d) Honest tags — what is NOT in this slice (named successors):

    * Slice 19: offline B-vs-C evaluator that consumes the labels
      this slice produces alongside dual_eval_log accumulated from
      DecisionTraces.
    * Daily / weekly scheduling task (matches Task 38/39 pattern)
      that runs the bulk labeler against new pages from production.
      Sibling.
    * Active-learning loop. The current pipeline labels every page
      Claude is asked about; an active-learning version would
      preferentially label pages where the trained model has high
      uncertainty. Sibling.
    * User-state conditioning. v0.1 features are page-only; adding
      BONG-mean / archetype features to the input is sibling.
    * Cohort-conditional labeling. Spine #7 BLOCKED on Loop B; sibling.
    * Disagreement adjudication. When B and C disagree at decision
      time, an adjudicator could fire a fresh Claude API call to
      break the tie. Sibling.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from pydantic import BaseModel, ConfigDict, Field

from adam.intelligence.goal_state_inventory import (
    GoalState,
    list_goal_states,
)

logger = logging.getLogger(__name__)


# Soft-import Anthropic SDK — generator gracefully falls back when
# library is missing. Mirrors claude_summarizer's pattern.
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


# =============================================================================
# A14 calibration-pending defaults
# =============================================================================

# A14 SPINE_5_LABEL_CONFIDENCE_THRESHOLD_PILOT_PENDING
MIN_CONFIDENCE_THRESHOLD: float = 0.50
"""Filter low-confidence labels from training data. Conservative
pre-pilot; LUXY data + held-out eval will calibrate."""

DEFAULT_MODEL: str = "claude-haiku-4-5-20251001"
"""Claude Haiku 4.5 — fast, cheap, capable of structured JSON output.
Right fit for label generation (high volume, simple structured task).
The SKILL guidance defaults to Opus 4.7 for general work; we override
explicitly to Haiku 4.5 here for cost-efficiency on the offline
label-generation pipeline."""

DEFAULT_MAX_TOKENS: int = 1024
"""Conservative max_tokens for the structured response (3 fields,
one short list, one short string). Keeps cost down."""

CACHE_CONTROL_TTL: str = "1h"
"""1-hour TTL on the system-prompt cache. Aligns with batch-labeling
cadence (typically minutes-to-hours per run). 5-minute default would
miss most reads on bursty workloads."""


_GOAL_STATE_NEO4J_LABEL_NODE = "GoalStateLabel"


# =============================================================================
# Pydantic schemas — structured output + persistence
# =============================================================================


class GoalStateLabelResponse(BaseModel):
    """Schema for ``client.messages.parse()`` structured output.

    Constrains Claude to multi-label JSON with active goals,
    confidence, and brief reasoning. The reasoning is a paper-trail
    aid for offline review; it is NOT used by the trained model.
    """

    model_config = ConfigDict(extra="forbid")

    active_goal_state_ids: List[str] = Field(
        description=(
            "List of goal_state_id strings from the LUXY goal-state "
            "inventory that the user is actively pursuing on this page. "
            "Multi-label — multiple can be active simultaneously. "
            "Empty list when no inventory goal applies."
        ),
    )
    confidence: float = Field(
        ge=0.0, le=1.0,
        description=(
            "Calibrated confidence in [0, 1] reflecting how unambiguously "
            "the page primes the listed goal states. 1.0 = unambiguous; "
            "0.0 = no signal."
        ),
    )
    reasoning: str = Field(
        max_length=500,
        description=(
            "One- or two-sentence explanation of which page features "
            "drove the goal-state inference. For offline review only."
        ),
    )


class GoalStateLabel(BaseModel):
    """Persisted label tuple for the training pipeline.

    page_features format matches the input contract of
    ``goal_state_logistic_model.extract_feature_vector`` — both B
    and C train from the same labels, same features.
    """

    model_config = ConfigDict(extra="forbid")

    label_id: str
    """Stable ID — typically derived from page_url hash or a UUID."""

    page_url: str
    page_features: Dict[str, Any]
    active_goal_state_ids: List[str]
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str = ""
    model_used: str = DEFAULT_MODEL
    generated_at_ts: float = Field(default_factory=time.time)


# =============================================================================
# Prompt construction (frozen — cacheable prefix)
# =============================================================================


def _build_system_prompt() -> str:
    """Build the static system prompt embedding the LUXY inventory.

    The prompt is FROZEN across requests — no timestamps, no per-page
    interpolation. The full 14-goal inventory + descriptions + keyword
    markers + posture compatibilities live here. This is the
    cacheable prefix; with ``cache_control`` the prefix invalidates
    only when the inventory itself changes (rare).
    """
    parts: List[str] = [
        (
            "You are a goal-state classifier for ADAM, a psycholinguistic "
            "advertising platform serving LUXY (corporate black-car). "
            "Given a webpage, your job is to identify which of LUXY's "
            "14 ACTIVE GOAL STATES the user is currently pursuing on "
            "that page.\n"
        ),
        (
            "Goal states are mechanism-adjacent but distinct: they "
            "capture WHY the user is on the page, not what mechanism "
            "would persuade them. Multiple goals can be active "
            "simultaneously (multi-label).\n"
        ),
        "## LUXY GOAL-STATE INVENTORY\n",
    ]

    for g in list_goal_states():
        posture_lines = ", ".join(
            f"{p}={v:.2f}" for p, v in sorted(g.posture_compatibility.items())
        )
        parts.append(
            f"### {g.id}: {g.name}\n"
            f"- Description: {g.description}\n"
            f"- Primary metaphor: {g.primary_metaphor}\n"
            f"- Posture compatibility: {posture_lines}\n"
            f"- Keyword markers: {', '.join(g.keywords[:8])}\n"
        )

    parts.append(
        "\n## CLASSIFICATION DISCIPLINE\n"
        "- Multi-label: a page about commute_readiness AND time_pressure "
        "can have BOTH active.\n"
        "- Empty active list when the page has no LUXY-relevant goal "
        "primed (e.g., entertainment / sports content unrelated to "
        "transportation).\n"
        "- Confidence reflects unambiguity — a clearly airport-themed "
        "page with explicit time-pressure language is high confidence; "
        "a generic business-news page touching travel briefly is low.\n"
        "- Use the keyword markers as priors but don't require them. A "
        "page about 'last-minute trip prep for tomorrow's pitch' "
        "primes professional_encounter_preparation + time_pressure even "
        "without exact keyword match.\n"
        "- Output JSON only. No preamble, no commentary outside the "
        "structured response.\n"
    )

    return "".join(parts)


def _build_user_prompt(
    page_url: str,
    page_text: Optional[str] = None,
    page_features: Optional[Dict[str, Any]] = None,
) -> str:
    """Build the per-page user prompt.

    This is the volatile portion — different per request. Lives
    AFTER the cache_control breakpoint on the system prompt.
    """
    parts: List[str] = [f"PAGE URL: {page_url}\n"]

    if page_features:
        posture = page_features.get("posture_class") or "(unknown)"
        confidence = page_features.get("posture_confidence")
        parts.append(f"PAGE POSTURE: {posture}\n")
        if confidence is not None:
            parts.append(f"POSTURE CONFIDENCE: {confidence:.2f}\n")

    if page_text:
        # Truncate to ~4000 chars to keep input bounded
        truncated = page_text[:4000]
        if len(page_text) > 4000:
            truncated += "...[truncated]"
        parts.append(f"\nPAGE TEXT:\n{truncated}\n")

    parts.append(
        "\nWhich of LUXY's 14 active goal states is the user pursuing "
        "on this page? Return structured JSON."
    )
    return "".join(parts)


# =============================================================================
# Generator
# =============================================================================


class GoalStateLabelGenerator:
    """Multi-label goal-state labeler driven by Claude Haiku 4.5.

    Soft-fails when ``ANTHROPIC_API_KEY`` is unset or the
    ``anthropic`` library isn't installed. ``generate_label_for_page``
    returns None on those paths; callers degrade to passthrough.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = DEFAULT_MODEL,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ) -> None:
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.model = model
        self.max_tokens = max_tokens
        self._client: Optional[Any] = None
        self._inventory_ids: Set[str] = {g.id for g in list_goal_states()}

    @property
    def is_configured(self) -> bool:
        """True iff the SDK is installed AND an API key is present."""
        return ANTHROPIC_AVAILABLE and bool(self.api_key)

    def _get_client(self) -> Any:
        """Lazy-instantiate the Anthropic client."""
        if not ANTHROPIC_AVAILABLE:
            raise ImportError("anthropic library is not installed")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not set")
        if self._client is None:
            self._client = anthropic.Anthropic(api_key=self.api_key)
        return self._client

    def generate_label_for_page(
        self,
        *,
        page_url: str,
        page_text: Optional[str] = None,
        page_features: Optional[Dict[str, Any]] = None,
    ) -> Optional[GoalStateLabel]:
        """Generate one label for a single page.

        Returns None when:
          - SDK / API key missing
          - API call fails
          - response parse fails
          - parsed response has zero valid goal_state_ids AND the
            confidence is below threshold (no signal worth persisting)
        """
        if not self.is_configured:
            logger.debug(
                "GoalStateLabelGenerator: not configured (api_key=%s, "
                "library=%s); skipping",
                bool(self.api_key), ANTHROPIC_AVAILABLE,
            )
            return None

        try:
            client = self._get_client()
        except Exception as exc:
            logger.warning("GoalStateLabelGenerator client init failed: %s", exc)
            return None

        system_prompt = _build_system_prompt()
        user_prompt = _build_user_prompt(
            page_url=page_url,
            page_text=page_text,
            page_features=page_features,
        )

        try:
            # Use messages.parse() for Pydantic-validated structured
            # output. cache_control on the system block — only the
            # static inventory caches; the per-page user_prompt is
            # the variable suffix.
            response = client.messages.parse(
                model=self.model,
                max_tokens=self.max_tokens,
                system=[
                    {
                        "type": "text",
                        "text": system_prompt,
                        "cache_control": {
                            "type": "ephemeral",
                            "ttl": CACHE_CONTROL_TTL,
                        },
                    },
                ],
                messages=[
                    {"role": "user", "content": user_prompt},
                ],
                output_format=GoalStateLabelResponse,
            )
        except Exception as exc:
            logger.warning(
                "GoalStateLabelGenerator API call failed for url=%s: %s",
                page_url, exc,
            )
            return None

        try:
            parsed: GoalStateLabelResponse = response.parsed_output
        except Exception as exc:
            logger.warning(
                "GoalStateLabelGenerator response parse failed: %s", exc,
            )
            return None

        # Filter goal_state_ids to inventory-known IDs only
        valid_ids = [
            gid for gid in parsed.active_goal_state_ids
            if gid in self._inventory_ids
        ]
        invalid_ids = [
            gid for gid in parsed.active_goal_state_ids
            if gid not in self._inventory_ids
        ]
        if invalid_ids:
            logger.debug(
                "GoalStateLabelGenerator: dropping unknown goal_state_ids %s "
                "for url=%s (Claude hallucinated)",
                invalid_ids, page_url,
            )

        # Filter low-confidence empty labels — no training signal
        if not valid_ids and parsed.confidence < MIN_CONFIDENCE_THRESHOLD:
            return None

        return GoalStateLabel(
            label_id=f"label-{abs(hash(page_url))}-{int(time.time() * 1000)}",
            page_url=page_url,
            page_features=dict(page_features or {}),
            active_goal_state_ids=valid_ids,
            confidence=float(parsed.confidence),
            reasoning=str(parsed.reasoning or ""),
            model_used=self.model,
        )

    def generate_labels_bulk(
        self,
        pages: List[Dict[str, Any]],
        *,
        rate_limit_delay_seconds: float = 0.0,
    ) -> List[GoalStateLabel]:
        """Bulk label generation. Each page is a dict with keys
        ``page_url``, optional ``page_text``, optional ``page_features``.

        rate_limit_delay_seconds: optional sleep between requests to
        avoid hammering the API. The SDK auto-retries 429s with
        exponential backoff, but a small inter-request delay reduces
        retry cost on tight rate-limit tiers.

        Returns successfully-labeled pages only. Failed labels are
        logged and dropped from the result.
        """
        labels: List[GoalStateLabel] = []
        for i, page in enumerate(pages):
            label = self.generate_label_for_page(
                page_url=page.get("page_url", ""),
                page_text=page.get("page_text"),
                page_features=page.get("page_features"),
            )
            if label is not None:
                labels.append(label)
            if rate_limit_delay_seconds > 0 and i + 1 < len(pages):
                time.sleep(rate_limit_delay_seconds)
        logger.info(
            "GoalStateLabelGenerator bulk: %d/%d labels produced",
            len(labels), len(pages),
        )
        return labels


# =============================================================================
# Neo4j persistence
# =============================================================================


_PERSIST_LABEL_CYPHER: str = (
    "MERGE (l:" + _GOAL_STATE_NEO4J_LABEL_NODE + " {label_id: $label_id}) "
    "SET l.page_url = $page_url, "
    "    l.page_features_json = $page_features_json, "
    "    l.active_goal_state_ids_json = $active_goal_state_ids_json, "
    "    l.confidence = $confidence, "
    "    l.reasoning = $reasoning, "
    "    l.model_used = $model_used, "
    "    l.generated_at_ts = $generated_at_ts"
)


_LOAD_LABELS_CYPHER: str = (
    "MATCH (l:" + _GOAL_STATE_NEO4J_LABEL_NODE + ") "
    "WHERE l.confidence >= $min_confidence "
    "RETURN l.label_id AS label_id, "
    "       l.page_url AS page_url, "
    "       l.page_features_json AS page_features_json, "
    "       l.active_goal_state_ids_json AS active_goal_state_ids_json, "
    "       l.confidence AS confidence, "
    "       l.reasoning AS reasoning, "
    "       l.model_used AS model_used, "
    "       l.generated_at_ts AS generated_at_ts"
)


async def persist_label_to_neo4j(
    label: GoalStateLabel,
    driver: Optional[Any],
) -> bool:
    """Idempotent MERGE of one GoalStateLabel."""
    if driver is None:
        return False
    try:
        async with driver.session() as session:
            await session.run(
                _PERSIST_LABEL_CYPHER,
                label_id=label.label_id,
                page_url=label.page_url,
                page_features_json=json.dumps(label.page_features),
                active_goal_state_ids_json=json.dumps(
                    label.active_goal_state_ids,
                ),
                confidence=float(label.confidence),
                reasoning=label.reasoning,
                model_used=label.model_used,
                generated_at_ts=float(label.generated_at_ts),
            )
        return True
    except Exception as exc:
        logger.warning(
            "persist_label_to_neo4j failed for label_id=%s: %s",
            label.label_id, exc,
        )
        return False


async def load_labels_from_neo4j(
    driver: Optional[Any],
    *,
    min_confidence: float = MIN_CONFIDENCE_THRESHOLD,
) -> List[GoalStateLabel]:
    """Load all labels above the confidence threshold.

    Used by the train_models_from_neo4j convenience to feed B and
    C with the same labeled set.
    """
    if driver is None:
        return []
    out: List[GoalStateLabel] = []
    try:
        async with driver.session() as session:
            result = await session.run(
                _LOAD_LABELS_CYPHER, min_confidence=float(min_confidence),
            )
            async for record in result:
                try:
                    label = GoalStateLabel(
                        label_id=str(record.get("label_id")),
                        page_url=str(record.get("page_url") or ""),
                        page_features=json.loads(
                            record.get("page_features_json") or "{}",
                        ),
                        active_goal_state_ids=json.loads(
                            record.get("active_goal_state_ids_json") or "[]",
                        ),
                        confidence=float(record.get("confidence") or 0.0),
                        reasoning=str(record.get("reasoning") or ""),
                        model_used=str(record.get("model_used") or ""),
                        generated_at_ts=float(
                            record.get("generated_at_ts") or 0.0
                        ),
                    )
                    out.append(label)
                except Exception as exc:
                    logger.debug("label parse failed: %s", exc)
                    continue
    except Exception as exc:
        logger.warning("load_labels_from_neo4j failed: %s", exc)
        return []
    return out


# =============================================================================
# Train both models from labels — convenience for the dual-eval setup
# =============================================================================


def train_models_from_labels(
    labels: List[GoalStateLabel],
) -> Tuple[Optional[Any], Optional[Any]]:
    """Train LogisticGoalStateModel (B) and HierarchicalGoalStateModel
    (C) from the same labeled set. Returns (logistic_model,
    hierarchical_model).

    Either / both may be None if their underlying library is
    unavailable (sklearn / numpyro). The DualEvalContext degrades
    cleanly when one model is None — the other still gets to be
    primary.

    Multi-label format mapping:
      - LogisticGoalStateModel takes (features, single_dominant_goal)
        — pick the lowest-id (deterministic) when multiple are active;
        skip when active list is empty.
      - HierarchicalGoalStateModel takes (features, set_of_active_goals)
        directly — multi-label is its native format.
    """
    if not labels:
        return None, None

    logistic_model: Optional[Any] = None
    try:
        from adam.intelligence.goal_state_logistic_model import (
            LogisticGoalStateModel,
        )
        # Single-label mapping: pick first sorted active goal as dominant.
        # Drops zero-active-goal labels (no positive signal for B).
        single_label_pairs: List[Tuple[Dict[str, Any], str]] = []
        for label in labels:
            if not label.active_goal_state_ids:
                continue
            dominant = sorted(label.active_goal_state_ids)[0]
            single_label_pairs.append((label.page_features, dominant))

        if single_label_pairs:
            candidate = LogisticGoalStateModel()
            if candidate.train(single_label_pairs):
                logistic_model = candidate
    except Exception as exc:
        logger.warning("LogisticGoalStateModel train failed: %s", exc)

    hierarchical_model: Optional[Any] = None
    try:
        from adam.intelligence.goal_state_hierarchical_model import (
            HierarchicalGoalStateModel,
        )
        multi_label_pairs: List[Tuple[Dict[str, Any], Set[str]]] = [
            (label.page_features, set(label.active_goal_state_ids))
            for label in labels
        ]

        candidate = HierarchicalGoalStateModel()
        if candidate.train(multi_label_pairs):
            hierarchical_model = candidate
    except Exception as exc:
        logger.warning("HierarchicalGoalStateModel train failed: %s", exc)

    return logistic_model, hierarchical_model
