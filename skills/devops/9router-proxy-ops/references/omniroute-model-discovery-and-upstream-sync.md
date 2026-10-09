# OmniRoute Model Discovery & Upstream Sync Guide

## 1. Provider Models Section Controls (`:20129/dashboard/providers/<provider>`)

In OmniRoute's provider detail view (e.g. `antigravity`), the **Available Models** toolbar contains key controls for model lifecycle and discovery:

| Control | Recommended State | Function & Purpose |
| :--- | :--- | :--- |
| **`Auto-fetch upstream models`** | **ENABLED (ON)** | Automatically queries the upstream discovery endpoint (e.g. `/v1internal:fetchAvailableModels` for Google Cloud Code / Antigravity) using active authenticated connections and proxies. |
| **`Auto-Sync`** | **ENABLED (ON)** | Automatically writes newly discovered upstream models into OmniRoute's database / model catalog cache. |
| **`Auto-hide failed models`** | **ENABLED (ON)** | Automatically hides deprecated, retired, or invalid models that fail with HTTP 400/404 during execution or validation. |
| **`Import from /models`** | **Manual Action** | Instantly triggers the upstream discovery probe across all active provider accounts without waiting for the background cycle. |

---

## 2. Built-in vs Discovered Models

* **`BUILT-IN` models**: Hardcoded catalog bundled with OmniRoute releases (defined in `open-sse/config/antigravityModelAliases.ts` as `ANTIGRAVITY_PUBLIC_MODELS`). When `Auto-fetch` is disabled, only these static models are displayed.
* **Discovered models**: Live callable models fetched dynamically from upstream servers.
  * For Antigravity, OmniRoute probes:
    - `https://daily-cloudcode-pa.googleapis.com/v1internal:fetchAvailableModels`
    - `https://cloudcode-pa.googleapis.com/v1internal:fetchAvailableModels`
  * Filtered via `isDiscoverableAntigravityModelId()` to strip internal non-chat endpoints (`image`, `tts`, `embedding`, etc.).

---

## 3. Workflow When a New Model Launches Upstream (e.g. Gemini 3.8)

When a new model is released upstream on Google / Antigravity but not yet listed in OmniRoute:

1. **Enable Auto-Discovery**:
   - Turn ON `Auto-fetch upstream models`.
   - Turn ON `Auto-Sync`.
2. **Trigger Instant Sync**:
   - Click the **`Import from /models`** button on the Provider Models toolbar.
3. **Verify Discovery**:
   - If Google's Cloud Code upstream has published the model ID to `fetchAvailableModels`, the new model will appear in the model grid immediately.
4. **Direct Combo Reference / Fallback**:
   - If the upstream endpoint has not yet listed the model in its discovery catalog or if OmniRoute requires a release update for custom parameter translation / alias mappings:
     - The model ID can still be tested directly or configured inside combos if upstream accepts the raw model identifier.

---

## 4. CRITICAL INVARIANT: Upstream Model IDs & Banned Source/Build Edits

* **Exact Upstream ID Invariant**: Always use the exact upstream model identifier provided by the vendor. For Google Antigravity, the Flash model with thinking capability is `antigravity/gemini-3.8-flash-tiered`.
* **CẤM TUYỆT ĐỐI tự chế alias hoặc sửa core files**:
  - KHÔNG tự tiện chế tên (e.g. `gemini-3.8-flash-high`) khi chưa có mapping upstream.
  - CẤM sửa trực tiếp các file core của OmniRoute (`modelSpecs.ts`, `antigravityModelAliases.ts`, `open-sse/config/...`) và CẤM chạy `npm run build` trên instance production đang phục vụ proxy. Hành động này sẽ làm sập server, đứt kết nối của toàn bộ agent và watchdog.
* **Quy trình chuẩn khi chuyển model**:
  1. Gửi request test cô lập tới `/v1/chat/completions` với model ID gốc (`antigravity/gemini-3.8-flash-tiered`) để xác minh upstream phản hồi và reasoning token hoạt động.
  2. Cập nhật combo (`ag-gemini-pool-3`) thông qua REST API (`PUT /api/combos/<id>`) để thay thế `model` của tất cả account sang ID chuẩn.
  3. Kiểm tra lại combo qua API để xác nhận 100% tài khoản đã nhận model mới mà không cần restart server.
