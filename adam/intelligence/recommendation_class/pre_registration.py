"""Pre-registration of ProjectedImpact claims via git-committed files.

A ProjectedImpact's `content_hash` is the content-addressed receipt — stable
SHA-256 over canonical JSON of the substantive claim. To establish that a
claim existed BEFORE the adjudication horizon opened, the pilot plan commits
ProjectedImpact files to this repository at authoring time. The git commit
hash that introduces the file is the time-ordered receipt; the content_hash
is the content-addressed receipt. Both together establish "claim X was
committed at time T" in a way downstream adjudicators can verify.

This module provides the canonical file convention and helpers for writing
and reading pre-registration files. The git-commit action itself is not
invoked here — the caller runs `git add` and `git commit` explicitly as
part of their ship flow. This preserves the git history as the authoritative
pre-registration log while keeping this module free of subprocess calls.

File convention:
    pre_registrations/{advertiser_id}/{claim_id}_{content_hash_prefix}.json

Example:
    pre_registrations/luxy_ride/status_seeker_regfit_autopilot_low_short_abc123de456f.json

The content_hash prefix (12 hex chars) in the filename ensures distinct
claims with the same claim_id don't collide, and makes the filesystem
content-addressed for git-blame navigation.
"""

from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path
from typing import Optional

from adam.intelligence.recommendation_class.projected_impact import ProjectedImpact

logger = logging.getLogger(__name__)

_PRE_REG_ROOT_DIR = "pre_registrations"
_CONTENT_HASH_FILENAME_PREFIX_LEN = 12


def pre_registration_root(repo_root: Path) -> Path:
    """Return the pre-registrations root directory path under repo_root."""
    return repo_root / _PRE_REG_ROOT_DIR


def pre_registration_path(claim: ProjectedImpact, repo_root: Path) -> Path:
    """Return the canonical file path for a pre-registered claim.

    Format: {repo_root}/pre_registrations/{advertiser_id}/{claim_id}_{hash_prefix}.json

    The advertiser_id comes from the claim's AudienceScope; the content_hash
    prefix comes from claim.content_hash (or is computed if not set).
    """
    content_hash = claim.content_hash or claim.compute_content_hash()
    advertiser_id = claim.audience_scope.advertiser_id
    hash_prefix = content_hash[:_CONTENT_HASH_FILENAME_PREFIX_LEN]
    filename = f"{claim.claim_id}_{hash_prefix}.json"
    return pre_registration_root(repo_root) / advertiser_id / filename


def write_pre_registration(claim: ProjectedImpact, repo_root: Path) -> Path:
    """Write a ProjectedImpact to its canonical pre-registration file.

    Creates parent directories as needed. Content is canonical JSON — the
    same serialization used for the content_hash, so the file is directly
    verifiable by re-hashing. Raises FileExistsError if the file already
    exists (pre-registration is append-only; re-writing is intentional drift).

    Returns the path written.
    """
    claim.validate()
    path = pre_registration_path(claim, repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.exists():
        raise FileExistsError(
            f"Pre-registration file already exists at {path}. "
            f"Pre-registration is append-only; new claims require distinct "
            f"claim_id or substantive content."
        )

    payload = claim.to_dict()
    canonical = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    )
    path.write_text(canonical, encoding="utf-8")
    return path


def read_pre_registration(path: Path) -> ProjectedImpact:
    """Read a pre-registered claim from its file.

    Verifies content integrity: the stored content_hash must match the
    hash of the substantive content after reconstruction. Raises ValueError
    on hash mismatch.
    """
    data = json.loads(path.read_text(encoding="utf-8"))
    claim = ProjectedImpact.from_dict(data)
    claim.validate()

    stored_hash = claim.content_hash
    recomputed = claim.compute_content_hash()
    if stored_hash and stored_hash != recomputed:
        raise ValueError(
            f"Content hash mismatch for {path}: stored={stored_hash}, "
            f"recomputed={recomputed}. File has been modified since "
            f"pre-registration."
        )

    return claim


def current_git_head(repo_root: Path) -> Optional[str]:
    """Return the current git HEAD commit hash for repo_root, or None if
    git is unavailable / not a git repository.

    Used to tag post-adjudication records with the pre-registration commit
    context. Pure bookkeeping — the authoritative pre-registration receipt
    is the git log itself (run `git log <pre_registration_path>` to see
    when a claim was committed).
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if result.returncode != 0:
            return None
        commit = result.stdout.strip()
        return commit if commit else None
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as exc:
        logger.debug("current_git_head: git not available or failed: %s", exc)
        return None
