# Xử lý Cảnh báo API Key Warning & Dọn dẹp Zombie Connection trên OmniRoute (:20129)

## 1. Cơ chế phát sinh cảnh báo "API Key Warning" trên Dashboard
Trên giao diện chính của OmniRoute (`/dashboard`), banner màu vàng xuất hiện khi:
- Trong bảng `provider_connections`, trường `provider_specific_data` chứa object `apiKeyHealth`.
- Một trong các key (thường là `primary`) mang trạng thái `status: "warning"` hoặc `status: "invalid"`.
- Cảnh báo này phát sinh khi một connection trải qua 1-2 lần request/test bị lỗi (ví dụ: `401 Unauthorized`, `Token invalid or revoked`, hoặc `ChatGPT session expired`).

## 2. Các nhóm lỗi phổ biến & Cách phân loại triệt để

### A. Nhóm Codex (OAuth Session bị expired)
- **Đặc điểm**: Thường là các tài khoản web/GPM được import vào provider `codex` mà không có `refresh_token` (`refresh_token IS NULL`).
- Khi OAuth session hết hạn (thường sau 1-2 tuần), API trả về `401.0 - Token invalid or revoked`.
- **Hành động chuẩn**:
  - Không để các connection này ở trạng thái `active=1` gây nhiễu và làm treo semaphore/failover combo.
  - Nếu không thể re-auth ngay, gọi `DELETE /api/providers/{id}` để gỡ bỏ khỏi pool.
  - Pool `codex` chỉ nên giữ lại connection chuẩn canonical (`Codex Session từ ~/.codex/auth.json`).

### B. Nhóm ChatGPT-Web (Lỗi định dạng Token hoặc Cookie cụt)
- **Đặc điểm**:
  - Provider `chatgpt-web` trong OmniRoute bắt buộc API Key phải là chuỗi cookie NextAuth hoàn chỉnh:
    `__Secure-next-auth.session-token=...` hoặc chunked: `__Secure-next-auth.session-token.0=...; __Secure-next-auth.session-token.1=...`
  - **Lỗi nghiêm trọng hay gặp**: Script tự động trích xuất token lưu nhầm chuỗi JWT Bearer (`eyJhbGci...`) vào trường `apiKey`, hoặc khi cookie bị chia thành chunk `.0` và `.1` (vượt 4KB), vòng lặp chỉ lấy chunk `.0` rồi `break`. Chuỗi cụt này không thể ghép lại ở phía máy chủ NextAuth, gây lỗi `401 - ChatGPT session expired — log into chatgpt.com and copy a fresh cookie`.
- **Hành động chuẩn**:
  - Khi trích xuất cookie qua Playwright hoặc SQLite, gom toàn bộ cookie có chứa `session-token`, sắp xếp theo thứ tự và ghép đầy đủ:
    `sorted_chunks = sorted(session_chunks.items(), key=lambda x: x[0])`
    `session_token = "; ".join(f"{k}={v}" for k, v in sorted_chunks)`
  - Kiểm tra trường `apiKey` của từng connection `chatgpt-web`. Nếu bị lỗi hoặc hết hạn thật, gọi `POST /api/providers/{id}/test` để xác thực. Nếu phục hồi thành công sẽ trả về `valid: true` (latency ~300-500ms). Nếu không thể re-login, tạm thời chuyển `isActive: false` hoặc xóa bỏ để tránh làm chậm chuỗi failover.

### C. Nhóm Antigravity / Google OAuth Revocation vs Gmail Account Death (Bài học thực tế 2026-09-20)
- **Phân biệt rạch ròi bản chất lỗi**:
  - Khi OmniRoute báo `Refresh token rejected (unrecoverable_refresh_error)` hoặc Google API trả về `invalid_grant: Token invalid or revoked`: **ĐÂY LÀ REVOKE Ở CẤP ĐỘ ỨNG DỤNG OAUTH (Google Cloud Console / Antigravity app)**, **TUYỆT ĐỐI KHÔNG TỰ TIỆN KẾT LUẬN LÀ TÀI KHOẢN GMAIL ĐÃ DIE!**
  - Tài khoản Gmail trên profile GPM có thể vẫn hoàn toàn LIVE và còn nguyên mật khẩu/TOTP 2FA.
- **Nguyên nhân không thể Silent Re-auth tự động**:
  - Profile Chrome trên GPM bị văng cookies / đăng xuất khỏi Google.
  - Script watchdog chạy nền chỉ hỗ trợ "Silent OAuth" (Account Chooser -> Consent "Tiếp tục/Cho phép"). Nếu gặp màn hình đăng nhập trắng (bắt gõ lại Email/Password) hoặc Security Checkpoint, script sẽ bị `Timeout bắt OAuth code` (35s).
