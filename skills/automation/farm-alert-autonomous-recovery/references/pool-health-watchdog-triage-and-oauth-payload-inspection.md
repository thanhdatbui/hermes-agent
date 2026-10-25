# Pool Health Watchdog Triage, OAuth Payload Inspection & Visual Evidence

> Kinh nghiệm vận hành và triage tự động cho Pool Healer Watchdog (`chatgpt-web-pool-healer-watchdog`), xử lý sự cố ChatGPT-Web, Codex OAuth và Antigravity trên OmniRoute (:20129) và GPM (:19995).

---

## 1. Phân Loại Cảnh Báo Watchdog (Pool Healer Alert Categories)
Khi nhận cảnh báo từ watchdog `chatgpt-web-pool-healer-watchdog`, phân loại ngay theo 3 nhóm độc lập trước khi quyết định can thiệp:
1. **ChatGPT-Web (`Validate fail: EMPTY_SESSION_TOKEN`)**: Watchdog kiểm tra session token hoặc khởi động profile GPM qua CDP (`/api/v3/profiles/start/{pid}`), kiểm tra cookie `__Secure-next-auth.session-token`. Thất bại khi cookie rỗng, trang chưa đăng nhập hoặc gặp lỗi mạng/proxy.
2. **Codex OAuth (`Timeout OAuth sau 90s` / `401_token_revoked`)**: Token upstream bị thu hồi hoặc hết hạn, watchdog chạy quy trình cấp lại OAuth qua callback server cổng `1455`. Thất bại khi kẹt tại màn hình chuyển hướng bên thứ 3 (Google SSO / 2FA).
3. **Antigravity Pro Tier (`g1-pro-tier`)**: Tài khoản Pro bị rớt trạng thái active hoặc lỗi refresh token Google Cloud.

---

## 2. Chống Bẫy "Cô Lập Thay Vì Cứu Acc" (Anti-Passive Isolation Trap)
- **Tư duy sai lầm:** Khi watchdog báo 7 acc cần chú ý, agent chỉ đọc log/error rồi kết luận "Đã cô lập `is_active = 0` trên OmniRoute để an toàn" và dừng lại báo cáo. Đây là hành vi bị coi là phá hoại / đùn việc vì nhiệm vụ là **hồi sinh tài khoản (Auto-Heal)**.
- **Quy chuẩn bắt buộc:**
  * BẮT BUỘC chủ động chạy quy trình **Active Token Rescue** (xem Mục 3) để cứu ngay các tài khoản chỉ bị lỗi mạng/proxy nhất thời.
  * Chỉ khi tài khoản có bằng chứng không thể hồi sinh ngay (bị OpenAI deactivated, hoặc cần Google TOTP theo ca định kỳ), mới duy trì cô lập tạm thời kèm lộ trình phục hồi rõ ràng.

---

## 3. Quy Trình Active Token Rescue (O(1) Live Probe Qua OmniRoute Test API)
Trước khi kết luận tài khoản mất session và phải mở GPM đăng nhập lại từ đầu, BẮT BUỘC thực hiện kiểm tra nhanh 4 bước:

1. **Kiểm tra độ dài token hiện có:**
   - Đọc cột `api_key` của connection trong bảng `provider_connections` (`storage.sqlite`).
   - Nếu `api_key` có độ dài hợp lệ (e.g. > 5000 ký tự cho ChatGPT-Web session token), token này có thể **hoàn toàn còn sống**, chỉ bị fail do proxy nghẽn lúc watchdog quét.

2. **Khắc phục lỗi xác thực Proxy trong `proxy_registry`:**
   - **MikroTik Proxies (`mirotik1.taadaa.click` port 10001-10035):** Kiểm tra xem có bị để trống `username` / `password` không. Cụm MikroTik farm yêu cầu auth `admin@1:admin@1`. Nếu rỗng, update ngay:
     ```sql
     UPDATE proxy_registry SET username='admin@1', password='admin@1' WHERE port=10006;
     ```
   - **MobiProxy 4G (`test.taadaa.click` port 5101-5138):** MobiProxy có chu kỳ reboot định kỳ (trả về `502 Bad Gateway` trong ~30-60s). Khi proxy phục hồi, token vẫn dùng tốt.

