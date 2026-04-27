"""Pin the Neo4j migration runner — dry-run default, idempotent statements,
soft-fail on driver unavailable, error surfacing.

Discipline anchors:
    - Dry-run is the DEFAULT. Any caller that wants to actually execute
      against Neo4j must pass dry_run=False explicitly. CLI defaults
      mirror this: --execute is required.
    - The runner stops on first failure rather than continuing through
      partial migration state. A migration that's half-applied is worse
      than one that's not applied at all — the operator can re-run a
      not-applied migration; a half-applied one needs forensics.
    - Statement parser drops comments and whitespace-only fragments so
      the .cypher file's docstring doesn't get sent to Neo4j.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from infra.migrations.runner import (
    load_migration,
    parse_statements,
    run_migration,
)


# -----------------------------------------------------------------------------
# Statement parser
# -----------------------------------------------------------------------------


def test_parse_statements_splits_on_semicolons():
    text = "MATCH (n:A) RETURN n;\nMATCH (m:B) RETURN m;"
    stmts = parse_statements(text)
    assert len(stmts) == 2
    assert stmts[0].startswith("MATCH (n:A)")
    assert stmts[1].startswith("MATCH (m:B)")


def test_parse_statements_strips_line_comments():
    text = """
    // This is a comment
    MATCH (n) RETURN n;
    // Another comment
    CREATE INDEX foo IF NOT EXISTS FOR (n:X) ON (n.y);
    """
    stmts = parse_statements(text)
    assert len(stmts) == 2
    assert "comment" not in stmts[0]
    assert "comment" not in stmts[1]


def test_parse_statements_drops_empty_fragments():
    text = ";;;\n  \n  ;\nMATCH (n) RETURN n;\n;;\n"
    stmts = parse_statements(text)
    assert len(stmts) == 1
    assert "MATCH" in stmts[0]


def test_parse_statements_handles_trailing_no_semicolon():
    text = "MATCH (n) RETURN n;\nMATCH (m) RETURN m"
    stmts = parse_statements(text)
    assert len(stmts) == 2


# -----------------------------------------------------------------------------
# Load migration
# -----------------------------------------------------------------------------


def test_load_migration_real_file_parses(tmp_path):
    p = tmp_path / "test.cypher"
    p.write_text("// comment\nMATCH (n) RETURN n;\nCREATE INDEX foo IF NOT EXISTS FOR (n:X) ON (n.y);")
    stmts = load_migration(p)
    assert len(stmts) == 2


def test_load_migration_raises_on_missing():
    with pytest.raises(FileNotFoundError):
        load_migration(Path("/nonexistent/foo.cypher"))


def test_load_real_m4_migration():
    """The actual M4 migration must parse without errors. Pinning this
    catches future cypher syntax drift in the file."""
    real_path = (
        Path(__file__).resolve().parent.parent.parent
        / "infra" / "migrations"
        / "2026_04_27_add_ts_propensity_to_ad_decision.cypher"
    )
    assert real_path.exists(), f"M4 migration file not found at {real_path}"
    stmts = load_migration(real_path)
    # Migration has 4 logical statements: pscore_known SET, two CREATE
    # INDEX, and one verification RETURN
    assert len(stmts) == 4


# -----------------------------------------------------------------------------
# Dry-run path
# -----------------------------------------------------------------------------


def test_dry_run_default_does_not_touch_driver(tmp_path):
    """The default path must NOT execute. Driver is never called.
    A dry-run that accidentally executes against the production graph
    is a category of bug serious enough to test for."""
    p = tmp_path / "m.cypher"
    p.write_text("MATCH (n) RETURN n;")
    driver = MagicMock()
    driver.session.side_effect = AssertionError("dry-run must not open session")

    summary = run_migration(p, dry_run=True, driver=driver)

    assert summary["dry_run"] is True
    assert summary["executed"] == 0
    assert summary["statements"] == 1


def test_dry_run_reports_statement_count(tmp_path):
    p = tmp_path / "m.cypher"
    p.write_text("MATCH (a) RETURN a;\nMATCH (b) RETURN b;\nMATCH (c) RETURN c;")
    summary = run_migration(p, dry_run=True)
    assert summary["statements"] == 3
    assert summary["executed"] == 0


def test_dry_run_handles_missing_file(tmp_path):
    summary = run_migration(tmp_path / "missing.cypher", dry_run=True)
    assert summary["statements"] == 0
    assert len(summary["errors"]) == 1
    assert "not found" in summary["errors"][0].lower()


# -----------------------------------------------------------------------------
# Execute path — driver unavailable
# -----------------------------------------------------------------------------


def test_execute_with_no_driver_returns_error(tmp_path):
    """When driver=None and no built-in driver available, must surface
    an error rather than silently no-op."""
    p = tmp_path / "m.cypher"
    p.write_text("MATCH (n) RETURN n;")
    summary = run_migration(p, dry_run=False, driver=None)
    # Either the dependencies module isn't importable (sandbox) or the
    # driver returns None — either way, errors should be non-empty.
    assert len(summary["errors"]) >= 1


# -----------------------------------------------------------------------------
# Execute path — happy path with mock driver
# -----------------------------------------------------------------------------


def _build_mock_driver(records_per_statement):
    """Build a mock Neo4j driver whose session.run returns the given
    records (one per statement, in order)."""
    driver = MagicMock()
    session = MagicMock()
    driver.session.return_value.__enter__ = MagicMock(return_value=session)
    driver.session.return_value.__exit__ = MagicMock(return_value=None)

    def session_run(query, **kwargs):
        record = records_per_statement.pop(0) if records_per_statement else None
        result = MagicMock()
        result.single = MagicMock(return_value=record)
        return result

    session.run = MagicMock(side_effect=session_run)
    return driver


def test_execute_runs_each_statement(tmp_path):
    p = tmp_path / "m.cypher"
    p.write_text("MATCH (a) RETURN a;\nMATCH (b) RETURN b;")
    driver = _build_mock_driver([{"a": 1}, {"b": 2}])

    summary = run_migration(p, dry_run=False, driver=driver)

    assert summary["executed"] == 2
    assert summary["errors"] == []
    assert summary["verification"] == {"b": 2}


def test_execute_stops_on_first_error(tmp_path):
    """A half-applied migration is worse than not applied. Stop on
    first failure so the operator can investigate."""
    p = tmp_path / "m.cypher"
    p.write_text("MATCH (a) RETURN a;\nBROKEN_QUERY;\nMATCH (c) RETURN c;")
    driver = MagicMock()
    session = MagicMock()
    driver.session.return_value.__enter__ = MagicMock(return_value=session)
    driver.session.return_value.__exit__ = MagicMock(return_value=None)

    call_count = {"n": 0}

    def session_run(query, **kwargs):
        call_count["n"] += 1
        if "BROKEN" in query:
            raise RuntimeError("syntax error")
        result = MagicMock()
        result.single = MagicMock(return_value={"ok": 1})
        return result

    session.run = MagicMock(side_effect=session_run)

    summary = run_migration(p, dry_run=False, driver=driver)

    # First statement ran, second failed, third was never attempted
    assert summary["executed"] == 1
    assert len(summary["errors"]) == 1
    assert call_count["n"] == 2  # Only first two attempted


def test_execute_with_session_level_failure(tmp_path):
    """Driver constructs but session opening fails — surface error
    cleanly rather than crashing."""
    p = tmp_path / "m.cypher"
    p.write_text("MATCH (n) RETURN n;")
    driver = MagicMock()
    driver.session.side_effect = ConnectionError("auth failed")

    summary = run_migration(p, dry_run=False, driver=driver)
    assert summary["executed"] == 0
    assert len(summary["errors"]) >= 1
    assert "auth failed" in str(summary["errors"]).lower() or "session-level" in str(summary["errors"]).lower()


# -----------------------------------------------------------------------------
# Real M4 migration end-to-end (dry-run only — never touches Aura)
# -----------------------------------------------------------------------------


def test_real_m4_migration_dry_run_completes_cleanly():
    """The actual M4 migration must dry-run without errors. This is the
    pre-execute check the operator runs before --execute."""
    real_path = (
        Path(__file__).resolve().parent.parent.parent
        / "infra" / "migrations"
        / "2026_04_27_add_ts_propensity_to_ad_decision.cypher"
    )
    summary = run_migration(real_path, dry_run=True)
    assert summary["dry_run"] is True
    assert summary["statements"] == 4
    assert summary["errors"] == []