- **Quy trình xử lý chuẩn hóa khi gặp lỗi Revoked / Timeout**:
  1. **BẮT BUỘC CHECK-LIVE TRƯỚC BẰNG NGUỒN ĐỘC LẬP**: Sử dụng canonical runner `run_checkmail_kibe_farm.py` (engine `checkmail.live` qua proxy di động và Turnstile solver). Không bao giờ tự suy diễn.
  2. **Nếu Checkmail.live xác nhận DIE/Disabled**: Dọn dẹp profile trên GPM qua `sync_gpm_lifecycle.py`, gỡ tài khoản khỏi máy farm S7 và xóa connection trên OmniRoute.
  3. **Nếu Checkmail.live xác nhận LIVE**:
     - Tài khoản hoàn toàn sống. Gọi script login tự động `run_oauth_s7_pipeline.py` (tự gõ pass, giải mã TOTP 2FA, giải reCAPTCHA, tự duyệt Google Prompt qua ADB trên máy S7).
     - Khung giờ chạy: Bắt buộc mở rộng time window vào các khoảng máy rảnh (`07:15-08:45`, `12:00-13:45`, `20:15-23:45`) để nạp cuốn chiếu.
     - Kiểm tra Google Antigravity warning: Với các app native mới, Google hiển thị màn hình cảnh báo "Đảm bảo rằng bạn đã tải ứng dụng này xuống từ Google" -> Click nút `button:has-text("Đăng nhập")` để tiếp tục bắt code.
     - Sau khi exchange token thành công: Nếu trả về `testStatus: "degraded"` do thiếu projectId, gọi ngay `PATCH /api/providers/{id}` với `{"projectId": "aicode-consumers"}` rồi gọi `POST /api/providers/{id}/test` để đưa connection về `testStatus: "active"`.

### D. Nhóm Stale Warning (Cờ cảnh báo treo dù account đã inactive/sửa)
- **Đặc điểm**: Tài khoản đã disable (`isActive: false`) hoặc đã sửa lỗi nhưng trong `providerSpecificData` vẫn còn `apiKeyHealth: {"primary": {"status": "warning", ...}}`.
- **Hành động chuẩn**:
  - Gọi API PATCH để reset cờ:
    ```bash
    curl -X PATCH http://127.0.0.1:20129/api/providers/{id} \
      -H "Content-Type: application/json" \
      -d '{"providerSpecificData": {"apiKeyHealth": {}}}'
    ```
  - Backend OmniRoute sẽ tự động xóa sạch `apiKeyHealth` khi nhận dictionary rỗng.

## 3. Kỹ thuật Phục hồi Offline Zero-UI từ GPM Profile (Chromium 130+ Binary Header) & Gán Proxy 1:1

```python
# 3. Gán proxy 1:1 theo port GPM gốc (BẮT BUỘC)
res_proxies = requests.get(f"{OMNIROUTE_URL}/api/settings/proxies", timeout=5).json()
port_to_pid = {p["port"]: p["id"] for p in res_proxies.get("items", [])}

target_pid = port_to_pid.get(gpm_proxy_port)
if target_pid:
    requests.put(f"{OMNIROUTE_URL}/api/settings/proxies/assignments", json={
        "scope": "account",
        "scopeId": cid,
        "proxyId": target_pid
    })
```
Khi người dùng yêu cầu "Add lại các acc lỗi đó" vào pool `chatgpt-web`:
- **Nguyên lý**: Tuyệt đối không cần khởi động Chrome/Playwright gây phiền toái hoặc kích hoạt WAF/Cloudflare Turnstile. Trích xuất trực tiếp cookie từ file SQLite `Default/Network/Cookies` của profile GPM.
- **Cạm bẫy Chromium 130+ Binary Header (32 bytes)**:
  - Khi giải mã `encrypted_value` qua DPAPI (`Local State` master key) và AESGCM, payload trả về có 32 bytes header nhị phân (`dec[:32]`).
  - Chuỗi UTF-8 session token thực tế bắt đầu từ byte thứ 32 trở đi (`dec[32:].decode("utf-8")`).
  - Bắt buộc lấy và ghép toàn bộ các chunk cookie:
    `__Secure-next-auth.session-token.0=<chunk0>; __Secure-next-auth.session-token.1=<chunk1>`
- **Nạp vào OmniRoute & Gán Proxy 1:1 (Bắt buộc)**:
  - Gửi `POST http://127.0.0.1:20129/api/providers` với `authType: "apikey"`, `apiKey: full_cookie`, `provider: "chatgpt-web"`.
  - Gọi ngay `POST /api/providers/{id}/test` để kiểm chứng. Nếu `valid: true`, giữ lại; nếu cookie trong profile đã thực sự hết hạn, xóa ngay connection để không làm bẩn pool.
  - **BẮT BUỘC GÁN PROXY 1:1 NGAY LẬP TỨC (User Correction "Có gán proxy đầy đủ chưa")**:
    - Khi tạo connection mới, OmniRoute mặc định KHÔNG tự động gán proxy (`assigned_map.get(cid) is None`). Nếu bỏ quên bước này, mọi request chat từ connection đó sẽ thoát thẳng qua IP mạng chủ (Host direct), gây lệch Geolocation, kích hoạt Cloudflare WAF hoặc dẫn tới checkpoint/ban tài khoản OpenAI.
    - Tra cứu port proxy của profile GPM tương ứng (ví dụ: Mobi 4G port `5101..5138` hoặc MikroTik `10001..10009`).
    - Tra cứu `proxyId` hợp lệ qua `GET /api/settings/proxies`.
    - Gán ngay qua endpoint chuẩn:
      ```python
      requests.put("http://127.0.0.1:20129/api/settings/proxies/assignments", json={
          "scope": "account",
          "scopeId": connection["id"],
          "proxyId": target_proxy_id
      })
      ```
    - Truy vấn lại `SELECT scope_id, proxy_id FROM proxy_assignments WHERE scope = 'account'` để audit 100% tài khoản đều có proxy trước khi chốt phiên.

