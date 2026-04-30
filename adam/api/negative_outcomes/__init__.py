"""Negative-outcome webhook API — Spine #11 end-to-end wire.

Closes directive Phase 1 LUXY negative-outcome adapter end-to-end
deliverable. Single endpoint that receives external negative-outcome
events (LUXY booking, Stripe refund, Shopify refund, generic JSON),
dispatches through the adapter registry, and feeds them into
OutcomeHandler so the fitness function (Foundation §7 rule 11)
takes the magnitude-weighted evidence against the producing mechanism.
"""

from adam.api.negative_outcomes.router import router as negative_outcomes_router

__all__ = ["negative_outcomes_router"]
