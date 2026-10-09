# Codex CLI with OmniRoute (:20129) & 9Router (:20128) for GPT Sol

## Protocol & Wire API Requirements

As of Codex CLI v0.145+, `wire_api = "chat"` has been deprecated/removed. Codex strictly requires:
```toml
wire_api = "responses"
```
Both OmniRoute (`http://localhost:20129/v1`) and 9Router (`http://localhost:20128/v1`) implement `/v1/responses` compliant with OpenAI Responses API SSE streaming (`response.created`, `response.output_item.added`, `response.output_text.delta`, `response.completed`).

## Provider Configuration in `~/.codex/config.toml`

To support both 9Router and OmniRoute, define providers under `[model_providers]`:

```toml
[model_providers.9router]
name = "9Router"
base_url = "http://localhost:20128/v1"
env_key = "NINEROUTER_API_KEY"
wire_api = "responses"

[model_providers.omniroute]
name = "OmniRoute"
base_url = "http://localhost:20129/v1"
env_key = "NINEROUTER_API_KEY"
wire_api = "responses"
```

## Sol Model Availability Matrix

- **OmniRoute (:20129)**:
  - `chatgpt-web/gpt-5.6-sol-high` (and tiers `-pro`, `-medium`, `-instant`): Active & functional over `/v1/responses`.
  - `gpt-5.6-sol` / `cx/gpt-5.6-sol`: May hit upstream cooldown (`model_cooldown`) on specific credentials.
- **9Router (:20128)**:
  - `gpt-5.6-sol`: Active & functional via vertex/gateway combo over `/v1/responses`.

## Execution Patterns

### 1. One-Shot via `-c` flags (No base config pollution)
```bash
# OmniRoute (:20129)
codex exec --skip-git-repo-check \
  -c 'model_providers.omniroute.name="OmniRoute"' \
  -c 'model_providers.omniroute.base_url="http://localhost:20129/v1"' \
  -c 'model_providers.omniroute.env_key="NINEROUTER_API_KEY"' \
  -c 'model_providers.omniroute.wire_api="responses"' \
  -c 'model_provider="omniroute"' \
  -m chatgpt-web/gpt-5.6-sol-high \
  --sandbox read-only "task"

# 9Router (:20128)
codex exec --skip-git-repo-check -c 'model_provider="9router"' -m gpt-5.6-sol --sandbox read-only "task"
```

### 2. Dedicated Profile via `-p` (Cleanest for CLI)
Create `~/.codex/sol-omni.config.toml`:
```toml
model = "chatgpt-web/gpt-5.6-sol-high"
model_provider = "omniroute"
model_reasoning_effort = "high"
```
Run with:
```bash
codex exec -p sol-omni --sandbox read-only "task"
```

## Critical Rules & Pitfalls
- **Do not modify base `model =` in `~/.codex/config.toml`**: The Codex Desktop App reads the base config file. Changing base `model` will silently alter the default model across desktop chats and can cause UI mismatch or startup errors.
- **`--skip-git-repo-check`**: Codex CLI refuses to run outside a git repo unless `--skip-git-repo-check` is passed.