## 4. Kỷ luật Bằng chứng & Trung thực Đồ họa (Anti-Fabricated Evidence)
- **CẤM TUYỆT ĐỐI** tự tạo ảnh đồ họa (PIL / Canvas / SVG render thành PNG) rồi đính kèm `MEDIA:` giả lập giao diện Dashboard hay báo cáo trạng thái hệ thống.
- User hỏi nguồn ảnh ("Hình này lấy ở trang nào v") sẽ gây mất niềm tin nghiêm trọng nếu ảnh không phải ảnh chụp màn hình thật (OS screenshot / browser screencap / ADB capture).
- Báo cáo số liệu phải viết thẳng dưới dạng văn bản và số đo thực tế từ log/API. Chỉ dùng `MEDIA:` khi có ảnh chụp thực từ thiết bị hoặc màn hình thực của máy.

## 5. Quy trình Audit, Clean & Recovery O(1) bằng Python Script

```python
import requests

OMNIROUTE_URL = "http://127.0.0.1:20129"

# 1. Quét danh sách connection có apiKeyHealth lỗi
res = requests.get(f"{OMNIROUTE_URL}/api/providers", timeout=10).json()
connections = res.get("connections", [])

unhealthy_ids = []
for c in connections:
    psd = c.get("providerSpecificData") or {}
    health = psd.get("apiKeyHealth") or {}
    has_issue = any(v.get("status") in ("warning", "invalid") for v in health.values())
    if has_issue:
        unhealthy_ids.append((c.get("id"), c.get("provider"), c.get("name")))

# 2. Xử lý: Purge connection chết hoặc reset cờ
for cid, provider, name in unhealthy_ids:
    if provider == "codex" and "auth.json" not in name:
        requests.delete(f"{OMNIROUTE_URL}/api/providers/{cid}")
    elif provider == "chatgpt-web":
        test = requests.post(f"{OMNIROUTE_URL}/api/providers/{cid}/test").json()
        if not test.get("valid"):
            requests.delete(f"{OMNIROUTE_URL}/api/providers/{cid}")
    else:
        requests.patch(f"{OMNIROUTE_URL}/api/providers/{cid}", json={"providerSpecificData": {"apiKeyHealth": {}}})
```

## 6. Phân biệt Standby (isActive=0) vs Broken Connection & Bẫy Silent Watchdog trong Cron Healer

### A. Phân biệt Standby Connection vs Broken Connection & Bắt buộc Test Request Thực Tế
- Trong OmniRoute (`:20129`), một connection có `isActive: false` (hoặc `is_active: 0`) nhưng `testStatus: "active"` và có `refresh_token` là tài khoản **Standby / Deep Standby** (được người dùng hoặc router chủ động tắt/hạ tải làm dàn dự phòng).
- **Cạm bẫy logic**: Tuyệt đối KHÔNG viết bộ lọc:
  ```python
  # SAI: Đánh đồng Standby với Broken, gây lôi acc bình thường ra mở Playwright OAuth lại
  ag_inactive = [c for c in ag_conns if not (c.get('isActive') and c.get('testStatus') == 'active')]

  # ĐÚNG: Chỉ hồi sinh acc thực sự hỏng kết nối hoặc lỗi token
  ag_need_heal = [c for c in ag_conns if c.get('testStatus') != 'active' or not c.get('hasRefreshToken', True)]
  ```
- **Kỷ luật "Test Request Thực Tế" trước khi kết luận trạng thái**:
  - Khi người dùng nghi ngờ: *"10 acc đó có đang sử dụng được không, test request thực tế vào 10 acc đó chưa, hay đã oauth nhưng lỗi expire token trên omni?"*
  - Tuyệt đối KHÔNG chỉ nhìn trạng thái `test_status` trên SQLite hay gật đầu lý thuyết suông.
  - **BẮT BUỘC BẮN TEST REQUEST THỰC TẾ (Verification Probe)** trực tiếp vào từng connection qua header `x-omniroute-connection-id`:
    ```python
    import requests, time
    payload = {
        "model": "antigravity/gemini-2.5-flash",
        "messages": [{"role": "user", "content": "1+1=? Answer 1 digit"}],
        "max_tokens": 5
    }
    headers = {"Content-Type": "application/json", "x-omniroute-connection-id": connection_id}
    r = requests.post("http://127.0.0.1:20129/v1/chat/completions", json=payload, headers=headers, timeout=25)
    # Xác nhận HTTP 200 OK + latency đo thực tế (~0.9s - 1.2s)
    ```
  - Báo cáo rõ ràng: Kết quả HTTP code, latency thực tế, và text output trả về để chứng minh connection hoàn toàn khả dụng.
  - Nếu connection chỉ bị tắt toggle (`is_active = 0`), bật lại bằng SQL `UPDATE provider_connections SET is_active=1 WHERE id=?` mà không cần can thiệp Playwright.

