# Hermes picker cleanup and session-only model switching

## Layered verification

When wiring a 9Router model into Hermes, verify three separate layers:

1. **Upstream catalog:** query the upstream provider and confirm canonical model ID and pricing.
2. **9Router route:** test `http://127.0.0.1:20128/v1`; the route may require a prefix such as `openrouter/stealth/ox-alpha` even when upstream uses `stealth/ox-alpha`.
3. **Hermes picker:** with `discover_models: false`, only the custom provider's explicit `models:` mapping appears. Add the exact callable 9Router route name to that mapping.

## Hide a provider without deleting credentials

To remove an unwanted provider from Hermes `/model` without logging out of another client, use the picker exclusion config:

```yaml
model_catalog:
  excluded_providers:
    - anthropic
```

This is a UI/discovery filter, not credential revocation. Never delete `~/.claude/.credentials.json`, `~/.claude.json`, or Claude app credentials merely to hide Anthropic from Hermes. If the installed Hermes picker ignores the config key, fix the picker discovery path to honor it; do not touch the credential files.

For a provider the user explicitly wants removed, remove only its Hermes env/pool/config entries, take a timestamped backup first, then validate YAML and re-list the picker.

## Quota versus route failure

A 404 or empty response from a route can be quota exhaustion rather than permanent model removal. Record the observed response and user intent separately. Removing a no-longer-needed vision route from Hermes' explicit model map is safe, but do not claim the upstream model is unavailable without a fresh upstream check.

## Session-only switching

Hermes supports:

```text
/model <model> --session
/model <model> --global
```

`--session` overrides persistence for the current session; `--global` explicitly saves the default. To make plain `/model <model>` session-only by default, set `model.persist_switch_by_default: false`, then verify the runtime parser and picker behavior.
