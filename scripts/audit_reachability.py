#!/usr/bin/env python3
"""
AST-based reachability analyzer for the ADAM codebase.

For each .py file under `adam/`, determines which `adam.*` modules it
imports — correctly handling:

  - absolute imports:   `from adam.X.Y import Z`
  - absolute imports:   `import adam.X.Y`
  - relative imports:   `from . import sibling`
  - relative imports:   `from .sibling import X`
  - relative imports:   `from ..parent.sibling import X`

The earlier regex-based version of this script missed relative imports
entirely, which produced a substantial number of false-positive orphan
classifications. See ADAM_INTEGRATION_AUDIT_2026-04-15.md Section 11a.

Produces:
  /tmp/adam_reachability_ast.json       — full reachability graph
  /tmp/adam_reachability_ast_diff.json  — diff vs. the previous grep-based run

Usage:
  python scripts/audit_reachability.py              # scan adam/ only
  python scripts/audit_reachability.py --with-tests # include scripts/, tests/, bin/
"""

from __future__ import annotations

import ast
import argparse
import json
import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import Set, Dict, List, Tuple


ADAM_ROOT = "adam"
EXTRA_SOURCE_ROOTS = ["scripts", "tests", "bin"]


def path_to_module(path: str) -> str:
    """Convert 'adam/foo/bar.py' → 'adam.foo.bar' (or 'adam.foo' for __init__.py)."""
    p = path.replace(".py", "").replace(os.sep, ".")
    if p.endswith(".__init__"):
        p = p[:-9]
    return p


def path_to_package(path: str) -> str:
    """Return the package containing this file — the context used to resolve
    relative imports.

    For 'adam/foo/bar.py', the package is 'adam.foo'.
    For 'adam/foo/__init__.py', the package is 'adam.foo' (itself, since an
    __init__.py IS the package).
    """
    module = path_to_module(path)
    if path.endswith("__init__.py"):
        return module
    if "." in module:
        return module.rsplit(".", 1)[0]
    return ""


def collect_py_files(root: str) -> List[str]:
    """Walk `root` and return all .py files, excluding __pycache__."""
    out = []
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d != "__pycache__"]
        for f in fns:
            if f.endswith(".py"):
                out.append(os.path.join(dp, f))
    return out


def collect_imports(file_path: str, package: str) -> Set[str]:
    """Parse a .py file and return the set of dotted adam.* targets it imports.

    The returned set may contain names that are NOT actual modules (e.g.,
    class or function names imported via `from adam.foo import SomeClass`)
    — the caller must resolve each raw name against the set of real modules
    by walking back until a match is found.
    """
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            source = f.read()
    except Exception:
        return set()

    try:
        tree = ast.parse(source, filename=file_path)
    except SyntaxError:
        return set()

    imports: Set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            # `import adam.foo.bar` or `import adam.foo.bar as x`
            for alias in node.names:
                name = alias.name
                if name == "adam" or name.startswith("adam."):
                    imports.add(name)

        elif isinstance(node, ast.ImportFrom):
            if node.level == 0:
                # Absolute: `from adam.X.Y import Z, W`
                if node.module and (node.module == "adam" or node.module.startswith("adam.")):
                    imports.add(node.module)
                    # Each imported name may itself be a submodule
                    for alias in node.names:
                        if alias.name == "*":
                            continue
                        imports.add(f"{node.module}.{alias.name}")
            else:
                # Relative: `from .sibling import X` or `from ..parent.sibling import X`
                if not package:
                    continue
                parts = package.split(".")
                # level=1 means "from . import" — stay in the same package.
                # level=2 means "from .. import" — go up one level.
                # Number of parts to keep = len(parts) - (level - 1).
                keep = len(parts) - (node.level - 1)
                if keep <= 0:
                    # Relative import walks above the root; cannot resolve
                    continue
                base = ".".join(parts[:keep])
                if not base:
                    continue
                target = f"{base}.{node.module}" if node.module else base
                imports.add(target)
                for alias in node.names:
                    if alias.name == "*":
                        continue
                    imports.add(f"{target}.{alias.name}")

    return imports


def resolve(raw: str, all_modules: Set[str]) -> str | None:
    """Walk back a dotted name until it matches an actual module, or None."""
    candidate = raw
    while candidate:
        if candidate in all_modules:
            return candidate
        if "." not in candidate:
            return None
        candidate = candidate.rsplit(".", 1)[0]
    return None


def build_graph(
    adam_files: List[str],
    extra_files: List[str],
) -> Tuple[Dict[str, Set[str]], Set[str]]:
    """Build the import graph for the given files.

    Returns:
        (imported_by, all_modules)
        — `imported_by[module]` is the set of source modules that import it.
        — `all_modules` is the set of real adam.* modules from adam_files.
    """
    module_for = {p: path_to_module(p) for p in adam_files}
    package_for = {p: path_to_package(p) for p in adam_files + extra_files}
    # Extra files (scripts/tests/bin) need their own package context. Since
    # they don't live under `adam/`, `path_to_package` returns a non-adam
    # package (e.g. 'scripts.foo'), which is fine — relative imports inside
    # them are not adam imports by construction.

    all_modules = set(module_for.values())
    imported_by: Dict[str, Set[str]] = defaultdict(set)

    def scan(files: List[str], src_labels: Dict[str, str]) -> None:
        for p in files:
            package = package_for.get(p, "")
            src_label = src_labels.get(p, p)
            raw_imports = collect_imports(p, package)
            for raw in raw_imports:
                target = resolve(raw, all_modules)
                if target and target != src_label:
                    imported_by[target].add(src_label)

    # Source label for adam files = their module name. For extra files, use
    # the file path so we can tell which orphans are "rescued only by tests."
    adam_labels = {p: module_for[p] for p in adam_files}
    extra_labels = {p: p for p in extra_files}

    scan(adam_files, adam_labels)
    scan(extra_files, extra_labels)

    return imported_by, all_modules


