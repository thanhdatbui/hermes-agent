#!/usr/bin/env python3
"""Set agent.disabled_toolsets on a Hermes PROFILE config (never the default profile).

Why this script exists: `hermes config set agent.disabled_toolsets '[...]'` does NOT
work — set_config_value (hermes_cli/config.py) only coerces bool/int/float, so a JSON
string is stored as a plain string and the runtime iterates it character-by-character
(a silent no-op). This python-yaml fallback is the sanctioned path for profile configs.

Usage:
    python set_disabled_toolsets.py <profile_config_path> [toolset1 toolset2 ...]

With no toolset args, uses the verified read-only coordinator lockdown list.
Exit code 0 only if the written list reloads identically.
"""
import sys
import yaml

DEFAULT_DISABLED = [
    "file", "terminal", "code_execution", "computer_use", "cronjob", "project",
    "memory", "image_gen", "kanban",
]

if len(sys.argv) < 2:
    print(__doc__)
    sys.exit(2)

CFG = sys.argv[1]
DISABLED = sys.argv[2:] or DEFAULT_DISABLED

with open(CFG, encoding="utf-8") as f:
    cfg = yaml.safe_load(f) or {}
assert isinstance(cfg, dict), "config is not a mapping"
agent = cfg.setdefault("agent", {})
assert isinstance(agent, dict), "agent section is not a mapping"
agent["disabled_toolsets"] = list(DISABLED)

with open(CFG, "w", encoding="utf-8") as f:
    yaml.safe_dump(cfg, f, sort_keys=False, allow_unicode=True, default_flow_style=False)

with open(CFG, encoding="utf-8") as f:
    check = yaml.safe_load(f)
assert check["agent"]["disabled_toolsets"] == list(DISABLED), "reload mismatch!"
print(f"OK: agent.disabled_toolsets = {check['agent']['disabled_toolsets']}")