3. **Gọi Test Live Trực Tiếp Qua OmniRoute:**
   - Gọi `POST http://127.0.0.1:20129/api/providers/{cid}/test` với body `{}`.
   - Nếu kết quả trả về `{"valid": true}`: Token hoàn toàn hợp lệ!

4. **Kích hoạt hồi sinh ngay (Reactivate O(1)):**
   ```sql
   UPDATE provider_connections 
   SET is_active=1, test_status='active', last_error=NULL, last_error_at=NULL, backoff_level=0, rate_limited_until=NULL 
   WHERE id=?;
   ```
   *Hiệu quả thực tế:* Trong phiên 2026-10-25, phương pháp này đã cứu sống tức thì 5 tài khoản ChatGPT-Web (`ukenmorneau45`, `brittanysbarnes`, `caoanh1109`, `phungthibichngoc`, `julescanon`) trong vài giây mà không cần khởi động lại GPM profile!

---

## 4. Trích Xuất & Giải Mã Base64 Payload Trên URL Lỗi OpenAI
Khi Codex OAuth chuyển hướng về URL lỗi của OpenAI:
```
https://auth.openai.com/error?payload=<base64_string>&...
```
- **Kỹ thuật trích xuất:** Tách lấy tham số `payload=`, chuẩn hóa padding `=` (bội số 4) và giải mã bằng `base64.b64decode(payload)`.
- **Ví dụ thực tế:**
  - Chuỗi: `eyJlcnJvckNvZGUiOiAiYWNjb3VudF9kZWFjdGl2YXRlZCJ9`
  - Giải mã JSON: `{"errorCode": "account_deactivated"}`
- **Phán quyết vận hành O(1):**
  - Khi gặp `account_deactivated`: Đây là bằng chứng xác thực từ upstream OpenAI rằng tài khoản đã bị đóng/banned vĩnh viễn.
  - **Hành động ngay:** Đánh dấu tài khoản `DEAD` trong database/lifecycle, giữ `is_active = 0` trên OmniRoute để loại bỏ hoàn toàn khỏi luồng điều phối routing.
  - **CẤM:** Không được tiếp tục retry OAuth lặp đi lặp lại vì sẽ gây lãng phí 90s timeout mỗi lần quét.

---

## 5. Bẫy Hiểu Nhầm `batch_gpm_5profiles_supervisor_state.json`
- **Cảnh báo bẫy:** Việc tài khoản đang ở `stage: "HOTMAIL_LOGIN"` và `status: "PENDING"` trong file state supervisor **KHÔNG** đồng nghĩa với việc tài khoản chưa từng đăng ký ChatGPT Web!
- **Thực tế hệ thống:** Nhiều tài khoản đã có sẵn tài khoản ChatGPT từ các batch chạy trước (kiểm tra `has_chatgpt: True`, có mật khẩu tại cột L `taikhoan_dat_v2_updated.xlsx` và có sẵn `api_key` trong OmniRoute).
- **Hành động:** Luôn kiểm tra song song cả hai nguồn: `storage.sqlite` và state file trước khi phán đoán vòng đời tài khoản.

---

## 6. Invariant Soi Mắt Đọc Ảnh GPM (`browser_navigate` + `browser_vision`)
Trước khi gửi bất kỳ thẻ ảnh `MEDIA:<path>` nào cho User theo Invariant Soi Mắt Đọc Ảnh:
1. **Nạp ảnh cục bộ qua Browser:**
   - Dùng `browser_navigate(url="file:///D:/Taadaa/GPM%20auto/debug_screenshots/<screenshot_name>.png")`.
2. **Soi mắt bằng Native Vision:**
   - Gọi `browser_vision(annotate=false, question="...")` để đọc trực tiếp nội dung màn hình.
3. **Phân loại hiện trường:**
   - **Ảnh đen / rỗng (< 2.5 KB):** Trình duyệt Chromium chưa kịp render frame đầu tiên (thường gặp khi profile GPM chạy nền hoặc scale nhỏ `win_scale=0.8`). CẤM gửi ảnh này làm bằng chứng.
   - **Ảnh lỗi mạng (`ERR_CONNECTION_RESET` / `ERR_PROXY_CONNECTION_FAILED`):** Chứng minh trực quan cổng proxy của profile bị ngắt kết nối (ví dụ cổng proxy 5115 reset kết nối khi tải `chatgpt.com/auth/login`). Phản hồi rõ ràng nguyên nhân là mạng/proxy.
   - **Ảnh Challenge / Checkpoint:** Phát hiện màn hình Cloudflare Turnstile, số điện thoại hoặc yêu cầu xác thực bảo mật 2FA.

