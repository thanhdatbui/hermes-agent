# 9Router Model Inventory & Hermes Integration

## 1. Querying Live 9Router Models
9Router exposes `/v1/models` requiring bearer authentication with `NINEROUTER_API_KEY`:

```python
import urllib.request, json, os

key = os.environ.get("NINEROUTER_API_KEY")
req = urllib.request.Request("http://127.0.0.1:20128/v1/models")
req.add_header("Authorization", f"Bearer {key}")
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode("utf-8"))
    models = [m["id"] for m in data.get("data", [])]
```

## 2. Model Categories & -review Quota Family
Models exposed by 9Router fall into 4 main categories:
1. **Combos (`combos` table in SQLite):** User-defined virtual fallbacks (`worker`, `opencode-free`, `openrouter-free`, `plan-review`, etc.).
2. **Antigravity (`ag/*`):** Google OAuth models (`ag/gemini-3.7-flash-high`, `ag/claude-sonnet-4-6`, `ag/claude-opus-4-6-thinking`).
3. **Codex (`cx/*`):** OpenAI Codex OAuth models (`cx/gpt-5.6-sol`, `cx/gpt-5.6-terra`, `cx/gpt-5.6-luna`).
   - **What `-review` models are (`quotaFamily: "review"`):** Models like `cx/gpt-5.6-sol-review` or `cx/gpt-5.6-terra-review` map upstream directly to their base model (`gpt-5.6-sol`, `gpt-5.6-terra`). 9Router adds `-review` variants to send headers targeting ChatGPT Plus/Pro's dedicated Code Review quota pool instead of regular chat quota.
4. **OpenRouter Free (`openrouter/*`):** Free-tier models routed via OpenRouter connection.

## 3. Free Model Aggregation Pattern (Combos)
Instead of exposing dozens of individual, verbose free-tier models that clutter Telegram/CLI pickers and fail on 429 rate limits, group them into auto-rotating combos:

- **`opencode-free`:** Gathers all active OpenCode free-tier models (`oc/deepseek-v4-flash-free`, `oc/x-preview-f-free`, `oc/mimo-v2.5-free`, `oc/hy3-free`, `oc/nemotron-3-ultra-free`, `oc/nemotron-3.5-lightning-free`, `oc/laguna-s-2.1-free`, `oc/big-pickle`, `oc/muse-spark-1.2-contributor-free`).
- **`openrouter-free`:** Gathers OpenRouter free models (`openrouter/cohere/north-mini-code:free`, `openrouter/nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free`, `openrouter/nvidia/nemotron-3-super-120b-a12b:free`, `openrouter/nvidia/nemotron-3-ultra-550b-a55b:free`, `openrouter/google/gemma-4-26b-a4b-it:free`, etc.).
- **Suppressing Individual OpenRouter Models from `/v1/models`:**
  - Individual custom/fetched OpenRouter models get saved into SQLite `kv` table (`C:\Users\Kibe\AppData\Roaming\9router\db\data.sqlite`).
  - To prune all individual `openrouter/*` models and keep only the virtual combo `openrouter-free`, purge the entries from `kv`:
    ```sql
    DELETE FROM kv WHERE scope="customModels" AND key LIKE "openrouter|%";
    ```
  - `/v1/models` updates dynamically on the next request without needing server restart.

## 4. Pruning Built-in Provider Models in 9Router Server Bundles
Built-in provider models (such as legacy Codex `cx/gpt-5.3*`, `cx/gpt-5.4*`, `cx/gpt-5.5*`, `*-review`, and unused Antigravity `ag/gemini-3.5*`, `ag/gemini-3.6*`, `ag/gemini-3-flash*`) are baked into Next.js server chunks at:
`C:\Users\Kibe\AppData\Roaming\npm\node_modules\9router\app\.next-cli-build\server\chunks\` (specifically `4953.js`, `5285.js`, `7011.js`).

**Cleanup Procedure:**
1. Backup target bundle chunks to `AppData/Roaming/9router_bundle_backup/`.
2. Edit target chunks to remove unwanted model objects from the provider's `models:[...]` array (under `id:"codex"`, `id:"antigravity"`, etc.).
3. Validate syntax across all modified files: `node --check <chunk.js>`.
4. Kill the active Node.js server process (`taskkill -F -PID <pid>`); the supervisor watchdog (`9router_watchdog.ps1`) will restart Node.js automatically within ~3-5s.
5. Verify `/v1/models` reflects the pruned catalog.
6. Update `config.yaml` `custom_providers[0].models` in Hermes so the CLI/Telegram model picker reflects the clean model dictionary.

## 4. Hermes Main Model & Worker (Delegation) Configuration
Set canonical model configurations via Hermes CLI commands:

- **Main Model:** `hermes config set model.default ag/gemini-3.7-flash-high`
- **Worker (Subagent/Delegation):**
  - `hermes config set delegation.model worker`
  - `hermes config set delegation.provider custom:9router`
- **Auxiliary Vision:** `hermes config set auxiliary.vision.model ag/gemini-3.7-flash-low`
