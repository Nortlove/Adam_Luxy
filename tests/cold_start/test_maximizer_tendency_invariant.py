"""A.1 — invariant-pinning tests for maximizer/satisficer consolidation.

Per audit memo `docs/audits/MAXIMIZER_FRAGMENTATION_AUDIT.md` §8.4
+ §8.6 + §8.8: regression-prevent reintroduction of the fragmentation
forms A.1 just consolidated. If a future slice introduces
"decision_maximizer" or MAXIMIZING_TENDENCY again, these tests fail.

Tests 1 + 2 are subprocess-grep regression sentinels.

Tests 3–7 are static-analysis tests on the migration `031` cypher
file: file presence, SET-clause contents, MATCH...SET pattern (which
gives idempotency-by-construction), and verification that migration
005's original properties are NOT overridden by 031.

Tests are static-only — no live Neo4j connection required. Per audit
finding (§3 Pass 2): `dim_cog_decision_style` has 0 READ_BY sites in
the codebase, so live-database execution would only test the
migration runner itself, which is out of A.1 scope.
"""
from pathlib import Path
import re
import subprocess

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
MIGRATION_031_PATH = (
    REPO_ROOT / "adam" / "infrastructure" / "neo4j" / "migrations"
    / "031_update_decision_style_dim.cypher"
)


# ----------------------------------------------------------------------------
# Test 1 — no "decision_maximizer" string literal in adam/ scope
# ----------------------------------------------------------------------------

def test_no_decision_maximizer_string_literal_in_adam():
    """Pin: zero `"decision_maximizer"` string literals in adam/.
    Reintroduction = consolidation regression. Scoped to .py source
    to skip __pycache__ .pyc binaries."""
    result = subprocess.run(
        ["grep", "-rn", "--include=*.py", '"decision_maximizer"', "adam/"],
        capture_output=True, text=True, cwd=REPO_ROOT,
    )
    # grep returns 0 if matches found, 1 if no matches.
    assert result.returncode != 0, (
        "Found 'decision_maximizer' string literal in adam/ — A.1 "
        f"consolidation regression. Hits:\n{result.stdout}"
    )


# ----------------------------------------------------------------------------
# Test 2 — no MAXIMIZING_TENDENCY identifier in adam/ scope
# ----------------------------------------------------------------------------

def test_no_maximizing_tendency_identifier_in_adam():
    """Pin: zero `MAXIMIZING_TENDENCY` identifiers in adam/. Per
    Q10.G adjudication: rename was UNCONDITIONAL; the old name must
    not reappear. Scoped to .py source to skip __pycache__ .pyc
    binaries (which retain the old name until next compile)."""
    result = subprocess.run(
        ["grep", "-rn", "--include=*.py", "MAXIMIZING_TENDENCY", "adam/"],
        capture_output=True, text=True, cwd=REPO_ROOT,
    )
    assert result.returncode != 0, (
        "Found MAXIMIZING_TENDENCY identifier in adam/ — A.1 "
        f"consolidation regression. Hits:\n{result.stdout}"
    )


# ----------------------------------------------------------------------------
# Test 3 — migration 031 file exists
# ----------------------------------------------------------------------------

def test_migration_031_file_exists():
    """Pin migration 031 path."""
    assert MIGRATION_031_PATH.exists(), (
        f"Expected migration at {MIGRATION_031_PATH}; not found."
    )
    assert MIGRATION_031_PATH.stat().st_size > 0, (
        f"Migration {MIGRATION_031_PATH} exists but is empty."
    )


# ----------------------------------------------------------------------------
# Test 4 — migration 031 SET clause contains expected new property
#          names + values
# ----------------------------------------------------------------------------

