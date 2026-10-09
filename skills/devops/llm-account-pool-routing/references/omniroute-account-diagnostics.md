# OmniRoute & 9Router Account Pool Diagnostics

## 0. Router Disambiguation Invariant
- **OmniRoute (`:20129`)**: UI title **OmniRoute**; DB is `C:\Users\Kibe\.omniroute\storage.sqlite` (legacy directory priority over `%APPDATA%\omniroute`), codebase at `C:\Users\Kibe\OmniRoute`.
- **9Router (`:20128`)**: UI title **9Router**; DB is `%APPDATA%\9router\db\data.sqlite` (or `9router.db`), codebase at `%APPDATA%\npm\node_modules\9router\app`.
- **Rule**: When operator asks about account status/quotas, check port (`:20129` vs `:20128`) and dashboard logo/version first. Never diagnose 9Router when the operator is asking about OmniRoute.

---

## 1. OmniRoute (`:20129`) Diagnostic Recipes

Database: `C:\Users\Kibe\.omniroute\storage.sqlite` (Note: `src/lib/dataPaths.ts` checks `~/.omniroute` before `%APPDATA%\omniroute`; the active production DB is under `C:\Users\Kibe\.omniroute`).

### Checking Account Status & Assigned Proxies
```python
import sqlite3
conn = sqlite3.connect(r'C:\Users\Kibe\.omniroute\storage.sqlite')
cursor = conn.cursor()
cursor.execute('''
  SELECT pc.id, pc.name, pc.priority, pc.is_active, pc.test_status, pc.error_code, pc.last_error, 
         pr.name as proxy_name, pr.host, pr.port, pr.username, pr.password
  FROM provider_connections pc
  LEFT JOIN proxy_assignments pa ON pa.scope_id = pc.id AND pa.scope = 'account'
  LEFT JOIN proxy_registry pr ON pa.proxy_id = pr.id
  WHERE pc.provider = 'antigravity'
  ORDER BY pc.priority ASC
''')
for row in cursor.fetchall():
    print(row)
```

### Checking Proxy Registry for Missing Auth
```python
import sqlite3
conn = sqlite3.connect(r'C:\Users\Kibe\.omniroute\storage.sqlite')
cursor = conn.cursor()
cursor.execute('''
  SELECT id, name, host, port, username, password, status
  FROM proxy_registry
  WHERE username = '' OR username IS NULL OR password = '' OR password IS NULL
''')
print("Proxies missing auth:", cursor.fetchall())
```

### Common Failure Modes in Dashboard:
1. **"Load failed" / "HTTP 503: fetch failed" / "Token expired":**
   - Account has `proxy_enabled = 1` and an assigned proxy in `proxy_assignments`.
   - **Root Cause A (Missing Auth):** The assigned proxy entry in `proxy_registry` has empty `username`/`password`. For MikroTik farm proxies (`mirotik1.taadaa.click:10001..10035`), credentials `admin@1:admin@1` are REQUIRED.
   - **Root Cause B (Dead Proxy/Bad Port):** The proxy is down or host/port is misconfigured.
   - **Mechanism:** OAuth tokens expire every ~1 hour. Token refresh requests are routed through the assigned proxy. When the proxy rejects connection, refresh fails with `refresh_transient` / `refresh_failed` and the account turns red in UI despite previously showing 100% quota.
   - **Fix:** Update `username='admin@1'`, `password='admin@1'` in `proxy_registry` (or reassign to live proxy), then trigger refresh in UI or call API `POST /api/providers/<id>/refresh-token`.

2. **Inactive / Grey Toggle (`is_active = 0`):**
   - Account toggle is switched OFF in the dashboard UI or lacks required configuration (e.g. empty `projectId`).
   - **Fix:** Update `is_active = 1` and ensure `projectId` is populated.

3. **"422: Missing Google projectId for Antigravity account" on Claude / Gemini models:**
   - **Root Cause:** In `open-sse/services/tokenRefresh.ts`, `formatProviderCredentials()` for `antigravity` / `agy` previously returned only `{ accessToken, refreshToken }`, dropping `projectId` and `providerSpecificData`.
   - **Mechanism:** When credentials were formatted before dispatch to `open-sse/executors/antigravity.ts`, `credentials.projectId` was undefined, triggering auto-discovery via `loadCodeAssist` which failed with 422.
   - **Fix:** Ensure `formatProviderCredentials` includes `projectId: credentials.projectId` and `providerSpecificData: credentials.providerSpecificData`.

