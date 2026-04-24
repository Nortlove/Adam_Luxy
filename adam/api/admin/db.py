"""
PostgreSQL Database Connection
================================

Async connection pool using asyncpg for the management platform.
Falls back to synchronous psycopg2 if asyncpg is not available.
SQLite fallback for development/testing without PostgreSQL.
"""

from __future__ import annotations

import logging
import os
import sqlite3
import json
import uuid
from contextlib import asynccontextmanager, contextmanager
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

DATABASE_URL = os.environ.get(
    "MANAGEMENT_DATABASE_URL",
    os.environ.get("DATABASE_URL", ""),
)

SQLITE_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "data", "management.db",
)

_pool = None
_use_sqlite = False


async def get_pool():
    """Get or create the async connection pool."""
    global _pool, _use_sqlite

    if _pool is not None:
        return _pool

    if DATABASE_URL and DATABASE_URL.startswith("postgres"):
        try:
            import asyncpg
            _pool = await asyncpg.create_pool(
                DATABASE_URL,
                min_size=2,
                max_size=10,
                command_timeout=30,
            )
            logger.info("PostgreSQL pool created: %s", DATABASE_URL.split("@")[-1] if "@" in DATABASE_URL else "local")
            return _pool
        except Exception as e:
            logger.warning("PostgreSQL connection failed, falling back to SQLite: %s", e)

    _use_sqlite = True
    _init_sqlite()
    logger.info("Using SQLite at %s", SQLITE_PATH)
    return None


