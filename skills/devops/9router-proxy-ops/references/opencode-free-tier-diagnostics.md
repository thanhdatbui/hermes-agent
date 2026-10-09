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
| `oc/muse-spark-1.3-contributor-free` | Meta Muse Spark 1.3 | High (100% Code Benchmark, Median ~25s) | ~2s – 5s | Successor to 1.2. Strong code intelligence, zero cost. |
| `oc/mimo-v2.6-flash-free` | Xiaomi MiMo 2.6 Flash | High (Fast, Strong Logic & Code) | ~3s – 5s | Successor to 2.5. Stable fallback in Jev router. |
| `oc/nemotron-3.5-lightning-free` | NVIDIA Nemotron 3.5 Lightning | Medium-High (Reasoning) | >250s (Congested) | Heavy server queue on upstream. Causes **HTTP 499 (Request aborted / Gateway timeout at 300s)**. Keep as lowest priority or safety net. |

## Upstream Client Barrier & Version Requirements (Enforced 2026-09)
- **403 External Proxy Block:** Request ngoài qua OmniRoute, 9Router, curl đều bị chặn:
  `HTTP 403: {"type":"FreeTierError","message":"OpenCode's free tier can only be used from within OpenCode"}`
- **CLI Minimum Version:** OpenCode CLI gọi trực tiếp bắt buộc version `>= 1.18.0`. Phiên bản cũ hơn (vd: 1.17.19) bị upstream từ chối với thông báo:
  `Error: Error from provider (Console): OpenCode 1.18.0 or newer is required to use the free tier`
- **Proxy Rotation Invariants for OpenCode CLI (`oc-farm`):**
  - OpenCode CLI nhận diện trực tiếp các biến môi trường `HTTPS_PROXY`, `HTTP_PROXY`, `ALL_PROXY`.
  - **Bắt buộc `NO_PROXY="localhost,127.0.0.1,::1"`**: Nếu thiếu, kết nối IPC nội bộ giữa CLI và daemon sẽ bị đẩy qua proxy gây timeout treo tiến trình.
  - **Mã hóa URL Auth**: Password/username có ký tự `@` (như `admin@1`) phải URL-encode thành `%40` (`admin%401:admin%401`).
  - **Xoay IP chống Rate Limit/Daily Quota**: Phân tán request qua pool 69 proxy farm để tránh cháy daily quota của từng IP. Khi gặp lỗi 429 hoặc kết nối nghẽn, đưa IP đó vào cooldown và lập tức retry sang IP tiếp theo.
- **Paid Tier (`opencode-go`):** Các model cao cấp như `glm-5.3`, `deepseek-v4.1-flash`, `kimi-k3` không thuộc pool free hoàn toàn mà nằm trong gói OpenCode Go ($5/mo). Free access cho GLM/DeepSeek v4.1 thường được lấy qua NVIDIA KiosAPI hoặc Zhipu BigModel Flash tokens.

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

---

## Multi-Proxy Pool & Fail-Fast Fallback for OpenCode Free Tier

### 1. The Problem with Direct Egress
Mặc định provider `opencode` (Muse Spark, MiMo, Big Pickle...) chạy qua 1 kết nối direct (`proxy: null`). Khi IP direct bị rate-limit (`429`) hoặc nghẽn, OmniRoute lập tức đánh fail model và chuyển sang model tiếp theo trong combo, gây lãng phí model mạnh như Muse Spark.

### 2. 69 Farm Proxy Topology
Tận dụng toàn bộ hạ tầng proxy có sẵn của farm:
- **32 Proxy Mobi**: `test.taadaa.click:5101..5138` (bỏ các port gap `5109..5110`, `5119..5120`, `5129..5130`). Auth `mobiN:TaadaaMobi#2026!`.
- **35 Proxy MikroTik**: `mirotik1.taadaa.click:10001..10035`. Auth `admin@1:admin@1`.
- **2 Proxy Khoalee**: `khoalee.duckdns.org:16001` (auth `Gyx4k1:RzI0fc3o`) và `khoalee.duckdns.org:16002` (auth `5ns08q:AmLmaMJ0`).
- **Tổng cộng**: 69 proxy độc lập.

### 3. Cấu hình Multi-Proxy Rotation trên OmniRoute
Đồng bộ 69 proxy vào `proxy_registry` trong `storage.sqlite` và bind vào provider connection `opencode`:
```json
{
  "provider": "opencode",
  "name": "OpenCode Free Pool",
  "authType": "apikey",
  "apiKey": "free",
  "proxyEnabled": true,
  "perKeyProxyEnabled": true,
  "providerSpecificData": {
    "fingerprints": ["fp_test.taadaa.click_5101", ...],
    "accountProxies": [
      {
        "fingerprint": "fp_test.taadaa.click_5101",
        "proxyId": "<uuid>",
        "proxy": {"type": "http", "host": "test.taadaa.click", "port": 5101, "username": "mobi1", "password": "TaadaaMobi#2026!"}
      },
      ...
    ],
    "maxAttempts": 5
  }
}
```

### 4. Cân bằng Tốc độ & Fallback Thông minh (Speed Balancing vs Resilience)
- **Lỗi IP (429 Rate-limit / Timeout / Connection Reset)**: Xoay vòng Round-Robin qua các IP khác trong pool 69 proxy. IP bị lỗi tự động vào cooldown.
- **Lỗi Model Hỏng (500 / 503 / 400 Empty Rejection)**: Do chính server upstream sập, đổi proxy không giải quyết được.
- **Capping Retry (Tối đa 3–5 Proxy / Request)**: CẤM lặp tuần tự qua cả 69 proxy trên một request hỏng vì sẽ gây treo request > 1 phút. Cấu hình `maxAttempts: 5` để thử tối đa 5 proxy; nếu sau 5 proxy vẫn không có kết quả $\rightarrow$ kích hoạt Combo Fallback ngay lập tức sang model tiếp theo (`mimo-v2.5` / `big-pickle`).
