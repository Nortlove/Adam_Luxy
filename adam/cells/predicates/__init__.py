"""S6.2 cell predicates package.

Predicate modules are imported here to trigger @cell_predicate
decorator registration at package import time. Adding a new
predicate file: add it to the import list below.

Per Q19=α: predicates are Python decorator-registered functions.
No DSL, no YAML, no parser.
"""

# Triggering imports — order doesn't matter for correctness, but
# is alphabetized for stable registration order across versions.
from adam.cells.predicates import compensatory_predicates  # noqa: F401
from adam.cells.predicates import fomo_predicates  # noqa: F401
from adam.cells.predicates import maximizer_predicates  # noqa: F401
from adam.cells.predicates import ownership_predicates  # noqa: F401
from adam.cells.predicates import persuasion_resistance_predicates  # noqa: F401