4. **Cascade Failover on Exhausted Model Quotas (Shared `correlation_id`):**
   - **Symptom:** Logs show a burst of 10-15 consecutive 429 errors within seconds across different accounts for the same model (e.g. `claude-sonnet-4-6`).
   - **Diagnosis:** Check `correlation_id` in `call_logs`. If multiple error rows share the exact same `correlation_id`, it is **NOT** a looping bug hitting the same account; it is the router sequentially attempting account failover across all candidate connections in the pool until all fail.
   - **Root Cause:** Upstream model quota is depleted across the entire account pool at the provider side.
   - **Fix:** Wait for provider quota reset window, or route traffic to an active alternative model pool (e.g. `gemini-3.7-flash-high`).

5. **Distinguishing Code Formatting Bugs vs OAuth Session Expiry (401/403 invalid_grant):**
   - **Code bug (422):** Fixed in router codebase (e.g. missing `projectId` or headers).
   - **Session Expiry / Revocation (401 / 403 `invalid_grant`):** Google invalidated the refresh token or requires user re-authentication/verification. Code patches cannot fix this; operator must click Re-login/Re-authenticate in the dashboard UI.

6. **Auditing Account Real Usage vs Health Checks:**
   - Inspect `TokensIn`, `last_used_at`, and `consecutive_use_count` in `provider_connections` and `usage_history`.
   - If `TokensIn == 0` and all 200 logs are `connection-test` (health checks) while actual inference calls returned 403/422/429, the account has never successfully served user traffic. Check project ID validity and OAuth scope.

7. **Auditing Worker Combos for Unintended Model Calls (e.g. Sonnet in `ag-worker`):**
   - **Symptom:** User notices requests unexpectedly hitting paid/restricted models (e.g. `antigravity/claude-sonnet-4-6`) during autonomous worker execution.
   - **Diagnosis:** Inspect `combos` table (`SELECT id, name, data FROM combos WHERE name='ag-worker'`).
   - **Root Cause:** When `delegation.model` is set to a combo (e.g. `ag-worker`), the combo's fallback hierarchy may contain intermediate tiers (e.g. Tier 1: `ag-gemini-pool-3` -> Tier 2A: `claude-sonnet-4-6` -> Tier 2B: `deepseek-v4-flash` -> Tier 3: `omni-free`). If Tier 1 experiences transient 429s or high concurrency, the combo silently falls over to Tier 2A.
   - **Fix:** Remove the unwanted model from the combo `models` array in `combos.data` so the fallback chain routes directly from pool to free tiers without hitting restricted models.

8. **Nested Combo Expansion (`combo-ref` vs `model` kind):**
   - **Symptom:** When calling a wrapper combo (e.g. `ag-worker`) that contains a sub-combo pool (e.g. `ag-gemini-pool-3`), a transient failure or rate-limit on Account 1 causes the router to immediately skip to the next top-level step (e.g. Tier 2 / Free models) without trying the remaining accounts in the sub-combo.
   - **Root Cause:** In the `combos` table `data` JSON, the sub-combo was saved as `{"kind": "model", "model": "combo/ag-gemini-pool-3", "providerId": "combo"}` instead of `{"kind": "combo-ref", "comboName": "ag-gemini-pool-3"}`. When `kind == "model"`, OmniRoute's `resolveComboTargets` does not recursively unroll the nested combo targets into individual account targets, treating the entire pool as a single monolithic model step.
   - **Fix:** Update the combo definition to use `{"kind": "combo-ref", "comboName": "<nested-combo-name>"}`. This allows `resolveComboTargets` to unroll all 18 individual account targets in order.

