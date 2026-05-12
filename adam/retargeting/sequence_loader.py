"""Parameterized typed loader for tenant Layer-2 therapeutic sequences (S8.2).

Resolves and materializes `adam/retargeting/campaigns/<tenant_id>/
<campaign_id>/sequences.yaml` into typed template objects. The loader
owns its own lightweight frozen-dataclass templates (`SequenceTemplate`,
`TouchTemplate`, `SuppressionRule`, `SequencesMetadata`) — these are
SPEC/TEMPLATE objects, distinct from the per-user runtime state machine
in `adam/retargeting/models/sequences.py` (`TherapeuticSequence` /
`TherapeuticTouch`, which carry `user_id`, delivered-touch history,
cumulative reactance, etc.). S8.3 will instantiate the runtime model
per-user, populating it from a `SequenceTemplate`; that is S8.3's job,
not this slice's.

Design (per S8.2 deviation D1, operator-approved 2026-05-12): keeping
the template metadata off the runtime model preserves the runtime
model's role and avoids a >30-LOC schema mutation; `models/sequences.py`
is untouched by S8.2.

Multi-tenant: a second tenant onboards by dropping a `sequences.yaml`
under their namespace — zero code changes. The same `load_sequences`
handles any tenant because the crosswalk and archetype set live in the
data, not the code. A test-only `campaigns_root` override lets fixtures
under `tests/retargeting/fixtures/...` exercise the loader.

Cache: module-level dict keyed by `(tenant_id, campaign_id, str(root))`
so fixture loads never pollute a production tenant's cache and vice
versa. Not thread-safe by design — FastAPI is single-process per
worker; the cache is per-worker. `force_reload` invalidates one
(tenant, campaign, root) entry; other entries are preserved.

Fail-loud at the loader boundary (`SequenceLoaderError` on any
structural / validation failure). Cascade fail-soft is S8.3's job.
"""

import pathlib
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union

import yaml

from adam.cold_start.models.enums import ArchetypeID

# Production tenant root. Fixtures override via the `campaigns_root` kwarg.
CAMPAIGNS_ROOT = pathlib.Path(__file__).parent / "campaigns"


# =============================================================================
# Loader-local template dataclasses (D1 — distinct from runtime models)
# =============================================================================


@dataclass(frozen=True)
class TouchTemplate:
    """One touch in a per-archetype therapeutic sequence template.

    `touch_text` is None when `touch_text_status == "needs_authoring"`
    (structure derived from bilateral findings; copy authored in a
    follow-up). When present, `touch_text` is <=15 words (copyright
    discipline on bilateral-doc quotations).
    """

    touch_number: int
    touch_role: str  # "initial_impression" | "retargeting"
    mechanism_primary: str
    mechanism_secondary: Optional[str] = None
    alignment_gap_addressed: str = ""
    touch_text_status: str = "needs_authoring"  # | "extracted_from_doc"
    touch_text: Optional[str] = None


@dataclass(frozen=True)
class SequenceTemplate:
    """Per-archetype therapeutic retargeting sequence template (active)."""

    archetype_id: str
    derivation_status: str  # "extracted_from_bilateral_doc"
                            # | "derived_from_bilateral_findings_needs_authoring"
    touch_count: int
    touches: Tuple[TouchTemplate, ...]
    bilateral_findings: Dict[str, Any] = field(default_factory=dict)
    becca_empirical_data: Dict[str, Any] = field(default_factory=dict)
    psychological_profile: Dict[str, Any] = field(default_factory=dict)
    population_pct: float = 0.0
    conversion_rate_pct: float = 0.0
    budget_allocation_pct: int = 0


@dataclass(frozen=True)
class SuppressionRule:
    """Suppression directive for an advertising-resistant archetype."""

    archetype_id: str
    action: str  # "suppress_bid"
    rationale: str
    psychological_basis: str
    bilateral_findings: Dict[str, Any] = field(default_factory=dict)
    becca_empirical_data: Dict[str, Any] = field(default_factory=dict)
    psychological_profile: Dict[str, Any] = field(default_factory=dict)
    population_pct: float = 0.0
    conversion_rate_pct: float = 0.0
    budget_allocation_pct: int = 0


@dataclass(frozen=True)
class SequencesMetadata:
    """Top-level metadata for a tenant's campaign sequences file."""

    tenant_id: str
    campaign_id: str
    tenant_display_name: str
    campaign_display_name: str
    schema_version: str
    source_doc: str
    layer: int
    archetype_count: int
    active_archetype_count: int
    suppress_archetype_count: int
    extra: Dict[str, Any] = field(default_factory=dict)  # remaining keys verbatim


