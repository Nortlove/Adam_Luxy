"""Tenant-scoped Layer-1 → Layer-2 archetype crosswalk resolver (S8.2).

The Layer-1 ArchetypeID enum (8 values; platform-generic; the
cold-start engine's output — `adam/cold_start/models/enums.py`) maps to
a tenant's Layer-2 archetypes (N values; tenant-specific; defined in
that tenant's `sequences.yaml`). The mapping is DATA, not code: each
tenant declares their own crosswalk inside their YAML via the
per-archetype `cold_start_archetype_crosswalk.maps_from` lists.

This module exports a thin resolver that reads the already-built
crosswalk off a `LoadedSequences` instance. The same code works for any
tenant because the mapping lives in the data — a second tenant onboards
by dropping a YAML file with their own maps_from lists; no code change.

(A previous draft of S8.2 considered a hardcoded `CROSSWALK` Python
constant — that was the architectural mistake. The crosswalk varies per
tenant, so it must be data not code.)
"""

from typing import Optional

from adam.cold_start.models.enums import ArchetypeID
from adam.retargeting.sequence_loader import LoadedSequences, SequenceLoaderError


def resolve_layer_1_to_layer_2(
    layer_1: ArchetypeID, sequences: LoadedSequences,
) -> Optional[str]:
    """Look up the Layer-2 archetype_id for a Layer-1 ArchetypeID.

    Returns None if the Layer-1 archetype has empty maps_from for this
    tenant (cold-start cannot distinguish — the cascade caller decides
    routing). Thin delegate over `LoadedSequences.crosswalk` so all
    tenant-specific logic stays in the data.
    """
    return sequences.crosswalk.get(layer_1)


def validate_crosswalk_coverage(sequences: LoadedSequences) -> None:
    """Confirm every Layer-1 ArchetypeID is mapped at most once.

    The loader's `_build_crosswalk` already enforces this at load time
    (raises on overlap), but this helper re-validates a LoadedSequences
    that may have been constructed by other means (e.g., in tests). It
    also confirms the crosswalk has exactly the 8 ArchetypeID keys.

    Raises SequenceLoaderError on:
      * a crosswalk key that isn't a valid ArchetypeID,
      * a missing ArchetypeID key,
      * a Layer-2 archetype_id value that isn't in the tenant's
        active+suppress archetype set,
      * (overlap is structurally impossible in a Dict, but a
        non-None value pointing at an unknown archetype is caught).
    """
    expected_keys = set(ArchetypeID)
    actual_keys = set(sequences.crosswalk)
    if actual_keys != expected_keys:
        missing = expected_keys - actual_keys
        extra = actual_keys - expected_keys
        raise SequenceLoaderError(
            f"crosswalk key mismatch for tenant {sequences.tenant_id!r}: "
            f"missing={sorted(a.name for a in missing)} "
            f"extra={sorted(str(k) for k in extra)}"
        )
    known_archetypes = set(sequences.archetype_ids())
    for layer1, layer2 in sequences.crosswalk.items():
        if layer2 is None:
            continue
        if layer2 not in known_archetypes:
            raise SequenceLoaderError(
                f"crosswalk for tenant {sequences.tenant_id!r}: Layer-1 "
                f"{layer1.name} maps to unknown Layer-2 archetype {layer2!r}; "
                f"known: {sorted(known_archetypes)}"
            )


__all__ = ["resolve_layer_1_to_layer_2", "validate_crosswalk_coverage"]
