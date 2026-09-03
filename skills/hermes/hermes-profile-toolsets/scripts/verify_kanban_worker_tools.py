#!/usr/bin/env python3
"""Verify a dispatcher WORKER profile's kanban lifecycle tools at runtime.

Unlike verify_profile_tools.py (COORDINATOR posture — kanban must be ABSENT),
this asserts the worker posture: with HERMES_KANBAN_TASK set, the kanban
toolset is auto-appended by _compute_tool_definitions (model_tools.py), so the
profile's kanban lifecycle tools must be PRESENT. This is the ONLY path that
models the re-add — _get_platform_tools + resolve_toolset do not.

Usage:
    python verify_kanban_worker_tools.py <profile_config_path> [profile_config_path ...]

Exit code 0 = worker lockdown intact (kanban lifecycle present, delegate/memory absent).
"""
import os
import sys

HERMES_AGENT_DIR = os.environ.get(
    "HERMES_AGENT_DIR",
    r"C:\Users\Kibe\AppData\Local\hermes\hermes-agent",
)

if len(sys.argv) < 2:
    print(__doc__)
    sys.exit(2)

sys.path.insert(0, HERMES_AGENT_DIR)

import yaml
from hermes_cli.config import load_config
from hermes_cli.tools_config import _get_platform_tools
from model_tools import get_tool_definitions

os.environ["HERMES_KANBAN_TASK"] = "1"  # model dispatcher-spawned worker context

ok = True
for arg in sys.argv[1:]:
    home = os.path.dirname(arg)
    os.environ["HERMES_HOME"] = home
    cfg = load_config()
    enabled = sorted(_get_platform_tools(cfg, "cli"))
    disabled = (cfg.get("agent") or {}).get("disabled_toolsets") or []
    defs = get_tool_definitions(
        enabled_toolsets=enabled, disabled_toolsets=disabled, quiet_mode=True
    )
    names = sorted(d["function"]["name"] for d in defs)
    print(f"[{os.path.basename(home)}]")
    print(f"  enabled(cli)={enabled}")
    print(f"  disabled_toolsets={disabled}")
    print(f"  total_tools={len(names)}")
    print(f"  kanban_in_disabled={'kanban' in disabled}")

    must_be_PRESENT = [
        "kanban_complete", "kanban_block", "kanban_heartbeat", "kanban_create",
    ]
    must_be_ABSENT = ["delegate_task", "memory"]
    prof_ok = True
    print("  --- kanban lifecycle must be PRESENT ---")
    for n in must_be_PRESENT:
        present = n in names
        prof_ok &= present
        print(f"    {n}: {'present (ok)' if present else 'FAIL-MISSING!'}")
    print("  --- delegate/memory must be ABSENT ---")
    for n in must_be_ABSENT:
        present = n in names
        prof_ok &= not present
        print(f"    {n}: {'FAIL-PRESENT!' if present else 'absent (ok)'}")
    print(f"  VERDICT: {'PASS' if prof_ok else 'FAIL'}")
    ok &= prof_ok

print("ALL OK:", ok)
sys.exit(0 if ok else 1)