def test_migration_031_sets_expected_new_properties():
    """Pin the new properties added by migration 031: name (renamed
    to canonical), academic_grounding (Schwartz citation),
    scale_min/max, scale_anchor_low/high, added_in, updated_at."""
    text = MIGRATION_031_PATH.read_text()

    # Canonical name set.
    assert "d.name = 'maximizer_tendency'" in text, (
        "migration 031 must SET d.name = 'maximizer_tendency'"
    )

    # Schwartz academic grounding present.
    assert "d.academic_grounding =" in text, (
        "migration 031 must SET d.academic_grounding"
    )
    assert "Schwartz" in text and "2002" in text, (
        "academic_grounding must contain Schwartz et al. 2002 citation"
    )

    # Scale bounds + anchors.
    assert "d.scale_min = 0.0" in text
    assert "d.scale_max = 1.0" in text
    assert "d.scale_anchor_low = 'satisficer" in text
    assert "d.scale_anchor_high = 'maximizer" in text

    # Provenance.
    assert "d.added_in = 'A.1'" in text
    assert "d.updated_at = datetime()" in text


# ----------------------------------------------------------------------------
# Test 5 — migration 031 uses MATCH...SET pattern (idempotency-by-
#          construction)
# ----------------------------------------------------------------------------

def test_migration_031_uses_match_set_pattern():
    """Idempotency: re-running this migration MATCHes the same node
    by unique dimension_id and SET overwrites with identical values.
    The MATCH...SET pattern (vs MERGE...ON CREATE/ON MATCH) is the
    correct choice for property-update migrations on an
    already-seeded node."""
    text = MIGRATION_031_PATH.read_text()

    assert re.search(
        r"MATCH\s+\(d:PersonalityDimension\s*\{\s*dimension_id:\s*'dim_cog_decision_style'\s*\}\)",
        text,
    ), (
        "migration 031 must MATCH the existing "
        "dim_cog_decision_style node (not MERGE — which would create "
        "a duplicate if migration 005 was misseeded)"
    )
    assert "SET d." in text, "migration 031 must SET properties"


# ----------------------------------------------------------------------------
# Test 6 — migration 031 does NOT override migration 005's original
#          12 properties (only sets new properties + the renamed name)
# ----------------------------------------------------------------------------

@pytest.mark.parametrize("preserved_property", [
    "full_name",
    "domain",
    "dimension_type",
    "description",
    "low_description",
    "high_description",
    "measurement_method",
    "ad_relevance",
    "population_mean",
    "population_std",
    "created_at",
])
def test_migration_031_does_not_override_migration_005_properties(
    preserved_property,
):
    """Per audit §8.4: migration 031 must NOT touch any of migration
    005's original 12 properties (other than the renamed `name`).
    This pin prevents accidental property-overlap that would silently
    rewrite migration-005 values."""
    text = MIGRATION_031_PATH.read_text()
    forbidden_pattern = f"d.{preserved_property}"
    assert forbidden_pattern not in text, (
        f"migration 031 must NOT SET d.{preserved_property} — "
        f"that property is owned by migration 005 and should remain "
        f"untouched per A.1 scope (Q10.B + audit §8.4)"
    )


# ----------------------------------------------------------------------------
# Test 7 — cold_start enum has the renamed identifier with renamed
#          value (full unconditional rename per Q10.G + Pass A
#          IN_MEMORY result)
# ----------------------------------------------------------------------------

def test_cold_start_enum_has_renamed_maximizer_tendency():
    """Per Pass A pre-flight: only 1 hit for the old string value
    ('maximizing_tendency'), at the declaration itself — no
    persistence sites. Q10.G unconditional rename: identifier AND
    value both become MAXIMIZER_TENDENCY = 'maximizer_tendency'."""
    from adam.cold_start.models.enums import ExtendedConstruct

    # New identifier present.
    assert hasattr(ExtendedConstruct, "MAXIMIZER_TENDENCY"), (
        "ExtendedConstruct must expose MAXIMIZER_TENDENCY identifier"
    )
    # Value is the renamed string.
    assert ExtendedConstruct.MAXIMIZER_TENDENCY.value == "maximizer_tendency", (
        "ExtendedConstruct.MAXIMIZER_TENDENCY.value must be "
        "'maximizer_tendency' (unconditional rename per Q10.G)"
    )
    # Old identifier gone.
    assert not hasattr(ExtendedConstruct, "MAXIMIZING_TENDENCY"), (
        "ExtendedConstruct.MAXIMIZING_TENDENCY must be absent — "
        "renamed to MAXIMIZER_TENDENCY in A.1"
    )
