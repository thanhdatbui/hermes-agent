#!/usr/bin/env python3
"""Lint executable contracts inside an implementation-plan Markdown file.

Checks two failure classes that prose reviews routinely miss:
1. RED pytest nodes are actually executed from the same module in Verification.
2. A plan declaring Git-Bash execution does not use PowerShell backtick line
   continuations in command fences or disguise Git-Bash commands as PowerShell.

Usage:
    python scripts/validate_plan_execution_contract.py path/to/plan.md

Exit 0 = no blocking inconsistency. Exit 1 = blocking findings printed.
"""

from __future__ import annotations

import argparse
import re
from collections import defaultdict
from pathlib import Path

NODE_RE = re.compile(
    r"(?P<module>[A-Za-z0-9_./\\ -]+?\.py)::(?P<node>test_[A-Za-z0-9_]+)"
)
MODULE_RE = re.compile(r"(?P<module>[A-Za-z0-9_./\\ -]+?\.py)(?!::)")
HEADING_RE = re.compile(r"^#{1,6}\s+")
BOLD_LABEL_RE = re.compile(r"^\*\*(?P<label>[^*]+)\*\*")


def _norm_module(value: str) -> str:
    return value.strip(" `\t\r\n,;()[]").replace("\\", "/")


def _section_label(line: str) -> str | None:
    match = BOLD_LABEL_RE.match(line.strip())
    if not match:
        return None
    return match.group("label").strip().lower()


def _collect_contracts(lines: list[str]) -> tuple[set[tuple[str, str]], set[tuple[str, str]], set[str]]:
    red_nodes: set[tuple[str, str]] = set()
    verify_nodes: set[tuple[str, str]] = set()
    verify_modules: set[str] = set()
    mode: str | None = None
    in_fence = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence

        label = _section_label(line)
        if label is not None:
            if label.startswith("red"):
                mode = "red"
            elif label.startswith("verification") or label.startswith("verify"):
                mode = "verify"
            elif mode is not None:
                mode = None
        elif HEADING_RE.match(stripped):
            mode = None

        if mode not in {"red", "verify"}:
            continue

        nodes_on_line: list[tuple[str, str]] = []
        for match in NODE_RE.finditer(line):
            item = (_norm_module(match.group("module")), match.group("node"))
            nodes_on_line.append(item)
            if mode == "red":
                red_nodes.add(item)
            else:
                verify_nodes.add(item)

        if mode == "verify" and (in_fence or stripped.startswith("-")):
            masked = line
            for module, node in nodes_on_line:
                masked = masked.replace(f"{module}::{node}", "")
                masked = masked.replace(f"{module.replace('/', chr(92))}::{node}", "")
            for match in MODULE_RE.finditer(masked):
                module = _norm_module(match.group("module"))
                if module:
                    verify_modules.add(module)

    return red_nodes, verify_nodes, verify_modules


def _shell_errors(lines: list[str], text: str) -> list[str]:
    errors: list[str] = []
    declares_git_bash = bool(re.search(r"Git-Bash|git bash", text, re.IGNORECASE))
    if not declares_git_bash:
        return errors

    in_fence = False
    fence_lang = ""
    fence_start = 0
    fence_lines: list[tuple[int, str]] = []

    def inspect_fence() -> None:
        if not fence_lines:
            return
        commandish = any(
            re.search(r"(^|\s)(/d/|git\s|python(?:\.exe)?\s|pytest\s|powershell\.exe\s)", line)
            for _, line in fence_lines
        )
        if not commandish:
            return
        for number, line in fence_lines:
            if line.rstrip().endswith("`"):
                errors.append(
                    f"line {number}: PowerShell backtick continuation inside a plan "
                    "whose command context is Git-Bash; use POSIX '\\' or invoke "
                    "powershell.exe explicitly with a self-contained -Command argument"
                )
        if fence_lang.lower() in {"powershell", "ps1"}:
            has_msys_command = any("/d/" in line for _, line in fence_lines)
            explicitly_invokes_powershell = any("powershell.exe" in line.lower() for _, line in fence_lines)
            if has_msys_command and not explicitly_invokes_powershell:
                errors.append(
                    f"line {fence_start}: fence is labelled {fence_lang!r} but uses an "
                    "MSYS /d/... command without explicitly invoking powershell.exe"
                )

    for number, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("```"):
            if not in_fence:
                in_fence = True
                fence_start = number
                fence_lang = stripped[3:].strip()
                fence_lines = []
            else:
                inspect_fence()
                in_fence = False
                fence_lang = ""
                fence_lines = []
            continue
        if in_fence:
            fence_lines.append((number, line))

    if in_fence:
        errors.append(f"line {fence_start}: unterminated Markdown code fence")
    return errors


def lint(path: Path) -> int:
    raw = path.read_bytes()
    text = raw.decode("utf-8")
    lines = text.splitlines()
    red_nodes, verify_nodes, verify_modules = _collect_contracts(lines)
    errors = _shell_errors(lines, text)

    by_name: dict[str, set[str]] = defaultdict(set)
    for module, node in verify_nodes:
        by_name[node].add(module)

    for module, node in sorted(red_nodes):
        if (module, node) in verify_nodes or module in verify_modules:
            continue
        other_modules = sorted(by_name.get(node, set()))
        if other_modules:
            errors.append(
                f"RED node {module}::{node} is verified under different module(s): "
                + ", ".join(other_modules)
            )
        else:
            errors.append(f"RED node is not executed by its Verification block: {module}::{node}")

    verification_only = sorted(verify_nodes - red_nodes)
    print(f"plan={path.resolve()}")
    print(f"bytes={len(raw)} lines={len(lines)} red_nodes={len(red_nodes)} verify_nodes={len(verify_nodes)}")
    if verification_only:
        print("INFO verification-only exact nodes (must be intentional regression anchors):")
        for module, node in verification_only:
            print(f"  {module}::{node}")

    if errors:
        print("BLOCKING FINDINGS:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("PLAN_EXECUTION_CONTRACT: PASS")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("plan", type=Path)
    args = parser.parse_args()
    return lint(args.plan)


if __name__ == "__main__":
    raise SystemExit(main())