9. **Upstream Model Discovery & Quota Characteristics (`gemini-3.8-flash-tiered` vs `3.7`):**
   - **Enabling Auto-Fetch & Auto-Sync:**
     * To enable model discovery across all pool accounts, send `PUT /api/providers/{id}` with `{"providerSpecificData": {"autoFetchModels": true, "autoSync": true}}`, then trigger `POST /api/providers/{id}/sync-models?mode=import`.
   - **Upstream `-tiered` Suffix:**
     * Google Cloud Code / Antigravity backend names reasoning models with `-tiered` (e.g. `gemini-3.8-flash-tiered`). Google routes reasoning depth via `generationConfig.thinkingConfig.thinkingBudget`.
     * The native Antigravity desktop app hides `-tiered` in its UI label, whereas raw API discovery surfaces the technical ID `gemini-3.8-flash-tiered`.
   - **Quota Consumption & Performance (3.8 vs 3.7):**
     * Quota is measured by `Total Tokens` (Prompt + Completion + Thinking tokens).
     * Gemini 3.8 Flash allocates deeper thinking phases for logic/code tasks, yielding ~10-15% higher total token usage due to additional thinking tokens.
     * Latency (TTFT) on complex queries is higher due to deeper reasoning, but logic precision and edge-case handling are significantly improved.
   - **Operational Migration Policy:**
     * Keep production pool combos (e.g. `ag-gemini-pool-3`) pinned to verified versions (3.7) until OmniRoute releases official alias presets (e.g. `gemini-3.8-flash-high`).
     * Run 3.8 as a direct model call (`antigravity/gemini-3.8-flash-tiered`) or in an experimental test combo first.

10. **Credential Health Check Scheduler & Connection Test Quota Mechanics (`tx = 0`):**
   - **Hiện tượng:** Operator thấy định kỳ (mỗi vài phút) OmniRoute tự động gửi `connection-test` tới toàn bộ account trong pool, hiển thị trên bảng Logger/Dashboard với `tx = 0` (hoặc 0 token).
   - **Cơ chế chạy ngầm:** `src/lib/credentialHealth/scheduler.ts` khởi chạy background scheduler sau khi boot 30s và quét định kỳ mỗi 5 phút (`CREDENTIAL_HEALTH_CHECK_INTERVAL=300000`). Mục đích: kiểm tra độ sống của token, phát hiện tài khoản bị thu hồi/vô hiệu hóa (`account_deactivated`), và chủ động kích hoạt refresh token trước khi token hết hạn.
   - **Có tốn Quota không? (HOÀN TOÀN KHÔNG - `tx = 0`):**
     * **Codex (ChatGPT OAuth):** Gửi `POST https://chatgpt.com/backend-api/codex/responses` với body rỗng `{ model: "gpt-5.5", input: [], stream: false, store: false }`. OmniRoute cố tình trigger phản hồi nhanh **HTTP 400 Bad Request** tại tầng Auth upstream (`acceptStatuses: [400]`). Upstream chỉ xác thực token mà KHÔNG chạy suy luận model, KHÔNG sinh token và KHÔNG trừ quota rate limit của ChatGPT.
     * **API Key Providers (OpenAI, DeepSeek, OpenRouter...):** Chỉ probe endpoint danh mục model `/v1/models` (endpoint metadata miễn phí 100%, 0 token).
     * **Claude OAuth:** Chỉ kiểm tra thời hạn (expiry) của token local (`checkExpiry: true`), không gửi HTTP request dư thừa lên upstream nếu token còn hạn.
     * **Antigravity / agy:** Probe tối thiểu kiểm tra kết nối `streamGenerateContent` và phát hiện geo-blocking (`maxOutputTokens: 1` hoặc ping).
   - **An toàn tài khoản & Chống flood API:**
     * Giới hạn concurrency tối đa 5 tests đồng thời (`CONCURRENCY_LIMIT = 5`).
     * Tự động áp dụng **Exponential Backoff** khi account lỗi: 5m -> 10m -> 30m -> tối đa 2h (`BACKOFF_SCHEDULE = [300_000, 600_000, 1_800_000, 7_200_000]`), không bao giờ spam tài khoản đang lỗi.
     * Tự động hoãn (defer) connection test nếu account đang có active exclusive session lease phục vụ request thật.
   - **Tùy chỉnh trong `C:\Users\Kibe\OmniRoute\.env`:**
     * Giãn cách thời gian sweep (ví dụ 30 phút/lần): `CREDENTIAL_HEALTH_CHECK_INTERVAL=1800000`.
     * Tắt hoàn toàn background check định kỳ: `OMNIROUTE_DISABLE_CREDENTIAL_HEALTH_CHECK=true`.
     * Ẩn log connection test khỏi bảng Logger: `OMNIROUTE_HIDE_HEALTHCHECK_LOGS=true`.

