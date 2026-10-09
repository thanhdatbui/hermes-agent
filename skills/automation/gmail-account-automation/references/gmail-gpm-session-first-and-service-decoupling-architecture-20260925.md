# Kiến Trúc Tách Lớp Vòng Đời Gmail — GPM Session-First & Decoupled Service Workers

**Ngày cập nhật:** 2026-09-25  
**Nguồn gốc:** Phản biện kiến trúc giữa Operator, Sol Brain (GPT-5.6 Sol High) và dữ liệu thực nghiệm vận hành farm.

---

## 1. Phản Biện Các Lỗ Hổng & Mâu Thuẫn Lịch Sử

1. **Sai lầm "Bắt buộc 2FA S7 trước khi Login GPM":**
   - *Quan niệm cũ sai:* Cho rằng phải bật 2FA Google Authenticator trên S7 thì mới được phép đưa lên GPM login.
   - *Hậu quả thực tế:* Trên Samsung S7 (Android 8), Google mở WebView bảo mật có reCAPTCHA/challenge xác minh danh tính không thể vượt qua bằng ADB thuần, làm script timeout (10,800s) và chặn đứng toàn bộ vòng đời tài khoản.
   - *Thực tế chứng minh:* Rất nhiều tài khoản Gmail chưa bật 2FA vẫn đăng nhập thành công vào trình duyệt GPM bằng pass/session bình thường. 2FA là **trạng thái bảo mật (security state)**, không phải **điều kiện tiên quyết để tạo session**.

2. **Sai lầm "Add 2FA GPM khi chưa có Google Session" (`NO_SESSION` Loop):**
   - *Hiện tượng:* Cron Add 2FA mở profile GPM và điều hướng thẳng vào `myaccount.google.com/signinoptions/two-step-verification` khi profile chưa từng đăng nhập Google. Trình duyệt bị redirect về `google.com/account/about` dẫn tới hàng loạt lỗi `NO_SESSION`.
   - *Nguyên tắc bắt buộc:* **Session trước, Security sau**. Bắt buộc xác minh `GPM_SESSION_VERIFIED == True` rồi mới được trigger thao tác thêm/bật bảo mật 2FA.

3. **Sai lầm "Gộp chung chuỗi Gmail -> ChatGPT -> TikTok 2FA":**
   - *Hiện tượng:* Khi ChatGPT link fail hoặc runner TikTok 2FA lỗi khởi động, toàn bộ batch bị báo fail và có nguy cơ retry mù làm hỏng trust của Gmail.
   - *Nguyên tắc:* Gmail Core là hạ tầng nền tảng. ChatGPT và TikTok là 2 dịch vụ độc lập chỉ liên kết qua metadata/credentials, tuyệt đối không phụ thuộc đồng bộ trong cùng một transaction.

---

## 2. Mô Hình State Machine 4 Domain Độc Lập

```
[S7 Farm]
Reg Gmail (S0_NEW -> S1_CREATED)
       │
       ▼
Cooldown / Health Check (S2_COOLDOWN)
       │
       ▼
[GPM Profiles]
Login Google trên GPM (S3_GPM_SESSION_VERIFIED)
       │
       ├───────────────────────────────────────────────┐
       ▼                                               ▼
Kích hoạt Google 2FA (S4_SECURITY_READY)      Service Binding (S5_SERVICE_READY)
(Bóc Base32 Secret Key + TOTP)                         │
                                         ┌─────────────┴─────────────┐
                                         ▼                           ▼
                                   ChatGPT Link                 TikTok 2FA
                                (Đọc OTP Mailbox)           (Runner Preflight)
```

### Chi tiết các State độc lập:
- **`gmail_state`**: `CREATED` -> `COOLDOWN` -> `MAILBOX_HEALTHY` -> `GPM_LOGIN_PENDING` -> `GPM_SESSION_VERIFIED` -> `HOLD` / `BLOCKED`.
- **`google_2fa_state`**: `NOT_STARTED` -> `PENDING_SESSION` -> `IN_PROGRESS` -> `ENABLED` -> `HUMAN_REVIEW` / `BLOCKED`.
- **`chatgpt_state`**: `NOT_STARTED` -> `ELIGIBLE` -> `IN_PROGRESS` -> `LINKED` -> `RETRY_LATER` / `BLOCKED`.
- **`tiktok_state`**: `NOT_STARTED` -> `ELIGIBLE` -> `RUNNER_PREFLIGHT` -> `IN_PROGRESS` -> `VERIFIED` -> `BLOCKED`.

---

## 3. Quy Tắc Điều Phối Cron & Safe Gates

