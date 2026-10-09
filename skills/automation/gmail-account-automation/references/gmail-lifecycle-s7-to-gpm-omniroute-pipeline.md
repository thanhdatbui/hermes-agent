# Chu Trình Vòng Đời Gmail: S7 Reg -> 7 Ngày Cooldown -> GPM Login Đêm -> OmniRoute Web Pool

Tài liệu chi tiết về vòng đời và cơ chế liên kết tự động của các tài khoản Gmail trên Taadaa Farm.

---

## 1. Tổng Quan Kiến Trúc Vòng Đời

Hệ thống tài khoản Gmail trên farm vận hành theo một chu trình khép kín 4 pha:

```
[PHA 1: S7 Reg & Warmup]
   │
   ├─► 1. Đăng ký Gmail mới trên Samsung S7 (gmail_reg_v10.py)
   ├─► 2. Tự động liên kết ChatGPT qua Direct Email OTP (hook_chatgpt_register.py)
   └─► 3. Đồng bộ vào master_gmail_manager.xlsx & gmail_clean_v2.xlsx
   │
   ▼
[PHA 2: Tạo Profile GPM & Cooldown 7 Ngày]
   │
   ├─► 1. Cronjob gpm-lifecycle-sync-watchdog (07:00-08:45) phát hiện Gmail LIVE mới
   ├─► 2. Tạo Profile GPMLogin chuẩn qua Local API (:19995), gán đúng Proxy S7
   └─► 3. Tài khoản được nuôi feed TikTok tự nhiên trên S7 trong 7 ngày để ngấu (tăng trust score)
   │
   ▼
[PHA 3: Watchdog Đêm Login GPM & Vượt 2SV]
   │
   ├─► 1. Khung giờ 21:30 - 23:45: post_evening_gpm_login_watchdog.py kích hoạt
   ├─► 2. Lọc ứng viên: cooldown_7days đã hết hạn, chưa có trong omniroute_success
   ├─► 3. Chạy run_oauth_s7_pipeline.py (tối đa 2 workers song song, proxy <= 2 acc/ngày)
   ├─► 4. Mở Profile GPM đăng nhập Google; nếu đòi Google Prompt số trên S7 -> tự động
   │       hook ATX/ADB sang máy S7 bấm số xác nhận (approve_s7_google_prompt)
   └─► 5. Đăng nhập Google vào Profile GPM thành công
   │
   ▼
[PHA 4: Nạp Token ChatGPT Vào OmniRoute Web Pool]
   │
   ├─► 1. Mở chatgpt.com trên Profile GPM -> Bấm Continue with Google / Sign in
   ├─► 2. Trích xuất Access Token / Session Token (eyJhbG...)
   ├─► 3. Nạp Token vào OmniRoute ChatGPT Web Pool (http://127.0.0.1:20129)
   └─► 4. Đánh dấu hoàn tất vào oauth_pipeline_status.json ("omniroute_success")
```

---

## 2. Chi Tiết Từng Thành Phần Trong Pipeline

### A. Pha 1: Tạo Tài Khoản & Warmup ChatGPT S7
- **Script thực thi**: `D:\Taadaa\register gmail\gmail_reg_v10.py`
- **Hook ChatGPT**: `D:\Taadaa\register gmail\scripts\hook_chatgpt_register.py`
- **Cơ chế**: Dùng luồng **Direct Email OTP** trực tiếp trên Chrome S7.
  - Nhập email -> OpenAI bắn OTP 6 số về App Gmail S7 -> đọc OTP từ *"Tất cả hộp thư đến"* -> điền vào Chrome -> hoàn tất tên & tuổi.
  - Giúp Gmail non nhận ngay email xác thực từ OpenAI, tăng độ trust chống Google purge (DIE).

### B. Pha 2: GPM Lifecycle Sync & Cooldown 7 Ngày
- **Cronjob**: `gpm-lifecycle-sync-watchdog` (Job ID: `b0f7828c992e`)
- **Lịch chạy**: `*/15 7,8 * * *` (mỗi 15 phút từ 07:00 đến 08:45).
- **Script**: `C:\Users\Kibe\AppData\Local\hermes\scripts\sync_gpm_lifecycle.py`
- **Nhiệm vụ**:
  - Đọc `D:\OneDrive\TaadaaData\kibe\master_gmail_manager.xlsx`.
  - Quét các tài khoản Gmail LIVE chưa có Profile trong GPM DB (`profile_data.db`).
  - Gọi GPM Local API (`POST http://127.0.0.1:19995/api/v3/profiles/create`) tạo profile Chrome sạch.
  - Gán đúng Proxy tĩnh của chính máy S7 tương ứng (`192.168.110.2:200xx` hoặc port Mobi 4G).
  - **Lý do cần 7 ngày cooldown**: Gmail mới reg tuyệt đối không đăng nhập Webmail/GPM ngay vì IP PC lạ sẽ kích hoạt checkpoint `challenge/iap` (đòi SMS số điện thoại). Sau 7 ngày có lịch sử nuôi feed trên máy thật, Google coi đây là tài khoản người dùng bình thường.

