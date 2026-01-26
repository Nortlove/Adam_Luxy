# ADAM Import Patterns & Cycle Prevention

## Overview

ADAM uses dynamic imports in specific locations to prevent circular import issues.
This document explains the patterns used and why they are necessary.

## Why Import Cycles Occur

Import cycles typically occur when:
1. **Service A** depends on **Service B** 
2. **Service B** also depends on **Service A**

In ADAM, this commonly happens between:
- Atoms and LLM services (atoms use LLM for fusion)
- Blackboard zones and components (zones reference component types)
- Gradient Bridge and all learning components

## Dynamic Import Patterns Used

### Pattern 1: Lazy Import in Method

Used when a service is only needed occasionally.

```python
# In adam/atoms/core/base.py
async def _fuse_with_claude(self, ...):
    # IMPORT CYCLE PREVENTION:
    # LLMService imports CircuitBreaker from performance module,
    # which may reference atom types. Import here to break cycle.
    from adam.llm.service import LLMService
    ...
```

**Why this works:** The import only happens at runtime when the method is called,
not at module load time. By then, all modules are fully initialized.

### Pattern 2: TYPE_CHECKING Block

Used for type hints only.

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # These imports are only for type hints, not runtime
    from adam.atoms.core.base import BaseAtom
    from adam.blackboard.service import BlackboardService
```

**Why this works:** `TYPE_CHECKING` is False at runtime, so no actual import occurs.
Type checkers (mypy, pyright) still see the types.

### Pattern 3: Local Import in Function

Used in factory functions or initialization.

```python
def create_atom_dag():
    # Import here to avoid cycle with atom implementations
    from adam.atoms.core.regulatory_focus import RegulatoryFocusAtom
    from adam.atoms.core.construal_level import ConstrualLevelAtom
    ...
```

## Locations of Dynamic Imports

### 1. `adam/atoms/core/base.py`

```python
# Line ~458: LLM service for Claude fusion
from adam.llm.service import LLMService

# Reason: LLMService depends on CircuitBreaker and FusionResult,
# which reference atom models. Importing at method call time
# ensures all dependencies are loaded.
```

### 2. `adam/atoms/core/base.py`

```python
# Line ~555: Legacy output conversion
from adam.blackboard.models.zone2_reasoning import AtomOutput as LegacyOutput

# Reason: Zone2 models reference AtomType which is defined in
# the same module. Lazy import prevents the models from trying
# to import themselves.
```

### 3. `adam/atoms/core/base.py`

```python
# Line ~575: Learning signal emission
from adam.blackboard.models.zone5_learning import (
    ComponentSignal,
    SignalSource,
    SignalPriority,
)

# Reason: Zone5 models may reference component types that
# include atoms. Import at signal emission time.
```

### 4. `adam/gradient_bridge/service.py`

Uses forward references with strings for Pydantic models to avoid
needing imports at class definition time.

### 5. `adam/verification/service.py`

Similar pattern - verification needs to import atom types for
validation but atoms may reference verification status.

## Best Practices

### DO:
1. Use dynamic imports when cycle is unavoidable
2. Add a comment explaining why the import is dynamic
3. Import at the latest possible moment
4. Use `TYPE_CHECKING` for type hints

### DON'T:
1. Use dynamic imports everywhere "just in case"
2. Forget to document why an import is dynamic
3. Import entire modules when you only need one class
4. Create new cycles - refactor instead if possible

## Refactoring Guide

If you find yourself adding more dynamic imports, consider:

1. **Extract common models** to a shared module
2. **Use dependency injection** instead of direct imports
3. **Create interface protocols** that both sides implement
4. **Move the dependency** to a third module

## Testing Import Order

Run this to verify no import cycles:

```bash
python -c "from adam.core.container import get_container; print('OK')"
```

If this fails with ImportError, there's a cycle to resolve.

## Module Load Order

The recommended import order for ADAM:

1. `adam.config.settings` - Configuration
2. `adam.infrastructure.*` - Redis, Neo4j, Kafka
3. `adam.blackboard.models.*` - Zone models
4. `adam.blackboard.service` - Blackboard service
5. `adam.atoms.models.*` - Evidence models
6. `adam.atoms.core.*` - Atom implementations
7. `adam.llm.*` - Claude integration
8. `adam.gradient_bridge.*` - Learning infrastructure
9. `adam.core.container` - Dependency container
10. `adam.api.*` - API routers

This order minimizes dynamic imports needed.
