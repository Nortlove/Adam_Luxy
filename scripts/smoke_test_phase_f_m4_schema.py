#!/usr/bin/env python3
"""Phase F smoke — M4 schema end-to-end verification on Neo4j.

Per Audit Item 2: 'M4 Aura migration + end-to-end smoke + A14 counter
scaffolding.'

Verifies:
  1. Neo4j connection (local 127.0.0.1:7687 in dev; Aura URI in prod)
  2. Migration 029 (M4 ts_propensity + pscore_known) is applied
  3. Indexes exist (ad_decision_user_created, ad_decision_pscore_known)
  4. Synthetic :DecisionContext write+read with M4 fields succeeds
  5. OPE-style filter query (WHERE pscore_known = true) works
  6. Cleanup: removes the synthetic decision row

Per the 2026-04-30 'use live data over simulation' directive: this
smoke runs against the actual configured Neo4j. In dev that's local;
in prod that's Aura. Same script, URI-driven.

Per the 'forward-anticipatory' directive: this smoke is the canonical
M4 schema verification that operator deployment runs BEFORE flipping
production traffic. Failures here mean OPE/CF/WCLS would silently
return zero rows (pscore_known never set true) or corrupt aggregates
(ts_propensity treated as 0.0 sentinel).

Exit codes:
  0  — all checks pass
  1  — Neo4j unreachable / connection failed
  2  — migration 029 not applied (run migration_runner first)
  3  — write/read failed
  4  — index missing

Usage:
    python3 scripts/smoke_test_phase_f_m4_schema.py
"""

from __future__ import annotations

import asyncio
import sys
import time
import uuid
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(_PROJECT_ROOT / ".env")


async def main() -> int:
    from neo4j import AsyncGraphDatabase
    from adam.config.settings import settings

    uri = settings.neo4j.uri
    username = settings.neo4j.username
    password = settings.neo4j.password
    print(f"=== Phase F M4 schema smoke ===")
    print(f"URI: {uri} (database: neo4j)\n")

    try:
        driver = AsyncGraphDatabase.driver(uri, auth=(username, password))
        await driver.verify_connectivity()
        print("✓ Neo4j connection established")
    except Exception as exc:
        print(f"✗ FATAL: Neo4j connection failed: {exc}")
        return 1

    try:
        async with driver.session(database="neo4j") as session:
            # 1. Migration 029 applied?
            res = await session.run(
                "MATCH (m:Migration {name: '029_add_ts_propensity_to_ad_decision'}) "
                "RETURN m.applied_at AS applied_at"
            )
            rec = await res.single()
            if rec is None:
                print("✗ Migration 029 NOT applied. Run migration_runner first:")
                print("    python3 -m adam.infrastructure.neo4j.migration_runner --database neo4j")
                return 2
            print(f"✓ Migration 029 applied at {rec['applied_at']}")

            # 2. Indexes exist?
            res = await session.run(
                "SHOW INDEXES YIELD name, labelsOrTypes, properties WHERE "
                "name IN ['ad_decision_user_created', 'ad_decision_pscore_known'] "
                "RETURN name, labelsOrTypes, properties"
            )
            idx_names = []
            async for r in res:
                idx_names.append(r["name"])
            for required in ("ad_decision_user_created", "ad_decision_pscore_known"):
                if required in idx_names:
                    print(f"✓ Index {required} exists")
                else:
                    print(f"✗ Index {required} MISSING")
                    return 4

            # 3. Synthetic :DecisionContext write with M4 schema fields
            decision_id = f"smoke_{uuid.uuid4().hex[:12]}"
            now = time.time()
            await session.run(
                """
                MERGE (dc:DecisionContext {decision_id: $decision_id})
                SET dc.archetype = 'professionals',
                    dc.mechanism_sent = 'social_proof',
                    dc.cascade_level = 3,
                    dc.buyer_id = 'smoke_buyer',
                    dc.segment_id = 'smoke_segment',
                    dc.created_at = $now,
                    dc.pscore_known = true,
                    dc.ts_propensity = 0.65,
                    dc.epsilon_floor = 0.02
                """,
                decision_id=decision_id, now=now,
            )
            print(f"✓ Synthetic :DecisionContext written (id={decision_id})")

            # 4. OPE-style read: WHERE pscore_known = true filter
            res = await session.run(
                """
                MATCH (dc:DecisionContext)
                WHERE dc.decision_id = $decision_id
                  AND dc.pscore_known = true
                RETURN dc.archetype AS archetype,
                       dc.mechanism_sent AS mechanism,
                       dc.ts_propensity AS p_t,
                       dc.epsilon_floor AS eps,
                       dc.pscore_known AS pscore_known
                """,
                decision_id=decision_id,
            )
            rec = await res.single()
            if rec is None:
                print("✗ Synthetic decision NOT readable via OPE filter")
                return 3
            print(
                f"✓ OPE read OK: archetype={rec['archetype']} "
                f"mechanism={rec['mechanism']} p_t={rec['p_t']:.4f} "
                f"eps={rec['eps']} pscore_known={rec['pscore_known']}"
            )

            # 5. Negative-case verification — pscore_known=false rows
            # MUST be filtered out by the OPE query
            decision_id_unknown = f"smoke_unknown_{uuid.uuid4().hex[:12]}"
            await session.run(
                """
                MERGE (dc:DecisionContext {decision_id: $decision_id})
                SET dc.archetype = 'professionals',
                    dc.mechanism_sent = 'authority',
                    dc.created_at = $now,
                    dc.pscore_known = false,
                    dc.ts_propensity = null,
                    dc.epsilon_floor = null
                """,
                decision_id=decision_id_unknown, now=now,
            )
            res = await session.run(
                """
                MATCH (dc:DecisionContext {decision_id: $decision_id})
                WHERE dc.pscore_known = true
                RETURN dc.decision_id AS id
                """,
                decision_id=decision_id_unknown,
            )
            rec = await res.single()
            if rec is not None:
                print(
                    f"✗ Discipline anchor BROKEN: pscore_known=false row "
                    f"matched OPE filter (this would corrupt OPE estimates)"
                )
                return 3
            print(
                "✓ pscore_known=false rows correctly EXCLUDED by OPE filter "
                "(Boruvka 2018 §2 discipline)"
            )

            # 6. Cleanup
            await session.run(
                """
                MATCH (dc:DecisionContext)
                WHERE dc.decision_id IN [$id1, $id2]
                DELETE dc
                """,
                id1=decision_id, id2=decision_id_unknown,
            )
            print(f"✓ Cleanup complete (synthetic rows removed)\n")

    finally:
        await driver.close()

    print("=" * 60)
    print("PHASE F M4 SMOKE PASSED — schema ready for OPE/WCLS reads")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