### B. Van 7 ngày (Profile Aging Gate) chỉ dành cho On-boarding, CẤM áp dụng vào Healer
- **Bản chất**: Van ngâm profile GPM $\ge 7$ ngày là chốt an toàn khi **Nạp mới (On-boarding)** tài khoản từ Phone Farm lên GPM để đăng nhập lần đầu.
- **Cạm bẫy trong Watchdog Hồi sinh (Self-healing)**: 
  - Khi tài khoản ĐÃ CÓ trong OmniRoute (đã từng hoàn tất OAuth thành công), việc kiểm tra lại `created_at` của profile GPM là hoàn toàn sai ngữ cảnh.
  - Hậu quả: Script nhận diện nhầm account Standby thành account cần hồi sinh, sau đó lại vấp van 7 ngày chặn không cho chạy, dẫn đến in lặp vô tận cảnh báo *"Đang ngâm profile GPM (chưa đủ 7 ngày) - bỏ qua Antigravity"*.
  - **Quy tắc**: Luồng Self-healing trên các connection đã tồn tại trong OmniRoute **KHÔNG ĐƯỢC CHẶN** bởi van 7 ngày ngâm profile.

### C. Kỷ luật Silent Watchdog (`no_agent=True`) & Chống Spam Alert
- Với Hermes cronjob `no_agent=True`:
  - **Quy tắc vàng**: Bất kỳ dữ liệu nào xuất ra `stdout` (dù chỉ là 1 dòng log `log("=== BẮT ĐẦU QUÉT ===")`) đều bị Hermes coi là thông điệp và gửi *verbatim* về Telegram Farm Alert.
  - Khi hệ thống bình thường, `stdout` **BẮT BUỘC PHẢI RỖNG 100%** (`sys.stdout` không có ký tự nào).
  - Không được gọi `print` rải rác trong các hàm kiểm tra lặp. Gom log vào buffer bộ nhớ, chỉ in ra `stdout` khi có hành động can thiệp thành công hoặc lỗi nghiêm trọng cần người can thiệp.
- **Tuân thủ Format Markdown Telegram**:
  - Tuyệt đối không in các thẻ HTML thô (`<b>`, `<code>`, `<i>`). Sử dụng định dạng Markdown chuẩn của Farm (`**bold**`, `` `code` ``).

## 7. Chẩn đoán Pool Imbalance qua SQLite (O(1), không cần API call)

**Key tables:**
- `call_logs`: `timestamp, status, model, account, connection_id, provider, combo_name, error_summary, duration`
- `quota_snapshots`: `connection_id, window_key, remaining_percentage, is_exhausted, next_reset_at, created_at`
- `provider_connections`: `id, email, provider, priority, is_active, test_status, provider_specific_data`

**Threshold logic:** `DEFAULT_QUOTA_THRESHOLD_PERCENT = 99` → `reachedThreshold = True` khi `remaining_percentage <= 1.0` (hoặc `is_exhausted = 1`). Acc còn dưới 1% vẫn không bị mark exhausted ngay nếu `fractionReported = False`.

**SQLite Diagnostic Queries:**

```python
import sqlite3
con = sqlite3.connect('file:C:/Users/Kibe/.omniroute/storage.sqlite?mode=ro', uri=True)
cur = con.cursor()

# 1. Phân phối calls 10 phút gần nhất (phát hiện monopoly)
rows = cur.execute('''
    SELECT account, COUNT(*) as calls,
           SUM(CASE WHEN status=200 THEN 1 ELSE 0 END) as ok,
           SUM(CASE WHEN status!=200 THEN 1 ELSE 0 END) as fail
    FROM call_logs
    WHERE timestamp >= datetime('now', '-10 minutes') AND provider = 'antigravity'
    GROUP BY account ORDER BY COUNT(*) DESC
''').fetchall()

# 2. Quota còn lại của Pro pool (check Pathology 8)
rows = cur.execute('''
    SELECT pc.email, qs.remaining_percentage, qs.is_exhausted, qs.next_reset_at
    FROM provider_connections pc
    JOIN quota_snapshots qs ON qs.connection_id = pc.id
      AND qs.id IN (
          SELECT MAX(id) FROM quota_snapshots
          WHERE window_key = 'gemini-3.8-flash-tiered' GROUP BY connection_id
      )
    WHERE pc.provider_specific_data LIKE '%Google AI Pro%'
    ORDER BY qs.remaining_percentage DESC
''').fetchall()

# 3. Tìm acc Active nhưng không có quota data (có thể là acc mới chưa được poll)
rows = cur.execute('''
    SELECT pc.id, pc.email FROM provider_connections pc
    WHERE pc.is_active=1 AND pc.provider='antigravity'
      AND pc.id NOT IN (SELECT DISTINCT connection_id FROM quota_snapshots)
''').fetchall()
con.close()
```

**Đọc window_key của antigravity:**
- Daily quota: `gemini-3.8-flash-tiered`, `gemini-3.7-flash-tiered`, `gemini-3.1-flash-lite`, v.v.
- Weekly quota: `gemini_weekly`, `claude_gpt_weekly`
- Claude models: `claude-sonnet-4-6`, `claude-opus-4-6-thinking`, `gpt-oss-120b-medium`
- Cùng 1 `remaining_percentage` cho tất cả models của 1 acc = bình thường (shared quota pool per-acc)

