#!/usr/bin/env python3
"""Verify a Hermes profile's ACTUAL tool list using the runtime resolver.

This is the real proof a lockdown works — it runs the same code the CLI uses
(_get_platform_tools + resolve_toolset), NOT a grep of config.yaml. A YAML list
could be syntactically present but wrong (e.g. string instead of list, wrong
names), and only resolution-level verification catches that.

Usage:
    python verify_profile_tools.py <profile_config_path>

Assumes HERMES_AGENT_DIR (default: %LOCALAPPDATA%\\hermes\\hermes-agent) contains
hermes_cli/ and toolsets.py. Run with the Hermes venv python so yaml + hermes_cli
import cleanly. Exit code 0 = lockdown intact.
"""
import sys
import os

HERMES_AGENT_DIR = os.environ.get(
    "HERMES_AGENT_DIR",
    r"C:\Users\Kibe\AppData\Local\hermes\hermes-agent",
)
HERMES_HOME = os.environ.get("HERMES_HOME", r"C:\Users\Kibe\AppData\Local\hermes")

if len(sys.argv) < 2:
    print(__doc__)
    sys.exit(2)
CFG = sys.argv[1]

sys.path.insert(0, HERMES_AGENT_DIR)
os.environ.setdefault("HERMES_HOME", HERMES_HOME)

import yaml
from hermes_cli.tools_config import _get_platform_tools
from toolsets import resolve_toolset

cfg = yaml.safe_load(open(CFG, encoding="utf-8"))
enabled = _get_platform_tools(cfg, "cli")
print("ENABLED TOOLSETS:", sorted(enabled))
print("DISABLED (config):", (cfg.get("agent") or {}).get("disabled_toolsets"))

tools = set()
for ts in enabled:
    tools.update(resolve_toolset(ts))

must_be_ABSENT = [
    "write_file", "patch", "terminal", "process", "execute_code", "computer_use",
    "cronjob", "project_create", "project_switch", "memory", "image_generate",
    "kanban_create", "kanban_complete", "kanban_block", "kanban_comment",
    "kanban_link", "kanban_unblock", "kanban_apply_expert_repair_plan",
    "kanban_record_plan_audit_verdict", "kanban_create_worker_escalation",
    "kanban_apply_plan_audit_actuation", "kanban_heartbeat",
]
must_be_PRESENT = [
    "delegate_task", "session_search", "skill_view", "skills_list", "web_search",
    "web_extract", "browser_navigate", "browser_snapshot", "vision_analyze",
    "todo", "clarify", "text_to_speech",
]
# Expected trade-off of blocking the `file` toolset (read_file/search_files ride along)
expected_ABSENT_tradeoff = ["read_file", "search_files"]

ok = True
print("\n--- MUST BE ABSENT (write/exec) ---")
for n in must_be_ABSENT:
    present = n in tools
    ok &= not present
    print(f"  {n}: {'FAIL-PRESENT!' if present else 'absent (ok)'}")
print("\n--- EXPECTED TRADE-OFF ABSENT (file toolset) ---")
for n in expected_ABSENT_tradeoff:
    print(f"  {n}: {'present (unexpected)' if n in tools else 'absent (expected trade-off)'}")
print("\n--- MUST BE PRESENT (read/delegate) ---")
for n in must_be_PRESENT:
    present = n in tools
    ok &= present
    print(f"  {n}: {'present (ok)' if present else 'FAIL-MISSING!'}")
print("\nTOTAL TOOLS:", len(tools))
print("VERDICT:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
