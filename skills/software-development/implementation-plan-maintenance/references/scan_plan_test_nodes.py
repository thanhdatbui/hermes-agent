#!/usr/bin/env python
# Deterministically verify an implementation plan's referenced test nodes against
# the live repo. Catches the classic plan-MAINTENANCE drift: a plan claiming a
# test "does not exist" / "must be added" while the live repo already has it.
#
# Usage (Git-Bash repo root):
#   python references/scan_plan_test_nodes.py <plan.md>
#   python references/scan_plan_test_nodes.py <plan.md> --repo python_runner/tests
#
# Reports:
#   - every `module.py::test_node` literal the plan references (exact-ref form)
#   - whether each currently EXISTS in the live test tree
#   - every bare `- `test_xxx`` list entry (future-node style) the plan declares
#   - whether the plan claims a test/module is "missing"/"does not exist" while
#     the live scan proves otherwise (the drift signal)
import ast, re, sys
from pathlib import Path


def collect_test_funcs(root: Path):
    mods = {}
    if not root.exists():
        return mods
    for f in sorted(root.rglob("test_*.py")):
        try:
            t = ast.parse(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        mods[str(f)] = {
            n.name for n in ast.walk(t)
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
            and n.name.startswith("test_")
        }
    return mods


def main():
    if len(sys.argv) < 2:
        print("usage: scan_plan_test_nodes.py <plan.md> [--repo DIR]", file=sys.stderr)
        return 2
    plan = Path(sys.argv[1])
    repo = Path("python_runner/tests")
    if "--repo" in sys.argv:
        repo = Path(sys.argv[sys.argv.index("--repo") + 1])
    s = plan.read_text(encoding="utf-8")
    mods = collect_test_funcs(repo)

    exact_refs = []
    for ln, line in enumerate(s.splitlines(), 1):
        for m in re.finditer(r"`([^`]+\.py)::(test_[A-Za-z0-9_]+)`", line):
            mod, node = m.group(1), m.group(2)
            exists = node in mods.get(mod, set())
            exact_refs.append((ln, mod, node, exists))

    missing_now = [r for r in exact_refs if not r[3]]
    print(f"PLAN {plan}")
    print(f"EXACT_REFS={len(exact_refs)} MISSING_NOW={len(missing_now)}")
    for ln, mod, node, exists in exact_refs:
        if not exists:
            print(f"  {ln}|MISSING_NOW|{mod}::{node}")

    # bare list test names (future-node style)
    bare = [line.strip() for n, line in enumerate(s.splitlines(), 1)
            if re.match(r"^- `test_[A-Za-z0-9_]+`", line)]
    print(f"BARE_FUTURE_NODES={len(bare)}")

    # claims of missing/non-existent while live proves present
    claim_re = re.compile(r"(missing|does not exist|không (tồn tại|có)|chưa có)", re.I)
    for ln, line in enumerate(s.splitlines(), 1):
        if claim_re.search(line):
            for m in re.finditer(r"test_[A-Za-z0-9_]+", line):
                name = m.group(0)
                present = any(name in names for names in mods.values())
                if present:
                    print(f"  {ln}|CLAIM_MISSING_BUT_PRESENT|{name}|{line.strip()[:120]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
