# Post-Shift GPM Login Watchdog & Account Lifecycle Integration

## 1. Mục đích & Khung giờ hoạt động
Watchdog `post-evening-gpm-login-watchdog` (script `post_evening_gpm_login_watchdog.py`) tự động đẩy tài khoản Gmail từ thiết bị Android Farm lên trình duyệt GPMLogin trên PC trong các khoảng thời gian rảnh giữa/sau các ca nuôi TikTok feed:
- **Ca Sáng:** 09:30 – 11:20 (ngay sau khi Ca 1 nuôi feed kết thúc lúc 09:25)
- **Ca Chiều:** 15:30 – 17:20 (ngay sau khi Ca 2 nuôi feed kết thúc lúc 15:25)
- **Ca Tối:** 21:30 – 23:45 (ngay sau khi Ca 3 nuôi feed kết thúc lúc 21:25)
*(Tuyệt đối tránh chạy vào giờ cao điểm nuôi feed: 06:00-09:25, 11:35-15:25, 17:35-21:25 khiến máy bận 100% và cron bị kẹt ảo).*

## 2. Nguồn tài khoản (Thứ tự ưu tiên)
1. **Gmail Mất Session từ Cron Nuôi (`nurture_reported_needs_login` - ƯU TIÊN CAO NHẤT):**
   - Đọc từ `D:/Taadaa/runtime/kibe/cron-state/gpm_gmail_nurture_state.json` tìm các profile có `status == "NEEDS_LOGIN"`.
   - BẮT BUỘC cho phép bypass qua bộ lọc trùng trong ngày (`seen_emails`) để được cứu ngay trong ca hiện tại.
   - Chạy pipeline đăng nhập lại `run_oauth_s7_pipeline.py <email>`. Thành công sẽ cập nhật `GroupId = 10` trong SQLite và ghi `status = "LOGIN_RECOVERED"`, chuyển acc sang ngâm (`GPM_SOAKING`).
2. **Gmail Cooldown 7 ngày đã hết hạn:** Kiểm tra trong `D:/Taadaa/GPM auto/config/oauth_pipeline_status.json`.
3. **Gmail LIVE mới:** Từ `D:/OneDrive/TaadaaData/kibe/master_gmail_manager.xlsx` (sheet `Kibe_Farm_S7`) chưa có profile trong Group 10 của GPM.

## 3. Ràng buộc an toàn & Farm Preflight (Invariants)
- **Kiểm tra Máy rảnh (Idle):**
  - Không có file lock tại `~/.codex/device-locks/machine_<mid>.*`.
  - Không vướng khung giờ nuôi trong manifest assignment (`MIN_IDLE_BUFFER_MIN = 10` phút trước ca tiếp theo).
- **Thiết bị ADB Online:**
  - Bắt buộc máy phải online trong danh sách `adb devices` để sẵn sàng phối hợp lấy OTP, Security Code hoặc xử lý Google prompt.
- **Ràng buộc Proxy & Máy cứng:**
  - Tối đa **2 acc / proxy port / ngày** (`MAX_LOGINS_PER_PROXY = 2`).
  - Mỗi máy (mid) chỉ được schedule login **đúng 1 lần / ngày**.
- **Concurrency & Stagger:**
  - Chạy tối đa 5 workers song song (`MAX_WORKERS = 5`), giãn cách khởi tạo (stagger) 5s giữa các worker.

## 4. State Machine, GPM_SOAKING & Auto-Nurture Chaining Invariant
- **CẤM GỌI DUAL OAUTH GOOGLE SSO NGAY LẬP TỨC:**
  - Sau khi login Gmail thành công trên GPM, tài khoản KHÔNG ĐƯỢC kích hoạt OAuth / SSO ngay để chống Google kích hoạt checkpoint reCAPTCHA hoặc SMS.
  - Profile được chuyển vào trạng thái `GPM_SOAKING`, cập nhật vào `GroupId = 10` trong SQLite GPM DB (`profile_data.db`).
- **NỐI TỰ ĐỘNG SCRIPT NUÔI NGAY SAU KHI LOGIN THÀNH CÔNG (AUTO-NURTURE CHAINING):**
  - Ngay trong nhánh `if success:`, sau khi đổi group, script tự động kích hoạt `cron_gpm_gmail_nurture.py --email <email>` thông qua tiến trình nền phi phong bế (`subprocess.Popen(..., stdout=DEVNULL, stderr=DEVNULL)`).
  - Profile vừa có session Google sẽ lập tức được mở lướt YouTube / đọc Google News 90–120s để tạo browsing history thật, cookie tương tác tự nhiên (`VISITOR_INFO1_LIVE`, `YSC`, `PREF`) và tăng Trust Score.
  - Điều này giúp tài khoản không bị "chết nguội" trong trạng thái chờ và giảm thiểu tối đa checkpoint khi bước vào luồng OAuth sau 24h–48h.

