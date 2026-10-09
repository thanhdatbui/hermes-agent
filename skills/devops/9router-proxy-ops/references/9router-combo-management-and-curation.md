# 9Router Combo Management & Model Curation

## Overview

9Router (`localhost:20128`) routes requests across CommandCode, OpenRouter, OpenCode, Codex, and Antigravity. Over time, upstream credentials expire (Codex 401, Antigravity 404, OpenRouter free 429), leaving combos polluted with dead models that trigger timeouts or multiple cascading failures.

This reference documents:
1. Managing 9Router combos via live REST API.
2. Latency & health testing for free/worker models.
3. Keeping Hermes `/model` clean via `discover_models: false`.
4. Fallback chain ordering between OmniRoute (`:20129`) and 9Router (`:20128`).

---

## 1. 9Router Combo API (`:20128`)

Combos are stored in SQLite at `C:\Users\Kibe\AppData\Roaming\9router\db\data.sqlite` (`combos` table) and managed live by the Next.js runtime.

- **List combos:**
  ```http
  GET http://127.0.0.1:20128/api/combos
  Authorization: Bearer <NINEROUTER_API_KEY>
  ```
- **Inspect specific combo:**
  ```http
  GET http://127.0.0.1:20128/api/combos/<combo_id>
  Authorization: Bearer <NINEROUTER_API_KEY>
  ```
- **Update combo models & order:**
  ```http
  PUT http://127.0.0.1:20128/api/combos/<combo_id>
  Authorization: Bearer <NINEROUTER_API_KEY>
  Content-Type: application/json

  {
    "name": "openrouter-free",
    "models": [
      "openrouter/nvidia/nemotron-3-super-120b-a12b:free",
      "openrouter/liquid/lfm-2.5-2.6b:free",
      "openrouter/nvidia/nemotron-3-ultra-550b-a55b:free",
      "openrouter/nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free"
    ]
  }
  ```
- **Syncing with repo template:**
  Always export the active config to Git after updating combos:
  ```bash
  python D:/Taadaa/AI-Tools/config/9router/sync_config.py --action export
  ```

---

## 2. Health & Latency Testing Protocol

Before updating any combo, benchmark candidate models directly via `/v1/chat/completions` with a 10s timeout:

```python
import urllib.request, json, time

def test_model(model_name, api_key):
    t0 = time.time()
    payload = json.dumps({
        "model": model_name,
        "messages": [{"role": "user", "content": "1+1="}],
        "max_tokens": 20
    }).encode("utf-8")
    req = urllib.request.Request(
        "http://127.0.0.1:20128/v1/chat/completions",
        data=payload,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            elapsed = time.time() - t0
            raw = resp.read().decode("utf-8")
            # OpenRouter / OpenCode free upstreams may append trailing 'data: [DONE]'
            clean = raw.replace("data: [DONE]", "").strip()
            data = json.loads(clean)
            return True, elapsed, data["choices"][0]["message"].get("content", "")
    except Exception as e:
        return False, time.time() - t0, str(e)
```

### Verified High-Performing Models (Benchmark 2026-09)

| Model | Upstream | Latency | Status |
|---|---|---|---|
| `openrouter/nvidia/nemotron-3-super-120b-a12b:free` | OpenRouter | **0.49s** | Active, Fast |
| `openrouter/liquid/lfm-2.5-2.6b:free` | OpenRouter | **0.74s** | Active, Fast |
| `openrouter/nvidia/nemotron-3-ultra-550b-a55b:free` | OpenRouter | **0.89s** | Active, High Quality |
| `openrouter/nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free` | OpenRouter | **0.96s** | Active |
| `oc/big-pickle` | OpenCode | **0.95s** | Active |
| `cmc/moonshotai/Kimi-K2.6` | CommandCode | **1.17s** | Active, Clean JSON |
| `cmc/deepseek/deepseek-v4-flash` | CommandCode | **1.38s** | Active, Clean JSON |
| `oc/laguna-s-2.1-free` | OpenCode | **2.17s** | Active |
| `cmc/stepfun/Step-3.5-Flash` | CommandCode | **2.00s** | Active, Clean JSON |
| `cmc/Qwen/Qwen3.6-Plus` | CommandCode | **2.40s** | Active, Clean JSON |

### Known Dead / Prune Candidates
- Codex models (`cx/gpt-5.6-*`): 401 Unauthorized when accounts expire.
- Antigravity routes on 9Router (`ag/*`): 404 when OAuth active credentials move to OmniRoute (:20129).
- OpenRouter rate-limited: `glm-5.2:free`, `gemma-4-31b-it:free`, `gemma-4-26b-a4b-it:free` (429).
- OpenCode dead: `oc/hy3-free` (401), `oc/x-preview-f-free` (401), `oc/nemotron-3-ultra-free` (timeout).

---

## 3. Hermes `/model` Picker Hygiene

When a provider definition in Hermes `config.yaml` omits `discover_models: false`, Hermes dynamically fetches all models from `/v1/models`. For 9Router, this exposes 29+ raw internal routes (`cx/*`, `ag/*`, `cmc/*`, dead combos), cluttering the Telegram `/model` UI.

### Clean Configuration Pattern

In `~/.hermes/config.yaml` and `D:\Taadaa\AI-Tools\config\hermes\hermes_config_template.yaml`:

```yaml
providers:
  9router:
    api: http://127.0.0.1:20128/v1
    default_model: worker
    discover_models: false
    key_env: NINEROUTER_API_KEY
    models:
      worker: {}
      deepseek-v4-flash: {}
      openrouter-free: {}
      opencode-free: {}
      cmc/moonshotai/Kimi-K2.6: {}
      cmc/deepseek/deepseek-v4-flash: {}
      cmc/Qwen/Qwen3.6-Plus: {}
      cmc/stepfun/Step-3.5-Flash: {}
    transport: chat_completions
```

Setting `discover_models: false` and explicitly enumerating curated models reduces the picker footprint from `9router (29)` to `9router (8)` clean, 100% verified models.

---

## 4. Hermes Fallback Chain Precedence

When primary reasoning/coding models on OmniRoute (`ag-gemini-pool-3` via `:20129`) hit rate limits or upstream errors, the fallback order should prefer OmniRoute free combos first before falling back to 9Router at the very end:

```yaml
fallback_providers:
  - model: omni-free
    provider: omni
  - model: worker
    provider: custom:9router
```

Verify the active fallback chain using:
```bash
hermes fallback list
```
Expected output:
```text
Primary:   ag-gemini-pool-3  (via omni)
Fallback chain (2 entries):
  1. omni-free  (via omni)
  2. worker  (via custom:9router)
```