**Đọc `OmniRoute` DB location:** `C:/Users/Kibe/.omniroute/storage.sqlite` (WAL mode — đọc readonly OK ngay cả khi server đang chạy).

---

## 8. Xử lý Lỗi 422 Missing projectId \u0026 Phân loại Bẫy Nhãn "Business" Giả Cầy (2026-09-21)

### A. Bẫy Nhãn "Business" Giả Cầy vs Antigravity Restricted
- **Hiện tượng**: Dashboard OmniRoute hiển thị cột Plan là `Business` (màu xanh), nhưng trong ruột `provider_specific_data` lại mang `subscriptionTier: "Antigravity (Restricted)"`.
- **Bản chất**: Tài khoản bị Google hạn chế quyền (Restricted). Khi gọi các model mới như `gemini-3.8-flash-tiered`, Google sẽ trả về `403 Forbidden` hoặc giữ kết nối đến khi timeout. Nếu account này bị cấu hình `maxConcurrent: 2`, nó sẽ gây ra bão lỗi `429 Semaphore timeout after 30000ms`.
- **Hành động**: Luôn đối soát trường `subscriptionTier` trong `provider_specific_data`. Nếu chứa chuỗi `Restricted`, KHÔNG ĐƯỢC tin vào nhãn `plan: "Business"`.

### B. Quy trình Hồi sinh 100% Accounts dính Lỗi 422 (Missing Google projectId)
- **Triệu chứng**: Request gọi vào account trả về `[422]: Missing Google projectId for Antigravity account...`. Account chỉ pass đúng 1 lượt test probe khi tạo rồi sau đó fail 100%.
- **Cách hồi sinh O(1) không cần re-OAuth**:
  ```python
  patch_payload = {
      "projectId": "aicode-consumers",
      "providerSpecificData": {
          "clientProfile": "ide",
          "projectId": "aicode-consumers",
          "tier": "free-tier",
          "subscriptionTier": "Antigravity Starter Quota",
          "plan": "Antigravity starter quota",
          "apiKeyHealth": {}
      },
      "isActive": True
  }
  requests.patch(f"http://127.0.0.1:20129/api/providers/{cid}", json=patch_payload)
  ```
- **Kiểm chứng (Verification Probe)**: Bắn test request trực tiếp qua header `x-omniroute-connection-id: cid` với model `antigravity/gemini-3.8-flash-tiered`. Xác nhận HTTP 200 OK trước khi bổ sung lại account vào các combo (`ag-gemini-free-pool`, `ag-claude`, `ag-opus`).

---

## 9. Sentinel/Turnstile Block trên ChatGPT-Web vs Unrecoverable Refresh Token trên Antigravity (2026-09-22)

### A. ChatGPT-Web dính Sentinel / Turnstile Required (`banned` status)
- **Triệu chứng**:
  - Request tới ChatGPT-Web trả về: `ChatGPT blocked the request (Sentinel/Turnstile required). Try again later or open chatgpt.com in a browser to refresh state.`
  - OmniRoute tự động đánh dấu connection: `test_status: 'banned'`, `is_active: 0`.
- **Cạm bẫy Healer**:
  - Khi watchdog tự động mở GPM profile bằng Playwright và gọi `page.locator(...).click()`, script gặp lỗi:
    `Locator.click: Timeout 30000ms exceeded.`
  - Nguyên nhân: Trang `chatgpt.com` kích hoạt iframe Cloudflare Turnstile / OpenAI Sentinel challenge chặn tương tác. Playwright không thể bấm tiếp tục hoặc submit form nếu chưa vượt qua challenge.
- **Hành động chuẩn**:
  - Tuyệt đối KHÔNG retry mở Playwright GPM lặp đi lặp lại trong các tick ngắn vì sẽ làm proxy bị OpenAI đưa vào black-list và tích tụ tiến trình Chrome mồ côi.
  - Cần để proxy/IP hạ nhiệt hoặc mở profile tương tác để giải Turnstile trực tiếp.
  - Sau khi giải xong trên browser GPM, trích xuất cookie từ `Default/Network/Cookies` (với Chromium 130+ 32-byte header) nạp lại vào OmniRoute mà không cần gọi Playwright tự động.

### B. Antigravity dính `unrecoverable_refresh_error` & Giải pháp Credential-Injected Re-auth
- **Triệu chứng**:
  - OmniRoute trả về: `Refresh token rejected (unrecoverable_refresh_error). Please re-authenticate this account.`.
- **Cạm bẫy Healer thô (Silent OAuth đơn thuần)**:
  - Khi watchdog mở GPM profile chạy `perform_antigravity_oauth`, nếu script chỉ hỗ trợ click Account Chooser và Consent button:
    1. Khi Google hiển thị màn hình "Verify it's you" / yêu cầu gõ lại mật khẩu hoặc 2FA TOTP, script không có dữ liệu credentials sẽ bị kẹt và văng lỗi `Timeout bắt OAuth code` (120s).
    2. Account Chooser của Google dùng DOM đa hình: chỉ bắt `div[data-email=...]` sẽ miss khi Google render dưới dạng thẻ có `data-identifier`, `role="link"`, hoặc text button.
