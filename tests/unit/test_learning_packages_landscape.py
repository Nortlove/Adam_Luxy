"""Pin G1 — four-package learning landscape stays canonical.

Discipline anchor: do NOT add a fifth learning package. The four
existing packages serve distinct lifecycle roles per the audit
documented in adam/core/learning/__init__.py. Adding a fifth would
be the same drift pattern as the construct ontologies (G2 found 5
files competing for canonical with 32 consumer migrations needed).

This test asserts:
  - All four packages remain importable (canonical structure intact)
  - The canonical landscape doc lives on adam.core.learning
  - The role notice appears in each non-canonical package
  - No fifth learning-named directory has appeared at top level
"""

from __future__ import annotations

import pathlib

import pytest


_ADAM_ROOT = pathlib.Path(__file__).resolve().parents[2] / "adam"


# -----------------------------------------------------------------------------
# All four packages remain importable
# -----------------------------------------------------------------------------


def test_core_learning_canonical_importable():
    """adam.core.learning is the production runtime canonical."""
    import adam.core.learning  # noqa: F401


def test_top_level_learning_aggregator_importable():
    """adam.learning is the convenience aggregator."""
    import adam.learning  # noqa: F401


def test_cold_start_learning_importable():
    """adam.cold_start.learning is the cold-start gradient bridge."""
    import adam.cold_start.learning  # noqa: F401


def test_intelligence_learning_importable():
    """adam.intelligence.learning is the offline-script-only path."""
    import adam.intelligence.learning  # noqa: F401


# -----------------------------------------------------------------------------
# Canonical landscape doc lives on adam.core.learning
# -----------------------------------------------------------------------------


def test_core_learning_docstring_names_canonical():
    """The canonical four-package landscape doc lives in
    adam/core/learning/__init__.py. A future contributor reading
    that file should learn which package to add new code to."""
    import adam.core.learning
    doc = adam.core.learning.__doc__ or ""
    assert "production runtime canonical" in doc.lower()
    assert "adam.learning" in doc
    assert "adam.cold_start.learning" in doc
    assert "adam.intelligence.learning" in doc


def test_non_canonical_packages_reference_canonical():
    """Each non-canonical __init__ should point readers back to the
    canonical landscape doc. Drift prevention: a contributor opening
    any of the four files learns the structure."""
    import adam.learning
    import adam.cold_start.learning
    import adam.intelligence.learning

    for module, name in [
        (adam.learning, "adam.learning"),
        (adam.cold_start.learning, "adam.cold_start.learning"),
        (adam.intelligence.learning, "adam.intelligence.learning"),
    ]:
        doc = module.__doc__ or ""
        assert "adam.core.learning" in doc, (
            f"{name} __doc__ does not reference adam.core.learning "
            f"as canonical — landscape drift risk"
        )


# -----------------------------------------------------------------------------
# Trip-wire: no fifth learning-named directory under adam/
# -----------------------------------------------------------------------------


def test_no_fifth_learning_package_at_canonical_locations():
    """If a contributor adds a fifth learning-named package, this test
    fails with the path of the new directory. The fix: either move
    the new content into one of the four canonical packages or update
    the landscape doc + this trip-wire to acknowledge a new role.

    Discipline: no SILENT addition of a fifth package. The decision
    must be deliberate and visible in code review.
    """
    learning_dirs = [
        p for p in _ADAM_ROOT.rglob("learning")
        if p.is_dir() and "__pycache__" not in str(p)
    ]
    expected = {
        _ADAM_ROOT / "core" / "learning",
        _ADAM_ROOT / "learning",
        _ADAM_ROOT / "cold_start" / "learning",
        _ADAM_ROOT / "intelligence" / "learning",
    }
    actual = {p.resolve() for p in learning_dirs}
    expected_resolved = {p.resolve() for p in expected}

    unexpected = actual - expected_resolved
    assert unexpected == set(), (
        f"New learning-named directories detected: {unexpected}. "
        f"Either move content into one of the four canonical packages "
        f"or update adam/core/learning/__init__.py landscape doc + "
        f"this trip-wire."
    )

    missing = expected_resolved - actual
    assert missing == set(), (
        f"Canonical learning packages missing: {missing}. "
        f"The four-package landscape was disrupted."
    )
