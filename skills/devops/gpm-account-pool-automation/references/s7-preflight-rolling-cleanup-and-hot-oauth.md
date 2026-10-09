# S7 Preflight Rolling Cleanup & Hot-Session OAuth Pipeline Integration

Tài liệu này ghi lại kiến trúc, chuẩn dữ liệu và cách vận hành của hai module tự động hóa:
1. `preflight_s7_rolling_cleanup.py`: Kiểm tra trần 5 tài khoản Google trên Samsung S7 trước khi reg và tự động gỡ cuốn chiếu 1 tài khoản cũ nhất thỏa 3 Safety Gates.
2. `hot_session_oauth.py`: Tận dụng phiên nóng (Hot Session) ngay sau khi bật 2FA trên Playwright CDP để cấp quyền OAuth Antigravity nạp thẳng vào OmniRoute (port 20129) và gán combo `ag-gemini-pool-3`.

---

## 1. Module 1: Preflight S7 Rolling Cleanup (`preflight_s7_rolling_cleanup.py`)

### A. Mục Đích & Nguyên Lý
- Thiết bị Samsung Galaxy S7 (Android 8.0) chỉ nên lưu giữ tối đa 3 đến 5 tài khoản Google active. Nếu vượt trần $\ge 5$, Google Play Services ngầm bị nặng tải và kích hoạt cảnh báo farm abuse.
- Trước khi chạy chu kỳ reg tài khoản mới trên S7, module kiểm tra số lượng tài khoản Google hiện có qua ADB.
- Nếu số lượng $\ge 5$, module tự động đối soát cơ sở dữ liệu để tìm ra tài khoản CŨ NHẤT thỏa mãn đồng thời 3 Safety Gates để gỡ bỏ.

### B. Kỹ Thuật Kiểm Tra Tài Khoản Trên S7 (`get_s7_google_accounts`)
- Thực thi lệnh ADB:
  ```bash
  adb -s <serial> shell dumpsys account
  ```
- Trích xuất email bằng regex chuẩn:
  ```python
  import re
  pattern = r"Account \{name=([^,\s]+),\s*type=com\.google\}"
  emails = [m.strip().lower() for m in re.findall(pattern, dumpsys_output)]
  ```

### C. Quy Tắc Gỡ Cuốn Chiếu Cập Nhật (`evaluate_s7_accounts` — Operator Invariant 2026-10-02)
Tài khoản được đánh giá theo thứ tự ưu tiên:
1. **Ưu tiên 1 (Đã lên GPM thành công — Operator Invariant):** Nếu tài khoản đã có profile thuộc Group 10 (`Google_Live_Ready` trong `profile_data.db`) HOẶC đã có `omniroute_success` trong `oauth_pipeline_status.json` ➔ **Cho phép gỡ khỏi S7 ngay lập tức** để giải phóng slot S7 đẻ nick mới (không bắt buộc đợi đủ 30 ngày).
2. **Ưu tiên 2 (Tài khoản ngâm lâu):** Nếu chưa có thông tin GPM nhưng có 2FA hợp lệ và tuổi ngâm $\ge 30$ ngày ➔ Cho phép gỡ cuốn chiếu theo thứ tự ngày tạo cũ nhất.
3. **Kỷ luật báo cáo lỗi:** Nếu gỡ thất bại (`REMOVE_FAILED`), runner bắt buộc báo `FAILED` (Lỗi script gỡ account) để can thiệp; tuyệt đối cấm nuốt vào nhóm `SKIPPED`.
4. **Bẫy UI Android S7:** Khi mở `SYNC_SETTINGS`, cấm tìm bấm node có text `"Google"` vì sẽ bấm trúng phụ đề của tài khoản đầu tiên; bắt buộc tìm đúng email mục tiêu để tap.

Nếu có nhiều ứng viên, ưu tiên nhóm GPM Live trước rồi sắp xếp theo ngày tạo tăng dần. Nếu không có tài khoản nào thỏa mãn, module trả về `FULL_NO_ELIGIBLE_CLEANUP` để safe-skip máy đó.

### D. Quy Trình Gỡ Tài Khoản Khỏi S7 (`remove_account_adb`)
- **Khóa thiết bị:** BẮT BUỘC sử dụng `acquire_device_lock`:
  ```python
  with acquire_device_lock(machine=str(machine_id), serial=serial, project="gpm-cleanup", force_preempt=True):
      # Thao tác gỡ trên S7
  ```
- **CẤM TUYỆT ĐỐI:** Không bao giờ vào web `myaccount.google.com/device-activity` để bấm "Đăng xuất thiết bị này" từ xa (kích hoạt lỗi cấm 7 ngày `rrk=77`).
- **Thực thi trên thiết bị:** Thực hiện qua Settings S7 (`android.settings.SYNC_SETTINGS`) hoặc AccountManager intent, tap vào tài khoản $\rightarrow$ Menu $\rightarrow$ Xóa tài khoản khỏi thiết bị.
- **Hỗ trợ cờ `--dry-run`:** Ở chế độ dry-run, chỉ in ra candidate và xác nhận số lượng mà không gỡ thật.

---

## 2. Module 2: Hot-Session OAuth (`hot_session_oauth.py`)