### C. Pha 3: Watchdog Đêm Login GPM (`post_evening_gpm_login_watchdog.py`)
- **Cronjob**: `post-evening-gpm-login-watchdog` (Job ID: `30ffbf1672e7`)
- **Lịch chạy**: `*/5 20,21,22,23 * * *` (chạy sau Ca 3 tối, từ 20:15/21:30 đến 23:45).
- **Script**: `C:\Users\Kibe\AppData\Local\hermes\scripts\post_evening_gpm_login_watchdog.py`
- **Ràng buộc an toàn (Invariants & Concurrency)**:
  - `MAX_WORKERS = 5`: Cấu hình 5 workers song song theo yêu cầu user (stagger 5s).
  - `MAX_LOGINS_PER_PROXY = 2`: Mỗi port proxy tối đa 2 acc/ngày (`proxy_limit 2/port/ngày`).
  - Mỗi máy (`mid`) chỉ login đúng 1 lần/ngày.
  - Cách ca nuôi feed tiếp theo ít nhất 45 phút (`MIN_IDLE_BUFFER_MIN = 45`).
  - **Gate 2FA_Secret bắt buộc khi lọc candidate (`get_candidates`)**:
    - Khi lọc từ `master_gmail_manager.xlsx` (Sheet `Kibe_Farm_S7`), BẮT BUỘC kiểm tra cột `2FA_Secret` (cột 4, `r[4]`).
    - Nếu `r[4]` rỗng, `None`, hoặc `'NONE'`, phải bỏ qua (`continue`). Tài khoản thiếu 2FA tuyệt đối không đưa vào GPM login pipeline vì sẽ bị Google checkpoint số điện thoại SMS (`challenge/iap`).
    - **Bản chất sống còn của 2FA TOTP**: 2FA không làm tăng "Trust Score" con người, nhưng là **Lá Chắn Thoát Hiểm (Deterministic Challenge Bypass)** duy nhất. Khi đổi môi trường từ Android S7 sang PC GPM qua IP mới, Google RBA bắt buộc kích hoạt Secondary Challenge: nếu có 2FA TOTP thì Google chỉ hỏi mã 6 số (vượt qua nhẹ nhàng bằng pyotp); nếu KHÔNG có 2FA, Google lập tức ép vào SMS SĐT (`challenge/iap`) làm chết via ngay lập tức.
    - **Tại sao bắt buộc bật 2FA trên S7, cấm bật trên GPM**: Thiết bị S7 có độ tin cậy phần cứng cao nhất. Nếu login GPM mà tài khoản chưa có 2FA, phiên GPM là Low Trust Session; vừa vào thiết bị mới mà lao vào đổi cài đặt bảo mật / bật 2FA sẽ bị Google gắn cờ Account Takeover (nghi ngờ hacker cướp nick) và văng session/khóa tài khoản ngay lập tức.
    - **Logic tính tuổi tài khoản >= 7 ngày ngâm**: BẮT BUỘC đọc ngày tạo gốc từ file `gmail_clean_v2.xlsx` (cột 7 / index 6). Tuyệt đối không đọc cột 15 (`Cập Nhật`) của `master_gmail_manager.xlsx` vì đây chỉ là timestamp của lần quét checkmail gần nhất (dẫn đến bị tính 0 ngày tuổi và loại bỏ nhầm 100% ứng viên).
    - **Khung giờ chạy mở rộng**: Hỗ trợ chạy cuốn chiếu cả ban ngày (Sáng 07:15 - 08:45, Trưa 12:00 - 13:45) và ban đêm (20:15 - 23:45). Tự động kiểm tra device lock và lịch manifest nuôi feed với bộ đệm `MIN_IDLE_BUFFER_MIN = 45 phút` để không bao giờ xung đột lịch máy farm.
    - **Tách biệt chiến lược ChatGPT-Web vs Google Antigravity OAuth**:
      - *ChatGPT-Web*: Ứng dụng tiêu dùng bên thứ 3 (OpenAI), Google xem là hành vi người dùng tự nhiên. Cần lấy token nạp pool ngay sau khi login GPM để vừa có tài nguyên vừa tạo thêm vết sinh hoạt uy tín.
      - *Google Antigravity (Google Cloud Developer API)*: Sân nhà của Google, có bộ lọc Sybil / Developer Abuse cực gắt. TUYỆT ĐỐI HOÃN 1-2 tuần sau khi login GPM, đợi profile có lịch sử cookies và hoạt động nhẹ (lướt 1 video YouTube, search vài truy vấn) mới cấp quyền OAuth Antigravity.
    - **Áp dụng đồng bộ cho cả 2 nhóm**: Nhóm 1 (`cooldown_expired`) và Nhóm 2 (`ready_gpm_oauth`) đều phải có `2FA_Secret` hợp lệ từ `master_gmail_manager.xlsx`.
    - **Tối ưu hiệu năng**: Đọc `master_gmail_manager.xlsx` một lần duy nhất để tạo `valid_2fa_emails` set và danh sách candidate hợp lệ, tránh đọc lại file Excel nhiều lần làm nghẽn I/O.
