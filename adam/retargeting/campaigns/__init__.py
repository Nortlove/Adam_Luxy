"""Multi-tenant retargeting campaigns namespace (S8.2).

Layout convention established by S8.2:

    adam/retargeting/campaigns/<tenant_id>/<campaign_id>/sequences.yaml

Each tenant onboards by dropping a `sequences.yaml` under their
namespace — zero code changes. The first tenant is LUXY Ride
(`luxy_ride/luxy_q2_2026/`). Per directive §0.5 #8: the multi-tenant
data architecture ships now; live cross-tenant priors wait for
Gate G8.

This package exposes thin discovery helpers (administrative, not in
the bid path). The typed loader lives in
`adam.retargeting.sequence_loader`.
"""

import pathlib
from typing import List

_CAMPAIGNS_ROOT = pathlib.Path(__file__).parent


def list_tenants() -> List[str]:
    """Return all tenant_ids that have a campaigns subdirectory.

    A tenant_id is any directory under `adam/retargeting/campaigns/`
    that is not a dunder/cache dir. Sorted for determinism.
    """
    out: List[str] = []
    for child in sorted(_CAMPAIGNS_ROOT.iterdir()):
        if not child.is_dir():
            continue
        if child.name.startswith("__") or child.name.startswith("."):
            continue
        out.append(child.name)
    return out


def list_campaigns(tenant_id: str) -> List[str]:
    """Return all campaign_ids for a tenant.

    Raises ValueError if the tenant_id directory does not exist.
    A campaign_id is any directory under the tenant's namespace
    that contains a `sequences.yaml`. Sorted for determinism.
    """
    tenant_dir = _CAMPAIGNS_ROOT / tenant_id
    if not tenant_dir.is_dir():
        raise ValueError(
            f"Unknown tenant_id {tenant_id!r}: no directory at "
            f"adam/retargeting/campaigns/{tenant_id}/"
        )
    out: List[str] = []
    for child in sorted(tenant_dir.iterdir()):
        if not child.is_dir():
            continue
        if (child / "sequences.yaml").is_file():
            out.append(child.name)
    return out


__all__ = ["list_tenants", "list_campaigns"]