### A. Mục Đích & Lợi Thế
- Thay vì phải đóng profile GPM rồi mở lại một tiến trình Playwright mới để login OAuth (dễ dính Re-auth password hoặc Google Prompt S7), module thực hiện cấp quyền OAuth **ngay trên tab trình duyệt đang mở (Hot Session)** ngay sau khi hoàn thành bật 2FA (`twofa_res.get("success") == True`).
- Tận dụng cookie vừa xác thực sạch, Google không yêu cầu nhập lại password hay mã OTP.

### B. Luồng Hoạt Động Cốt Lõi (`trigger_hot_session_oauth`)
1. **Lấy Authorize URL:**
   - Gọi API OmniRoute:
     ```python
     res = requests.get("http://127.0.0.1:20129/api/oauth/antigravity/authorize", params={"redirect_uri": "http://127.0.0.1:20129/callback"}, timeout=10)
     auth_data = res.json()
     auth_url = auth_data["authUrl"]
     code_verifier = auth_data["codeVerifier"]
     state = auth_data["state"]
     ```
2. **Lắng nghe Network Request bắt Code tức thì:**
   - Đăng ký listener trên Playwright page:
     ```python
     captured_code = None
     def on_request(req):
         nonlocal captured_code
         if "/callback" in req.url and "code=" in req.url:
             qs = urllib.parse.parse_qs(urllib.parse.urlparse(req.url).query)
             if "code" in qs:
                 captured_code = qs["code"][0]
     page.on("request", on_request)
     ```
3. **Điều hướng trực tiếp:**
   - `page.goto(auth_url, wait_until="domcontentloaded")`
4. **Vòng lặp xử lý Consent Screen (Timeout 30s):**
   - Nếu xuất hiện Account Chooser: Tìm node khớp `email` hoặc `div[data-identifier="{email}"]` để click.
   - Tự động tick các checkbox cấp quyền nếu chưa tick.
   - Bấm các nút xác nhận visible: `"Sign in"`, `"Tiếp tục"`, `"Cho phép"`, `"Continue"`, `"Allow"`, `#submit_approve_access`.
   - Ngắt vòng lặp ngay khi `captured_code` được gán giá trị.
5. **Exchange Code & Gán Cấu Hình OmniRoute:**
   - Gửi exchange:
     ```python
     payload = {"code": captured_code, "redirectUri": redirect_uri, "codeVerifier": code_verifier, "state": state}
     ex_res = requests.post("http://127.0.0.1:20129/api/oauth/antigravity/exchange", json=payload, timeout=25).json()
     cid = ex_res["connection"]["id"]
     ```
   - Gán Proxy 1:1 theo `port` vật lý:
     ```python
     # Lấy proxy_id khớp với port từ GET /api/settings/proxies
     requests.put("http://127.0.0.1:20129/api/settings/proxies/assignments", json={"scope": "account", "scopeId": cid, "proxyId": px_id})
     ```
   - Đồng bộ models:
     ```python
     requests.post(f"http://127.0.0.1:20129/api/providers/{cid}/sync-models", timeout=10)
     ```
   - Nối vào combo `ag-gemini-pool-3`:
     ```python
     from append_to_combo_pool3 import append_connections
     append_connections([{"cid": cid, "email": email, "port": port}])
     ```
     *(LƯU Ý QUAN TRỌNG: Giữ nguyên tên combo `ag-gemini-pool-3`, không đổi sang `ag-gemini-pool-3.8`)*
   - Ghi nhận trạng thái vào `D:\Taadaa\GPM auto\config\oauth_pipeline_status.json`.

---

## 3. Điểm Tích Hợp Vào Pipeline GPM (`run_batch_turn2_gmails.py`)

Trong hàm `process_single_account(account)` của `D:\Taadaa\GPM auto\scripts\run_batch_turn2_gmails.py`, tại dòng 1125 (ngay sau lệnh `sync_to_excels` khi `twofa_res.get("success") == True`):

```python
        if twofa_res.get("success"):
            outcome["status"] = "SUCCESS"
            outcome["reason"] = f"Login OK, 2FA status: {twofa_res.get('status')}"
            logger.info(f"[M{machine_id:02d} | {email}] 🎉 SUCCESS! 2FA: {twofa_res.get('status')}, Secret: {secret_key}")
            # Sync to Excels
            note_str = f"Batch 12 Untouched: Login OK | 2FA {twofa_res.get('status')}"
            sync_to_excels(email, "LIVE", standard_name, raw_proxy, secret_key=secret_key, note_msg=note_str)

            # HOT-SESSION OAUTH INTEGRATION (Non-blocking)
            try:
                from hot_session_oauth import trigger_hot_session_oauth
                logger.info(f"[M{machine_id:02d} | {email}] Triggering Hot-Session OAuth OmniRoute...")
                oauth_res = trigger_hot_session_oauth(page, email, machine_id, port, standard_name)
                logger.info(f"[M{machine_id:02d} | {email}] Hot-Session OAuth Result: {oauth_res.get('status')}")
            except Exception as oe:
                logger.warning(f"[M{machine_id:02d} | {email}] Hot-Session OAuth error (non-blocking): {oe}")
```
Luồng bọc trong `try...except` đảm bảo nếu bước OAuth gặp sự cố tạm thời, tài khoản đã login và bật 2FA thành công trên GPM vẫn được bảo toàn nguyên vẹn trong cơ sở dữ liệu.