- **Giải pháp Credential-Injected Re-auth (Đã chuẩn hóa 2026-09-22)**:
  - **Truyền Credentials vào Healer**: Bắt buộc nạp `password` và `totp` secret từ `gmail_clean_v2.xlsx` vào hàm `perform_antigravity_oauth(cdp_addr, email, creds)`.
  - **Account Chooser đa hình**:
    ```python
    # Bắt đa hình selector
    acc_div = page.locator(f'div[data-email="{email.lower()}"]').first
    if acc_div.count() == 0:
        acc_div = page.locator(f'[data-identifier="{email.lower()}"]').first
    if acc_div.count() == 0:
        acc_div = page.get_by_text(email.lower()).first
    if acc_div.count() > 0 and acc_div.is_visible():
        acc_div.click(timeout=5000)
    ```
  - **Tự động điền Mật khẩu xác minh**:
    ```python
    pwd_inp = page.locator('input[name="Passwd"], input[type="password"]:visible').first
    if pwd_inp.count() > 0 and pwd_inp.is_visible() and password:
        pwd_inp.fill(password)
        page.locator('#passwordNext, button:has-text("Tiếp theo"), button:has-text("Next")').first.click()
    ```
  - **Tự động giải mã TOTP 2FA**:
    ```python
    if ("challenge/totp" in u or page.locator('#totpPin:visible').count() > 0) and totp_key:
        code = pyotp.TOTP(totp_key).now()
        page.locator('#totpPin, input[type="tel"]').first.fill(code)
        page.locator('#totpNext, button:has-text("Tiếp theo"), button:has-text("Next")').first.click()
    ```
  - **Tự động chọn Checkbox quyền (Select all permissions)**:
    Khi màn hình consent có các checkbox quyền riêng lẻ chưa được tick, bắt buộc duyệt qua các checkbox và check trước khi bấm "Tiếp tục" / "Cho phép".
  - **Telemetry bằng chứng (Gate 6)**: Nếu timeout bắt code, tự động chụp `page.screenshot(path=f"C:/Users/Kibe/AppData/Local/hermes/cache/oauth_err_{email}.png")` để Coordinator có bằng chứng thị giác O(1) kiểm tra nguyên nhân.
  - **Xử lý Bẫy Bot-check "Verify it's you - Confirm you're not a robot" Bằng Audio reCAPTCHA Solver (User Correction 2026-09-24)**:
    - Khi Google bật màn hình bot-check: `Sign in with Google | Verify it's you | Confirm you're not a robot`:
    - KHÔNG ĐƯỢC fail-fast bỏ cuộc hay kết luận bế tắc! Hệ thống đã có sẵn module `solve_recaptcha_audio(page)` (tích hợp `pydub`, `speech_recognition`, FFmpeg).
    - Tự động bắt `enterprise/bframe` -> click biểu tượng âm thanh -> tải MP3 -> convert WAV -> Google Speech-to-Text -> điền đáp án và submit xác minh.
  - **Tự Động Đọc Mã OTP Gửi Về Recovery Email Qua IMAP (User Correction 2026-09-24)**:
    - Khi Google chuyển sang màn hình Security Checkpoint (*"Choose how you want to sign in: Get a verification code at <recovery_email>"*):
    - KHÔNG ĐƯỢC dừng lại! Codebase đã có sẵn module đọc IMAP từ `D:/Taadaa/add mail khoi phuc/read_otp_mail.py` và `automation_core/mailbox.py` (`fetch_latest_otp`), sử dụng biến môi trường `OTP_MAIL_USER` (`thanhdatbui1995@gmail.com`) và `OTP_MAIL_APP_PASSWORD`.
    - Tự động click vào phương thức nhận mã -> lắng nghe và bóc tách OTP 6 số qua IMAP SSL (`imap.gmail.com:993`) -> điền vào `input[name="code"]` / `#idvPin` và hoàn tất OAuth.
  - **Canary Re-auth & Phone Checkpoint Protection Gate (2026-09-24)**:
    - Khi chạy canary test re-auth đơn lẻ (ví dụ qua `refresh_antigravity_account_via_gpm(pid, email, None, creds)` trong `cron_chatgpt_web_pool_watchdog.py`):
    - **Bẫy Audio reCAPTCHA Disabled**: Nếu nút audio challenge bị vô hiệu hóa (`rc-button-disabled` hoặc IP proxy bị Google hạn chế audio), module click timeout 5000ms.
    - **Bảo Vệ Tài Khoản Khỏi Phone Checkpoint**: Khi Google kích hoạt màn hình yêu cầu xác minh qua số điện thoại (*"Google yêu cầu xác minh qua SỐ ĐIỆN THOẠI (Phone Checkpoint)"*), script phải lập tức dừng luồng (`ok=False`) để bảo vệ tài khoản, tránh rủi ro checkpoint cứng hoặc khóa vĩnh viễn.
    - **Cổng Kiểm Thử OmniRoute & SQLite Gatekeeper**: CHỈ KHI re-auth trả về `ok=True` VÀ gọi `POST /api/providers/{cid}/test` trả về `valid: true`, mới được cập nhật `C:\Users\Kibe\.omniroute\storage.sqlite` (`UPDATE provider_connections SET is_active=1, test_status='active', last_error=NULL, last_error_at=NULL WHERE id=?`). Nếu `ok=False`, tuyệt đối giữ nguyên trạng thái inactive/broken để router không route nhầm traffic vào tài khoản đang checkpoint.
    - **Quy Trình Dọn Dẹp GPM Profile & Orphan Chrome**: Sau khi canary kết thúc (dù thành công hay thất bại), luôn gọi API dừng profile `POST http://127.0.0.1:19995/api/v3/profiles/stop/{pid}` và audit qua `Get-CimInstance Win32_Process` lọc `CommandLine` chứa profile ID để đảm bảo không rò rỉ tiến trình Chromium chạy ngầm.