def _init_sqlite():
    """Initialize SQLite database with schema."""
    os.makedirs(os.path.dirname(SQLITE_PATH), exist_ok=True)
    conn = sqlite3.connect(SQLITE_PATH)
    conn.row_factory = sqlite3.Row

    # Create tables (simplified from PostgreSQL schema)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS organizations (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            slug TEXT NOT NULL UNIQUE,
            domain TEXT,
            industry TEXT,
            tier TEXT DEFAULT 'standard',
            status TEXT DEFAULT 'active',
            settings_json TEXT DEFAULT '{}',
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            organization_id TEXT REFERENCES organizations(id),
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL,
            role TEXT NOT NULL,
            is_active INTEGER DEFAULT 1,
            last_login_at TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS refresh_tokens (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL REFERENCES users(id),
            token_hash TEXT NOT NULL UNIQUE,
            expires_at TEXT NOT NULL,
            revoked INTEGER DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS campaigns (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL REFERENCES organizations(id),
            name TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'draft',
            brand_name TEXT NOT NULL,
            brand_asin TEXT,
            brand_website TEXT,
            brand_category TEXT,
            brand_logo_url TEXT,
            total_budget REAL,
            daily_budget REAL,
            currency TEXT DEFAULT 'USD',
            start_date TEXT,
            end_date TEXT,
            timezone TEXT DEFAULT 'America/New_York',
            geo_targets TEXT DEFAULT '[]',
            frequency_cap TEXT DEFAULT '{}',
            dayparting TEXT DEFAULT '{}',
            dsp_platform TEXT DEFAULT 'stackadapt',
            dsp_advertiser_id TEXT,
            dsp_api_key_encrypted TEXT,
            dcil_enabled INTEGER DEFAULT 1,
            dcil_auto_execute INTEGER DEFAULT 0,
            dcil_safety_rails TEXT DEFAULT '{}',
            tier_a_frequency TEXT DEFAULT 'adaptive',
            conversion_pixel_id TEXT,
            conversion_type TEXT DEFAULT 'purchase',
            conversion_value REAL,
            attribution_window_days INTEGER DEFAULT 30,
            notes TEXT,
            created_by TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS campaign_archetypes (
            id TEXT PRIMARY KEY,
            campaign_id TEXT NOT NULL REFERENCES campaigns(id),
            archetype_name TEXT NOT NULL,
            is_custom INTEGER DEFAULT 0,
            budget_weight REAL DEFAULT 0.0,
            primary_mechanism TEXT,
            secondary_mechanism TEXT,
            framing TEXT DEFAULT 'gain',
            notes TEXT,
            dsp_campaign_id TEXT,
            dsp_campaign_status TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(campaign_id, archetype_name)
        );

        CREATE TABLE IF NOT EXISTS creative_variants (
            id TEXT PRIMARY KEY,
            campaign_archetype_id TEXT NOT NULL REFERENCES campaign_archetypes(id),
            variant_label TEXT NOT NULL,
            mechanism TEXT NOT NULL,
            headline TEXT NOT NULL,
            body_copy TEXT,
            cta_text TEXT,
            image_url TEXT,
            landing_url TEXT,
            tone TEXT,
            construal_level TEXT,
            status TEXT DEFAULT 'draft',
            dsp_creative_id TEXT,
            impressions INTEGER DEFAULT 0,
            clicks INTEGER DEFAULT 0,
            conversions INTEGER DEFAULT 0,
            spend REAL DEFAULT 0,
            ctr REAL DEFAULT 0,
            cvr REAL DEFAULT 0,
            cpa REAL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS domain_lists (
            id TEXT PRIMARY KEY,
            campaign_archetype_id TEXT REFERENCES campaign_archetypes(id),
            campaign_id TEXT REFERENCES campaigns(id),
            list_type TEXT NOT NULL,
            domain TEXT NOT NULL,
            audience TEXT,
            tier INTEGER DEFAULT 2,
            source TEXT DEFAULT 'manual',
            added_by TEXT,
            added_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS dcil_directives (
            id TEXT PRIMARY KEY,
            campaign_id TEXT NOT NULL REFERENCES campaigns(id),
            directive_type TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'proposed',
            campaign_archetype_id TEXT,
            parameter TEXT,
            current_value TEXT,
            proposed_value TEXT,
            source_finding_id TEXT,
            rationale TEXT,
            bilateral_evidence TEXT,
            scope TEXT,
            i_squared REAL,
            confidence REAL,
            expected_impact TEXT,
            expected_lift_pct REAL,
            rollback_conditions TEXT DEFAULT '[]',
            max_change_pct REAL,
            cooldown_hours INTEGER DEFAULT 48,
            reviewed_by TEXT,
            reviewed_at TEXT,
            review_notes TEXT,
            executed_at TEXT,
            pre_change_snapshot TEXT,
            execution_result TEXT,
            rolled_back_at TEXT,
            rollback_reason TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS conversion_trackers (
            id TEXT PRIMARY KEY,
            campaign_id TEXT NOT NULL REFERENCES campaigns(id),
            tracker_type TEXT NOT NULL,
            pixel_id TEXT,
            pixel_snippet TEXT,
            postback_url TEXT,
            webhook_secret TEXT,
            is_verified INTEGER DEFAULT 0,
            verified_at TEXT,
            events_received INTEGER DEFAULT 0,
            last_event_at TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS reports (
            id TEXT PRIMARY KEY,
            campaign_id TEXT NOT NULL REFERENCES campaigns(id),
            organization_id TEXT NOT NULL REFERENCES organizations(id),
            tier TEXT NOT NULL,
            period_start TEXT NOT NULL,
            period_end TEXT NOT NULL,
            report_data TEXT NOT NULL,
            generated_at TEXT NOT NULL DEFAULT (datetime('now')),
            generated_by TEXT DEFAULT 'dcil',
            viewed_by_client INTEGER DEFAULT 0,
            viewed_at TEXT
        );

        CREATE TABLE IF NOT EXISTS campaign_performance_snapshots (
            id TEXT PRIMARY KEY,
            campaign_id TEXT NOT NULL REFERENCES campaigns(id),
            snapshot_date TEXT NOT NULL,
            impressions INTEGER DEFAULT 0,
            clicks INTEGER DEFAULT 0,
            conversions INTEGER DEFAULT 0,
            spend REAL DEFAULT 0,
            revenue REAL DEFAULT 0,
            ctr REAL DEFAULT 0,
            cvr REAL DEFAULT 0,
            cpa REAL DEFAULT 0,
            roas REAL DEFAULT 0,
            archetype_breakdown TEXT DEFAULT '{}',
            domain_breakdown TEXT DEFAULT '{}',
            dcil_directives_active INTEGER DEFAULT 0,
            dcil_last_run_at TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(campaign_id, snapshot_date)
        );

        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            organization_id TEXT,
            user_id TEXT,
            action TEXT NOT NULL,
            entity_type TEXT,
            entity_id TEXT,
            changes TEXT,
            ip_address TEXT,
            user_agent TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
    """)
    conn.commit()
    conn.close()


class Database:
    """Unified database interface supporting both PostgreSQL and SQLite."""

    async def fetch_all(self, query: str, *args) -> List[Dict[str, Any]]:
        if _use_sqlite:
            return self._sqlite_fetch_all(query, args)
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(query, *args)
            return [dict(r) for r in rows]

    async def fetch_one(self, query: str, *args) -> Optional[Dict[str, Any]]:
        if _use_sqlite:
            return self._sqlite_fetch_one(query, args)
        pool = await get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(query, *args)
            return dict(row) if row else None

    async def execute(self, query: str, *args) -> str:
        if _use_sqlite:
            return self._sqlite_execute(query, args)
        pool = await get_pool()
        async with pool.acquire() as conn:
            return await conn.execute(query, *args)

    async def execute_returning(self, query: str, *args) -> Optional[Dict[str, Any]]:
        if _use_sqlite:
            return self._sqlite_execute_returning(query, args)
        pool = await get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(query, *args)
            return dict(row) if row else None

    def _sqlite_query_adapt(self, query: str, args: tuple) -> Tuple[str, tuple]:
        """Adapt PostgreSQL-style queries for SQLite."""
        # Replace $1, $2, etc. with ?
        adapted = query
        for i in range(len(args), 0, -1):
            adapted = adapted.replace(f"${i}", "?")
        # Remove RETURNING clause for non-returning operations
        adapted = adapted.replace("gen_random_uuid()", f"'{uuid.uuid4()}'")
        adapted = adapted.replace("now()", "datetime('now')")
        return adapted, args

    def _sqlite_fetch_all(self, query: str, args: tuple) -> List[Dict[str, Any]]:
        query, args = self._sqlite_query_adapt(query, args)
        conn = sqlite3.connect(SQLITE_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(query, args)
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows

    def _sqlite_fetch_one(self, query: str, args: tuple) -> Optional[Dict[str, Any]]:
        query, args = self._sqlite_query_adapt(query, args)
        conn = sqlite3.connect(SQLITE_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(query, args)
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def _sqlite_execute(self, query: str, args: tuple) -> str:
        query, args = self._sqlite_query_adapt(query, args)
        conn = sqlite3.connect(SQLITE_PATH)
        conn.execute(query, args)
        conn.commit()
        conn.close()
        return "OK"

    def _sqlite_execute_returning(self, query: str, args: tuple) -> Optional[Dict[str, Any]]:
        query_adapted, args = self._sqlite_query_adapt(query, args)
        # Extract RETURNING columns
        if "RETURNING" in query_adapted.upper():
            parts = query_adapted.upper().split("RETURNING")
            query_no_return = query_adapted[:query_adapted.upper().index("RETURNING")].strip()
            conn = sqlite3.connect(SQLITE_PATH)
            conn.row_factory = sqlite3.Row
            conn.execute(query_no_return, args)
            conn.commit()
            # Fetch the inserted/updated row
            # For INSERT, get last rowid
            cursor = conn.execute("SELECT * FROM " + self._extract_table(query_adapted) + " ORDER BY rowid DESC LIMIT 1")
            row = cursor.fetchone()
            conn.close()
            return dict(row) if row else None
        return self._sqlite_fetch_one(query_adapted, args)

    def _extract_table(self, query: str) -> str:
        """Extract table name from INSERT/UPDATE query."""
        upper = query.upper()
        if "INSERT INTO" in upper:
            start = upper.index("INSERT INTO") + len("INSERT INTO")
            rest = query[start:].strip()
            return rest.split()[0].strip("(")
        if "UPDATE" in upper:
            start = upper.index("UPDATE") + len("UPDATE")
            rest = query[start:].strip()
            return rest.split()[0]
        return ""


_db: Optional[Database] = None


def get_db() -> Database:
    global _db
    if _db is None:
        _db = Database()
    return _db
