# Antigravity Free-Tier vs Standard-Restricted Diagnosis

## 1. The "Business" Label Trap in OmniRoute UI
- **Hiện tượng**: Trên giao diện OmniRoute (:20129) tại trang Dashboard / Quota / Providers, một số tài khoản Google Antigravity hiển thị plan/tier là **`Business`**, khiến người vận hành lầm tưởng đây là tài khoản Google Workspace Business trả phí.
- **Nguyên nhân code**: Trong `open-sse/services/usage/antigravity.ts` (hàm `mapCodeAssistTierIdToLabel` dòng 319 và `mapSubscriptionTierStringToPlanLabel` dòng 333):
  ```ts
  if (upper.includes("BUSINESS") || upper.includes("STANDARD")) return "Business";
  ```
- Khi tài khoản Google không đủ điều kiện nhận gói Starter Quota tự động từ Google, endpoint `/v1internal:loadCodeAssist` trả về `ineligibleTiers` và rớt vào `standard-tier` với tên hiển thị `Antigravity (Restricted)`. OmniRoute gộp chung xâu `STANDARD` thành `Business`.

## 2. Sự thật về tài khoản Free-Tier (Starter Quota)
- **Tài khoản Free thường HOÀN TOÀN DÙNG ĐƯỢC**:
  - Google Antigravity cấp gói Starter Quota miễn phí cho các tài khoản Google thông thường đủ điều kiện.
  - Trong SQLite `provider_connections`, tài khoản free hợp lệ có:
    - `tier`: `free-tier`
    - `subscriptionTier`: `Antigravity Starter Quota`
    - `plan`: `Antigravity starter quota`
    - `projectId`: Tự động được Google cấp hoặc liên kết qua `cloudaicompanionProject`.
  - Bằng chứng thực tế trong pool: Các tài khoản `thanhdatbui1995`, `alicelmoralesjvcrj`, `brittanysbarneskn2xa`, `hoangvy27091999`, `genewhicksb9906`... đều xử lý thành công hàng chục đến hàng trăm request `gemini-3.8-flash-tiered` khi tải tràn xuống cuối combo.

## 3. Tại sao một số tài khoản thường bị lỗi 422 & 403 (Ground Truth đối chiếu)
- **Cơ chế `ineligibleTiers` từ Google `loadCodeAssist`**:
  - Khi token được gửi lên `POST https://cloudcode-pa.googleapis.com/v1internal:loadCodeAssist`:
    + Tài khoản Free hợp lệ (`brittanys`, `alicel`): Google trả về `currentTier: free-tier`, `allowedTiers: [free-tier, standard-tier]`, và **tự động gán `cloudaicompanionProject: "aicode-consumers"`**.
    + Tài khoản lỗi (`lamngocdiep`, `lequynh`, `vothimyhanh`, `yenduypham`): Google trả về `ineligibleTiers` với `reasonCode: "VALIDATION_REQUIRED"`:
      ```json
      "ineligibleTiers": [{
        "reasonCode": "VALIDATION_REQUIRED",
        "reasonMessage": "Your current account is not eligible for Antigravity. Verify your account to continue.",
        "tierId": "free-tier",
        "tierName": "Antigravity",
        "validationErrorMessage": "Verify your account to continue.",
        "validationUrl": "https://accounts.google.com/signin/continue?continue=https://developers.google.com/gemini-code-assist/auth/auth_success_gemini..."
      }]
      ```
    + Khi `free-tier` bị block do `VALIDATION_REQUIRED`, Google **không trả về `currentTier` hay `paidTier`**, mà chỉ trả về duy nhất `allowedTiers: [{ id: "standard-tier", userDefinedCloudaicompanionProject: true }]`.
- **Lỗi 422 (`missing_project_id`)**:
  - Do `standard-tier` yêu cầu BYOP (`userDefinedCloudaicompanionProject: true`), Google **không bao giờ tự cấp `cloudaicompanionProject`**.
  - Trường `project_id` trong connection bị `null`/rỗng. Khi gửi request tới `antigravity.ts` executor, OmniRoute auto-discovery qua `loadCodeAssist` không tìm thấy project nên ném: `[422]: Missing Google projectId for Antigravity account...`.
- **Bẫy lỗi 403 (`PERMISSION_DENIED` / `project_route_error`)**:
  - **CẤM gán cứng `projectId: "aicode-consumers"` khi chưa giải quyết cờ `VALIDATION_REQUIRED`**:
  - `aicode-consumers` là project dùng chung của Google cấp cho cả Google AI Pro lẫn tài khoản `free-tier` hợp lệ.
  - Tuy nhiên, khi một tài khoản đang bị cắm cờ `VALIDATION_REQUIRED` (chưa đủ điều kiện entitlement vào `free-tier`), backend Google kiểm tra quyền sử dụng quota của `aicode-consumers` và trả về HTTP **`403 Forbidden` / `PERMISSION_DENIED`**.

