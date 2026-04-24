"""
Campaign Intelligence Loop — DCIL
===================================

Automated daily pipeline: Pull → Analyze → Scope → Decide → Validate → Execute → Report.

Enforces two principles:
1. No decisions in silos — every directive validated against full platform state
2. All learning scoped correctly — DerSimonian-Laird I² determines campaign vs system-wide
"""