## 5. Báo cáo & Telemetry (Minh bạch Acc Bị Hoãn / Nhường Máy)
Báo cáo chỉ gửi **1 lần duy nhất** khi toàn ca hoàn tất hoặc khi chạm mốc kết thúc ca (ví dụ 11:15 ca sáng, 17:15 ca chiều, 23:30 ca tối):
- Định dạng: `[LOGIN GPM <CA> - TỔNG KẾT]`
- Các chỉ số bắt buộc:
  - `• Kết quả ca: ✓ <success> | ✗ <fail> | proxy_limit 2/port/ngày | Hoàn tất ca <desc>`
  - `• Bỏ qua an toàn: <N> acc nhường máy đang bận cron khác (TikTok/Avatar)` *(khi có acc bị hoãn do máy bận hoặc hết ca)*
  - `• Antigravity Pool: <count> accounts LIVE trên OmniRoute (:20129)`
  - `• Profile sẵn Google Session chờ OAuth: <count> accounts`
- **Kỷ luật Báo Cáo Farm:** Tuyệt đối không giấu nhẹm số lượng candidate bị skip khi hết ca. Bắt buộc hiển thị dòng `• Bỏ qua an toàn` để User phân biệt rõ ràng giữa "Cron bị lỗi không chạy" vs "Cron chủ động nhường máy cho lịch nuôi TikTok".

## 12. Cơ Chế Khóa Thiết Bị 2 Tầng Chống Tranh Chấp & Phá Lẫn Nhau Giữa Các Cron
- **Vấn đề tranh chấp ADB trên Farm:** Nhiều cron độc lập cùng thao tác trên máy thật S7 (`post-evening-gpm-login-watchdog`, `post-noon-chain-watchdog`, `post-evening-avatar-watchdog`, `tiktok-runner`). Nếu không có khóa độc quyền, hai cron có thể cùng gõ ADB lên một máy, làm đứt phiên nuôi TikTok hoặc làm hỏng quy trình lấy Security Code Google.
- **Cơ Chế 2 Tầng Bảo Vệ Chuẩn:**
  1. **Tầng 1 — Khóa độc quyền thiết bị (Device Lock Lease):**
     - Mọi thao tác phần cứng trên máy S7 bắt buộc bọc trong `acquire_device_lock(machine=str(mid), serial=serial, project="gpm-login")` từ `automation_core.device_lock`.
     - Tạo file mutex `~/.codex/device-locks/machine_{mid}.{serial}.lock.json` kèm PID, TTL và heartbeat.
     - Các cron khác kiểm tra `LOCK_DIR`: nếu thấy cờ `running/active` trên máy `mid` thì lập tức bỏ qua, không tranh chấp.
     - Watchdog dọn dẹp `reap-dead-owner-locks` chạy mỗi 5 phút để tự động thu hồi lock rác nếu tiến trình bị kill đột ngột.
  2. **Tầng 2 — Vùng đệm lịch nuôi TikTok (Manifest Schedule Buffer):**
     - Trước khi khởi động worker, script gọi `is_machine_idle(mid)` đối soát trực tiếp file `assignment-v1-*.json` trong `D:/Taadaa/runtime/kibe/cron-state/manifests/`.
     - Bỏ qua máy nếu máy đang trong slot nuôi HOẶC giờ nuôi tiếp theo sắp bắt đầu trong vòng `MIN_IDLE_BUFFER_MIN = 10` phút.
     - Đảm bảo tác vụ login phụ trợ không bao giờ chiếm máy quá sát giờ nuôi TikTok.

## 6. Kiến trúc cuốn chiếu OAuth (Rolling OAuth Onboarding vs Passive Stockpile)
- **Hiện tượng ứ đọng profile chờ OAuth:**
  - Watchdog login xong sẽ chuyển acc sang `GPM_SOAKING` và cập nhật `GroupId = 10`.
  - Nếu hệ thống chỉ trông chờ kho chính OmniRoute hụt mới thêm acc thì số lượng "Profile sẵn Google Session chờ OAuth" sẽ dồn ứ (ví dụ 90-100+ acc) gây lãng phí tài nguyên đã nuôi sạch.