## 4. Kỷ luật kiểm tra & Quy trình xử lý (Coordinator Checklist)
1. **Truy vấn nhanh O(1) qua Management API (:20129)**:
   - **CẤM đoán mò hay quét SQL**: OmniRoute cung cấp endpoint chính thức:
     - Lấy toàn bộ danh sách connections: `GET http://localhost:20129/api/providers` (lưu ý: các path `/api/connections`, `/api/provider-connections`, `/api/accounts` đều là **404**).
     - Test live credential một connection: `POST http://localhost:20129/api/providers/:id/test` với body `{}`.
   - Script inspect nhanh toàn pool:
     ```python
     import urllib.request, json
     with urllib.request.urlopen('http://localhost:20129/api/providers') as resp:
         data = json.loads(resp.read().decode())
     conns = [c for c in data['connections'] if c.get('provider') == 'antigravity']
     active = [c for c in conns if c.get('isActive')]
     expired = [c for c in conns if c.get('testStatus') == 'expired']
     print(f"Total: {len(conns)}, Active: {len(active)}, Expired: {len(expired)}")
     ```
2. **Phân biệt `tokenExpiresAt` vs `testStatus: 'expired'`**:
   - `tokenExpiresAt` / `expiresAt`: Chỉ là hạn của Access Token tạm thời (~3600s/1h). OmniRoute tự động refresh access token ngầm bằng Refresh Token, **đây KHÔNG PHẢI là tài khoản bị hỏng**.
   - `testStatus: 'expired'`: Xảy ra khi Google thu hồi hẳn Refresh Token (`unrecoverable_refresh_error` / `Token invalid or revoked`). Lúc này OmniRoute tự động set `isActive: false` để cách ly khỏi router, không làm nghẽn pool.
3. **CẤM quy chụp vội vã & CẤM sửa codebase**: Khi thấy 1-2 tài khoản free bị lỗi hoặc expired, tuyệt đối CẤM kết luận "toàn bộ pool bị lỗi" hay "hỏng hệ thống". Phải kiểm tra tỷ lệ active, đặc biệt là nhóm `g1-pro-tier` (Google AI Pro) và `free-tier` còn lại.
4. **Kiểm tra trạng thái Tier**:
   - Nếu `tier = 'free-tier'`: Tài khoản hoạt động bình thường theo cơ chế Natural Spillover ở đuôi combo.
   - Nếu `tier = 'standard-tier'` / `sub = 'Antigravity (Restricted)'`: Xác định đây là tài khoản chưa vượt qua checkpoint xác thực của Google (`VALIDATION_REQUIRED`).
3. **Quy trình gỡ cờ `VALIDATION_REQUIRED` để phục hồi `free-tier`**:
   - Mở profile GPM tương ứng của tài khoản trên trình duyệt.
   - Truy cập link xác minh nhận từ API hoặc thông báo bảo mật:
     `https://accounts.google.com/signin/continue?continue=https://developers.google.com/gemini-code-assist/auth/auth_success_gemini`
   - Hoàn tất các bước xác minh danh tính của Google (xác nhận thiết bị, xác minh số điện thoại hoặc đồng ý cảnh báo bảo mật).
   - Truy cập `https://codeassist.google.com` để chấp thuận Điều khoản dịch vụ cá nhân (Personal ToS) nếu được hỏi.
   - Sau khi hoàn tất trên browser, vào OmniRoute Dashboard bấm **Refresh Token** (hoặc gọi API refresh token).
   - Khi đó `loadCodeAssist` sẽ tự động nhận `currentTier = "free-tier"`, Google tự trả về `cloudaicompanionProject = "aicode-consumers"`, tài khoản tự động được gán `tier: 'free-tier'`, `subscriptionTier: 'Antigravity Starter Quota'` và dùng bình thường ở đuôi combo mà không cần tự tạo GCP project.

## 5. Re-Authentication cho tài khoản "Token expired" (`invalid_grant` / `unrecoverable_refresh_error`)
1. **Hiện tượng**: Trên dashboard Quota hoặc Providers, thẻ tài khoản hiện dòng chữ đỏ **`Token expired`** kèm icon đồng hồ cảnh báo vàng. Trong DB, `test_status = 'expired'`, `is_active = 0`, và `last_error` ghi:
   `Refresh token rejected (unrecoverable_refresh_error). Please re-authenticate this account.`