@dataclass(frozen=True)
class LoadedSequences:
    """Materialized result of loading a tenant's campaign sequences.yaml."""

    tenant_id: str
    campaign_id: str
    metadata: SequencesMetadata
    active_archetypes: Dict[str, SequenceTemplate]
    suppress_archetypes: Dict[str, SuppressionRule]
    # 8 keys (one per ArchetypeID); value is the Layer-2 archetype_id the
    # Layer-1 archetype routes to, OR None when no Layer-2 archetype lists
    # that Layer-1 in maps_from (e.g., the 2 suppress archetypes' empty
    # maps_from — cold-start can't route there).
    crosswalk: Dict[ArchetypeID, Optional[str]]

    def archetype_ids(self) -> Tuple[str, ...]:
        """All Layer-2 archetype_ids (active + suppress), sorted."""
        return tuple(sorted([*self.active_archetypes, *self.suppress_archetypes]))


class SequenceLoaderError(Exception):
    """Raised on YAML structural / validation failures at the loader boundary."""


# =============================================================================
# Module-level cache
# =============================================================================

_CACHE: Dict[Tuple[str, str, str], LoadedSequences] = {}


def clear_cache() -> None:
    """Test-only: clear the entire loader cache.

    Production should use `force_reload=True` on a specific
    (tenant_id, campaign_id) instead.
    """
    _CACHE.clear()


# =============================================================================
# Loader
# =============================================================================


def _resolve_yaml_path(
    tenant_id: str, campaign_id: str, campaigns_root: pathlib.Path,
) -> pathlib.Path:
    return campaigns_root / tenant_id / campaign_id / "sequences.yaml"


