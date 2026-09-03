# Secondary Machine Hermes Model & Proxy Sync Recipe

When configuring a secondary Hermes instance (e.g. Admin PC) to route LLM queries through the primary host's (Kibe PC) OmniRoute & 9Router proxies:

## Target Machine Self-Configuration Prompt

Send this prompt directly to the secondary machine's Hermes / Telegram bot:

```text
Bạn là Hermes Agent trên máy Admin. Hãy đồng bộ cấu hình Model, Providers, Context Compression và Fallback Chain 3 tầng của Worker cho khớp 100% với máy Kibe (IP: 192.168.110.123).

Hãy chạy script Python sau để cập nhật trực tiếp:

```python
import os, re, yaml
from pathlib import Path

hermes_dir = Path(os.path.expandvars(r"%LOCALAPPDATA%\hermes"))
env_path = hermes_dir / ".env"
config_path = hermes_dir / "config.yaml"

# 1. Nạp API Key vào .env
env_content = env_path.read_text(encoding="utf-8") if env_path.exists() else ""
keys_to_add = {
    "OMNIROUTE_API_KEY": "***",
    "NINEROUTER_API_KEY": "***",
    "OMNIROUTE_BASE_URL": "http://192.168.110.123:20129/v1"
}
for k, v in keys_to_add.items():
    if f"{k}=" in env_content:
        env_content = re.sub(rf"^{k}=.*$", f"{k}={v}", env_content, flags=re.M)
    else:
        env_content += f"\n{k}={v}"
env_path.write_text(env_content.strip() + "\n", encoding="utf-8")

# 2. Cập nhật config.yaml
cfg = {}
if config_path.exists():
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}

cfg["model"] = {
    "default": "ag-gemini-pool-3",
    "provider": "omni",
    "persist_switch_by_default": False,
    "context_length": 1000000
}

cfg["providers"] = {
    "omni": {
        "api": "http://192.168.110.123:20129/v1",
        "default_model": "ag-gemini-pool-3",
        "discover_models": False,
        "key_env": "OMNIROUTE_API_KEY",
        "models": {
            "ag-gemini-pool-3": {},
            "ag-claude": {},
            "ag-opus": {},
            "omni-free": {}
        },
        "transport": "chat_completions"
    },
    "9router": {
        "api": "http://192.168.110.123:20128/v1",
        "default_model": "gpt-5.6-luna",
        "key_env": "NINEROUTER_API_KEY",
        "transport": "chat_completions"
    }
}

cfg["custom_providers"] = [
    {
        "name": "9router",
        "base_url": "http://192.168.110.123:20128/v1",
        "key_env": "NINEROUTER_API_KEY",
        "api_key": "***",
        "api_mode": "chat_completions",
        "discover_models": False,
        "model": "ag/gemini-3.7-flash-high",
        "models": {
            "ag/gemini-3.7-flash-high": {"context_length": 1048576},
            "ag/claude-sonnet-4-6": {"context_length": 1000000},
            "ag/claude-opus-4-6-thinking": {"context_length": 1000000},
            "deepseek-v4-flash": {"context_length": 1048576},
            "deepseek-v4-pro": {"context_length": 1048576},
            "gpt-5.6-luna": {"context_length": 256000},
            "gpt-5.6-sol": {"context_length": 256000},
            "gpt-5.6-terra": {"context_length": 256000},
            "opencode-audit": {"context_length": 1048576},
            "opencode-free": {"context_length": 1048576},
            "openrouter-free": {"context_length": 1048576},
            "plan-review": {"context_length": 256000},
            "plan-review-hard": {"context_length": 256000},
            "worker": {"context_length": 1048576}
        }
    }
]

cfg["model_catalog"] = {
    "excluded_providers": ["anthropic"]
}

if "agent" not in cfg or not isinstance(cfg["agent"], dict):
    cfg["agent"] = {}
cfg["agent"]["image_input_mode"] = "native"
cfg["agent"]["reasoning_effort"] = "high"
cfg["agent"]["reasoning_overrides"] = {
    "ag/claude-sonnet-4-6": "high",
    "deepseek-v4-flash": "high",
    "gpt-5.6-luna": "high",
    "oc/deepseek-v4-flash-free": "high",
    "oc/hy3-free": "high",
    "opencode-audit": "high"
}

cfg["auxiliary"] = {
    "compression": {
        "provider": "omni",
        "model": "ag-gemini-pool-3",
        "fallback_chain": [
            {"model": "gpt-5.6-luna", "provider": "9router"}
        ]
    }
}

# Subagent Worker 3 tầng: T1 (omni: ag-gemini-pool-3) -> T2 (9router: worker) -> T3 (omni: omni-free)
cfg["delegation"] = {
    "provider": "omni",
    "model": "ag-gemini-pool-3",
    "reasoning_effort": "high",
    "max_concurrent_children": 4,
    "max_iterations": 100
}

cfg["fallback_providers"] = [
    {
        "provider": "custom:9router",
        "model": "worker"
    },
    {
        "provider": "omni",
        "model": "omni-free"
    }
]

with open(config_path, "w", encoding="utf-8") as f:
    yaml.safe_dump(cfg, f, allow_unicode=True, sort_keys=False)

print("SUCCESS: Synced config and .env with Kibe!")
```

Sau khi chạy xong, hãy chạy `hermes doctor` kiểm tra và báo cáo kết quả.
```

## Key Configuration Invariants

- **OmniRoute (:20129):** Primary gateway for pool combos (`ag-gemini-pool-3` with 13 Antigravity accounts).
- **Subagent Worker Fallback Chain (3 Levels):** 
  - Primary: `delegation.provider: omni`, `delegation.model: ag-gemini-pool-3`.
  - Fallback Level 1: `fallback_providers[0]`: `custom:9router` with combo `worker`.
  - Fallback Level 2: `fallback_providers[1]`: `omni` with combo `omni-free`.
- **Context Bloat vs. Telegram Silent UI:** Telegram suppression of intermediate turns (`[SILENT]` / `tool_progress: false`) is only UI filtering; executing multi-step tools (>3 steps) directly in the parent loop bloats parent context and degrades model reasoning. Long/heavy tasks must be delegated via `delegate_task` to `delegation.model` so intermediate tool turns stay within isolated subagent contexts.
- **Auxiliary Compression:** `auxiliary.compression` routes to `ag-gemini-pool-3` (1M context, threshold 0.3 = 300k tokens) with fallback to `gpt-5.6-luna` via `9router`.
- **9Router (:20128):** Dedicated fallback provider for code review combos (`plan-review`, `plan-review-hard`), auxiliary compression fallback (`gpt-5.6-luna`), and the exact `worker` combo.
- **`custom_providers` for Telegram `/model` Picker:** Defining the `custom_providers` block with discrete model lists and explicit `context_length` values ensures the `/model` inline menu matches across all farm nodes.
- **Excluded Providers:** `model_catalog.excluded_providers: ["anthropic"]` prevents unauthenticated provider entries from surfacing in the model picker.
- **Multimodal / Vision:** Set `agent.image_input_mode: native` so screenshots and UI verification payloads stream directly without legacy vision tool crashes.
