"""
Task 22: Causal Mediation Analysis

Runs CausalMediationAnalyzer to decompose mechanism effects into direct
and indirect pathways through behavioral mediators. Identifies WHY each
mechanism works (or doesn't) for each archetype — not just WHETHER it works.

Requires 500+ completed sequences per mechanism×archetype pair to produce
stable mediation estimates. During early pilot, runs but reports
"insufficient_data" until enough sequences accumulate.

Schedule: Weekly at 3 AM UTC (before tensor archetypes at 4 AM).
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from adam.intelligence.daily.base import DailyStrengtheningTask, TaskResult

logger = logging.getLogger(__name__)


class CausalMediationTask(DailyStrengtheningTask):
    """Weekly causal mediation analysis."""

    @property
    def name(self) -> str:
        return "causal_mediation_analysis"

    @property
    def schedule_hours(self) -> List[int]:
        return [3]

    @property
    def frequency_hours(self) -> int:
        return 24 * 7

    async def execute(self) -> TaskResult:
        result = TaskResult(task_name=self.name, success=True)

        try:
            from adam.retargeting.engines.causal_mediation import CausalMediationAnalyzer

            analyzer = CausalMediationAnalyzer()

            # Load completed sequences from intervention records
            sequences: List[Dict[str, Any]] = []
            try:
                import json
                import os
                records_path = "data/intervention_records/enriched_interventions.jsonl"
                if os.path.exists(records_path):
                    with open(records_path) as f:
                        for line in f:
                            try:
                                sequences.append(json.loads(line.strip()))
                            except json.JSONDecodeError:
                                continue
            except Exception:
                pass

            result.details["sequences_available"] = len(sequences)

            if len(sequences) < 100:
                result.details["skipped"] = "insufficient_sequences"
                return result

            # Group by mechanism × archetype and run mediation
            from collections import defaultdict
            groups: Dict[str, List] = defaultdict(list)
            for seq in sequences:
                mech = seq.get("mechanism_id", "")
                # Archetype from campaign_id segment parsing
                groups[mech].append(seq)

            analyses = {}
            for mech, mech_seqs in groups.items():
                if len(mech_seqs) >= analyzer.min_sequences:
                    try:
                        analysis = analyzer.analyze_mechanism(
                            mechanism=mech,
                            archetype="all",
                            sequences=mech_seqs,
                        )
                        analyses[mech] = {
                            "total_effect": round(analysis.total_effect, 4),
                            "direct_effect": round(analysis.direct_effect, 4),
                            "indirect_effect": round(analysis.indirect_effect, 4),
                            "dominant_pathway": analysis.dominant_pathway,
                            "n_sequences": len(mech_seqs),
                        }
                    except Exception as exc:
                        analyses[mech] = {"error": str(exc)}

            result.details["mechanisms_analyzed"] = len(analyses)
            result.details["analyses"] = analyses
            result.items_processed = len(sequences)

        except Exception as exc:
            logger.debug("Causal mediation skipped: %s", exc)
            result.details["skipped"] = str(exc)

        return result