### D. Tích tụ Chromium mồ côi (Orphan Process Leak) & Bẫy GPM Close API Ảo
- **Bẫy GPM API Close/Stop Ảo (`success: true` nhưng Chromium vẫn sống)**:
  - Khi gọi `GET /api/v3/profiles/close/{pid}` và `GET /api/v3/profiles/stop/{pid}`, GPM API đều trả về `{"success": true, "message": "OK"}`. Tuy nhiên, API này chỉ cập nhật trạng thái trong database GPM, còn các tiến trình Chromium (`chrome.exe` trong `gpm_browser_chromium_core_127` hoặc `142`) thường xuyên bị bỏ quên và tiếp tục chạy ngầm (GPU/Crashpad/Utility).
  - Sau vài ca chạy, máy có thể tích tụ 30-200+ tiến trình Chromium mồ côi gây tràn RAM và giữ khóa `SingletonLock`.
- **CẤM TUYỆT ĐỐI `taskkill /f /im chrome.exe`**: Lệnh này sẽ giết nhầm toàn bộ trình duyệt Google Chrome chính của User (`C:\Program Files\Google\Chrome\Application\chrome.exe`), làm sập các tab làm việc của người dùng.
- **Quy tắc dọn dẹp chuẩn an toàn qua Python psutil**:
  ```python
  import psutil
  for p in psutil.process_iter(["pid", "name", "exe", "cmdline"]):
      name = (p.info["name"] or "").lower()
      if "chrome" in name:
          exe = (p.info["exe"] or "").lower()
          cmd = " ".join(p.info["cmdline"] or []).lower()
          # CHỈ kill khi exe hoặc cmdline nằm trong thư mục GPMLogin
          if "gpmlogin" in exe or "gpm_browser" in exe or "gpmlogin" in cmd or "gpm_browser" in cmd:
              try:
                  p.kill()
              except Exception:
                  pass
  ```
- **Hạ Profile 2 Pha + Force-Kill Bắt Buộc**: Khi script thao tác xong với GPM API, gọi đồng thời cả 2 endpoint `close/{pid}` + `stop/{pid}`, sau đó quét `psutil` diệt sạch tiến trình con còn sót lại.
  1. **Tra cứu `last_error` trong `storage.sqlite`**:
     ```python
     SELECT provider, name, is_active, test_status, last_error 
     FROM provider_connections WHERE name LIKE '%<email>%'
     ```
     Phân biệt rõ: Turnstile/Sentinel (`banned`) vs Token revoked (`unrecoverable_refresh_error`).
  2. **Kiểm tra Session Cookies trong SQLite GPM Profile**:
     Đọc file `Default/Network/Cookies` của profile tương ứng trong `C:\Users\Kibe\AppData\Local\Programs\GPMLogin\profile\<ProfilePath>`.
     Nếu đủ 4 session cookie (`SID`, `SSID`, `HSID`, `SAPISID`) mà vẫn dính `Timeout bắt OAuth code` $\rightarrow$ Xác nhận Google vẫn giữ session nhưng chặn bằng challenge xác minh danh tính ("Verify it's you" / gõ lại mật khẩu).
  3. **Đánh giá tải và routing combo**:
     Kiểm tra tỷ lệ khả dụng của pool (`16/17` Web, `111/116` Antigravity). Xác nhận rõ: Dung lượng pool vẫn dư thừa $>94\%$, các combo (`ag-claude`, `ag-gemini-free-pool`, `chatgpt-web-pool`) hoàn toàn không bị nghẽn hay thiếu tải.
- **Cấu trúc phản hồi 3 ý bắt buộc**:
  - **Tình trạng Pool**: Tỷ lệ active thực tế & kết luận combo có an toàn không.
  - **Nguyên nhân gốc rễ từng nhóm nick lỗi**: Turnstile challenge trên IP proxy (ChatGPT) vs Re-verification challenge của Google (Antigravity).
  - **Hành động & Quyết định**: Nêu rõ không cần can thiệp gấp vì pool dư tải; đưa ra lựa chọn can thiệp cụ thể nếu user muốn đưa pool về 100%.

