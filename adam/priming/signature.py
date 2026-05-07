"""PagePrimingSignature — frozen dataclass per directive §S3.1.

The page-priming-signature is the architectural substitute for the
spec-only `MicroStateDetector` at bid time (per §S3 reframe). It is
computed offline by the ContentProfiler-driven pipeline (§S3.2) and
written to the Feature Store (§S3.3) for sub-5ms cascade-time lookup.

Dimensions (per directive §S3.1):
  * valence                          ∈ [-1, 1]
  * arousal                          ∈ [0, 1]
  * regulatory_focus_priming         ∈ {promotion, prevention, neutral}
  * cognitive_load_estimate          ∈ [0, 1]
  * activated_frames                 tuple[str, ...] (canonical frame IDs)
  * persuasion_knowledge_activation  ∈ [0, 1]  (added in B / S6-prep.2)
  * confidence_per_dimension         dict[str, float] each ∈ [0, 1]

Plus identity fields (url_hash, computed_at, signature_version) for
Feature Store keying + cache invalidation across signature-version
upgrades.

Schema versions:
  * page_priming_v1 (initial): 5 dimensions
  * page_priming_v2 (B/S6-prep.2): adds persuasion_knowledge_activation
    per Friestad-Wright PKM (gap assessment §3 Block F #25).
    Backward-compatible: old v1 cached entries deserialize cleanly with
    persuasion_knowledge_activation defaulted to 0.0; signature_version
    field preserved as 'page_priming_v1' on those entries.

Serialization:
  * to_feature_store_row()      — flat dict suitable for Redis/etc.
  * from_feature_store_row(d)   — round-trip safe constructor.

Cold-miss fallback (§S3.3): caller catches missing-key, calls
`neutral_signature(url_hash)` which returns a frozen all-floor
signature so the cascade never blocks.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Literal, Mapping, Tuple


# ----------------------------------------------------------------------------
# Constants
# ----------------------------------------------------------------------------

RegulatoryFocus = Literal["promotion", "prevention", "neutral"]

SIGNATURE_DIMENSIONS: Tuple[str, ...] = (
    "valence",
    "arousal",
    "regulatory_focus_priming",
    "cognitive_load_estimate",
    "activated_frames",
    "persuasion_knowledge_activation",
)

SIGNATURE_VERSION_V1: str = "page_priming_v1"
SIGNATURE_VERSION_V2: str = "page_priming_v2"


# ----------------------------------------------------------------------------
# Dataclass
# ----------------------------------------------------------------------------

@dataclass(frozen=True)
class PagePrimingSignature:
    """Immutable signature row per directive §S3.1.

    Range invariants are enforced in __post_init__ so no caller can
    construct an out-of-range signature; downstream cascade code can
    rely on the invariants without re-validating.
    """
    url_hash: str
    valence: float                                # [-1, 1]
    arousal: float                                # [0, 1]
    regulatory_focus_priming: RegulatoryFocus     # promotion|prevention|neutral
    cognitive_load_estimate: float                # [0, 1]
    activated_frames: Tuple[str, ...]             # canonical frame IDs
    # Friestad-Wright Persuasion Knowledge Model activation score
    # (B/S6-prep.2). Higher values = page content cues activate
    # consumer's persuasion-knowledge schemas (#ad / sponsored /
    # salesy diction / aggressive persuasion language). Default 0.0
    # for backward-compat with v1 cached entries.
    persuasion_knowledge_activation: float = 0.0  # [0, 1]
    confidence_per_dimension: Mapping[str, float] = field(default_factory=dict)
    computed_at: datetime = field(
        default_factory=lambda: datetime.now(tz=timezone.utc),
    )
    signature_version: str = SIGNATURE_VERSION_V2

    def __post_init__(self) -> None:
        if not (-1.0 <= self.valence <= 1.0):
            raise ValueError(
                f"valence out of range [-1,1]: {self.valence}"
            )
        if not (0.0 <= self.arousal <= 1.0):
            raise ValueError(
                f"arousal out of range [0,1]: {self.arousal}"
            )
        if self.regulatory_focus_priming not in (
            "promotion", "prevention", "neutral",
        ):
            raise ValueError(
                f"regulatory_focus_priming invalid: "
                f"{self.regulatory_focus_priming!r}"
            )
        if not (0.0 <= self.cognitive_load_estimate <= 1.0):
            raise ValueError(
                f"cognitive_load_estimate out of range [0,1]: "
                f"{self.cognitive_load_estimate}"
            )
        if not (0.0 <= self.persuasion_knowledge_activation <= 1.0):
            raise ValueError(
                f"persuasion_knowledge_activation out of range "
                f"[0,1]: {self.persuasion_knowledge_activation}"
            )
        if not isinstance(self.activated_frames, tuple):
            raise TypeError(
                "activated_frames must be a tuple (frozen-friendly)"
            )
        for k, v in self.confidence_per_dimension.items():
            if not (0.0 <= v <= 1.0):
                raise ValueError(
                    f"confidence_per_dimension[{k!r}] out of range "
                    f"[0,1]: {v}"
                )

    # -------- serialization --------

    def to_feature_store_row(self) -> Dict[str, Any]:
        """Flat dict suitable for Redis HSET / SQL row write.

        Lists/tuples and dicts are JSON-encoded so the row is
        scalar-only at the storage layer (matches the Enhancement #30
        feature-store row contract).
        """
        return {
            "url_hash": self.url_hash,
            "valence": self.valence,
            "arousal": self.arousal,
            "regulatory_focus_priming": self.regulatory_focus_priming,
            "cognitive_load_estimate": self.cognitive_load_estimate,
            "activated_frames_json": json.dumps(list(self.activated_frames)),
            "persuasion_knowledge_activation": (
                self.persuasion_knowledge_activation
            ),
            "confidence_per_dimension_json": json.dumps(
                dict(self.confidence_per_dimension),
            ),
            "computed_at_iso": self.computed_at.isoformat(),
            "signature_version": self.signature_version,
        }

    @classmethod
    def from_feature_store_row(
        cls, row: Mapping[str, Any],
    ) -> "PagePrimingSignature":
        """Round-trip constructor from a feature-store row dict."""
        frames_raw = row.get("activated_frames_json", "[]")
        confs_raw = row.get("confidence_per_dimension_json", "{}")
        if isinstance(frames_raw, (list, tuple)):
            frames = tuple(frames_raw)
        else:
            frames = tuple(json.loads(frames_raw))
        if isinstance(confs_raw, dict):
            confs = dict(confs_raw)
        else:
            confs = json.loads(confs_raw)
        ts_raw = row.get("computed_at_iso") or row.get("computed_at")
        if isinstance(ts_raw, datetime):
            ts = ts_raw
        else:
            ts = datetime.fromisoformat(ts_raw) if ts_raw else \
                datetime.now(tz=timezone.utc)
        # Backward-compat (B/S6-prep.2): old v1 cached entries lack
        # persuasion_knowledge_activation; default to 0.0. Legacy
        # entries also preserve their signature_version (v1) — only
        # newly-constructed signatures default to V2.
        return cls(
            url_hash=row["url_hash"],
            valence=float(row["valence"]),
            arousal=float(row["arousal"]),
            regulatory_focus_priming=row["regulatory_focus_priming"],
            cognitive_load_estimate=float(row["cognitive_load_estimate"]),
            activated_frames=frames,
            persuasion_knowledge_activation=float(
                row.get("persuasion_knowledge_activation", 0.0),
            ),
            confidence_per_dimension=confs,
            computed_at=ts,
            signature_version=row.get(
                "signature_version", SIGNATURE_VERSION_V1,
            ),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Idiomatic dict (lists for tuples, ISO timestamp). For
        JSON serialization outside the feature-store row contract."""
        d = asdict(self)
        d["activated_frames"] = list(self.activated_frames)
        d["confidence_per_dimension"] = dict(self.confidence_per_dimension)
        d["computed_at"] = self.computed_at.isoformat()
        return d


# ----------------------------------------------------------------------------
# Cold-miss fallback (§S3.3)
# ----------------------------------------------------------------------------

def neutral_signature(url_hash: str) -> PagePrimingSignature:
    """Return an all-floor neutral signature for cold-miss fallback.

    Per directive §S3.3: when the L1/L2/L3 cascade misses, the
    cascade returns this synthetic neutral so it never blocks.
    Confidence floored at 0.0 across all dimensions so downstream
    consumers can detect the cold-miss case.
    """
    now = datetime.now(tz=timezone.utc)
    return PagePrimingSignature(
        url_hash=url_hash,
        valence=0.0,
        arousal=0.0,
        regulatory_focus_priming="neutral",
        cognitive_load_estimate=0.0,
        activated_frames=tuple(),
        persuasion_knowledge_activation=0.0,
        confidence_per_dimension={
            "valence": 0.0,
            "arousal": 0.0,
            "regulatory_focus_priming": 0.0,
            "cognitive_load_estimate": 0.0,
            "activated_frames": 0.0,
            "persuasion_knowledge": 0.0,
        },
        computed_at=now,
        signature_version=SIGNATURE_VERSION_V2,
    )
