# Pitfall & Closed-Loop Architecture: Dual-Provider (Antigravity vs Codex) Session Desync in GPM Login Watchdog

## 1. Triệu chứng & Hiện tượng "Kẹt giữa 2 làn nước"
- Cron `chatgpt-web-pool-healer-watchdog` (job `fff7f688990d`) phát hiện và ghi nhận vào `chatgpt_web_pool_telemetry.json`:
  * Tài khoản Codex lỗi `Timeout OAuth sau 90s. URL: https://accounts.google.com/v3/signin/identifier?...` hoặc `OAuth token revoked / Google SID missing`.
- Kiểm tra cookie trong GPM Profile (`Default/Network/Cookies`) thấy đã mất sạch session Google (`SID`, `SSID`, `HSID`).
- Tuy nhiên:
  * **Cron Login Gmail (`post_evening_gpm_login_watchdog.py`):** Hoàn toàn KHÔNG đưa tài khoản này vào candidates để login lại vào các ca rảnh.
  * **Cron Nuôi Gmail (`cron_gpm_gmail_nurture.py`):** Hoàn toàn KHÔNG nuôi và không kiểm tra liveness của tài khoản này.

---

## 2. Nguyên nhân cốt lõi (3 Điểm mù liên thông / Siloed Crons)
1. **Lệch trạng thái Dual-Provider trên OmniRoute:**
   * Cùng một Gmail (ví dụ: `lamngocdiep030420000304@gmail.com`) được nạp cả 2 provider trên OmniRoute: Antigravity (Google AI Pro, `tier: g1-pro-tier`) và Codex (OpenAI via Google SSO).
   * Antigravity giữ token OAuth riêng và vẫn đang `is_active: 1`.
   * Trình duyệt GPM văng cookie Google khiến Codex không thể re-auth qua "Continue with Google".
2. **Bộ lọc loại trừ của GPM Login Watchdog (`omniroute_success`):**
   * Trong `post_evening_gpm_login_watchdog.py`:
     ```python
     omniroute_success = _get_live_omniroute_antigravity_emails()
     ...
     if em_l in omniroute_success and not is_lost_session:
         continue
     ```
   * Watchdog thấy Antigravity vẫn active trên OmniRoute nên đánh dấu `omniroute_success` và bỏ qua.
   * `is_lost_session` chỉ lắng nghe duy nhất `nurture_needs_login` từ `gpm_gmail_nurture_state.json`.
3. **Rào chắn cứng của Cron Nuôi (`GroupId == 10`):**
   * `cron_gpm_gmail_nurture.py` có rào chắn `DEFAULT_NURTURE_GROUP_ID = 10` (`Google_Live_Ready`).
   * Các profile nằm ở Group 1 ("All") hoặc Group 0 bị `skipped_group += 1` bỏ qua 100%.
   * Vì cron nuôi không mở profile, nó không bao giờ phát hiện mất session để ghi cờ `NEEDS_LOGIN`.
   * Kết quả: Vòng lặp mù chéo — Cron nuôi bỏ qua vì sai GroupId, Cron login bỏ qua vì tưởng đã xong trên OmniRoute.

---

## 3. Kiến trúc sửa đổi khép kín (Closed-Loop Repair Specification)

### A. Mở rộng định nghĩa `is_lost_session` trong `post_evening_gpm_login_watchdog.py`:
Tài khoản kể cả đã có trong `omniroute_success` bắt buộc phải re-login khi thỏa mãn BẤT KỲ điều kiện nào:
1. `em_l in nurture_needs_login` (nguồn nurture truyền thống).
2. **Telemetry Failures Bridge:** Đọc `D:/Taadaa/chatgpt_web_pool_telemetry.json` -> nếu email nằm trong mảng `failures` với lỗi `TIMEOUT` / `accounts.google.com` / `EMPTY_SESSION_TOKEN` / `OAuth token revoked / Google SID missing` -> Đánh dấu `is_lost_session = True`.
3. **Zero-Cookie Audit:** Đã có profile GPM nhưng hàm `_get_gpm_profiles_with_google_session()` trả về `em_l not in session_emails` (thiếu `SID/SSID/HSID` thực tế trên đĩa) -> Đánh dấu `is_lost_session = True`.