11. **Provider Quota Dashboard Visual Signs: 'Token expires in' vs 'Token expired' vs Inactive Toggle Switches (`is_active = 0`):**
   - **Trang `/dashboard/quota` (Provider Quota):**
     * **'Token expires in 0h Xm' (BÌNH THƯỜNG):** Token Antigravity OAuth có hạn 60 phút. OmniRoute cài đặt cơ chế proactive refresh trước 15 phút (`REFRESH_LEAD_MS.antigravity = 15 * 60 * 1000`). Nếu đồng hồ hiện `0h 18m` hay `0h 58m`, đây là đếm ngược tự nhiên, hoàn toàn không phải lỗi.
     * **'Token expired' chữ đỏ kèm biểu tượng đồng hồ cam:** Xảy ra khi background refresh gọi token endpoint của Google (`https://oauth2.googleapis.com/token`) và bị Google từ chối với HTTP 400 `{"error": "invalid_grant"}` (mapped sang `unrecoverable_refresh_error` trong `open-sse/services/tokenRefresh/providers/google.ts`). Connection bị chuyển sang `test_status = 'expired'`. Khắc phục: Phải re-authenticate/re-login lại từ GPM Profile.
     * **Thẻ hiển thị nhãn '● Business' (Màu vàng):** Không phải tài khoản Business trả phí! Là tài khoản rớt vào `standard-tier` / `Antigravity (Restricted)` do Google cắm cờ `VALIDATION_REQUIRED` trên `loadCodeAssist`. Tài khoản này bị Google từ chối cấp `cloudaicompanionProject` tự động nên trường `projectId` bị rỗng. Khi gửi request model thật sẽ văng `422 Missing Google projectId`. Xem chi tiết cách khắc phục tại `antigravity-free-tier-vs-restricted-diagnosis.md`.
     * **Công tắc thẻ màu xám/viền đỏ (`is_active = 0`):** Khi operator thấy nhiều thẻ vàng "Business" hoặc đỏ "Token expired", thường thao tác tắt công tắc trên UI (`PUT /api/providers/[id]` với `isActive: false`). Trình định tuyến combo (`resolveComboTargets`) tự động lọc bỏ các connection `is_active = 0` và `expired`, bảo đảm phần còn lại của pool tiếp tục hoạt động mà không bị crash.

12. **Cảnh Báo Đỏ '• degraded' Do Thiếu Google Cloud Code projectId ('Connected, but the Google Cloud Code projectId could not be found...'):**
   - **Hiện tượng:** Trên bảng Dashboard Providers Antigravity (`/dashboard/providers/antigravity`), thẻ tài khoản hiển thị cờ đỏ `• degraded` kèm cảnh báo *"Connected, but the Google Cloud Code projectId could not be found..."*.
   - **Nguyên nhân:** Khi exchange OAuth authorization code lấy access/refresh token, Google API đôi khi trả về payload thiếu `cloudaicompanionProject` hoặc trả về rỗng `""`. OmniRoute khi chạy health check hoặc validate không thấy `projectId` nên đánh cờ `degraded` (hạ cấp) dù token vẫn còn hạn.
   - **Khắc phục O(1) phục hồi xanh lá 100% ('• đã kết nối'):**
     1. Gửi request `PUT /api/providers/{cid}` gán project mặc định:
        ```json
        {
          "projectId": "aicode-consumers",
          "providerSpecificData": {
            "clientProfile": "ide",
            "projectId": "aicode-consumers",
            "tier": "free-tier"
          }
        }
        ```
     2. Gửi request `POST /api/providers/{cid}/sync-models` để đồng bộ lại 12 models.
     3. Cờ `degraded` lập tức biến mất, connection chuyển sang trạng thái `active` (`• đã kết nối` màu xanh lá).

