"""W.2a — cold_start_archetype_mapper tests.

Pin: 4-signal voting heuristic correctness; deterministic tie-break;
PRAGMATIST default fallback; bid-time latency; full archetype
coverage given right signals.
"""
import random
import time

import pytest

from adam.cold_start.models.enums import ArchetypeID
from adam.intelligence.cold_start_archetype_mapper import (
    COLD_START_DEFAULT_ARCHETYPE,
    DEVICE_ARCHETYPE_HINTS,
    HOUR_BUCKET_ARCHETYPE_HINTS,
    IAB_CATEGORY_ARCHETYPE_HINTS,
    RURAL_GEO_INDICATORS,
    URBAN_GEO_INDICATORS,
    _hour_to_bucket,
    map_cold_start_archetype,
)


class TestDefaultFallback:

    def test_no_signals_returns_pragmatist(self):
        """Q25=(β) default: PRAGMATIST when no signals usable."""
        assert map_cold_start_archetype() == COLD_START_DEFAULT_ARCHETYPE
        assert COLD_START_DEFAULT_ARCHETYPE == ArchetypeID.PRAGMATIST

    def test_unrecognized_signals_fall_through(self):
        """Unknown device/IAB/geo → no contributions → default."""
        result = map_cold_start_archetype(
            device="unknown_device",
            iab_category="UnknownCategory",
            geo="UNKNOWN_GEO",
        )
        assert result == ArchetypeID.PRAGMATIST


class TestSingleSignalAssignment:

    @pytest.mark.parametrize("device", list(DEVICE_ARCHETYPE_HINTS))
    def test_device_only_returns_top_hint(self, device):
        """First (most-voted by tie-break) hint of the device."""
        result = map_cold_start_archetype(device=device)
        # Single signal → top hint by lex order on archetype.value
        hints = DEVICE_ARCHETYPE_HINTS[device]
        expected = sorted(hints, key=lambda a: a.value)[0]
        assert result == expected

    @pytest.mark.parametrize("iab", list(IAB_CATEGORY_ARCHETYPE_HINTS))
    def test_iab_only_returns_top_hint(self, iab):
        result = map_cold_start_archetype(iab_category=iab)
        hints = IAB_CATEGORY_ARCHETYPE_HINTS[iab]
        expected = sorted(hints, key=lambda a: a.value)[0]
        assert result == expected

    def test_device_lowercase_normalization(self):
        """Device matching is case-insensitive."""
        upper = map_cold_start_archetype(device="MOBILE")
        lower = map_cold_start_archetype(device="mobile")
        assert upper == lower


class TestVotingTieBreak:

    def test_votes_combine_multiplicatively(self):
        """desktop=[ANALYST,GUARDIAN] + workday=[ANALYST,PRAGMATIST]
        + 'Business and Finance'=[ANALYST,GUARDIAN]
        → ANALYST=3 votes (winner), GUARDIAN=2, PRAGMATIST=1."""
        result = map_cold_start_archetype(
            device="desktop",
            hour_of_day=14,
            iab_category="Business and Finance",
        )
        assert result == ArchetypeID.ANALYST

    def test_tie_broken_by_lex_order_on_archetype_value(self):
        """tablet=[CREATOR,NURTURER] + late_night=[EXPLORER,CREATOR]
        + Travel=[EXPLORER,CONNECTOR] → CREATOR=2, EXPLORER=2,
        NURTURER=1, CONNECTOR=1 → tie between CREATOR and EXPLORER →
        CREATOR wins (lex order: 'creator' < 'explorer')."""
        result = map_cold_start_archetype(
            device="tablet",
            hour_of_day=23,
            iab_category="Travel",
        )
        assert result == ArchetypeID.CREATOR

    def test_geo_modifier_amplifies_existing_tilts(self):
        """Urban geo adds EXPLORER + CONNECTOR; combined with
        device=mobile (also tilts EXPLORER+CONNECTOR), urban
        amplifies."""
        with_urban = map_cold_start_archetype(
            device="mobile", geo="NYC",
        )
        # mobile alone → EXPLORER (lex first among mobile hints)
        # mobile + NYC urban → EXPLORER amplified (still wins)
        assert with_urban in (
            ArchetypeID.EXPLORER, ArchetypeID.CONNECTOR,
        )

    def test_rural_tilts_toward_guardian_nurturer(self):
        rural = map_cold_start_archetype(
            geo="RURAL_NE", iab_category="Home and Garden",
        )
        # Home and Garden → NURTURER + PRAGMATIST; RURAL → GUARDIAN
        # + NURTURER. NURTURER=2, GUARDIAN=1, PRAGMATIST=1.
        assert rural == ArchetypeID.NURTURER


class TestHourOfDayBuckets:

    @pytest.mark.parametrize("hour,expected_bucket", [
        (6, "morning_commute"), (9, "morning_commute"),
        (10, "workday"), (16, "workday"),
        (17, "evening_leisure"), (21, "evening_leisure"),
        (22, "late_night"), (3, "late_night"), (0, "late_night"),
    ])
    def test_hour_bucket_boundaries(self, hour, expected_bucket):
        assert _hour_to_bucket(hour) == expected_bucket


class TestArchetypeCoverage:

    def test_all_8_archetypes_can_be_assigned(self):
        """Pin that the mapping rules cover all 8 ArchetypeIDs —
        no archetype is structurally unreachable."""
        recovered = set()
        # Iterate over reasonable signal combinations.
        for device in DEVICE_ARCHETYPE_HINTS:
            for hour in [8, 14, 19, 23]:
                for iab in IAB_CATEGORY_ARCHETYPE_HINTS:
                    for geo in [None, "NYC", "RURAL_NE"]:
                        result = map_cold_start_archetype(
                            device=device, hour_of_day=hour,
                            iab_category=iab, geo=geo,
                        )
                        recovered.add(result)
        assert len(recovered) == 8, (
            f"only {len(recovered)} archetypes reachable: "
            f"{sorted(a.value for a in recovered)}"
        )


class TestDeterminism:

    def test_same_inputs_yield_same_archetype(self):
        kwargs = dict(
            device="mobile", hour_of_day=10,
            iab_category="Travel", geo="NYC",
        )
        first = map_cold_start_archetype(**kwargs)
        for _ in range(100):
            assert map_cold_start_archetype(**kwargs) == first


class TestLatency:

    def test_p99_under_100us(self):
        """Q25 latency target: <100μs per call. With dict lookups +
        Counter, this should be well under in mock-fixture runs."""
        rng = random.Random(2026)
        devices = list(DEVICE_ARCHETYPE_HINTS) + [None]
        iabs = list(IAB_CATEGORY_ARCHETYPE_HINTS) + [None]
        geos = list(URBAN_GEO_INDICATORS) + list(RURAL_GEO_INDICATORS) + [None]

        latencies_us = []
        for _ in range(10000):
            t0 = time.perf_counter()
            map_cold_start_archetype(
                device=rng.choice(devices),
                hour_of_day=rng.randint(0, 23),
                iab_category=rng.choice(iabs),
                geo=rng.choice(geos),
            )
            latencies_us.append((time.perf_counter() - t0) * 1_000_000)
        latencies_us.sort()
        p99 = latencies_us[int(len(latencies_us) * 0.99)]
        assert p99 < 100, (
            f"map_cold_start_archetype p99 {p99:.1f}μs exceeds "
            f"100μs Q25 budget"
        )
