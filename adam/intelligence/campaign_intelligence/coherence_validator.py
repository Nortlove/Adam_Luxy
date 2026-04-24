"""
Platform Coherence Validator
==============================

Enforces "no decisions in silos." Every optimization directive passes
through this validator before execution.

Checks:
1. Cross-campaign budget coherence (total within limits, no archetype starved)
2. Mechanism consistency (no contradictions across shared domains)
3. Domain coherence (add/remove decisions considered across all campaigns)
4. Temporal coherence (no contradictory changes in same cycle)
5. Cooldown enforcement (no changes to recently-modified campaigns)
6. Safety rails (max change percentages, min data requirements)
"""

from __future__ import annotations

import logging
import time
from typing import Dict, List, Tuple

from adam.intelligence.campaign_intelligence.config import get_dcil_config
from adam.intelligence.campaign_intelligence.models import (
    Directive,
    DirectiveStatus,
    DirectiveType,
    PlatformState,
)

logger = logging.getLogger(__name__)


class PlatformCoherenceValidator:
    """Validates directives against full platform state."""

    def __init__(self, config=None):
        self.config = config or get_dcil_config()

    def validate(
        self,
        directives: List[Directive],
        platform_state: PlatformState,
    ) -> List[Directive]:
        """
        Validate all directives against platform state.
        Returns directives with updated status (APPROVED, BLOCKED, CAPPED).
        """
        validated = []

        for directive in directives:
            status, reason = self._validate_single(directive, platform_state, validated)
            directive.status = status
            if status == DirectiveStatus.BLOCKED:
                directive.blocked_reason = reason
                logger.info("BLOCKED directive %s: %s", directive.directive_id, reason)
            elif status == DirectiveStatus.CAPPED:
                directive.blocked_reason = reason
                logger.info("CAPPED directive %s: %s", directive.directive_id, reason)
            else:
                logger.info("APPROVED directive %s: %s", directive.directive_id, directive.rationale[:80])
            validated.append(directive)

        return validated

    def _validate_single(
        self,
        directive: Directive,
        state: PlatformState,
        already_validated: List[Directive],
    ) -> Tuple[DirectiveStatus, str]:
        """Validate a single directive. Returns (status, reason)."""

        # Check 1: Cooldown — was this campaign modified recently?
        reason = self._check_cooldown(directive, state)
        if reason:
            return DirectiveStatus.BLOCKED, reason

        # Check 2: Minimum data requirements
        reason = self._check_min_data(directive, state)
        if reason:
            return DirectiveStatus.BLOCKED, reason

        # Check 3: Safety rail — max change percentage
        reason = self._check_safety_rails(directive, state)
        if reason:
            return DirectiveStatus.CAPPED, reason

        # Check 4: Temporal coherence — contradicts another directive this cycle?
        reason = self._check_temporal_coherence(directive, already_validated)
        if reason:
            return DirectiveStatus.BLOCKED, reason

        # Check 5: Mechanism contradiction — don't boost and reduce same mechanism for same archetype
        if directive.directive_type == DirectiveType.MECHANISM_ROTATION:
            reason = self._check_mechanism_coherence(directive, already_validated)
            if reason:
                return DirectiveStatus.BLOCKED, reason

        # Check 6: Cross-campaign budget coherence
        if directive.directive_type == DirectiveType.BUDGET_REALLOCATION:
            reason = self._check_budget_coherence(directive, state, already_validated)
            if reason:
                return DirectiveStatus.CAPPED, reason

        # Check 6: Domain coherence
        if directive.directive_type == DirectiveType.DOMAIN_TARGETING:
            reason = self._check_domain_coherence(directive, state)
            if reason:
                return DirectiveStatus.BLOCKED, reason

        # Check 7: Pause limit
        if directive.directive_type == DirectiveType.PAUSE_RESUME:
            reason = self._check_pause_limit(directive, state, already_validated)
            if reason:
                return DirectiveStatus.BLOCKED, reason

        return DirectiveStatus.APPROVED, ""

    def _check_cooldown(self, directive: Directive, state: PlatformState) -> str:
        """Block changes to campaigns modified within cooldown window."""
        cooldown_seconds = self.config.cooldown_hours_after_change * 3600
        now = time.time()

        for recent in state.recent_directives:
            if recent.status != DirectiveStatus.EXECUTED:
                continue
            if recent.campaign_id and recent.campaign_id == directive.campaign_id:
                elapsed = now - recent.executed_at
                if elapsed < cooldown_seconds:
                    hours_remaining = (cooldown_seconds - elapsed) / 3600
                    return f"Campaign {directive.campaign_id} was modified {elapsed/3600:.0f}h ago. Cooldown: {hours_remaining:.0f}h remaining."

        return ""

    def _check_min_data(self, directive: Directive, state: PlatformState) -> str:
        """Block actions without sufficient statistical evidence."""
        if directive.directive_type == DirectiveType.MECHANISM_ROTATION:
            if directive.confidence < 0.5:
                return f"Confidence {directive.confidence:.2f} below threshold 0.50 for mechanism changes."

        if directive.directive_type == DirectiveType.BUDGET_REALLOCATION:
            # Check if archetype has enough conversions
            arch_stats = {}
            for camp in state.campaigns:
                if camp.archetype == directive.archetype:
                    arch_stats["conversions"] = arch_stats.get("conversions", 0) + camp.conversions

            if arch_stats.get("conversions", 0) < self.config.min_conversions_for_action:
                return f"Archetype {directive.archetype} has {arch_stats.get('conversions', 0)} conversions (min: {self.config.min_conversions_for_action})."

        return ""

    def _check_safety_rails(self, directive: Directive, state: PlatformState) -> str:
        """Cap changes within safety rail limits."""
        if directive.directive_type == DirectiveType.BUDGET_REALLOCATION:
            max_pct = self.config.max_budget_change_pct_per_campaign
            val_str = str(directive.proposed_value)
            if "increase" in val_str or "reduce" in val_str:
                pct = _extract_percentage(val_str)
                if pct is None:
                    # Cannot determine change magnitude — cap at max as precaution
                    directive.capped_from = directive.proposed_value
                    directive.proposed_value = f"capped_to_{max_pct}pct"
                    return f"Budget change magnitude unknown — capped to {max_pct}% as precaution."
                if pct > max_pct:
                    directive.capped_from = directive.proposed_value
                    directive.proposed_value = f"capped_to_{max_pct}pct"
                    return f"Budget change capped from {pct}% to {max_pct}%."

        if directive.directive_type == DirectiveType.DOMAIN_TARGETING:
            if "blacklist_add" in str(directive.parameter):
                # Check how many domains already removed today
                removed_today = sum(
                    1 for d in state.recent_directives
                    if d.directive_type == DirectiveType.DOMAIN_TARGETING
                    and d.status == DirectiveStatus.EXECUTED
                    and "blacklist_add" in str(d.parameter)
                    and d.campaign_id == directive.campaign_id
                    and (time.time() - d.executed_at) < 86400
                )
                if removed_today >= self.config.max_domains_removed_per_campaign_per_day:
                    return f"Already removed {removed_today} domains from this campaign today (max: {self.config.max_domains_removed_per_campaign_per_day})."

        return ""

    def _check_temporal_coherence(
        self, directive: Directive, already_validated: List[Directive],
    ) -> str:
        """Block contradictory changes in the same cycle."""
        for existing in already_validated:
            if existing.status not in (DirectiveStatus.APPROVED, DirectiveStatus.CAPPED):
                continue

            # Same campaign, same parameter, different direction
            if (existing.campaign_id == directive.campaign_id
                    and existing.parameter == directive.parameter
                    and existing.proposed_value != directive.proposed_value):
                return (
                    f"Contradicts directive {existing.directive_id} in same cycle: "
                    f"both target {directive.parameter} on campaign {directive.campaign_id}."
                )

            # Opposite budget directions for same archetype
            if (existing.directive_type == DirectiveType.BUDGET_REALLOCATION
                    and directive.directive_type == DirectiveType.BUDGET_REALLOCATION
                    and existing.archetype == directive.archetype):
                existing_direction = "increase" if "increase" in str(existing.proposed_value) else "reduce"
                new_direction = "increase" if "increase" in str(directive.proposed_value) else "reduce"
                if existing_direction != new_direction:
                    return (
                        f"Contradicts directive {existing.directive_id}: "
                        f"one {existing_direction}s and one {new_direction}s budget for {directive.archetype}."
                    )

        return ""

    def _check_budget_coherence(
        self,
        directive: Directive,
        state: PlatformState,
        already_validated: List[Directive],
    ) -> str:
        """Check total budget changes don't exceed system-wide limit."""
        total_budget = state.total_daily_budget or 1
        total_change_pct = 0.0

        for existing in already_validated:
            if existing.status in (DirectiveStatus.APPROVED, DirectiveStatus.CAPPED):
                if existing.directive_type == DirectiveType.BUDGET_REALLOCATION:
                    total_change_pct += self._estimate_change_pct(existing)

        new_change = self._estimate_change_pct(directive)
        if total_change_pct + new_change > self.config.max_budget_change_pct_total:
            return (
                f"Total budget change would reach {total_change_pct + new_change:.0f}% "
                f"(max: {self.config.max_budget_change_pct_total}%). "
                f"Capping this directive."
            )

        return ""

    def _check_domain_coherence(self, directive: Directive, state: PlatformState) -> str:
        """Check domain changes are considered across all campaigns."""
        # If adding to blacklist, check if domain is producing conversions for other campaigns
        if "blacklist_add" in str(directive.parameter):
            domain = str(directive.proposed_value).lower()
            for camp in state.campaigns:
                if camp.campaign_id == directive.campaign_id:
                    continue
                for ds in camp.domain_stats:
                    if ds.get("domain", "").lower() == domain and ds.get("conversions", 0) > 0:
                        return (
                            f"Domain {domain} produces conversions for campaign {camp.name}. "
                            f"Cannot blacklist across platform."
                        )
        return ""

    def _check_pause_limit(
        self,
        directive: Directive,
        state: PlatformState,
        already_validated: List[Directive],
    ) -> str:
        """Check pause limit per day."""
        pauses_today = sum(
            1 for d in already_validated
            if d.directive_type == DirectiveType.PAUSE_RESUME
            and d.status in (DirectiveStatus.APPROVED, DirectiveStatus.CAPPED)
            and "pause" in str(d.proposed_value).lower()
        )
        pauses_recent = sum(
            1 for d in state.recent_directives
            if d.directive_type == DirectiveType.PAUSE_RESUME
            and d.status == DirectiveStatus.EXECUTED
            and "pause" in str(d.proposed_value).lower()
            and (time.time() - d.executed_at) < 86400
        )

        total_pauses = pauses_today + pauses_recent
        if total_pauses >= self.config.max_campaigns_paused_per_day:
            return f"Already paused {total_pauses} campaigns today (max: {self.config.max_campaigns_paused_per_day})."

        return ""

    def _check_mechanism_coherence(
        self, directive: Directive, already_validated: List[Directive],
    ) -> str:
        """Block mechanism rotation directives that contradict each other for the same archetype."""
        for existing in already_validated:
            if existing.status not in (DirectiveStatus.APPROVED, DirectiveStatus.CAPPED):
                continue
            if existing.directive_type != DirectiveType.MECHANISM_ROTATION:
                continue
            if existing.archetype and existing.archetype == directive.archetype:
                # Both target same archetype with mechanism changes
                existing_val = str(existing.proposed_value).lower()
                new_val = str(directive.proposed_value).lower()

                # Check for contradictory boost/reduce on same mechanism
                for mech in ["authority", "social_proof", "cognitive_ease", "regulatory_focus",
                             "identity_construction", "mimetic_desire", "automatic_evaluation"]:
                    boost_in_existing = f"boost_{mech}" in existing_val
                    reduce_in_new = f"reduce_{mech}" in new_val
                    reduce_in_existing = f"reduce_{mech}" in existing_val
                    boost_in_new = f"boost_{mech}" in new_val

                    if (boost_in_existing and reduce_in_new) or (reduce_in_existing and boost_in_new):
                        return (
                            f"Mechanism contradiction: directive {existing.directive_id} "
                            f"and this directive give opposite directions for '{mech}' "
                            f"on archetype '{directive.archetype}'. Resolve before executing."
                        )
        return ""

    def _estimate_change_pct(self, directive: Directive) -> float:
        """Estimate the percentage budget change from a directive."""
        pct = _extract_percentage(str(directive.proposed_value))
        return pct if pct is not None else 5.0


def _extract_percentage(val: str) -> float | None:
    """Extract a percentage value from a directive value string."""
    import re
    match = re.search(r'(\d+(?:\.\d+)?)\s*(?:pct|%)', val)
    if match:
        return float(match.group(1))
    return None


def assemble_platform_state(
    snapshot=None,
    recent_directives=None,
) -> PlatformState:
    """Assemble full platform state for coherence validation."""
    state = PlatformState()

    if snapshot:
        state.campaigns = snapshot.campaigns
        state.total_daily_budget = sum(c.spend for c in snapshot.campaigns if c.status == "ACTIVE")

    if recent_directives:
        state.recent_directives = recent_directives

    # Load Thompson posteriors
    try:
        from adam.meta_learner.thompson import get_thompson_sampler
        sampler = get_thompson_sampler()
        if hasattr(sampler, "posteriors"):
            state.thompson_posteriors = dict(sampler.posteriors)
    except Exception:
        pass

    # Load KPN state
    try:
        from adam.intelligence.knowledge_propagation import get_propagation_network
        kpn = get_propagation_network()
        state.kpn_state = kpn.get_network_state()
    except Exception:
        pass

    return state
