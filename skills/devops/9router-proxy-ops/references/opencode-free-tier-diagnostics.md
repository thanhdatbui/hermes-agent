# OpenCode Free Tier Model Diagnostics & Combo Tuning

## Context & Architecture
OmniRoute / 9Router routes free tier queries through OpenCode (`opencode-zen` / `oc/*`) and OpenRouter (`openrouter/free`).

## Model Characteristics & Latency Profiles (OpenCode Zen Tier)

| Model ID | Provider Name | Quality / Intelligence | Latency | Upstream Stability & Behavior |
| :--- | :--- | :--- | :--- | :--- |
| `oc/nemotron-3-ultra-free` | NVIDIA Nemotron 3 Ultra | High (Deep Reasoning, Strong Coding & Logic) | ~8s – 14s | Highly reliable, handles complex reasoning tasks without upstream timeout. |
| `oc/mimo-v2.5-free` | Xiaomi MiMo 2.5 | High (Fast, Strong Vietnamese & Coding) | ~3s – 6s | Very stable, excellent for instruction following. |
| `oc/big-pickle` | Big Pickle (MiMo-based) | High (Clean logic, structured responses) | ~4s – 7s | Very stable fallback. |
| `oc/laguna-s-2.1-free` | Poolside Laguna S 2.1 | Medium-High (Coding specialist) | ~4s – 10s | Occasional 503 (`Endpoint is unavailable`) during traffic surges. |
| `oc/muse-spark-1.2-contributor-free` | Meta Muse Spark 1.2 | Medium (Lightweight Chat / General QA) | ~2s – 4s | Ultra fast, lowest latency, reliable safety net. |
| `oc/nemotron-3.5-lightning-free` | NVIDIA Nemotron 3.5 Lightning | Medium-High (Reasoning) | >250s (Congested) | Heavy server queue on upstream. Causes **HTTP 499 (Request aborted / Gateway timeout at 300s)**. Keep as lowest priority or safety net. |

## Delisted / Unsupported Upstream Free Models (Delist Return Codes)
- `oc/hy3-free` / `opencode/hy3-free`: Delisted (`HTTP 401: Model hy3-free is not supported`). Note: `hy3` on `opencode-go` requires paid OpenCode API key (`HTTP 402`).
- `oc/deepseek-v4-flash-free`: Returns `HTTP 400: Upstream request failed`.
- `oc/north-mini-code-free`: Delisted (`HTTP 401`).

## Tuning `omni-free` Priority Combo via Local API
To update the priority combo on OmniRoute `:20129`:
```python
import urllib.request, json

combo_id = "5a72c9bc-94d8-4e35-a9c6-51545cb73d7a"
url = f"http://127.0.0.1:20129/api/combos/{combo_id}"

payload = {
    "name": "omni-free",
    "description": "Balanced Intelligence & Speed: Nemotron 3 Ultra -> MiMo 2.5 -> Big Pickle -> Laguna 2.1 -> Muse Spark -> Nemotron 3.5 Lightning",
    "models": [
        {"id": "omni-free-model-1-oc-nemotron-3-ultra-free", "kind": "model", "model": "oc/nemotron-3-ultra-free", "providerId": "opencode", "weight": 0, "label": "NVIDIA Nemotron 3 Ultra (Tier 1: Deep Reasoning & High Intelligence)"},
        {"id": "omni-free-model-2-oc-mimo-v2-5-free", "kind": "model", "model": "oc/mimo-v2.5-free", "providerId": "opencode", "weight": 0, "label": "Xiaomi MiMo 2.5 (Tier 2: Smart Logic & Fast Vietnamese)"},
        {"id": "omni-free-model-3-oc-big-pickle", "kind": "model", "model": "oc/big-pickle", "providerId": "opencode", "weight": 0, "label": "Big Pickle (Tier 3: Smart Fallback)"},
        {"id": "omni-free-model-4-oc-laguna-s-2-1-free", "kind": "model", "model": "oc/laguna-s-2.1-free", "providerId": "opencode", "weight": 0, "label": "Poolside Laguna S 2.1 (Tier 4: Coding & Logic)"},
        {"id": "omni-free-model-5-oc-muse-spark-1-2-contributor-free", "kind": "model", "model": "oc/muse-spark-1.2-contributor-free", "providerId": "opencode", "weight": 0, "label": "Muse Spark 1.2 (Tier 5: Fast Chat Net)"},
        {"id": "omni-free-model-6-oc-nemotron-3-5-lightning-free", "kind": "model", "model": "oc/nemotron-3.5-lightning-free", "providerId": "opencode", "weight": 0, "label": "NVIDIA Nemotron 3.5 Lightning (Tier 6: Final Safety Net)"}
    ],
    "strategy": "priority",
    "config": {
        "maxRetries": 0,
        "retryDelayMs": 0,
        "handoffThreshold": 0.85,
        "handoffModel": "",
        "maxMessagesForSummary": 30,
        "trackMetrics": True,
        "reasoningTokenBufferEnabled": True,
        "failoverBeforeRetry": True,
        "zeroLatencyOptimizationsEnabled": False,
        "resetAwareQuotaCacheTtlMs": 0,
        "resetAwareQuotaCacheMaxStaleMs": 0
    }
}

req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"}, method="PUT")
with urllib.request.urlopen(req, timeout=10) as resp:
    print(resp.status)
```
