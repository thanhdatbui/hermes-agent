#!/usr/bin/env python3
"""Orphan-reachability probe for read-only dirty-diff audits.

Proves whether a suspect function/branch is still reachable from a set of
live root callers after a change, using ONLY an AST transitive-closure walk
(no import, no execution, no device/live artifact). Use it to confirm a
removed fallback path is truly dead before issuing an APPROVED verdict --
`git diff` absence alone does not prove a path is unreachable.

Usage:
  python orphan_reachability_probe.py <file.py> --roots f1 f2 --suspects s1 s2

Prints, per root, the intersection of reachable def-names with the suspect
set. Empty intersection == orphaned (no live caller path remains).
"""
import argparse
import ast
from pathlib import Path


def load_funcs(path):
    tree = ast.parse(Path(path).read_text(encoding="utf-8"))
    return {
        n.name: n
        for n in ast.walk(tree)
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def direct_calls(node):
    return sorted(
        {
            x.func.id
            for x in ast.walk(node)
            if isinstance(x, ast.Call) and isinstance(x.func, ast.Name)
        }
    )


def reachable(funcs, root):
    seen = set()
    stack = [root]
    while stack:
        name = stack.pop()
        if name in seen:
            continue
        seen.add(name)
        for callee in direct_calls(funcs[name]):
            if callee in funcs and callee not in seen:
                stack.append(callee)
    return seen


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--roots", nargs="+", required=True,
                    help="live entrypoints to walk from")
    ap.add_argument("--suspects", nargs="+", required=True,
                    help="functions you suspect are now orphaned")
    args = ap.parse_args()

    funcs = load_funcs(args.file)
    suspects = set(args.suspects)
    for root in args.roots:
        if root not in funcs:
            print(f"{root}: NOT FOUND in {args.file}")
            continue
        reach = reachable(funcs, root)
        hits = sorted(suspects.intersection(reach))
        status = "ORPHANED (safe)" if not hits else "STILL REACHABLE"
        print(f"{root}: reachable_defs={len(reach)} suspect_refs={hits} -> {status}")


if __name__ == "__main__":
    main()
