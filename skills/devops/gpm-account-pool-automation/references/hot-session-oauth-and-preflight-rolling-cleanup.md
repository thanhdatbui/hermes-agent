# Hot-Session OAuth & Preflight S7 Rolling Cleanup

## 1. Preflight S7 Rolling Cleanup (`preflight_s7_rolling_cleanup.py`)

### Mục đích:
Samsung S7 giới hạn tối đa 5 tài khoản Google active (`dumpsys account`). Giữ quá 5 acc gây tràn RAM, crash Google Play Services ngầm và kích hoạt cờ *Google Device Farm Abuse*. Tuy nhiên, cấm gỡ tài khoản non hoặc chưa đủ điều kiện.

### 3 Safety Gates Bắt Buộc Trước Khi Gỡ Cuốn Chiếu:
1. **Gate 1 - Đã kích hoạt 2FA Google Authenticator**: Kiểm tra cột `2fa` trong `gmail_clean_v2.xlsx` hoặc `master_gmail_manager.xlsx`. Secret key $\ge 16$ ký tự Base32, có khả năng tự sinh TOTP độc lập qua `pyotp`.
2. **Gate 2 - Đã nạp thành công OAuth Antigravity / OmniRoute**: Kiểm tra danh sách `omniroute_success` trong `D:\Taadaa\GPM auto\config\oauth_pipeline_status.json`.
3. **Gate 3 - Tuổi tài khoản $\ge 30$ ngày**: Tính từ `created_date` trong `gmail_clean_v2.xlsx`. Tuyệt đối không gỡ tài khoản non dưới 30 ngày (tránh bị Google coi là "Device Churn").

### Quy Trình Thao Tác An Toàn:
- Trích xuất danh sách tài khoản hiện hữu trên S7:
  ```bash
  adb -s <serial> shell dumpsys account
  # Regex: Account\s*\{\s*name=([^,\s]+),\s*type=com\.google\s*\}
  ```
- Nếu `count < 5`: Đủ điều kiện đăng ký / nạp thêm acc mới (`status: OK`).
- Nếu `count >= 5`: Lọc các acc thỏa mãn cả 3 Gates. Chọn acc **CŨ NHẤT** (tuổi cao nhất) để gỡ cuốn chiếu 1 acc. Nếu không có acc nào thỏa mãn cả 3 Gates -> `FULL_NO_ELIGIBLE_CLEANUP`, dừng và cảnh báo, không gỡ bừa.
- Thao tác gỡ: Dưới `acquire_device_lock(machine=..., serial=..., project="gpm-cleanup", force_preempt=True)` mở `android.settings.SYNC_SETTINGS` trên S7 và thao tác qua Android OS. **TUYỆT ĐỐI CẤM** vào `myaccount.google.com/device-activity` để gỡ từ xa qua web.

---

## 2. Hot-Session OAuth OmniRoute Hook (`hot_session_oauth.py`)

### Vấn đề của Cold-Session OAuth:
Trước đây, sau khi login Google và bật 2FA thành công trên GPM, script đóng trình duyệt. Khi chạy bước OAuth riêng biệt, trình duyệt phải khởi động lại (cold start), Google dễ đòi re-auth password, kích hoạt Sensitive Action Cooldown hoặc yêu cầu xác minh lại.

### Giải pháp Hot-Session:
Nối thẳng bước nạp OAuth OmniRoute (`http://127.0.0.1:20129`) ngay trong active Playwright page đang mở sau khi bật 2FA, không đóng browser:

1. **Lấy Authorize URL**:
   `GET http://127.0.0.1:20129/api/oauth/antigravity/authorize?redirect_uri=http://127.0.0.1:20129/callback`
   Nhận `authUrl`, `state`, `codeVerifier`.
2. **Bắt Authorization Code qua Event Listener**:
   Lắng nghe request sự kiện trong page:
   ```python
   def on_request(req):
       if "/callback" in req.url and "code=" in req.url:
           # parse and extract code
   page.on("request", on_request)
   ```
3. **Điều Hướng & Tự Động Consent**:
   - `page.goto(auth_url)`
   - Nếu hiện Account Chooser: Click chọn đúng `div[data-email="{email}"]`.
   - Nếu hiện màn hình cấp quyền: Click nút "Cho phép" / "Allow" / "Tiếp tục" / `#submit_approve_access`.
4. **Exchange Token & Gán Proxy 1:1**:
   - `POST http://127.0.0.1:20129/api/oauth/antigravity/exchange` với `code`, `redirectUri`, `codeVerifier`, `state`.
   - Nhận `connection_id`.
   - Tìm proxy tương ứng với cổng port của máy và gán:
     `PUT http://127.0.0.1:20129/api/settings/proxies/assignments` với `scope: account`, `scopeId: conn_id`, `proxyId: px_id`.
5. **Sync Models & Nối Vào Combo**:
   - `POST http://127.0.0.1:20129/api/providers/{conn_id}/sync-models`.
   - Nối connection vào combo pool qua hàm `append_connections([{"cid": conn_id, "email": email, "port": port}])` (giữ nguyên tên combo `ag-gemini-pool-3`).
6. **Cập nhật Trạng Thái**:
   - Ghi nhận `hot_session: True`, `status: HTTP_200_OK` vào `oauth_pipeline_status.json`.