---

## 7. Phân Biệt Google SSO Federation vs Direct Auth Trong Codex OAuth
- Khi tài khoản OpenAI được đăng ký qua Google SSO, việc gõ email vào ô input của OpenAI sẽ tự động kích hoạt redirect sang Google:
  `https://accounts.google.com/v3/signin/identifier?opparams=...`
- **Kiểm tra cookie GPM trước khi OAuth:**
  - Chạy query SQLite kiểm tra cookie Google SID trong thư mục profile GPM (`Default/Network/Cookies`):
    ```sql
    SELECT count(*) FROM cookies WHERE host_key LIKE '%google%' AND name = 'SID';
    ```
  - Nếu `has_sid = False`: Profile GPM hiện đang chưa đăng nhập Google. Bất kỳ cố gắng chạy OAuth nào cũng sẽ dừng tại form đăng nhập Google.
  - **Lộ trình hồi sinh:** Chờ hoặc kích hoạt watchdog `post_evening_gpm_login_watchdog.py` trong ca rảnh để thực hiện đăng nhập lại Google tự động bằng TOTP/2FA trước khi chạy lại Codex OAuth.

---

## 8. Bẫy Mù Chéo Giữa 3 Cron (Pool Healer vs Login Watchdog vs Nurture Cron)
- **Triệu chứng:** Tài khoản bị văng session Google trong GPM nhưng **vĩnh viễn không được login lại**:
  * `chatgpt-web-pool-healer-watchdog` thấy Timeout OAuth tại Google signin -> ghi vào `chatgpt_web_pool_telemetry.json` rồi dừng.
  * `post_evening_gpm_login_watchdog.py` thấy nhánh Antigravity vẫn active trên OmniRoute (`omniroute_success`) -> **bỏ qua không login**, vì cờ `is_lost_session` chỉ lấy từ `nurture_needs_login`.
  * `cron_gpm_gmail_nurture.py` chỉ nuôi `DEFAULT_NURTURE_GROUP_ID = 10` (`Google_Live_Ready`), các profile ở Group 1 bị skip 100% nên không bao giờ mở lên để gắn cờ `NEEDS_LOGIN`.
- **Kiến trúc sửa đổi khép kín (Closed-Loop Bridge):**
  1. **Bridge Telemetry Failures:** Login watchdog đọc `chatgpt_web_pool_telemetry.json` (`failures`) và mảng zero-cookie GPM (`em_l not in session_emails`). Nếu acc có trong danh sách này, cưỡng chế bật `is_lost_session = True` bất kể OmniRoute có nhánh Antigravity active hay không.
  2. **Auto-Promotion Group 10:** Khi quét profile GPM thấy cookie Google sống (`cnt >= 2`), tự động chạy `UPDATE profiles SET GroupId = 10 WHERE ProfilePath = ? AND GroupId != 10` để bàn giao sang cron nuôi.

---

## 9. Dispatch Gate & Worker Routing Discipline (Anti-Timeout & Agy Fast-Track)
- **Chốt chặn Dispatch Gate:** `delegate_task` bị cấm cứng đối với các task sửa code (`⛔ [DISPATCH GATE - BLOCKED_BY_DISPATCH_GATE]`). BẮT BUỘC dùng Worker CLI (`dispatch_worker.py`, `ag_cli.py fix`).
- **Bẫy Sol Hang trong `dispatch_worker.py`:**
  * Tier 1 (`sol_worker.py`) gọi `gpt-web-sol` (:20129) với timeout mặc định 300s/turn. Nếu endpoint này bị treo, lệnh shell ngoài (timeout 360s) sẽ bị kill trước khi `dispatch_worker.py` kịp fallback sang Tier 2 (Agy) hay Tier 3 (Haiku).
- **Agy CLI Fast-Track:**
  * Kiểm tra nhanh trạng thái pool Antigravity qua `python D:/Taadaa/tools/ag_cli.py pool-status`. Nếu pool có sẵn profile READY (100% quota), có thể điều phối trực tiếp qua Agy CLI để tránh chờ Sol timeout:
    ```bash
    python "D:/Taadaa/tools/ag_cli.py" fix --workdir "<repo_path>" --file "<target_file>" "<prompt>"
    ```

