# OmniRoute Model Visibility and Quota Display Coupling

## Symptom
On the OmniRoute Provider Limits / Quota dashboard (`/dashboard/quota`), quota progress bars for specific model families (such as Gemini) disappear completely, leaving only unrelated models (e.g., Claude Opus / Sonnet), even though API requests to those models succeed normally.

## Root Cause
OmniRoute frontend couples model catalog visibility with quota row rendering:
1. When models are hidden in the Model Catalog (via UI `visibility_off` or bulk "Hide all" to clean up bloated model lists), OmniRoute saves `{ id: modelId, isHidden: true }` in `key_value` table (namespace: `modelCompatOverrides`, key: `<provider>`).
2. Hook `useVisibleQuotaData` on `/dashboard/quota` fetches `/api/provider-models?provider=<provider>`, collects all models where `isHidden === true`, and executes `filterHiddenModelQuotas()`.
3. Upstream Google Antigravity (`retrieveUserQuota`) aggregates quotas into canonical buckets:
   - `gemini-3.1-flash-lite` (used for Pro/Business Flash pool)
   - `gemini-3.7-flash-tiered` (used for Starter/Free Flash pool)
   - `gemini-pro-agent` (used for Pro tiers)
4. If an agent or operator hides `gemini-3.7-flash-tiered` or `gemini-3.1-flash-lite`, the quota dashboard hides the quota rows for those accounts completely.

## Safe Restoration Pattern (No DB Surgery / No Process Restart)
Do not execute raw SQLite writes. Instead, call OmniRoute's administrative REST API directly:

```python
import urllib.request
import json

url = 'http://localhost:20129/api/provider-models?provider=antigravity'
models_to_unhide = [
    'gemini-3.8-flash-tiered', 'gemini-3.8-flash-high', 'gemini-3.8-flash-medium', 'gemini-3.8-flash-low',
    'gemini-3.7-flash-tiered', 'gemini-3.7-flash-high', 'gemini-3.7-flash-medium', 'gemini-3.7-flash-low',
    'gemini-3.1-flash-lite', 'gemini-pro-agent', 'gemini-3.1-pro-low', 'gemini-3.1-pro-high'
]
payload = json.dumps({'modelIds': models_to_unhide, 'isHidden': False}).encode()
req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'}, method='PATCH')
with urllib.request.urlopen(req) as resp:
    result = json.load(resp)
    print("Updated:", result.get("updated"))
```

## Gemini 3.8 Flash Quota Pool Mechanics
- The upstream Google Antigravity backend tracks Flash requests under a unified family pool.
- Pro/Business accounts surface this bucket as `gemini-3.1-flash-lite` (5-hour and weekly reset windows).
- Starter accounts surface this bucket as `gemini-3.7-flash-tiered`.
- When routing combo requests to `antigravity/gemini-3.8-flash-tiered` (e.g. `ag-gemini-pool-3`), token usage is drawn directly from this shared Flash quota bucket.