### B. Cơ chế Auto-Promotion lên Group 10 (`Google_Live_Ready`):
- Trong chu kỳ kiểm tra profile GPM của `post_evening_gpm_login_watchdog.py` hoặc `sync_gpm_lifecycle.py`:
  * Nếu phát hiện profile có cookie Google sống (`cnt >= 2` cookies `SID`, `SSID`, `HSID`) nhưng vẫn đang ở `GroupId != 10`:
    ```python
    conn.execute("UPDATE profiles SET GroupId = 10 WHERE Id = ?", (pid,))
    ```
  * Tự động bàn giao cho `cron_gpm_gmail_nurture.py` tiếp quản giữ ấm cookie hàng ngày.

### C. Fallback cho Cron Nuôi (`cron_gpm_gmail_nurture.py`):
- Cho phép nuôi bổ sung các profile có email nằm trong danh sách Active của OmniRoute hoặc có session cookie Google sống, không phụ thuộc cứng 100% vào trường `GroupId` tĩnh trong DB.

---

## 4. Hiện thực hoá & Kiểm chứng Unit Test (Verified Artifacts 2026-10-25)
Đã thi công hoàn chỉnh trên `D:/Taadaa/GPM auto/scripts/post_evening_gpm_login_watchdog.py` và kiểm chứng qua `tests/test_post_evening_gpm_login_watchdog.py`:
1. `_get_pool_telemetry_failures()`: Trích xuất tự động danh sách failure từ `D:/Taadaa/chatgpt_web_pool_telemetry.json`.
2. `_get_gpm_profiles_with_google_session()`: Tự động chạy `UPDATE profiles SET GroupId = 10` cho các profile có `cnt >= 2` cookies `SID/SSID/HSID` nhưng `GroupId != 10`.
3. `get_candidates()`: Nhận diện `is_lost_session = True` và ưu tiên `priority = 1` cho cả 3 trường hợp: nurture báo mất session, telemetry báo lỗi OAuth timeout, hoặc OmniRoute active nhưng GPM profile rỗng cookie Google.
4. **Pytest Verification (3/3 Passed Offline < 1s)**:
   ```bash
   pytest "D:/Taadaa/GPM auto/tests/test_post_evening_gpm_login_watchdog.py" -v
   ```

---

## 5. Bẫy Chặn Mù "khoale" vs Bản Chất Tài Khoản Clean_v2 (Chỉ Dùng TOTP 2FA)

### A. Sự nhầm lẫn giữa "Phối hợp S7" và "Login GPM thuần túy":
- Khi tài khoản văng session, Agent hay ngộ nhận: *"Phải cắm máy Samsung S7 (Máy 07) để bấm xác minh 'Có' hoặc lấy mã bảo mật 10 số"*.
- **Thực tế:** Các tài khoản thuộc phân loại **`clean_v2`** đã được cấu hình:
  * **Đã tắt hoàn toàn Google Prompt (Lời nhắc của Google).**
  * Google **KHÔNG BAO GIỜ** gửi popup "Có/Không" hay đòi mở thiết bị S7 khi đăng nhập từ GPM.
  * Phương thức 2FA duy nhất được Google yêu cầu là **Mã 6 chữ số từ ứng dụng Authenticator (TOTP)**.
  * Vì `totp_secret` đã có sẵn trong Master Excel / database, script trên PC tự động tính toán mã 6 số qua `pyotp.TOTP(totp_secret).now()` trong 0.01 giây và điền thẳng vào form.
  * **Hệ quả kỹ thuật:** Quá trình đăng nhập GPM cho tài khoản `clean_v2` diễn ra **100% độc lập trên PC**, không cần thiết bị S7 online, không chiếm ADB, không cần màn hình S7 sáng.

### B. Bẫy loại trừ cứng `khoale` (False-Positive Blacklist):
- Trong `run_oauth_s7_pipeline.py` và `post_evening_gpm_login_watchdog.py` tồn tại logic:
  ```python
  if "khoale" in recovery.lower() or "khoale" in email.lower():
      return SKIPPED_KHOALEE
  ```