- **Quy tắc vận hành chuẩn (User Invariant):**
  - Không để tài khoản ngâm xong nằm chờ thụ động kho chính hụt.
  - Phân biệt rõ 3 giai đoạn của profile:
    1. *Mới login:* `GPM_SOAKING` (CẤM OAuth ngay để tránh reCAPTCHA/SMS).
    2. *Đang ngâm & nuôi:* `gpm-gmail-nurture-watchdog` chạy định kỳ (xem YouTube/Google News).
    3. *Đã ngâm đủ hạn (>= 48h - 72h):* Đủ điều kiện cuốn chiếu.
  - **Chỉ tiêu vận hành Cron cuốn chiếu OAuth Antigravity:**
    - **Concurrency:** Tối đa 5 Workers song song (`MAX_WORKERS = 5`).
    - **Ràng buộc IP/Proxy:** Tối đa **1 acc / 1 IP (proxy port) / 1 ngày** (chặt hơn mức 2 acc của khâu login để bảo vệ dải proxy khi gọi Google Cloud Platform OAuth).
    - **Bộ lọc loại trừ an toàn:** Loại trừ 100% các tài khoản dính `khoaleemagic` (`SKIPPED_KHOALEE`).

## 7. Pitfall: Chạy Playwright Trực tiếp vs GPM API Launcher
- **Lỗi Google "Trình duyệt không an toàn" (`/v3/signin/rejected`):**
  - Nếu dùng Playwright `launch_persistent_context` trỏ thẳng vào `user_data_dir` của profile GPM, các cờ tự động hóa (`navigator.webdriver`, thiếu profile injection hook của GPM) sẽ bị Google bắt bài ngay lập tức, dẫn tới màn hình: *"Không thể đăng nhập cho bạn - Trình duyệt hoặc ứng dụng này có thể không an toàn"*.
- **Mẫu thực thi chuẩn (CDP via GPM Local REST API):**
  1. Gọi GPM API khởi chạy profile:
     `GET http://127.0.0.1:19995/api/v3/profiles/start/{profile_id}?win_scale=0.8`
  2. Lấy `remote_debugging_address` (CDP address, ví dụ `127.0.0.1:56601`) từ JSON response.
  3. Kết nối Playwright qua CDP:
     `browser = pw.chromium.connect_over_cdp(f"http://{addr}")`
  4. Nếu gặp Google reCAPTCHA challenge: Kích hoạt `solve_recaptcha_audio(page)` (sử dụng SpeechRecognition + pydub + FFmpeg) để giải audio challenge tự động.
  5. Đóng profile an toàn sau khi hoàn tất:
     `GET http://127.0.0.1:19995/api/v3/profiles/close/{profile_id}`

## 8. Pitfall: Chốt ca và Báo cáo khi không còn máy rảnh (`not ready` nhưng `is_late`)
- **Triệu chứng**: Watchdog thoát sớm tại nhánh kiểm tra máy rảnh (`if not ready: return 0`), khiến đoạn kiểm tra `is_late` ở cuối hàm `main()` bị bỏ qua hoàn toàn. Kết quả là các tài khoản đã login thành công trước đó trong ca không được gửi báo cáo tổng kết (`_format_summary_report`) và state không được đánh dấu hoàn thành ca.
- **Khắc phục chuẩn**: Bắt buộc kiểm tra `is_late` ngay trong nhánh `if not ready:`. Nếu đã quá giờ giới hạn của ca (Sáng >= 08:40, Trưa >= 13:40, Tối >= 23:30) thì thực hiện chốt ca, gửi báo cáo tổng kết và lưu `state` trước khi `return 0`.

## 9. Pitfall & Invariant: Preflight Check Google Cookie O(1) Trước Khi Nuôi
- **Hiện tượng & Bẫy ngầm:**
  - Nhầm lẫn rằng "mọi profile trong GroupId = 10 đều là profile sống có sẵn cookie Google".
  - Khi một số profile bị văng cookie / hết hạn phiên, cron nuôi (`cron_gpm_gmail_nurture.py`) nếu không tiền kiểm sẽ tuần tự: gọi GPM API start -> bật Chromium -> kết nối CDP (tốn 10-15s/máy) rồi mới phát hiện `0 token` Google, cảnh báo `NEEDS_LOGIN` và tắt đi.
  - Hậu quả: Toàn bộ batch nuôi tốn nhiều phút mở/tắt trình duyệt lãng phí và kết quả nuôi trả về 0/N tài khoản (`CHƯA_LOGIN (NEEDS_LOGIN)`).