def _build_touch_template(raw: Dict[str, Any]) -> TouchTemplate:
    try:
        return TouchTemplate(
            touch_number=int(raw["touch_number"]),
            touch_role=str(raw["touch_role"]),
            mechanism_primary=str(raw["mechanism_primary"]),
            mechanism_secondary=(
                str(raw["mechanism_secondary"])
                if raw.get("mechanism_secondary") is not None
                else None
            ),
            alignment_gap_addressed=str(raw.get("alignment_gap_addressed", "")),
            touch_text_status=str(raw.get("touch_text_status", "needs_authoring")),
            touch_text=(
                str(raw["touch_text"]) if raw.get("touch_text") is not None else None
            ),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise SequenceLoaderError(f"malformed touch entry: {raw!r} ({exc})") from exc


def _build_active(archetype_key: str, raw: Dict[str, Any]) -> SequenceTemplate:
    seq = raw.get("therapeutic_sequence")
    if not isinstance(seq, dict):
        raise SequenceLoaderError(
            f"active archetype {archetype_key!r} missing therapeutic_sequence block"
        )
    touches_raw = seq.get("touches", [])
    if not isinstance(touches_raw, list) or not touches_raw:
        raise SequenceLoaderError(
            f"active archetype {archetype_key!r} has empty/invalid touches list"
        )
    touches = tuple(_build_touch_template(t) for t in touches_raw)
    # touch_count must equal len(touches); touches 1-indexed contiguous.
    declared_count = int(seq.get("touch_count", len(touches)))
    if declared_count != len(touches):
        raise SequenceLoaderError(
            f"active archetype {archetype_key!r}: touch_count={declared_count} "
            f"!= len(touches)={len(touches)}"
        )
    numbers = [t.touch_number for t in touches]
    if numbers != list(range(1, len(touches) + 1)):
        raise SequenceLoaderError(
            f"active archetype {archetype_key!r}: touch_numbers {numbers} "
            f"are not 1-indexed contiguous"
        )
    return SequenceTemplate(
        archetype_id=str(raw.get("archetype_id", archetype_key)),
        derivation_status=str(seq.get("derivation_status", "")),
        touch_count=len(touches),
        touches=touches,
        bilateral_findings=dict(raw.get("bilateral_findings", {}) or {}),
        becca_empirical_data=dict(raw.get("becca_empirical_data", {}) or {}),
        psychological_profile=dict(raw.get("psychological_profile", {}) or {}),
        population_pct=float(raw.get("population_pct", 0.0) or 0.0),
        conversion_rate_pct=float(raw.get("conversion_rate_pct", 0.0) or 0.0),
        budget_allocation_pct=int(raw.get("budget_allocation_pct", 0) or 0),
    )


def _build_suppress(archetype_key: str, raw: Dict[str, Any]) -> SuppressionRule:
    rule = raw.get("suppression_rule")
    if not isinstance(rule, dict):
        raise SequenceLoaderError(
            f"suppress archetype {archetype_key!r} missing suppression_rule block"
        )
    if raw.get("therapeutic_sequence") is not None:
        raise SequenceLoaderError(
            f"suppress archetype {archetype_key!r} must NOT carry a "
            f"therapeutic_sequence block"
        )
    return SuppressionRule(
        archetype_id=str(raw.get("archetype_id", archetype_key)),
        action=str(rule.get("action", "suppress_bid")),
        rationale=str(rule.get("rationale", "")),
        psychological_basis=str(rule.get("psychological_basis", "")),
        bilateral_findings=dict(raw.get("bilateral_findings", {}) or {}),
        becca_empirical_data=dict(raw.get("becca_empirical_data", {}) or {}),
        psychological_profile=dict(raw.get("psychological_profile", {}) or {}),
        population_pct=float(raw.get("population_pct", 0.0) or 0.0),
        conversion_rate_pct=float(raw.get("conversion_rate_pct", 0.0) or 0.0),
        budget_allocation_pct=int(raw.get("budget_allocation_pct", 0) or 0),
    )


def _build_crosswalk(
    archetypes_raw: Dict[str, Dict[str, Any]],
) -> Dict[ArchetypeID, Optional[str]]:
    """Build the Layer-1 → Layer-2 crosswalk from per-archetype maps_from.

    Every ArchetypeID value must appear in AT MOST ONE archetype's
    maps_from. Values not in any maps_from map to None (cold-start can't
    route there).
    """
    crosswalk: Dict[ArchetypeID, Optional[str]] = {a: None for a in ArchetypeID}
    seen: Dict[str, str] = {}  # layer1-value -> layer2-archetype-id (for overlap detection)
    for arch_key, raw in archetypes_raw.items():
        cw = raw.get("cold_start_archetype_crosswalk", {}) or {}
        maps_from = cw.get("maps_from", []) or []
        for layer1_str in maps_from:
            layer1_str_norm = str(layer1_str).strip().upper()
            try:
                layer1 = ArchetypeID[layer1_str_norm]
            except KeyError:
                raise SequenceLoaderError(
                    f"archetype {arch_key!r} maps_from references unknown "
                    f"Layer-1 archetype {layer1_str!r}; valid: "
                    f"{[a.name for a in ArchetypeID]}"
                )
            if layer1_str_norm in seen and seen[layer1_str_norm] != arch_key:
                raise SequenceLoaderError(
                    f"Layer-1 archetype {layer1_str_norm} mapped by BOTH "
                    f"{seen[layer1_str_norm]!r} and {arch_key!r}; each Layer-1 "
                    f"archetype must map to at most one Layer-2 archetype"
                )
            seen[layer1_str_norm] = arch_key
            crosswalk[layer1] = arch_key
    return crosswalk


def load_sequences(
    tenant_id: str,
    campaign_id: str,
    *,
    force_reload: bool = False,
    campaigns_root: Optional[pathlib.Path] = None,
) -> LoadedSequences:
    """Eager-load + validate + cache the sequences YAML for a tenant campaign.

    Path resolved from `{campaigns_root}/{tenant_id}/{campaign_id}/
    sequences.yaml` (campaigns_root defaults to the production
    CAMPAIGNS_ROOT; fixtures pass their own root).

    Validation pipeline:
      1. Path exists; YAML parses (yaml.safe_load).
      2. Top-level structure (exactly `metadata` + `archetypes` keys).
      3. metadata.tenant_id / metadata.campaign_id match the args
         (defends against a misplaced YAML file).
      4. Per-archetype schema (active → therapeutic_sequence;
         suppress → suppression_rule, no therapeutic_sequence).
      5. Crosswalk completeness over all 8 ArchetypeID values
         (each Layer-1 mapped at most once; values not mapped → None).
      6. touch_count == len(touches); touches 1-indexed contiguous.

    Raises SequenceLoaderError with specific context on any failure.
    """
    root = campaigns_root if campaigns_root is not None else CAMPAIGNS_ROOT
    cache_key = (tenant_id, campaign_id, str(root))
    if not force_reload and cache_key in _CACHE:
        return _CACHE[cache_key]

    yaml_path = _resolve_yaml_path(tenant_id, campaign_id, root)
    if not yaml_path.is_file():
        raise SequenceLoaderError(
            f"no sequences.yaml for tenant_id={tenant_id!r} "
            f"campaign_id={campaign_id!r} at {yaml_path}"
        )

    try:
        raw_text = yaml_path.read_text(encoding="utf-8")
        doc = yaml.safe_load(raw_text)
    except yaml.YAMLError as exc:
        raise SequenceLoaderError(f"{yaml_path}: YAML parse error: {exc}") from exc

    if not isinstance(doc, dict):
        raise SequenceLoaderError(f"{yaml_path}: top-level is not a mapping")
    extra_top = set(doc) - {"metadata", "archetypes"}
    if extra_top:
        raise SequenceLoaderError(
            f"{yaml_path}: unexpected top-level keys {sorted(extra_top)}; "
            f"expected exactly metadata + archetypes"
        )
    meta_raw = doc.get("metadata")
    archetypes_raw = doc.get("archetypes")
    if not isinstance(meta_raw, dict) or not isinstance(archetypes_raw, dict):
        raise SequenceLoaderError(
            f"{yaml_path}: metadata and archetypes must both be mappings"
        )

    # tenant/campaign id consistency check
    if str(meta_raw.get("tenant_id", "")) != tenant_id:
        raise SequenceLoaderError(
            f"{yaml_path}: metadata.tenant_id={meta_raw.get('tenant_id')!r} "
            f"!= requested {tenant_id!r}"
        )
    if str(meta_raw.get("campaign_id", "")) != campaign_id:
        raise SequenceLoaderError(
            f"{yaml_path}: metadata.campaign_id={meta_raw.get('campaign_id')!r} "
            f"!= requested {campaign_id!r}"
        )

    known_meta = {
        "tenant_id", "campaign_id", "tenant_display_name",
        "campaign_display_name", "schema_version", "source_doc", "layer",
        "archetype_count", "active_archetype_count", "suppress_archetype_count",
    }
    try:
        metadata = SequencesMetadata(
            tenant_id=str(meta_raw["tenant_id"]),
            campaign_id=str(meta_raw["campaign_id"]),
            tenant_display_name=str(meta_raw.get("tenant_display_name", "")),
            campaign_display_name=str(meta_raw.get("campaign_display_name", "")),
            schema_version=str(meta_raw.get("schema_version", "")),
            source_doc=str(meta_raw.get("source_doc", "")),
            layer=int(meta_raw.get("layer", 2)),
            archetype_count=int(meta_raw.get("archetype_count", len(archetypes_raw))),
            active_archetype_count=int(meta_raw.get("active_archetype_count", 0)),
            suppress_archetype_count=int(meta_raw.get("suppress_archetype_count", 0)),
            extra={k: v for k, v in meta_raw.items() if k not in known_meta},
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise SequenceLoaderError(f"{yaml_path}: malformed metadata ({exc})") from exc

    active: Dict[str, SequenceTemplate] = {}
    suppress: Dict[str, SuppressionRule] = {}
    for arch_key, arch_raw in archetypes_raw.items():
        if not isinstance(arch_raw, dict):
            raise SequenceLoaderError(
                f"{yaml_path}: archetype {arch_key!r} is not a mapping"
            )
        role = str(arch_raw.get("archetype_role", ""))
        if role == "active":
            active[arch_key] = _build_active(arch_key, arch_raw)
        elif role == "suppress":
            suppress[arch_key] = _build_suppress(arch_key, arch_raw)
        else:
            raise SequenceLoaderError(
                f"{yaml_path}: archetype {arch_key!r} has invalid "
                f"archetype_role={role!r}; expected 'active' or 'suppress'"
            )

    crosswalk = _build_crosswalk(archetypes_raw)

    loaded = LoadedSequences(
        tenant_id=tenant_id,
        campaign_id=campaign_id,
        metadata=metadata,
        active_archetypes=active,
        suppress_archetypes=suppress,
        crosswalk=crosswalk,
    )
    _CACHE[cache_key] = loaded
    return loaded


# =============================================================================
# Lookup helpers
# =============================================================================


def get_sequence_for_archetype(
    archetype_id: str, sequences: LoadedSequences,
) -> Union[SequenceTemplate, SuppressionRule]:
    """Look up a Layer-2 archetype by id.

    Returns a SequenceTemplate for active archetypes, a SuppressionRule
    for suppress archetypes. Raises KeyError if archetype_id is not in
    this tenant's archetype set.
    """
    if archetype_id in sequences.active_archetypes:
        return sequences.active_archetypes[archetype_id]
    if archetype_id in sequences.suppress_archetypes:
        return sequences.suppress_archetypes[archetype_id]
    raise KeyError(
        f"archetype_id {archetype_id!r} not in tenant "
        f"{sequences.tenant_id!r}/{sequences.campaign_id!r} archetype set "
        f"{sequences.archetype_ids()}"
    )


def resolve_cold_start_archetype(
    layer_1: ArchetypeID, sequences: LoadedSequences,
) -> Optional[str]:
    """Translate a Layer-1 ArchetypeID to this tenant's Layer-2 archetype_id.

    Returns None when the Layer-1 archetype has empty maps_from for this
    tenant (e.g., LUXY's skeptical_analyst / disillusioned at cold-start
    time). The cascade caller (S8.3) decides what to do with None —
    e.g., default-route to the highest-conversion active archetype, or
    run the bid through a no-sequence path.
    """
    return sequences.crosswalk.get(layer_1)


__all__ = [
    "CAMPAIGNS_ROOT",
    "TouchTemplate",
    "SequenceTemplate",
    "SuppressionRule",
    "SequencesMetadata",
    "LoadedSequences",
    "SequenceLoaderError",
    "load_sequences",
    "get_sequence_for_archetype",
    "resolve_cold_start_archetype",
    "clear_cache",
]