2. **Nguyên nhân**: Google thu hồi refresh token (do đổi mật khẩu, đăng xuất phiên trên thiết bị, hoặc token bị Google invalidate theo chính sách bảo mật).
3. **Bẫy bỏ qua (Skip Trap) trong `run_oauth_s7_pipeline.py`**:
   - Trong `run_oauth_s7_pipeline.py`, hàm `process_account(acc)` kiểm tra:
     ```python
     if email in status_data.get("omniroute_success", {}):
         return {"mid": mid, "email": email, "status": "ALREADY_SUCCESS", "conn_id": cid}
     ```
   - Nếu tài khoản trước đó đã từng nạp thành công và có trong `oauth_pipeline_status.json`, script sẽ **bỏ qua ngay lập tức với `ALREADY_SUCCESS`** mà không thực hiện re-authenticate!
   - **Khắc phục**: Trước khi chạy re-auth, bắt buộc xóa key email đó khỏi `omniroute_success` trong `D:\Taadaa\GPM auto\config\oauth_pipeline_status.json`.
4. **Quy trình Re-Authentication chuẩn**:
   - **Xác minh Profile GPM**: Kiểm tra folder profile thực tế trên đĩa (ví dụ `C:\Users\Kibe\AppData\Local\Programs\GPMLogin\profile\p_m69_nguyenvysfj3102`). Nếu tồn tại, script sẽ dùng trực tiếp; nếu không, fallback query `ProfilePath` UUID trong `profile_data.db`.
   - **Hardware Ground Truth**: Chạy `adb -s <serial> shell dumpsys account` đảm bảo tài khoản Google tồn tại trên máy S7 để sẵn sàng nhận Google Prompt PIN.
   - **Chạy Re-Auth**: Mở browser persistent context qua đúng Singbox proxy của máy (`20000 + (port - 5100)`), điều hướng `auth_url`, duyệt Prompt trên S7, bắt code exchange gửi lên OmniRoute.
   - **Cập nhật OmniRoute**: API exchange của OmniRoute sẽ cập nhật refresh token mới vào connection ID hiện có trong SQLite `provider_connections`, tự động reset `test_status: "active"`, xóa `last_error` và kích hoạt lại tài khoản trong combo `ag-gemini-pool-3` mà không làm duplicate connection.

## 6. Phục hồi nhanh hàng loạt tài khoản token sống bị TẮT công tắc & rớt vào standard-tier (2026-09-08)
1. **Hiện tượng**: Operator thấy nhiều tài khoản bị chuyển sang công tắc TẮT (`is_active = 0`) và hiển thị nhãn vàng "Business" trên UI Quota/Providers với `projectId` bị rỗng.
2. **Kiểm tra độ sống của token (Test Token Liveness)**:
   - Trước khi quyết định re-auth, bắt buộc kiểm tra live qua `POST /api/providers/{id}/test`.
   - Nếu API trả về `valid: True` hoặc `statusCode: 400 (probe_inconclusive)` kèm `refreshed: True` $\rightarrow$ Refresh token Google upstream **vẫn hoàn toàn hợp lệ 100%**.
3. **CẤM mở GPM profile re-auth bừa bãi**:
   - Khi token còn sống, việc mở lại profile GPM sau khi cookie đã nguội qua IP proxy mới sẽ kích hoạt **Hard SMS Checkpoint** (`challenge/iap`). Google sẽ khóa chặt và đòi SĐT nhận SMS, gây hỏng phiên.
4. **Phục hồi O(1) qua Management API**:
   - Gọi API `PUT /api/providers/{id}` gán project chung và chuyển tier về Starter Quota:
     ```python
     payload = {
         'isActive': True,
         'projectId': 'aicode-consumers',
         'providerSpecificData': {
             **existing_psd,
             'projectId': 'aicode-consumers',
             'tier': 'free-tier',
             'subscriptionTier': 'Antigravity Starter Quota'
         }
     }
     requests.put(f'http://localhost:20129/api/providers/{cid}', json=payload)
     ```
   - Thẻ tài khoản trên Dashboard lập tức chuyển từ vàng "● Business" sang xanh "● Starter quota", bật lại công tắc (`isActive = True`).
   - **BẪY CHIẾN LƯỢC COMBO CỰC KỲ NGUY HIỂM (2026-09-22)**: TUYỆT ĐỐI CẤM nạp tài khoản này vào `ag-gemini-pool-3` (Tier 1 Pro)! Combo này dùng chiến lược `cache-optimized` với `sticky: 8` và Rendezvous Hashing ghim chặt session vào 1 acc, sẽ gây nổ lỗi `Semaphore timeout after 30000ms`.
   - **ĐÍCH ĐẾN BẮT BUỘC**: CHỈ ĐƯỢC nạp vào các combo dùng chiến lược **`p2c`** (`ag-gemini-free-pool` và `ag-claude`). Thuật toán `p2c` tự động san đều tải ngẫu nhiên giữa 70–96 targets, đảm bảo không tài khoản nào bị dồn 2–3 requests đồng thời, nuốt trọn cả context ngắn lẫn context siêu nặng 30k–80k tokens mà không lo kẹt semaphore.