### D. Tích tụ Chromium mồ côi (Orphan Process Leak) từ Watchdog Healer
- **Hiện tượng**: Khi watchdog chạy mở profile GPM rồi đóng bằng `requests.get(f"{GPM_API}/profiles/close/{pid}")`, nếu Playwright gặp exception/timeout hoặc proxy lag, Chromium thường bỏ lại các tiến trình con (GPU, Renderer, Utility, Crashpad). Sau vài ngày có thể tích tụ hơn 200+ tiến trình Chrome mồ côi chiếm dụng RAM và giữ khóa `SingletonLock`.
- **Hành động**: Định kỳ rà soát số lượng tiến trình GPM Chrome (`CommandLine -like '*GPMLogin\\gpm_browser*'`) và sử dụng cơ chế dọn dẹp theo `--user-data-dir` hoặc Scanned Kill để bảo vệ tài nguyên máy.

---

## 10. Kỹ thuật Tra cứu & Phân loại Danh sách Tài khoản theo Tier (Google AI Pro vs Starter vs Restricted) O(1) (2026-09-24)

### A. Cạm bẫy môi trường & Kỷ luật O(1)
- **Môi trường Windows MSYS/Git-Bash KHÔNG CÓ `jq`**: Lệnh pipe qua `jq` sẽ trả về `/usr/bin/bash: line 3: jq: command not found`.
- **CẤM TUYỆT ĐỐI dùng `grep -rn` quét diện rộng**: Quét trên `AppData/Local` hoặc `C:\Users\Kibe` sẽ chạm trần timeout 180s và vi phạm trực tiếp Farm Safety & O(1) Discipline.
- **Phân định rõ Source of Truth**:
  - GPM Profiles (`http://127.0.0.1:19995/api/v3/profiles`): Chỉ quản lý profile trình duyệt, proxy port, và email hiển thị. GPM **KHÔNG** lưu thông tin subscription tier hay quota Google AI Pro.
  - OmniRoute (`http://127.0.0.1:20129/api/providers` hoặc SQLite `C:/Users/Kibe/.omniroute/storage.sqlite`): **Source of Truth duy nhất** về OAuth token, subscription tier thật sự của Google (`g1-pro-tier`), trạng thái active/quota và mapping vào các combo (`ag-gemini-pool-3`).

### B. Dấu hiệu nhận diện chuẩn xác 3 Tier Antigravity trong OmniRoute
1. **Google AI Pro (Gói Pro trả phí thật sự - Hiện có 18 accounts)**:
   - `provider`: `"antigravity"`
   - `providerSpecificData.tier`: `"g1-pro-tier"`
   - `providerSpecificData.subscriptionTier`: `"Google AI Pro"`
   - `providerSpecificData.plan`: `"Pro"`
   - Được định tuyến ưu tiên trong combo `ag-gemini-pool-3` (Tier 1 Pro chạy Gemini 3.8 Flash Tiered).
2. **Antigravity Starter Quota (Gói Free Tier thông thường)**:
   - `providerSpecificData.tier`: `"free-tier"`
   - `providerSpecificData.subscriptionTier`: `"Antigravity Starter Quota"`
   - `providerSpecificData.plan`: `"Antigravity starter quota"`
   - Nằm trong combo `ag-gemini-free-pool` (Tier 2 Free fallback).
3. **Antigravity Restricted / Standard-Tier (Acc bị Google hạn chế hoặc dính nhãn Business giả)**:
   - `providerSpecificData.tier`: `"standard-tier"`
   - `providerSpecificData.subscriptionTier`: `"Antigravity (Restricted)"`
   - `providerSpecificData.plan`: `"Business"` hoặc `"Antigravity (restricted)"`
   - Không được để lọt vào combo Pro.

### C. Snippet O(1) Tra cứu Danh sách Google AI Pro (Node.js & Python)

**Cách 1: One-liner Node.js (Fetch trực tiếp REST API :20129, không cần jq):**
```bash
node -e '
fetch("http://localhost:20129/api/providers")
  .then(r => r.json())
  .then(data => {
    const pros = data.connections.filter(c => 
      c.provider === "antigravity" && 
      (c.providerSpecificData?.tier === "g1-pro-tier" || c.providerSpecificData?.subscriptionTier === "Google AI Pro")
    );
    console.log(`Total Google AI Pro: ${pros.length}`);
    pros.forEach((c, i) => console.log(`${i + 1}. ${c.email || c.name} | Priority: ${c.priority} | Active: ${c.isActive}`));
  });
'
```

**Cách 2: SQLite Query O(1) (Đọc trực tiếp file storage.sqlite, siêu nhanh):**
```python
import sqlite3, json

con = sqlite3.connect('file:C:/Users/Kibe/.omniroute/storage.sqlite?mode=ro', uri=True)
cur = con.cursor()
rows = cur.execute('''
    SELECT email, priority, is_active, test_status, provider_specific_data
    FROM provider_connections
    WHERE provider = "antigravity"
    ORDER BY priority ASC
''').fetchall()

pros = []
for email, priority, is_active, test_status, psd_str in rows:
    psd = json.loads(psd_str or "{}")
    if psd.get("tier") == "g1-pro-tier" or psd.get("subscriptionTier") == "Google AI Pro":
        pros.append((email, priority, is_active, test_status))

print(f"Total Google AI Pro: {len(pros)}")
for i, (email, prio, act, st) in enumerate(pros, 1):
    print(f"{i}. {email} | Priority: {prio} | Active: {act} | Status: {st}")
con.close()
```