- **Xử lý 2-Step Verification (Google Prompt)**:
  - Khi đăng nhập Google trên GPM, Google hiển thị màn hình: *"Kiểm tra điện thoại của bạn... Chạm vào số [XX] trên màn hình S7"*.
  - Script gọi hàm `approve_s7_google_prompt(mid, serial, target_pin, target_email)`:
    - Chiếm device lock trên S7 (`acquire_device_lock`).
    - Bật màn hình S7 (`keyevent 224` + `82`).
    - Dump XML qua ATX agent (`port 17000 + mid -> 7912`).
    - Tự động tìm và tap chính xác vào con số `XX` trên màn hình điện thoại.
    - Nhả device lock, Google trên GPM đăng nhập thành công.
- **Xử lý Hard Phone Checkpoint & Cấm Spam SĐT (Farm Invariant)**:
  - Khi Google chuyển hướng sang màn hình đòi nhập số điện thoại (`challenge/iap` hoặc `hard_phone_checkpoint`):
    - Ảnh debug được tự động chụp và lưu tại `D:\Taadaa\GPM auto\debug_screenshots\oauth_<email>_hard_phone_checkpoint_<ts>.png`.
    - **Quy tắc an toàn Farm tối cao**: Tuyệt đối CẤM spam SĐT hoặc cố bypass bừa bãi trên GPM. Trả về `FAIL` fail-closed an toàn, không kích hoạt thêm luồng thử lại trong cùng ca tối để tránh làm tài khoản bị Google khóa vĩnh viễn (DIE).
- **Chuẩn Báo Cáo Action-First Cho Cron Watchdog**:
  - Im lặng hoàn toàn trong lúc chạy từng batch con lẻ.
  - Chỉ xuất đúng 1 dòng stdout tổng kết khi hoàn tất toàn ca hoặc chạm mốc giới hạn ca tối (`post_evening_gpm_login_state.json`):
    `[LOGIN GPM ĐÊM - TỔNG KẾT] ✓ <ok> | ✗ <fail> | proxy_limit 2/port/ngày | Hoàn tất ca tối`.

### D. Pha 4: Nạp Token ChatGPT Vào OmniRoute Pool
- **Script**: `D:\Taadaa\GPM auto\scripts\run_oauth_s7_pipeline.py` & `add_oauth_omniroute.py`
- **Endpoint OmniRoute**: `http://127.0.0.1:20129`
- **Cách thức**:
  - Mở trang `https://chatgpt.com` trên Profile GPM vừa đăng nhập Google.
  - Do tài khoản đã được đăng ký ChatGPT từ trước (ở Pha 1), việc đăng nhập diễn ra trơn tru không cần onboard lại tên/tuổi.
  - Bóc tách token xác thực (`accessToken` / `sessionToken` dạng `eyJhbG...`).
  - Nạp token vào pool xoay vòng (Round-Robin Pool) của OmniRoute `:20129`.
  - OmniRoute dùng pool này để phục vụ:
    - Sol Review / Sol Scorecard (chấm điểm code review).
    - Sol Plan (lập kế hoạch kiến trúc cho các task lớn).
    - Terra API và các luồng AI Coordinator phân tích farm.
  - Ghi nhận trạng thái hoàn tất vào `D:\Taadaa\GPM auto\config\oauth_pipeline_status.json` tại mục `omniroute_success`.

---

## 3. Bảng Tổng Hợp Trạng Thái & File Dữ Liệu Liên Quan

| Thành Phần | Đường Dẫn / Endpoint | Vai Trò |
|---|---|---|
| Master Gmail Manager | `D:\OneDrive\TaadaaData\kibe\master_gmail_manager.xlsx` | Bảng quản lý gốc toàn bộ Gmail, pass, máy, proxy |
| Pipeline Status JSON | `D:\Taadaa\GPM auto\config\oauth_pipeline_status.json` | Theo dõi trạng thái cooldown_7days, omniroute_success, checkpoint |
| GPM Local API v3 | `http://127.0.0.1:19995/api/v3` | Tạo và điều khiển Profile GPM trình duyệt |
| OmniRoute AI Proxy | `http://127.0.0.1:20129` | Cụm proxy ChatGPT Web pool phục vụ review/planning |
| Watchdog Đêm | `C:\Users\Kibe\AppData\Local\hermes\scripts\post_evening_gpm_login_watchdog.py` | Bộ điều phối tự động chạy lúc 21:30 - 23:45 |
| Pipeline Runner | `D:\Taadaa\GPM auto\scripts\run_oauth_s7_pipeline.py` | Bộ thực thi Playwright + S7 prompt approval |