def summarize(imported_by: Dict[str, Set[str]], all_modules: Set[str]) -> dict:
    orphaned = sorted(m for m in all_modules if not imported_by.get(m))
    imported = sorted(all_modules - set(orphaned))

    # Top-level breakdown of orphans
    by_area: Dict[str, List[str]] = defaultdict(list)
    for m in orphaned:
        parts = m.split(".")
        key = ".".join(parts[:2]) if len(parts) >= 2 else parts[0]
        by_area[key].append(m)

    # Orphans only rescued by non-adam callers
    rescued_by_extras_only = []
    for m in sorted(all_modules):
        importers = imported_by.get(m, set())
        if importers:
            adam_importers = {i for i in importers if i.startswith("adam.")}
            if not adam_importers:
                rescued_by_extras_only.append(m)

    return {
        "total_modules": len(all_modules),
        "imported_count": len(imported),
        "orphaned_count": len(orphaned),
        "orphaned": orphaned,
        "rescued_by_extras_only": rescued_by_extras_only,
        "by_area": {k: sorted(v) for k, v in by_area.items()},
        "imported_by": {k: sorted(list(v)) for k, v in imported_by.items()},
    }


def diff_against_previous(current_orphans: Set[str], previous_path: str) -> dict:
    """Compare current orphan set against the previous regex-based audit."""
    if not os.path.exists(previous_path):
        return {"note": f"No previous audit at {previous_path}; no diff."}
    try:
        with open(previous_path) as f:
            prev = json.load(f)
    except Exception as exc:
        return {"note": f"Could not read previous audit: {exc}"}
    prev_orphans = set(prev.get("orphaned", []))
    now_live = sorted(prev_orphans - current_orphans)  # were orphan, now live
    still_orphaned = sorted(prev_orphans & current_orphans)
    newly_orphaned = sorted(current_orphans - prev_orphans)  # were live, now orphan
    return {
        "previous_orphan_count": len(prev_orphans),
        "current_orphan_count": len(current_orphans),
        "were_orphaned_now_live": now_live,
        "were_orphaned_now_live_count": len(now_live),
        "still_orphaned_count": len(still_orphaned),
        "newly_orphaned_count": len(newly_orphaned),
        "newly_orphaned": newly_orphaned,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--with-tests",
        action="store_true",
        help="Include scripts/, tests/, bin/ as import sources for rescue.",
    )
    parser.add_argument(
        "--out",
        default="/tmp/adam_reachability_ast.json",
        help="Output path for the full JSON report.",
    )
    parser.add_argument(
        "--prev",
        default="/tmp/adam_reachability.json",
        help="Previous (grep-based) audit JSON for diffing. Optional.",
    )
    args = parser.parse_args()

    if not os.path.isdir(ADAM_ROOT):
        print(f"ERROR: {ADAM_ROOT}/ not found. Run from repo root.", file=sys.stderr)
        return 2

    adam_files = collect_py_files(ADAM_ROOT)
    extra_files = []
    if args.with_tests:
        for r in EXTRA_SOURCE_ROOTS:
            if os.path.isdir(r):
                extra_files.extend(collect_py_files(r))

    print(f"Scanning {len(adam_files)} files in {ADAM_ROOT}/")
    if args.with_tests:
        print(f"Plus {len(extra_files)} files in scripts/tests/bin/")

    imported_by, all_modules = build_graph(adam_files, extra_files)
    summary = summarize(imported_by, all_modules)

    print()
    print(f"Total adam/* modules: {summary['total_modules']}")
    print(f"Imported by at least one other file: {summary['imported_count']}")
    print(f"Orphaned: {summary['orphaned_count']}")
    if args.with_tests:
        print(f"  (of which rescued only by scripts/tests/bin: {len(summary['rescued_by_extras_only'])})")

    print()
    print("Top 15 orphan areas:")
    for area, mods in sorted(summary["by_area"].items(), key=lambda x: -len(x[1]))[:15]:
        print(f"  {area}: {len(mods)}")

    # Diff against previous run
    diff = diff_against_previous(set(summary["orphaned"]), args.prev)
    summary["diff_vs_previous"] = diff

    with open(args.out, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\nWrote full report: {args.out}")

    if "previous_orphan_count" in diff:
        print()
        print(f"Diff vs. previous audit ({args.prev}):")
        print(f"  Previous orphans: {diff['previous_orphan_count']}")
        print(f"  Current orphans:  {diff['current_orphan_count']}")
        print(f"  Rescued (were orphaned, now live): {diff['were_orphaned_now_live_count']}")
        print(f"  Newly orphaned:   {diff['newly_orphaned_count']}")
        if diff["were_orphaned_now_live"]:
            print()
            print("  Rescued modules (first 40):")
            for m in diff["were_orphaned_now_live"][:40]:
                print(f"    {m}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
