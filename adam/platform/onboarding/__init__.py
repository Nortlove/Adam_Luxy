"""
ADAM Self-Service Onboarding — 6-phase guided enterprise activation.

Phases:
  1. Account creation (company, contact, auth token)
  2. Platform identification (business type → Blueprint)
  3. Inbound data specification (dynamic questions, capability scoring)
  4. Intelligence menu (ranked products, power levels, upgrade hints)
  5. Connection wiring (connectors, adapters, activation)
  6. Feedback loop setup (outcome events, learning systems)

Also supports legacy single-call activation via `onboard()`.
"""

from adam.platform.onboarding.service import OnboardingService, get_onboarding_service

__all__ = ["OnboardingService", "get_onboarding_service"]