- **Hậu quả:** 51 tài khoản Farm S7 có recovery email là `khoaleemagic@gmail.com` (ví dụ `lamngocdiep030420000304@gmail.com`) bị bỏ qua vĩnh viễn dù có đầy đủ `password` và `totp_secret` sạch.
- **Cơ Chế Khắc Phục Chuẩn (ALLOWED_KHOALE_EXCEPTIONS):**
  * Khai báo danh sách ngoại lệ được phép bỏ qua bộ lọc `khoale` trong cả `post_evening_gpm_login_watchdog.py` và `run_oauth_s7_pipeline.py`:
    ```python
    ALLOWED_KHOALE_EXCEPTIONS: set[str] = {
        "lamngocdiep030420000304@gmail.com",
    }
    ```
  * Áp dụng ngoại lệ tại cả 3 vị trí: `sync_gpm_profiles_lifecycle()`, `get_candidates()` và `run_oauth_s7_pipeline.py:process_account()`.
  * **Kiểm chứng thực tế (Execution Receipt 2026-10-26)**:
    Khi chạy `python "D:/Taadaa/GPM auto/scripts/run_oauth_s7_pipeline.py" lamngocdiep030420000304@gmail.com --login-only`:
    - Script mở GPM profile `Zytr3EkLsk-09092026` qua proxy 5107.
    - Điền email `lamngocdiep030420000304@gmail.com` + password `Dieplam0304@`.
    - Google challenge hiện TOTP -> Tự động tính toán mã 6 số qua `pyotp.TOTP(totp_secret).now()` và điền vào form.
    - Điền email khôi phục -> **Đăng nhập thành công 100% trong 47 giây** mà không cần bất kỳ tương tác phần cứng nào với máy S7.
    - Unit test suite: `pytest "D:/Taadaa/GPM auto/tests/test_post_evening_gpm_login_watchdog.py" -v` đạt **4/4 PASSED**.

---

## 6. Cạm Bẫy Thoát Sớm Thiếu Screenshot Trong `--login-only` (`run_oauth_s7_pipeline.py`)

### A. Hiện tượng:
- Khi chạy lệnh:
  ```bash
  python "D:/Taadaa/GPM auto/scripts/run_oauth_s7_pipeline.py" <email> --login-only
  ```
- Script in ra stdout:
  ```text
  03:55:46 [INFO] [M07] Dang nhap Google thanh cong: https://gds.google.com/web/recoveryoptions?...
  03:55:49 [INFO] Máy 07 | <email> -> SUCCESS | Conn: N/A | Port: N/A
  ```
- **Vấn đề cốt lõi:** Script thoát sớm tại dòng 1353 (`if login_only and captured_code == "LOGIN_ONLY_SUCCESS": return {"status": "SUCCESS"}`) trước khi tới khối chụp ảnh `page.screenshot(path=shot_path)` ở dòng 1404.
- **Hậu quả:** Thư mục `D:/Taadaa/GPM auto/debug_screenshots/` hoàn toàn KHÔNG có file ảnh thành công nào được lưu. Nếu Coordinator vội vàng tin vào dòng log `SUCCESS` trên terminal để báo hoàn tất mà không kiểm tra file ảnh thực tế trên đĩa $\rightarrow$ **Vi phạm trực tiếp Gate 6 (Max blind steps = 1, báo xong không có ảnh).**

### B. Giải pháp khắc phục & Quy trình nghiệm thu:
1. **Chụp ảnh độc lập qua CDP:** Nếu phát hiện script thoát mà không sinh file ảnh, Coordinator BẮT BUỘC kết nối CDP tới cổng DevTools của profile GPM, mở `https://myaccount.google.com/` và chụp ảnh xác nhận.
2. **Soi mắt OCR trước khi gửi:** Chạy `python D:/Taadaa/tools/run_winrt_ocr.py <screenshot_path>` để xác nhận đúng họ tên, đúng email và gói dịch vụ (ví dụ `Gói Google AI Pro`) trên giao diện trước khi đính kèm thẻ `MEDIA:<path>`.
3. **Quy tắc bất biến:** Tuyệt đối không bao giờ dùng text output của terminal để thay thế cho ảnh chụp thực tế màn hình.


