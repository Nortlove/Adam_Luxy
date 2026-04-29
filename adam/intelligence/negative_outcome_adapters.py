# =============================================================================
# ADAM Negative-Outcome Adapters (task #26 substrate)
# Location: adam/intelligence/negative_outcome_adapters.py
# =============================================================================

"""
NEGATIVE-OUTCOME ADAPTERS — pluggable input layer for refund/complaint/
churn events

Foundation §7 rule 11: the fitness function IS the ethics. Without
negative signals (refund / complaint / regret_signal / churn_30d /
ad_fatigue / negative_review), the OutcomeHandler's selection
pressure is silently asymmetric — only positive evidence flows into
posteriors. The system optimizes toward whatever maximizes immediate
conversion regardless of downstream damage.

OutcomeHandler.process_outcome already accepts these outcome_types
(per `adam/core/outcome_types.py`). What's missing is the WIRING from
LUXY's stack — refund / complaint / etc. events landing on
process_outcome.

LUXY's actual stack details are external dependency #1 for the pilot.
Until those land, this module ships:

  1. A pluggable AdapterProtocol — production adapters for common
     stack shapes (Stripe-style webhook, Shopify-style webhook,
     generic JSON-POST). When LUXY confirms the shape, wiring is
     a one-line registration.
  2. A SyntheticNegativeOutcomeInjector — the failure-mode runbook's
     Week-4 rehearsal substrate. Generates synthetic refund/complaint/
     regret events from the SyntheticABSimulator's outcome stream.
     Lets us TEST the negative-outcome path end-to-end before LUXY
     data flows.
  3. Adapter-stack registry + a unified `inject_negative_outcome()`
     entry point — production callers route negative events through
     a single function regardless of source.

DESIGN

The OutcomeHandler.process_outcome contract is the canonical interface;
every adapter normalizes to it. The adapter's job is to translate
upstream payload shapes (varying from provider to provider) into the
canonical (decision_id, outcome_type, outcome_value, metadata) tuple.

The SyntheticNegativeOutcomeInjector turns a SyntheticABSimulator
decision stream into a stream of synthetic refund/complaint/regret
events with realistic timing and rates. Used for:
  - Failure-mode rehearsal (Week 4)
  - Verifying the negative-outcome path doesn't break under volume
  - Ensuring the contribution tracker accumulates backfire signals
    correctly
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Protocol


# =============================================================================
# Canonical normalized event
# =============================================================================


@dataclass(frozen=True)
class NormalizedNegativeOutcome:
    """The canonical shape every adapter normalizes to.

    Maps directly to OutcomeHandler.process_outcome's parameters:
      - decision_id → decision_id
      - outcome_type → outcome_type (string from the
        adam.core.outcome_types.OutcomeType enum's value)
      - outcome_value → outcome_value (typically 0.0 for negative,
        but caller can override)
      - metadata → metadata (preserves source-specific fields for
        audit)
    """

    decision_id: str
    outcome_type: str
    outcome_value: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# Adapter Protocol
# =============================================================================


class NegativeOutcomeAdapterProtocol(Protocol):
    """Adapter contract — translate upstream payload to canonical shape.

    Implementations:
      - StripeRefundAdapter — Stripe webhook payload → REFUND
      - ShopifyRefundAdapter — Shopify webhook payload → REFUND
      - GenericJSONAdapter — flat JSON with explicit decision_id +
        outcome_type fields
      - GenericComplaintAdapter — support-ticket / email / form events
      - SyntheticAdapter — SyntheticABSimulator decision-and-outcome
        pairs
    """

    source_id: str
    """Stable identifier for the adapter — used in metadata for audit."""

    def normalize(
        self, payload: Dict[str, Any],
    ) -> Optional[NormalizedNegativeOutcome]:
        """Translate an upstream payload to NormalizedNegativeOutcome.

        Returns None if the payload doesn't match this adapter's
        expected shape (e.g., the webhook fired for a non-refund
        event). Caller can chain multiple adapters and try each.
        """
        ...


# =============================================================================
# Production adapter shells
# =============================================================================


class GenericJSONAdapter:
    """Generic adapter for flat JSON with explicit fields.

    Expected payload shape:
      {
        "decision_id": "...",
        "outcome_type": "refund" | "complaint" | "regret_signal" | ...,
        "outcome_value": 0.0,  # optional
        "metadata": {...}        # optional
      }

    Used as a fallback adapter or as the bridge from internal services.
    """

    source_id: str = "generic_json"

    REQUIRED_KEYS = ("decision_id", "outcome_type")
    KNOWN_OUTCOME_TYPES = {
        "refund", "complaint", "regret_signal", "churn_30d",
        "ad_fatigue", "negative_review",
    }

    def normalize(
        self, payload: Dict[str, Any],
    ) -> Optional[NormalizedNegativeOutcome]:
        if not isinstance(payload, dict):
            return None
        for key in self.REQUIRED_KEYS:
            if key not in payload:
                return None
        outcome_type = payload["outcome_type"]
        if outcome_type not in self.KNOWN_OUTCOME_TYPES:
            return None
        return NormalizedNegativeOutcome(
            decision_id=str(payload["decision_id"]),
            outcome_type=str(outcome_type),
            outcome_value=float(payload.get("outcome_value", 0.0)),
            metadata={
                "source_adapter": self.source_id,
                **(payload.get("metadata") or {}),
            },
        )


class StripeRefundAdapter:
    """Translates Stripe-shaped webhook payloads.

    Stripe webhook envelope:
      {
        "type": "charge.refunded",
        "data": {
          "object": {
            "metadata": { "decision_id": "..." },
            "amount_refunded": 1000,
            ...
          }
        }
      }

    Looks for type=charge.refunded; pulls decision_id from
    object.metadata.decision_id (stamped at decision-time when LUXY's
    pipeline records the conversion).
    """

    source_id: str = "stripe_refund"

    def normalize(
        self, payload: Dict[str, Any],
    ) -> Optional[NormalizedNegativeOutcome]:
        if not isinstance(payload, dict):
            return None
        if payload.get("type") != "charge.refunded":
            return None
        try:
            obj = payload["data"]["object"]
            decision_id = obj["metadata"]["decision_id"]
        except (KeyError, TypeError):
            return None
        amount_refunded = obj.get("amount_refunded", 0)
        return NormalizedNegativeOutcome(
            decision_id=str(decision_id),
            outcome_type="refund",
            outcome_value=0.0,
            metadata={
                "source_adapter": self.source_id,
                "stripe_event_type": "charge.refunded",
                "stripe_amount_refunded": amount_refunded,
            },
        )


class ShopifyRefundAdapter:
    """Translates Shopify-shaped webhook payloads.

    Shopify webhook for refund:
      {
        "id": ...,
        "order_id": ...,
        "note": "...",
        "note_attributes": [
          { "name": "decision_id", "value": "..." },
          ...
        ],
        ...
      }

    Pulls decision_id from note_attributes.
    """

    source_id: str = "shopify_refund"

    def normalize(
        self, payload: Dict[str, Any],
    ) -> Optional[NormalizedNegativeOutcome]:
        if not isinstance(payload, dict):
            return None
        if "note_attributes" not in payload:
            return None
        decision_id: Optional[str] = None
        for attr in payload.get("note_attributes", []):
            if isinstance(attr, dict) and attr.get("name") == "decision_id":
                decision_id = attr.get("value")
                break
        if not decision_id:
            return None
        return NormalizedNegativeOutcome(
            decision_id=str(decision_id),
            outcome_type="refund",
            outcome_value=0.0,
            metadata={
                "source_adapter": self.source_id,
                "shopify_order_id": payload.get("order_id"),
            },
        )


# =============================================================================
# Adapter registry + dispatch
# =============================================================================


class NegativeOutcomeAdapterRegistry:
    """Stack of adapters tried in order. First matching adapter wins.

    Production wire: the webhook endpoint receives payloads from
    multiple sources (Stripe, Shopify, internal CRM, support
    ticketing) and dispatches through this registry. The first
    adapter that returns a non-None normalize() result handles the
    payload.
    """

    def __init__(self) -> None:
        self._adapters: List[NegativeOutcomeAdapterProtocol] = []

    def register(self, adapter: NegativeOutcomeAdapterProtocol) -> None:
        self._adapters.append(adapter)

    def dispatch(
        self, payload: Dict[str, Any],
    ) -> Optional[NormalizedNegativeOutcome]:
        """Try each adapter in order; return the first non-None result."""
        for adapter in self._adapters:
            result = adapter.normalize(payload)
            if result is not None:
                return result
        return None

    def adapter_count(self) -> int:
        return len(self._adapters)

    def reset(self) -> None:
        """Test-only — clear the registry."""
        self._adapters.clear()


# =============================================================================
# Synthetic Negative Outcome Injector (failure-mode rehearsal substrate)
# =============================================================================


@dataclass
class SyntheticNegativeOutcomeStream:
    """A stream of synthetic negative outcomes for rehearsal."""

    events: List[NormalizedNegativeOutcome]
    refund_rate: float
    complaint_rate: float
    churn_rate: float


class SyntheticNegativeOutcomeInjector:
    """Generates synthetic refund / complaint / churn events from a
    decision stream.

    Use:
      sim = SyntheticABSimulator(planted_lift=0.25, seed=42)
      decisions = sim.generate_decisions(n=10000)
      outcomes = sim.generate_outcomes(decisions)
      injector = SyntheticNegativeOutcomeInjector(
          refund_rate=0.05,
          complaint_rate=0.02,
          churn_rate=0.10,
          backfire_pressure_multiplier=1.5,
          seed=42,
      )
      stream = injector.inject(decisions, outcomes)

    The stream is a list of NormalizedNegativeOutcome events with
    realistic LUXY-shaped rates. Used by:
      - Failure-mode runbook Week-4 rehearsal
      - Pre-pilot pipeline validation (does the contribution tracker
        accumulate backfire signal as expected?)
      - Pre-pilot dashboard validation (does the agency_dashboard
        attention_inversion_diagonals respond correctly to backfire?)
    """

    def __init__(
        self,
        *,
        refund_rate: float = 0.05,
        complaint_rate: float = 0.02,
        churn_rate: float = 0.10,
        backfire_pressure_multiplier: float = 1.5,
        seed: int = 42,
    ) -> None:
        if not (0.0 <= refund_rate <= 1.0):
            raise ValueError(f"refund_rate must be in [0, 1]; got {refund_rate}")
        if not (0.0 <= complaint_rate <= 1.0):
            raise ValueError(f"complaint_rate must be in [0, 1]; got {complaint_rate}")
        if not (0.0 <= churn_rate <= 1.0):
            raise ValueError(f"churn_rate must be in [0, 1]; got {churn_rate}")
        self.refund_rate = refund_rate
        self.complaint_rate = complaint_rate
        self.churn_rate = churn_rate
        self.backfire_pressure_multiplier = backfire_pressure_multiplier

        import random
        self._rng = random.Random(seed)

    def inject(
        self,
        decisions: List[Any],
        outcomes: List[Any],
    ) -> SyntheticNegativeOutcomeStream:
        """Build a synthetic negative-outcome event stream.

        Args:
            decisions: list of SyntheticDecision (must have request_id +
                treatment_arm + mechanism_recommended.is_vigilance_activating)
            outcomes: parallel list of SyntheticOutcome (must have
                outcome_type)

        Returns:
            SyntheticNegativeOutcomeStream with events, plus the
            effective rates as observed in the synthetic stream
            (used for assertion in tests).
        """
        outcomes_by_id = {o.request_id: o for o in outcomes}
        events: List[NormalizedNegativeOutcome] = []

        n_conversions = 0
        n_refunds = 0
        n_complaints = 0
        n_churn = 0

        for d in decisions:
            o = outcomes_by_id.get(d.request_id)
            if o is None:
                continue
            if o.outcome_type != "conversion":
                continue
            n_conversions += 1

            # Backfire pressure for vigilance-activating × treatment
            local_refund_rate = self.refund_rate
            local_complaint_rate = self.complaint_rate
            if (
                d.treatment_arm == "bilateral"
                and getattr(d.mechanism_recommended, "is_vigilance_activating", False)
            ):
                local_refund_rate *= self.backfire_pressure_multiplier
                local_complaint_rate *= self.backfire_pressure_multiplier

            # Refund
            if self._rng.random() < local_refund_rate:
                events.append(NormalizedNegativeOutcome(
                    decision_id=d.request_id,
                    outcome_type="refund",
                    outcome_value=0.0,
                    metadata={
                        "source_adapter": "synthetic_injector",
                        "treatment_arm": d.treatment_arm,
                    },
                ))
                n_refunds += 1
                continue

            # Complaint
            if self._rng.random() < local_complaint_rate:
                events.append(NormalizedNegativeOutcome(
                    decision_id=d.request_id,
                    outcome_type="complaint",
                    outcome_value=0.0,
                    metadata={
                        "source_adapter": "synthetic_injector",
                        "treatment_arm": d.treatment_arm,
                    },
                ))
                n_complaints += 1
                continue

            # Churn (no negative event but counted in rate)
            if self._rng.random() < self.churn_rate:
                events.append(NormalizedNegativeOutcome(
                    decision_id=d.request_id,
                    outcome_type="churn_30d",
                    outcome_value=0.0,
                    metadata={
                        "source_adapter": "synthetic_injector",
                        "treatment_arm": d.treatment_arm,
                    },
                ))
                n_churn += 1

        observed_refund_rate = n_refunds / n_conversions if n_conversions else 0.0
        observed_complaint_rate = n_complaints / n_conversions if n_conversions else 0.0
        observed_churn_rate = n_churn / n_conversions if n_conversions else 0.0

        return SyntheticNegativeOutcomeStream(
            events=events,
            refund_rate=observed_refund_rate,
            complaint_rate=observed_complaint_rate,
            churn_rate=observed_churn_rate,
        )


# =============================================================================
# Singleton registry (production)
# =============================================================================


_default_registry: Optional[NegativeOutcomeAdapterRegistry] = None


def get_default_registry() -> NegativeOutcomeAdapterRegistry:
    """Get or build the default registry with the production adapters.

    Default adapter stack (in dispatch order):
      1. StripeRefundAdapter
      2. ShopifyRefundAdapter
      3. GenericJSONAdapter (catch-all)

    Wiring of LUXY-specific adapter happens here when LUXY's actual
    payload shape is confirmed by Becca.
    """
    global _default_registry
    if _default_registry is None:
        _default_registry = NegativeOutcomeAdapterRegistry()
        _default_registry.register(StripeRefundAdapter())
        _default_registry.register(ShopifyRefundAdapter())
        _default_registry.register(GenericJSONAdapter())
    return _default_registry


def reset_default_registry() -> None:
    """Test-only — clear and rebuild the singleton on next access."""
    global _default_registry
    _default_registry = None


__all__ = [
    "GenericJSONAdapter",
    "NegativeOutcomeAdapterProtocol",
    "NegativeOutcomeAdapterRegistry",
    "NormalizedNegativeOutcome",
    "ShopifyRefundAdapter",
    "StripeRefundAdapter",
    "SyntheticNegativeOutcomeInjector",
    "SyntheticNegativeOutcomeStream",
    "get_default_registry",
    "reset_default_registry",
]