- **Quy tắc giải quyết chuẩn (Preflight Disk Check O(1)):**
  - Không bao giờ khởi chạy GPM hay mở Chromium chỉ để kiểm tra xem profile còn đăng nhập Google hay không.
  - Đọc trực tiếp file SQLite cookie trên ổ cứng (`<GPM_PROFILE_BASE>/<profile_path>/Default/Network/Cookies` hoặc `Default/Cookies`).
  - Truy vấn kiểm tra: `SELECT count(*) FROM cookies WHERE host_key LIKE '%google.com' AND name IN ('SID', 'SSID', 'HSID', 'SAPISID')`.
  - Nếu số token `< 2`:
    1. Đánh dấu ngay `status = "NEEDS_LOGIN"` vào `gpm_gmail_nurture_state.json`.
    2. Loại bỏ profile khỏi danh sách nuôi ngay tại khâu tiền lọc (`filter_nurture_candidates`), không bao giờ gọi API start.
    3. Hàng đợi của `post_evening_gpm_login_watchdog.py` sẽ tự động nhặt các tài khoản này ở mức Ưu tiên 1 để tự động đăng nhập lại (re-authenticate) bằng mật khẩu và OTP từ S7.

## 10. Phân Tích & Đối Soát Số Liệu "Profile sẵn Google Session chờ OAuth" vs Antigravity Pool
- **Bẫy hiểu nhầm số liệu:**
  - Báo cáo ca in dòng: `• Profile sẵn Google Session chờ OAuth: 97 accounts` trong khi `Antigravity Pool: 121 accounts LIVE`.
  - Dễ gây hiểu lầm là đang có 97 tài khoản nhàn rỗi nằm chờ nạp vào OmniRoute nhưng hệ thống không chịu nạp.
- **Thực tế tính toán:**
  - `session_count` được tính bằng `len(_get_gpm_profiles_with_google_session())` trên **toàn bộ profile trong database GPM** có $\ge 2$ cookies Google (`SID, SSID, HSID, SAPISID`).
  - Hàm này **KHÔNG** trừ đi các tài khoản đã LIVE trên OmniRoute. Trong 97 profile có session thì đã có tới **85 profile đang LIVE trên OmniRoute**.
  - Số tài khoản thực tế có session nhưng chưa có trên OmniRoute là `net_pending = with_session - existing_omni` (ví dụ 12 accounts).
- **Phân loại 12 accounts pending:**
  1. *Đang ngâm Cooldown 72h an toàn:* Nhóm dính cờ risk engine của Google, chờ đúng mốc thời gian ISO trong `oauth_pipeline_status.json` để tự động mở hạn.
  2. *Bộ lọc loại trừ:* Dính recovery mail `khoaleemagic` hoặc cooldown 7 ngày.
  3. *Thiếu thông tin:* Thiếu mật khẩu trong `master_gmail_manager.xlsx`.
  4. *Tài khoản mới login:* Vừa hoàn tất login trong ca, bắt buộc đi qua gate `GPM_SOAKING` để cron nuôi lướt web trước, cấm kích hoạt OAuth SSO ngay.

## 11. Tối Ưu Lịch Cron Theo 2 Khoảng Rảnh Vàng Của Phone Farm (Idle Windows)
- **Xung đột ca nuôi feed vs Ca login S7:**
  - Đăng nhập Gmail trên GPM cần thiết bị S7 online và rảnh để nhận Google Prompt (OOTP/Security Code).
  - Ca nuôi feed TikTok diễn ra vào các khung:
    + Ca 1: 06:00 – 09:25
    + Ca 2: 11:35 – 15:25 (đợt 1: 11:35–13:25, đợt 2: 13:10–15:25)
    + Ca 3: 17:35 – 21:25
  - Nếu xếp cron login vào giữa ca feed (ví dụ 07:15–08:45 hoặc 12:00–13:45), máy bị chiếm dụng liên tục (`idle=False`), candidates bị dồn ứ đến cuối ca chạm ngưỡng `is_late` và bị hủy bỏ (force close).
- **2 Khoảng Rảnh Vàng Tối Ưu:**
  1. **Khoảng rảnh vàng 1 (Sau Ca 1):** `09:30 – 11:20` (~2 tiếng cả Farm rảnh 100%).
  2. **Khoảng rảnh vàng 2 (Sau Ca 2):** `15:30 – 17:20` (~2 tiếng cả Farm rảnh 100%).
  3. **Khung tối (Sau Ca 3):** `21:30 – 23:45` — Tối ưu hóa bằng cơ chế khóa theo từng thiết bị (`machine lock`), chỉ tránh đúng máy đang chạy avatar thay vì chờ cứng toàn bộ Farm up avatar xong mới bắt đầu.



