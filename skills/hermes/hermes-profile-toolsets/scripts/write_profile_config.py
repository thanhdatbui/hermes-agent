#!/usr/bin/env python3
"""Author a minimal STANDALONE Hermes profile config.yaml via utils.atomic_yaml_write.

Why: `hermes profile create <name> --no-skills --no-alias --description "..."` creates
the profile DIR but NO config.yaml (verified v0.18.2). Minimal worker-lane profiles
(no coordinator clone) need a self-contained config written from scratch. This script
writes exactly the fields a minimal profile needs; `load_config` deep-merges the rest
from DEFAULT_CONFIG (hermes_cli/config.py:7093-7107), so missing keys fall back safely.

Usage:
    python write_profile_config.py <profile_name> <model_name> [base_url] [key_env_name]

    profile_name : must already exist under %LOCALAPPDATA%\\hermes\\profiles\\<name>
    model_name   : e.g. deepseek-v4-pro / deepseek-v4-flash
    base_url     : default http://127.0.0.1:20128/v1  (9router)
    key_env_name : default NINEROUTER_API_KEY  (env-var NAME only — NEVER a secret)

Writes: _config_version, model.provider=custom:<name-from-url>, model.default,
custom_providers (dict-shape models), platform_toolsets.cli=[file,terminal,code_execution,no_mcp],
agent.disabled_toolsets (broad lockdown that deliberately KEEPS file/terminal/code_execution).

Exit 0 only if read-back verification passes (model, provider, custom_providers,
cli toolsets, disabled list, no inline api_key, no fallback_providers, no mcp_servers).
"""
import sys
import hashlib
import yaml

DEFAULT_DISABLED = [
    "delegation", "browser", "computer_use", "cronjob", "memory", "web",
    "session_search", "clarify", "skills", "image_gen", "video", "video_gen",
    "x_search", "homeassistant", "spotify", "discord", "discord_admin",
    "project", "kanban",
]
# NOTE: file, terminal, code_execution intentionally NOT in the disabled list.

DEFAULT_BASE_URL = "http://127.0.0.1:20128/v1"
DEFAULT_KEY_ENV = "NINEROUTER_API_KEY"


def profile_config(model_name: str, base_url: str, key_env: str) -> dict:
    provider_name = base_url.rstrip("/").split("/")[-2] if "/v1" in base_url else "custom"
    return {
        "_config_version": 33,
        "model": {"provider": f"custom:{provider_name}", "default": model_name},
        "custom_providers": [
            {
                "name": provider_name,
                "base_url": base_url,
                "key_env": key_env,
                "api_mode": "chat_completions",
                "discover_models": False,
                "model": model_name,
                "models": {model_name: {"context_length": 1048576}},
            }
        ],
        "platform_toolsets": {"cli": ["file", "terminal", "code_execution", "no_mcp"]},
        "agent": {"disabled_toolsets": list(DEFAULT_DISABLED)},
    }


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    name = sys.argv[1]
    model = sys.argv[2]
    base_url = sys.argv[3] if len(sys.argv) > 3 else DEFAULT_BASE_URL
    key_env = sys.argv[4] if len(sys.argv) > 4 else DEFAULT_KEY_ENV

    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # repo root for utils

    cfg_path = Path(r"C:\Users\Kibe\AppData\Local\hermes\profiles") / name / "config.yaml"
    if not cfg_path.parent.is_dir():
        print(f"FAIL: profile dir missing: {cfg_path.parent}")
        return 1

    from utils import atomic_yaml_write  # repo-sanctioned structured write

    data = profile_config(model, base_url, key_env)
    atomic_yaml_write(cfg_path, data, sort_keys=False)
    after = cfg_path.read_bytes()
    check = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))

    ok = (
        check["model"]["default"] == model
        and check["model"]["provider"] == f"custom:{base_url.rstrip('/').split('/')[-2] if '/v1' in base_url else 'custom'}"
        and isinstance(check.get("custom_providers"), list)
        and len(check["custom_providers"]) == 1
        and check["custom_providers"][0]["name"] == (base_url.rstrip("/").split("/")[-2] if "/v1" in base_url else "custom")
        and check["custom_providers"][0]["key_env"] == key_env
        and check["custom_providers"][0]["discover_models"] is False
        and check["custom_providers"][0]["api_mode"] == "chat_completions"
        and "api_key" not in check["custom_providers"][0]
        and check["platform_toolsets"]["cli"] == ["file", "terminal", "code_execution", "no_mcp"]
        and check["agent"]["disabled_toolsets"] == DEFAULT_DISABLED
        and "fallback_providers" not in check.get("model", {})
        and "mcp_servers" not in check
    )
    print(f"{name}: all_ok={ok} sha256={hashlib.sha256(after).hexdigest()} bytes={len(after)}")
    if not ok:
        print("model:", check.get("model"))
        print("custom_providers:", check.get("custom_providers"))
        print("cli:", check.get("platform_toolsets", {}).get("cli"))
        print("disabled:", check.get("agent", {}).get("disabled_toolsets"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