13. **Antigravity Dashboard Multi-Account Proof & Full Table Bottom Capture Playbook (Pagination & Internal Container Scroll 2026-09-08):**
   - **Kỷ luật Proof OAuth**: Khi nghiệm thu tài khoản Antigravity mới nạp OAuth vào OmniRoute, BẮT BUỘC chụp ảnh bằng chứng ở cuối bảng Antigravity dashboard (`:20129`) hiển thị rõ các tài khoản mới nhất ở cuối; CẤM chụp lửng lơ hoặc chụp màn hình điện thoại S7.
   - **Đường dẫn chuẩn**: `http://localhost:20129/dashboard/providers/antigravity`.
   - **Bẫy Phân Trang (Pagination Trap >50 accounts)**:
     * Giao diện Antigravity giới hạn hiển thị 50 tài khoản/trang (ví dụ `1 – 50 / 63` ở trang 1).
     * Khi pool vượt quá 50 tài khoản (ví dụ 63 tài khoản), toàn bộ tài khoản mới nhất nạp trong ngày nằm ở **Trang 2** (`51 – 63 / 63`).
     * BẮT BUỘC bấm nút chuyển trang tiếp theo (`>`) trước khi chụp ảnh hoặc kiểm tra.
   - **Bẫy Internal Scroll Container (`overflow-y-auto`) vs Window Scroll**:
     * Khung danh sách tài khoản nằm trong container cuộn riêng biệt (`div.flex-1.min-h-0.overflow-y-auto` với `scrollHeight > 5000px`), KHÔNG phải `window` hay `<main>`.
     * Dùng `window.scrollTo` hoặc cuộn mù `browser_scroll` thường không cuộn đúng danh sách, hoặc cuộn vọt qua bảng tài khoản xuống tận khối "Chặn công cụ Web" ở đáy trang.
     * **Căn chỉnh chính xác O(1)**: Dùng JavaScript scroll phần tử cuối cùng vào giữa khung nhìn:
       ```javascript
       const cards = Array.from(document.querySelectorAll("p")).filter(p => p.textContent.includes("@"));
       if (cards.length > 0) cards[cards.length - 1].scrollIntoView({behavior: "instant", block: "center"});
       ```
   - **Kỹ thuật bao quát & Chống Cắt Mép (Anti-Clipping)**:
     * Để hiển thị trọn vẹn toàn bộ các tài khoản từ #51 đến #63 trên trang 2 trong một khung hình, đặt tỷ lệ thu nhỏ: `document.body.style.zoom = "55%"`.
     * Sau đó gọi `cards[cards.length - 1].scrollIntoView({behavior: "instant", block: "center"})` để đảm bảo hàng tài khoản cuối cùng (#63) nằm gọn trong khung nhìn, không bị cắt mép dưới (cut off).
   - **4 Điểm Nghiệm Thu Bắt Buộc Trên Ảnh Proof**:
     1. Tên email tài khoản (đúng tiền tố).
     2. Badge trạng thái: **`🟢 Đã kết nối`**.
     3. Đếm ngược thời gian phiên/token (ví dụ `~28m #63`).
     4. Tag Proxy 1:1 gán theo cổng máy farm / MikroTik (ví dụ `mirotik_10005`, `39`, `41`, `67`, `70`).

14. **Ghost Model Requests / 418 Errors (`duckduckgo-web` / `claude-haiku-4-5`, `gpt-5.4-mini/nano`) do Vision Bridge Guardrail tự ý kích hoạt:**
   - **Hiện tượng**: Operator thấy trên Dashboard Logs (`:20129/dashboard/logs`) xuất hiện các request lạ gọi vào `duckduckgo-web/claude-haiku-4-5`, `duckduckgo-web/gpt-5.4-nano`, `duckduckgo-web/gpt-5.4-mini` với HTTP status 418 (hoặc 502/429) và Provider `DUCKDUCKGO-WEB`, dù hoàn toàn không cài đặt combo nào chứa các model này.
   - **Nguyên nhân gốc rễ**:
     1. *Trigger*: Client (ví dụ Hermes Agent khi chạy `computer_use(action="capture", mode="vision")` hoặc `vision_analyze_tool`) gửi một request mang hình ảnh (image payload) tới một combo như `omni-worker` hoặc model text-only.
     2. *Vision Bridge Guardrail kích hoạt*: Trong OmniRoute (`src/lib/guardrails/visionBridge.ts`), tính năng Vision Bridge mặc định bật (`enabled: true`). Khi request có ảnh gửi vào combo chứa `kind: "combo-ref"` (như `omni-worker` trỏ `ag-gemini-pool-3`), hàm `getComboVisionBridgeDecision()` đánh giá combo có thể chứa model không hỗ trợ vision trực tiếp nên kích hoạt luồng trích xuất mô tả ảnh (`callVisionModel`).
     3. *Auto-selection rơi vào no-auth provider*: Do OmniRoute không có API key OpenAI/Anthropic/Vertex riêng, hàm `getBestVisionModel()` quét danh mục model vision và rơi vào nhóm `NOAUTH_PROVIDERS` (nhà cung cấp miễn phí không cần key). Registry `duckduckgo-web` chứa đúng 3 model theo thứ tự: `gpt-5.4-mini` (chính) -> `gpt-5.4-nano` (fallback 1) -> `claude-haiku-4-5` (fallback 2).
     4. *HTTP 418 Anti-abuse*: DuckDuckGo chặn request web chat ẩn danh bằng HTTP 418 (`DuckDuckGo AI Chat anti-abuse challenge failed: ERR_BN_LIMIT (7b08)`). OmniRoute retry tuần tự qua cả 3 model và cả 3 đều fail 418, để lại đúng 3 dòng log rác trên dashboard.
   - **Cách xử lý & Khắc phục**:
     1. *Tắt Vision Bridge*: Set `visionBridgeEnabled: false` trong settings OmniRoute (hoặc `modalityBridgeEnabled: false` trên dashboard).
     2. *Gán Vision Model cố định*: Nếu cần mô tả ảnh cho text models, gán `visionBridgeModel` (hoặc `modalityBridgeVisionModel`) trỏ đích danh vào 1 model vision ổn định thay vì để auto rơi xuống no-auth provider.
     3. *Trong Hermes*: Cấu hình `auxiliary.vision` trong `config.yaml` trỏ trực tiếp provider/model có hỗ trợ multimodal native (ví dụ Gemini Flash trong Antigravity) thay vì gửi payload qua combo bọc nhiều tầng.

---

## 1b. Quick API-First Diagnosis — "Account X can't make requests through Pool Y"

When a user reports a specific account failing in a pool, skip UI navigation and diagnose via API in <30s:

### Step 1: Find the account in `/api/providers`
```bash
curl -s http://localhost:20129/api/providers | python -c "
import json,sys; data=json.load(sys.stdin)
for c in data.get('connections',[]):
    if '<partial_email>' in c.get('email','').lower():
        exp=c.get('expiresAt','N/A'); act=c.get('isActive'); ts=c.get('testStatus')
        print(f'{c[\"email\"]} | active={act} testStatus={ts} expiresAt={exp} priority={c.get(\"priority\")}')
        print(f'  tier={c.get(\"providerSpecificData\",{}).get(\"tier\",\"?\")} backoff={c.get(\"backoffLevel\",0)}')
"
```

### Step 2: Verify the account is in the target pool via `/api/combos`
```bash
curl -s http://localhost:20129/api/combos | python -c "
import json,sys; data=json.load(sys.stdin)
for combo in (data if isinstance(data,list) else data.get('combos',[])):
    if combo.get('name')=='<pool_name>':
        ids={m.get('connectionId') for m in combo.get('models',[])}
        print(f'{combo[\"name\"]}: {len(ids)} targets')
        # Check if target conn_id is present
        print('Target in pool:', '<conn_id>' in ids)
"
```

### Step 3: Diagnose by field combination

| `isActive` | `testStatus` | `expiresAt` vs now | Meaning | Fix |
|---|---|---|---|---|
| true | active | in the future | ✅ Healthy | — |
| true | active | **in the past** | ⚠️ Token expired, health check not yet caught it | Re-login / `POST /api/providers/{id}/refresh` |
| true | expired | any | 🔴 `invalid_grant` — Google revoked refresh token | Re-authenticate via GPM profile |
| false | any | any | ⚠️ Toggle off | `PUT /api/providers/{id}` with `isActive: true` |
| true | active | any + `backoffLevel > 0` | ⚠️ In backoff from errors | Wait or fix underlying issue |

**Key pitfall:** `isActive: true` is the operator toggle, NOT a health status. An account can show `isActive: true` + `testStatus: active` while its OAuth token is already expired (last health check was before expiry). The `expiresAt` field is the ground truth for token validity.

**Dashboard shortcut:** The red error badge (e.g. "error 1") on the top-right of the dashboard → click to see which account has `invalid_grant` and the recommended action ("Đăng nhập lại").

---

## 2. 9Router (`:20128`) Diagnostic Recipes

Database: `%APPDATA%\9router\db\data.sqlite`

### 429 Priority Demotion to 9999 ("No active credentials")
- When all accounts for a provider hit 429 rate limits, 9Router demotes their priority to 9999.
- If all accounts have `priority >= 9000`, 9Router returns `No active credentials for provider: <provider>` (404).
- **Fix:**
```python
import sqlite3, os, json
db_path = os.path.join(os.environ['APPDATA'], '9router', 'db', 'data.sqlite')
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("""
    UPDATE providerConnections 
    SET priority = json_extract(data, '$.priorityBase'),
        updatedAt = datetime('now')
    WHERE provider = 'antigravity' AND priority = 9999
""")
conn.commit()
```
