# Hermes Fallback Providers: OmniRoute Direct Fallback (Bypass 9Router)

*User decision 2026-09-04 (Tad Shavershian): "Chỉnh lại lỗi thì fallback qua thẳng omni router bỏ qua 9router đi"*

## Context & Incident Trace

- Primary model: `ag-gemini-pool-3` (via `omni` on `http://127.0.0.1:20129/v1`).
- Problem observed: When the primary model hits an error (rate-limit, 429, or upstream overload), Hermes announced in Telegram:
  `Switched to fallback model: worker via custom:9router -> omni-free via omni`
- Root Cause: `fallback_providers` in `config.yaml` had `worker via custom:9router` placed ahead of `omni-free via omni`. When 9router failed or degraded, Hermes hit a double failure before landing on the working free fallback.
- Policy: Completely remove 9Router from the Hermes fallback chain. All fallback must route directly through OmniRoute.

## Canonical Configuration

### 1. In `~/.hermes/config.yaml` (Windows: `%LOCALAPPDATA%\hermes\config.yaml`):

```yaml
fallback_providers:
  - model: omni-free
    provider: omni
```

### 2. Synchronization Invariant:
Whenever editing Hermes AI tool configs, MUST synchronize template in:
`D:\Taadaa\AI-Tools\config\hermes\hermes_config_template.yaml`

```yaml
fallback_providers:
- model: omni-free
  provider: omni
```

## CLI Verification & Pitfalls

1. **Verify active chain:**
   ```bash
   hermes fallback list
   ```
   Output must show:
   ```text
   Primary:   ag-gemini-pool-3  (via omni)

     Fallback chain (1 entry):
       1. omni-free  (via omni)
   ```

2. **CLI non-interactive pitfall:**
   Running `hermes fallback remove` via stdin piping (e.g. `echo 1 | hermes fallback remove`) fails with `Cancelled — no change.` because `_curses_prompt_choice` in `hermes_cli/setup.py` detects a non-TTY environment and returns -1.
   To programmatically update `fallback_providers`, use `load_config`/`save_config` from `hermes_cli.config` or targeted patch on `config.yaml`.
