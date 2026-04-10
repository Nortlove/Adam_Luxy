"""
ADAM Blueprint Engine

Blueprints are pre-deployed compositions of ADAM enhancement components
that activate instantly for new tenants. Each Blueprint type (PUB-ENR,
DSP-TGT, AUD-LST, etc.) specifies which connectors, intelligence components,
and delivery adapters are wired together.

The shared ADAM intelligence graph (52.8M+ elements, 441 constructs, 27-dim edges)
is NEVER duplicated — tenants share the core intelligence while getting isolated
content, segments, and delivery pipelines.

See ADAM_Deep_Technical_Architecture.md §Blueprint System.
"""

from adam.platform.blueprints.engine import BlueprintEngine, get_blueprint_engine
from adam.platform.blueprints.registry import BlueprintRegistry

__all__ = [
    "BlueprintEngine",
    "get_blueprint_engine",
    "BlueprintRegistry",
]
