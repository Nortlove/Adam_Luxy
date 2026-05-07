"""Offline page-priming pipeline (directive §S3.2).

Runs offline in batch over a URL set: fetch page content, profile via
the existing `ContentProfiler` (8 NDF dimensions + mechanisms +
emotions per `adam/platform/intelligence/content_profiler.py`),
map the profile to a `PagePrimingSignature`, and persist to the
Feature Store via the §S3.3 surface.

Reuse-not-recreate per directive §1.3: ContentProfiler is the
canonical NDF/mechanism profiler; this module composes it rather
than reimplementing scoring.

Mapping ContentProfiler output → PagePrimingSignature dimensions:

  * valence ∈ [-1, 1]
      Aggregated from positive vs negative emotions:
        +(joy + trust + excitement) - (fear) ; normalized into [-1,1]
      Backstop: derive from approach_avoidance NDF dim
      (approach_avoidance ∈ [0,1] → 2*(x-0.5) ∈ [-1,1]).
      Both signals combined with 0.6/0.4 weight (emotion stronger if
      detected) so URLs without emotion words still get a valence.

  * arousal ∈ [0, 1]
      Direct from NDF arousal_seeking dimension (already in [0,1]).
      Augmented with emotion intensity sum (clipped) when emotions
      detected.

  * regulatory_focus_priming ∈ {promotion, prevention, neutral}
      Higgins regulatory focus operationalized via:
        - promotion if approach_avoidance > 0.6 (gain-framed) or
          mechanisms include reciprocity / liking (advancement frames)
        - prevention if approach_avoidance < 0.4 (loss-framed) or
          mechanisms include loss_aversion / scarcity (vigilance frames)
        - neutral otherwise

  * cognitive_load_estimate ∈ [0, 1]
      Inverse of cognitive_velocity NDF (high velocity = low load to
      process), clipped to [0, 1].

  * activated_frames: tuple[str, ...]
      Top-N mechanisms from ContentProfiler output, capped at 5.

  * confidence_per_dimension
      Distributed from ContentProfiler's overall confidence:
        - emotion-derived dims (valence, arousal) get
          confidence * (0.7 if emotions_detected else 0.3)
        - mechanism-derived dims get confidence * 0.7
        - NDF-derived dim (cognitive_load) gets confidence * 0.6

The mapper is pure (deterministic given the ContentProfiler output)
so tests can pin invariants without HTTP or graph dependencies.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple

from adam.priming.signature import (
    PagePrimingSignature,
    SIGNATURE_VERSION_V1,
    neutral_signature,
)

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------------
# URL-content fetcher signature (injectable for testability)
# ----------------------------------------------------------------------------

@dataclass(frozen=True)
class FetchedPage:
    """Output of a URL fetch step."""
    url: str
    title: str
    body: str
    fetched_at: datetime
    http_status: int
    failure_reason: Optional[str] = None


# Async fetcher signature: takes URL, returns FetchedPage.
# Implementations can use requests + BeautifulSoup, httpx + readability,
# or any other HTML→(title, body) extractor. Tests inject mocks.
FetchFn = Callable[[str], Awaitable[FetchedPage]]


# ----------------------------------------------------------------------------
# ContentProfiler-output → PagePrimingSignature mapping
# ----------------------------------------------------------------------------

def url_to_hash(url: str) -> str:
    """Stable URL identity for Feature Store keying. SHA-256 hex
    digest of the canonical URL string (no normalization beyond
    strip + lowercase scheme/host)."""
    return hashlib.sha256(url.strip().encode("utf-8")).hexdigest()


# Emotion classes the mapper consumes (from ContentProfiler EMOTION_KEYWORDS).
_POSITIVE_EMOTIONS = ("joy", "trust", "excitement")
_NEGATIVE_EMOTIONS = ("fear",)


def _compute_valence(
    emotions: Dict[str, float], ndf: Dict[str, float],
) -> float:
    """Combine emotion-based valence with NDF approach_avoidance backstop.

    Emotion weight: 0.6 (when detected); NDF weight: 0.4. When emotions
    are all zero, falls back to NDF-only.
    """
    pos = sum(emotions.get(k, 0.0) for k in _POSITIVE_EMOTIONS)
    neg = sum(emotions.get(k, 0.0) for k in _NEGATIVE_EMOTIONS)
    total_emo = pos + neg
    if total_emo > 0:
        # Normalize to [-1, 1].
        emo_valence = (pos - neg) / max(total_emo, 1e-6)
    else:
        emo_valence = 0.0

    # NDF approach_avoidance is in [0, 1]; map to [-1, 1].
    aa = ndf.get("approach_avoidance", 0.5)
    ndf_valence = 2.0 * (aa - 0.5)

    if total_emo > 0:
        v = 0.6 * emo_valence + 0.4 * ndf_valence
    else:
        v = ndf_valence
    return max(-1.0, min(1.0, v))


def _compute_arousal(
    emotions: Dict[str, float], ndf: Dict[str, float],
) -> float:
    """NDF arousal_seeking + emotion-intensity augmentation."""
    base = ndf.get("arousal_seeking", 0.5)
    emo_sum = sum(emotions.values())
    augmented = base + 0.3 * min(1.0, emo_sum / 3.0)
    return max(0.0, min(1.0, augmented))


_PROMOTION_MECHS = frozenset({"reciprocity", "liking",
                              "commitment_consistency"})
_PREVENTION_MECHS = frozenset({"loss_aversion", "scarcity"})


def _compute_regulatory_focus(
    ndf: Dict[str, float], mechanisms: List[str],
) -> str:
    """Higgins promotion/prevention/neutral classification."""
    aa = ndf.get("approach_avoidance", 0.5)
    mech_set = set(mechanisms)
    promotion_signal = (aa > 0.6) or bool(mech_set & _PROMOTION_MECHS)
    prevention_signal = (aa < 0.4) or bool(mech_set & _PREVENTION_MECHS)
    if promotion_signal and not prevention_signal:
        return "promotion"
    if prevention_signal and not promotion_signal:
        return "prevention"
    return "neutral"


def _compute_cognitive_load(ndf: Dict[str, float]) -> float:
    """Inverse of cognitive_velocity; clipped to [0, 1].

    High velocity (text easily processed) → low load. Default mid
    value 0.5 when velocity is missing."""
    velocity = ndf.get("cognitive_velocity", 0.5)
    load = 1.0 - velocity
    return max(0.0, min(1.0, load))


def _compute_confidence_per_dim(
    overall: float, emotions: Dict[str, float],
) -> Dict[str, float]:
    """Distribute the ContentProfiler overall confidence to per-dim
    confidences with named weighting."""
    base = max(0.0, min(1.0, overall))
    emo_factor = 0.7 if sum(emotions.values()) > 0 else 0.3
    return {
        "valence": base * emo_factor,
        "arousal": base * emo_factor,
        "regulatory_focus_priming": base * 0.7,
        "cognitive_load_estimate": base * 0.6,
        "activated_frames": base * 0.7,
    }


def map_profile_to_signature(
    url: str,
    profile: Dict[str, Any],
    *,
    signature_version: str = SIGNATURE_VERSION_V1,
    computed_at: Optional[datetime] = None,
) -> PagePrimingSignature:
    """Pure mapper: ContentProfiler output → PagePrimingSignature.

    Determines all 5 dimensions + per-dim confidences from the
    profile dict + B/S6-prep.2 persuasion_knowledge_activation.
    No I/O.
    """
    ndf = profile.get("ndf_profile") or {}
    mechs = profile.get("mechanisms") or []
    emotions = profile.get("emotions") or {}
    overall_conf = float(profile.get("confidence", 0.0))

    # B/S6-prep.2 — extract Persuasion Knowledge Model activation
    # from ContentProfiler.profile() output. Old profile dicts
    # without the key default to (0.0, 0.5) — backward-compat for
    # any profile producer that hasn't been updated.
    pk_block = profile.get("persuasion_knowledge") or {}
    pk_activation = float(pk_block.get("activation", 0.0))
    pk_confidence = float(pk_block.get("confidence", 0.5))

    confidence_dim = _compute_confidence_per_dim(overall_conf, emotions)
    confidence_dim["persuasion_knowledge"] = pk_confidence

    return PagePrimingSignature(
        url_hash=url_to_hash(url),
        valence=_compute_valence(emotions, ndf),
        arousal=_compute_arousal(emotions, ndf),
        regulatory_focus_priming=_compute_regulatory_focus(ndf, mechs),
        cognitive_load_estimate=_compute_cognitive_load(ndf),
        activated_frames=tuple(mechs[:5]),
        persuasion_knowledge_activation=pk_activation,
        confidence_per_dimension=confidence_dim,
        computed_at=computed_at or datetime.now(tz=timezone.utc),
        signature_version=signature_version,
    )


# ----------------------------------------------------------------------------
# Pipeline orchestration
# ----------------------------------------------------------------------------

@dataclass(frozen=True)
class PipelineResult:
    """Per-URL pipeline outcome."""
    url: str
    signature: Optional[PagePrimingSignature]
    fetch_failure: Optional[str] = None
    profile_failure: Optional[str] = None

    @property
    def succeeded(self) -> bool:
        return self.signature is not None and self.fetch_failure is None \
            and self.profile_failure is None


async def profile_url_to_signature(
    url: str,
    fetcher: FetchFn,
    profiler: Any,
    *,
    fallback_to_neutral_on_failure: bool = True,
) -> PipelineResult:
    """End-to-end: fetch URL → profile → map to signature.

    On fetch failure: if `fallback_to_neutral_on_failure`, return a
    neutral signature (so the pipeline never blocks downstream
    consumers); otherwise return PipelineResult with failure reason.

    `profiler` must implement `async profile(title, body, metadata)`
    matching ContentProfiler's interface.
    """
    try:
        page = await fetcher(url)
    except Exception as exc:
        msg = f"fetch_exception:{type(exc).__name__}:{exc}"
        logger.warning("fetch failed for %s: %s", url, msg)
        if fallback_to_neutral_on_failure:
            return PipelineResult(
                url=url,
                signature=neutral_signature(url_to_hash(url)),
                fetch_failure=msg,
            )
        return PipelineResult(url=url, signature=None, fetch_failure=msg)

    if page.failure_reason or page.http_status >= 400:
        reason = (page.failure_reason
                  or f"http_{page.http_status}")
        if fallback_to_neutral_on_failure:
            return PipelineResult(
                url=url,
                signature=neutral_signature(url_to_hash(url)),
                fetch_failure=reason,
            )
        return PipelineResult(url=url, signature=None, fetch_failure=reason)

    try:
        profile = await profiler.profile(
            title=page.title, body=page.body,
            metadata={"url": url},
        )
    except Exception as exc:
        msg = f"profile_exception:{type(exc).__name__}:{exc}"
        logger.warning("profile failed for %s: %s", url, msg)
        if fallback_to_neutral_on_failure:
            return PipelineResult(
                url=url,
                signature=neutral_signature(url_to_hash(url)),
                profile_failure=msg,
            )
        return PipelineResult(url=url, signature=None, profile_failure=msg)

    sig = map_profile_to_signature(url, profile)
    return PipelineResult(url=url, signature=sig)


async def batch_process_urls(
    urls: List[str],
    fetcher: FetchFn,
    profiler: Any,
    *,
    persist_fn: Optional[Callable[[PagePrimingSignature], Awaitable[bool]]] = None,
    concurrency: int = 8,
    fallback_to_neutral_on_failure: bool = True,
) -> List[PipelineResult]:
    """Batch-pipeline N URLs with bounded concurrency. If `persist_fn`
    is provided, every successful signature is persisted via that
    callable (the §S3.3 Feature Store row-write API).

    Returns one `PipelineResult` per input URL, in the original order.
    """
    semaphore = asyncio.Semaphore(concurrency)

    async def _process_one(u: str) -> PipelineResult:
        async with semaphore:
            return await profile_url_to_signature(
                u, fetcher, profiler,
                fallback_to_neutral_on_failure=fallback_to_neutral_on_failure,
            )

    results = await asyncio.gather(
        *(_process_one(u) for u in urls), return_exceptions=False,
    )

    if persist_fn is not None:
        for r in results:
            if r.signature is not None:
                try:
                    await persist_fn(r.signature)
                except Exception as exc:
                    logger.warning("persist failed for %s: %s", r.url, exc)
    return list(results)