1. **GPM Login Worker (`post_evening_gpm_login_watchdog.py`):**
   - Điều kiện: `gmail_state in {COOLDOWN, MAILBOX_HEALTHY}` và đã qua thời gian ngâm (`cooldown_until <= now`).
   - CẤM: Không kiểm tra `google_2fa_state == ENABLED`.
   - Giới hạn concurrency: Tối đa 5 workers song song, map đúng Proxy di động tương ứng của máy S7.

2. **GPM Google 2FA Worker (`post_morning_gmail_2fa_watchdog.py`):**
   - Điều kiện: BẮT BUỘC `gmail_state == GPM_SESSION_VERIFIED` (kiểm tra local session preflight `_profile_has_google_session`).
   - **Session Cookie Preflight:** Phải đọc file SQLite cookie của profile (`Default/Network/Cookies` hoặc `Default/Cookies`), kiểm tra `host_key LIKE '%google.com'` và `name IN ('SID', 'SSID', 'HSID', 'SAPISID')` (count >= 2). Bắt buộc nạp `profile_path` vào candidate dict để helper truy cập đúng đường dẫn DB.
   - **Silent Watchdog Invariant on `pending_list` (Anti-Spam stdout Suppression):** `save_state_results(success_list, fail_list, pending_list)` bắt buộc luôn được gọi để persist state, nhưng lệnh xuất báo cáo `print()` ra `stdout` BẮT BUỘC chỉ chạy khi `if success_list or fail_list:`. In báo cáo khi chỉ có `pending_list` sẽ khiến cron scheduler gửi tin nhắn rác lên Telegram mỗi tick (5 phút).
   - **Structured Telemetry qua `stderr` (Observability Không Gây Rác):** Phát metric JSON có cấu trúc `[TELEMETRY_METRIC] {"event": ..., "timestamp": ..., "pid": ..., "data": ...}` ra `sys.stderr` cho các sự kiện `2fa_setup_pending`, `2fa_setup_success`, `2fa_setup_failed`, `2fa_setup_error`, và `watchdog_execution_summary`. Đảm bảo đạt điểm tối đa trên các gate audit (Sol Auditor) mà không làm rò rỉ bất kỳ byte nào ra `stdout`.
   - **Decoupled 6h Aggregated Reporting Pattern (Runner vs Reporter):**
     * Worker cuốn chiếu (`post-morning-gmail-2fa-watchdog`, `693dcacb8999`) BẮT BUỘC cấu hình `deliver: local` để chạy ngầm hoàn toàn im lặng, không spam Telegram mỗi tick 5 phút. Worker ghi nhận kết quả và `events` (kèm timestamp) vào `post_morning_gmail_2fa_state.json` (retention 7 ngày).
     * Báo cáo Telegram được tách thành cronjob định kỳ 6h chuyên trách (`gmail-gpm-2fa-6h-report`, `88a5cd11c3a9`, `0 */6 * * *`, deliver `telegram:-5373649734`, script `cron_gmail_gpm_2fa_6h_report.py`). Báo cáo tổng hợp số liệu Group 10 trên GPM DB, Excel và danh sách sự kiện hoàn tất trong 6h vừa qua.
   - **Kibe Runtime vs Deploy Sync:** `cron_sync_watchdog.py` chỉ đồng bộ xuôi từ `KIBE_SCRIPTS` (`~/AppData/Local/hermes/scripts`) sang deploy/OneDrive. Nếu chỉnh sửa script trong repo `deploy/hermes-home/scripts`, bắt buộc copy ngược lại `KIBE_SCRIPTS` để cron runtime nhận bản mới.
   - Nếu gặp `NO_SESSION` thực tế: Không retry Add 2FA, chuyển trạng thái `PENDING_GPM_LOGIN_NO_SESSION` cho ca login tiếp theo.
   - Nếu gặp CAPTCHA/Phone Checkpoint: Chuyển thẳng `HUMAN_REVIEW`, dừng nick đó, cấm retry vòng lặp.

3. **Post-Noon Chain & Decoupled Services (`post_noon_chain_watchdog.py`):**
   - Tách bạch các cờ `--lane gmail`, `--lane tiktok`, `--lane all`. Mặc định ca trưa chỉ chạy `--lane gmail`.
   - ChatGPT link fail chỉ cập nhật `chatgpt_state = RETRY_LATER/BLOCKED`, không quy nạp mù ChatGPT count vào Gmail success.
   - TikTok Add 2FA gặp lỗi khởi động runner (`RUNNER_STARTUP_FAILURE`) phải fail-fast và báo cáo kiểm tra runner, cấm re-run phase tạo Gmail.
