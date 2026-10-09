# Hotmail → GPM → ChatGPT → Codex → 7d Change-Info Continuous Eligibility Scanner

## 1. Bản chất kiến trúc & Nguyên tắc điều phối

- **Kiến Trúc Điều Phối Token-First (Token-First Architecture)**:
  - **Tài khoản ĐÃ CÓ Microsoft Graph OAuth Token (`token` / `refresh_token`)**:
    + Nguồn: Cột 9 `gmail_clean_v2.xlsx` hoặc `hotmail_input.txt` (chiếm 222/403 tài khoản farm).
    + `get_hotmail_credentials()` trong `chatgpt_gpm_direct_reg.py` tự động đọc token & client_id trực tiếp từ `gmail_clean_v2.xlsx`.
    + **BỎ QUA 100% Stage 1 (`HOTMAIL_LOGIN`)**: Tuyệt đối KHÔNG đăng nhập web `login.live.com` qua proxy GPM trước khi reg ChatGPT/Codex. Việc đăng nhập sớm bằng password làm Microsoft phát hiện IP proxy mới và kích hoạt Checkpoint đòi mail khôi phục vô ích.
    + Mở profile GPM nhảy thẳng vào Stage 2 (`CHATGPT_REG`) truy cập `chatgpt.com`.
    + Khi OpenAI gửi mã xác nhận về Hotmail, script PC gọi **Microsoft Graph API** (`https://graph.microsoft.com/v1.0/me/messages`) bốc OTP tức thì trong 2s.
    + Nối tiếp Stage 3 (`CODEX_OAUTH`) kích hoạt 5sim số VN $\rightarrow$ Nạp quota vào OmniRoute `:20129`.
    + Mục đích đăng nhập web Hotmail thực chất chỉ để chạy Stage 6 (`CHANGE_INFO`) đổi mật khẩu sau khi tài khoản đã kích hoạt xong ChatGPT và ngâm đủ 7 ngày.
  - **Tài khoản CHƯA CÓ OAuth Token (181/403 tài khoản)**:
    + Bắt buộc chạy Stage 1 (`HOTMAIL_LOGIN`) trên GPM để có phiên webmail lấy OTP ChatGPT.
    + Nếu gặp màn hình đòi mail khôi phục domain `@fviainboxes.com`: áp dụng quy trình cào OTP từ web `https://fviainboxes.com/` (nhập prefix mail khôi phục, click Get Email) để giải phóng checkpoint (xem `references/boxtaikhoan-hotmail-fviainboxes-and-s7-audit.md`).

- **Continuous Eligibility Scanner (Quét điều kiện liên tục)**:
  - Cron chạy định kỳ (mỗi 15-30 phút).
  - Không ép toàn bộ profile chạy cùng một stage; mỗi lượt quét toàn bộ danh sách profile mục tiêu và chọn **stage đầu tiên đang đủ điều kiện và chưa hoàn tất** của từng profile để chạy.
  - Ví dụ trong cùng 1 tick: Profile A chưa login Hotmail thì login; Profile B đã reg ChatGPT đủ 24-48h thì nhảy thẳng vào Codex OAuth; Profile C chưa đủ thời gian ngâm thì skip; Profile D đủ 7 ngày thì chạy change-info.

- **Mô hình Concurrency 5 Profile Song Song & IP Collision Filter**:
  - Chạy đồng thời tối đa **5 profiles** qua `ThreadPoolExecutor(max_workers=5)` hoặc batch workers độc lập.
  - **Bộ lọc Cooldown 24h THEO LOẠI THAO TÁC trên từng IP/Proxy (BẮT BUỘC GHI NHẬN CẢ KHI FAIL)**:
    - *CÙNG LOẠI THAO TÁC*: Trong vòng 24h, trên 1 cổng IP/proxy, chỉ được phép chạy tối đa 1 nick cho cùng 1 loại thao tác (ví dụ: nếu IP Máy 2 vừa chạy `CHATGPT_REG` thì trong 24h tới không nick nào khác trên IP Máy 2 được chạy `CHATGPT_REG` nữa).
    - *Bẫy Bỏ Sót Cooldown Khi Thất Bại (Critical Failure Loop Pitfall - User Correction 2026-09-30)*: Nếu supervisor chỉ ghi `ip_action_history[port][stage] = now()` khi `status == "COMPLETED"`, thì khi một nick bị `FAILED` / `BLOCKED`, IP và nick đó không được cập nhật timestamp. 5 phút sau cron tick lại thấy IP rảnh và nick cũ chưa xong -> tiếp tục bốc lại đúng nick đó trên đúng proxy đó, gây vòng lặp thử đi thử lại liên tục làm hỏng session và rủi ro bị OpenAI ban IP. BẮT BUỘC cập nhật `ip_action_history[port][stage] = now()` và `info["updated_at"] = now()` cho MỌI kết quả (kể cả FAILED / ERROR / BLOCKED).
    - *KHÁC LOẠI THAO TÁC*: Trên IP đó, các nick khác (hoặc chính nick đó) **vẫn được phép chạy các thao tác khác** (`CODEX_OAUTH`, `CHANGE_INFO`...) hoàn toàn bình thường mà không bị áp cooldown chéo.
    - Duy trì cấu trúc theo dõi: `ip_action_history[port][stage] = timestamp`. Khi chọn tối đa 5 nick chạy song song trong 1 tick cron, supervisor bắt buộc chọn 5 nick trên 5 IP/proxy port hoàn toàn khác nhau.
  - Bên trong từng profile, các stage thực thi **hoàn toàn tuần tự**.
  - **Kiến Trúc Hybrid Concurrency: Reg ChatGPT Song Song vs Codex OAuth Mutex**:
    - *Khâu Reg ChatGPT (`CHATGPT_REG`)*: Chạy song song tối đa 5 profiles trên 5 proxy khác nhau vì chỉ tương tác với web `chatgpt.com` và Microsoft Graph API, không chiếm dụng tài nguyên localhost.
    - *Khâu Codex OAuth (`CODEX_OAUTH`)*: Bắt buộc chiếm **Mutex độc quyền cho cổng TCP 1455** (`localhost:1455/auth/callback`). OmniRoute chỉ mở 1 callback server singleton tại 1 thời điểm (`globalThis.__pkceCallbackStates["codex"]`). Nếu 2 worker cùng lúc gọi `start-callback-server`, worker sau sẽ hủy server và xóa `codeVerifier` của worker trước, gây lỗi mismatch state hoặc nuốt nhầm token của nhau. Do đó, bước Codex OAuth bắt buộc phải xếp hàng tuần tự (FIFO) qua file lock/mutex dù các bước trước đó chạy song song.

- **Cơ chế Chống Mở Trùng Profile GPM (Per-Profile Mutex Lock)**:
  - Để chống triệt để việc nhiều cronjobs khác nhau (nuôi Gmail, login Hotmail, ChatGPT reg, Codex) mở nhầm cùng một profile GPM cùng lúc:
  - Thư mục lock: `D:\Taadaa\runtime\kibe\cron-state\profile_locks\<profile_id>.lock`.
  - Tích hợp trực tiếp vào `gpm_client.py`:
    - `start_profile(profile_id)`: Tự động `acquire_profile_lock(profile_id)`. Nếu profile đang bị tiến trình khác giữ lock -> Ném ngay `RuntimeError("GPM profile is locked by another process")`. Lock cũ > 30 phút hoặc PID đã chết sẽ được tự động dọn dẹp (auto-heal).
    - `stop_profile(profile_id)`: Luôn giải phóng lock trong khối `finally`.
    - `is_profile_locked(profile_id)`: Supervisor gọi hàm này trong `select_candidates()` để chủ động bỏ qua các profile đang bận.
  - **Kỷ luật Teardown**: Bất kỳ stage nào kết thúc (thành công, thất bại hay timeout), script BẮT BUỘC gọi `api("GET", f"/api/v3/profiles/close/{pid}")` trong khối `finally` để đóng sạch cửa sổ Chrome, không bao giờ để profile chạy ngầm.

- **Báo Cáo Định Kỳ Mỗi 6 Giờ về Farm Alert & Kỷ Luật Silent Supervisor 5m**:
  - **Supervisor 5m (`gpm-5profiles-lifecycle-supervisor`)**:
    - Lịch: `*/5 * * * *`.
    - Cấu hình delivery: BẮT BUỘC `deliver: 'local'`.
    - Nguyên tắc: Chạy quét ngầm liên tục, TUYỆT ĐỐI KHÔNG spam tin nhắn mỗi 5 phút về Telegram dưới bất kỳ hình thức nào.
  - **Báo Cáo Tổng Hợp 6 Giờ (`hotmail-gpm-lifecycle-6h-report`)**:
  - Script: `cron_hotmail_gpm_lifecycle_6h_report.py`.
  - Lịch: `0 */6 * * *` (đúng 6 tiếng gửi 1 lần).
  - Cấu hình delivery: `telegram:-5373649734` (Farm Alerts).
  - **Yêu cầu bắt buộc về hiển thị lỗi (User Instruction & Pitfall)**: Báo cáo 6h KHÔNG ĐƯỢC CHỈ đưa ra các con số tổng hợp vô hồn. BẮT BUỘC phải trích xuất và hiển thị rõ ràng danh sách tài khoản bị `FAILED/ERROR` thành một khối riêng: `🔴 DANH SÁCH TÀI KHOẢN GẶP LỖI CẦN XỬ LÝ` kèm máy, email và lý do cụ thể (sai mật khẩu, vướng verify email, rate limit do thử sai nhiều lần...). Không giấu lỗi trong số liệu stage tổng. Khi danh sách lỗi lớn, giới hạn hiển thị tối đa 15 dòng lỗi đại diện kèm dòng tóm tắt `... và N tài khoản khác` để chống spam làm tràn khung chat Telegram.
  - **Yêu cầu bắt buộc về chỉ số Tỉ Lệ Codex OAuth (User Directive & Audit Invariant)**: Báo cáo 6h BẮT BUỘC phải có dòng hiển thị rõ ràng số lượng và tỉ lệ phần trăm hoàn tất Codex OAuth: `• Đã kích hoạt Codex OAuth: <completed_codex>/<completed_chatgpt> (<codex_pct>% trên nick có GPT, <overall_pct>% trên tổng)`.
      + Điều kiện tính `completed_codex`: tài khoản có `info.get("codex_oauth_at")` HOẶC đã chuyển sang các stage sau Codex OAuth (`WAIT_7D`, `CHANGE_INFO`, `REMOVE_RECOVERY`, `SIGN_OUT_EVERYWHERE`, `RELOGIN_NEW_PASSWORD`, `DONE`).
      + Tuyệt đối không để báo cáo chỉ hiển thị số lượng ChatGPT Reg mà khuyết thiếu tỉ lệ kích hoạt Codex OAuth thực tế.
      + **BẮT BUỘC BỔ SUNG TỈ LỆ CODEX OAUTH RIÊNG TRONG CHU KỲ 6H (User Directive 2026-10-01)**: Báo cáo 6h KHÔNG ĐƯỢC chỉ đưa tỉ lệ tổng lũy kế và xả log sự kiện thô. BẮT BUỘC phải gom và tính tỉ lệ chuyển đổi riêng của chu kỳ 6 giờ:
        `• Tỉ lệ Codex OAuth trong 6h: <codex_6h_ok>/<codex_6h_total> (<pct>%) (+<codex_6h_ok> nick kích hoạt mới)`
        (với `codex_6h_ok`: số nick CODEX_OAUTH COMPLETED trong 6h, `codex_6h_total`: tổng số lượt CODEX_OAUTH được thử trong 6h). Nhờ đó User thấy ngay hiệu suất và tốc độ hoàn tất thực tế của ca vừa qua.
    - **Kỷ luật đồng bộ 3 điểm khi sửa Cron Script**: Khi cập nhật script cron tại `C:\Users\Kibe\AppData\Local\hermes\scripts\`, bắt buộc sao chép đồng bộ ngay sang `D:\Taadaa\Hermes\deploy\hermes-home\scripts\` và `D:\OneDrive\Taadaa_Sync_Shared\hermes-cron\scripts\` để tránh bị `cron_sync_watchdog.py` ghi đè ngược lại phiên bản cũ.
    - Nội dung: Tổng hợp toàn bộ tiến độ, phân bổ stage, danh sách nick lỗi chi tiết và thống kê các sự kiện/profile đã xử lý trong suốt 6 giờ vừa qua thành một bản tin duy nhất.

- **Tự động tạo Profile GPM ở Stage 1 (Profile Auto-Creation)**:
  - Nếu tài khoản chưa có profile trên GPM, Stage 1 tự động gọi GPM API `POST /api/v3/profiles/create` với tên chuẩn `<máy 2 số> - <email> - <cổng_proxy>`, gán `raw_proxy` tương ứng từ `PROXYgandienthoai.xlsx`, `browser_type='Chrome'`, `group_id=1`, lưu `profile_id` vào state rồi mới mở lên login.

- **Single Batch Guard (Cấm dựng Lock Map rườm rà)**:
  - CẤM viết hệ thống lock map phức tạp per-account gây nghẽn và deadlock.
  - Chỉ dùng **1 batch-level single-instance lock duy nhất** (qua file lock Windows `msvcrt.locking(LK_NBLCK)` trên `batch_gpm_hotmail_supervisor.lock`) để ngăn 2 tiến trình cron chạy đè lên nhau.

---

## 2. Thứ tự 10 Stage Bắt Buộc (Strict Stage Progression)

Thứ tự thực thi trong vòng đời từng tài khoản Hotmail trên GPM:

```text
1. HOTMAIL_LOGIN (Đăng nhập web login.live.com trên profile GPM theo proxy máy S7)
   ↓
2. CHATGPT_REG (Direct Email + PASS CHATGPT + Microsoft Graph OTP)
   ↓
3. CODEX_OAUTH (Codex OAuth vào OmniRoute :20129 + Auto-ver sim VN 5sim + TẠM TẮT OMNIROUTE is_active=0)
   ↓
4. WAIT_48H_SOAK (Ngâm tài khoản Codex trên OmniRoute ở trạng thái is_active=0 đủ 48h để bảo toàn Trust Score)
   ↓
5. WAIT_7D (Ngâm tài khoản Hotmail trên GPM đủ >= 7 ngày từ ngày login)
   ↓
6. CHANGE_INFO (Đổi mật khẩu Hotmail về đúng PASS CHATGPT để đồng nhất quản lý)
   ↓
7. REMOVE_RECOVERY (Gỡ sạch email khôi phục của bên bán)
   ↓
8. SIGN_OUT_EVERYWHERE (Đăng xuất Hotmail khỏi toàn bộ thiết bị cũ của bên bán)
   ↓
9. RELOGIN_NEW_PASSWORD (Đăng nhập lại Hotmail trên GPM bằng mật khẩu mới)
   ↓
10. DONE
```

*Chiến lược Combo Trọn Gói (Nối Luồng Tức Thì) & Tạm Tắt OmniRoute*:
- **Combo Liền Tay (Zero-Wait giữa ChatGPT & Codex)**: Worker khi nhận profile chạy liên tục `HOTMAIL_LOGIN` $\rightarrow$ `CHATGPT_REG` $\rightarrow$ `CODEX_OAUTH (Ver Sim VN 5sim)` trong cùng 1 phiên làm việc trên đúng 1 IP proxy tĩnh đó, tránh việc nhiều ngày sau mở lại profile bị lệch session hoặc bắt login lại. Tuyệt đối KHÔNG ngâm chờ giữa chặng Reg ChatGPT và Ver Codex.
- **Khai Thác Kép Ngay Sau Reg ChatGPT (Dual-Harvest Web Session + Codex OAuth - User Correction 2026-10-01)**:
  + *Ngay khi Reg ChatGPT xong (`CHATGPT_REG`)*: Trích xuất ngay cookie `__Secure-next-auth.session-token` (hỗ trợ cả cookie đơn và chunked `.0`, `.1`) qua hàm `sync_registered_chatgpt_web_connection()` trong `chatgpt_gpm_direct_reg.py` $\rightarrow$ nạp connection `provider = 'chatgpt-web'` vào OmniRoute với `is_active = 0` và `test_status = 'soaking'`.
  + *Ngay khi Codex OAuth xong (`CODEX_OAUTH`)*: Nạp connection `provider = 'codex'` vào OmniRoute với `is_active = 0`.
  + *Ngâm tĩnh kép 48h*: Cả 2 connection (`chatgpt-web` và `codex`) đều được ngâm an toàn 48h để bảo vệ Trust Score, chống Cloudflare Sentinel / Turnstile quét làm bay màu nick non trong 48h đầu.
  + *Kích hoạt đồng bộ & Nạp Combo tự động (`cron_omni_activate_soaked_codex.py`)*: Sau đủ 48h ngâm, cronjob tự động bật `is_active = 1` cho cả 2 connection và tự động nạp vào đúng các combo:
    * `chatgpt-web` $\rightarrow$ `chatgpt-web-pool` và `gpt-web-sol` (model `chatgpt-web/gpt-5.6-sol-high`).
    * `codex` $\rightarrow$ `codex-terra` (model `codex/gpt-5.6-terra`) và `codex-luna` (model `codex/gpt-5.6-luna-high`).
  + *Tối ưu 100% tài nguyên*: 1 tài khoản đăng ký phục vụ đồng thời cả Coding CLI (Codex) lẫn Web Inference mà không phát sinh thêm chi phí proxy hay mua SIM phụ.
- **Tạm Tắt OmniRoute Ngay Sau Khi Ver**: Ngay khi lấy được OAuth Connection ID, script bắt buộc chạy truy vấn SQLite O(1) trên `C:\Users\Kibe\.omniroute\storage.sqlite`:
  `UPDATE provider_connections SET is_active = 0 WHERE id = ?`
  để ngâm tĩnh tài khoản 48h, tuyệt đối không cho traffic API chạm vào bào dồn dập khiến OpenAI gắn cờ bot velocity/spam.

---

## 2.1. Bẫy Đồng Bộ Hóa Khi Tích Hợp "Reg Xong Ver Luôn" trong Supervisor
- **Bẫy Đồng Bộ Hóa Khi Tích Hợp "Reg Xong Ver Luôn" trong Supervisor**:
  - Khi supervisor hỗ trợ cả luồng gộp và luồng rời, nếu chỉ nối chuỗi `run_cmd(CODEX_OAUTH_SCRIPT)` ở nhánh `if stage == "HOTMAIL_LOGIN"` mà quên nhánh `elif stage == "CHATGPT_REG"`, thì các tài khoản retry hoặc chạy riêng stage reg ChatGPT sẽ chỉ reg xong rồi dừng lại, không tự động ver số.
  - Cả 2 nhánh BẮT BUỘC đều phải xâu chuỗi gọi `codex_5sim_auto_verify.py` ngay khi `chatgpt_gpm_direct_reg.py` trả về `SUCCESS`.
- **Bẫy thứ tự `STAGE_ORDER` chặn ngâm ngược vị trí**:
  - Nếu `STAGE_ORDER` khai báo `"WAIT_24_48H"` ĐỨNG TRƯỚC `"CODEX_OAUTH"`, hàm `select_candidates()` sẽ kiểm tra `now - chatgpt_registered_at < 24h` và `continue` (bỏ qua), khiến hàng chục tài khoản bị kẹt ngâm 24h vô ích thay vì được ver số ngay.
  - Thứ tự chuẩn trong code supervisor:
    `STAGE_ORDER = ["HOTMAIL_LOGIN", "CHATGPT_REG", "CODEX_OAUTH", "WAIT_7D", ...]`
  - Bất kỳ tài khoản nào vừa reg ChatGPT xong phải có `next_stage = "CODEX_OAUTH"` (hoặc nếu ver luôn trong lượt thì nhảy thẳng sang `WAIT_7D`).
- **Xử lý tài khoản cũ còn kẹt stage `WAIT_24_48H` sau khi đổi flow**:
  - Khi bỏ giai đoạn ngâm trước OAuth, nhánh `if stage == "WAIT_24_48H"` trong `execute()` phải nối thẳng sang chạy `CODEX_OAUTH_SCRIPT` và hàm `select_candidates()` phải gỡ bỏ bộ lọc chặn `(now_dt - reg_time) < 24 * 3600` để toàn bộ tài khoản tồn đọng được giải phóng ngay sang chặng ver số.
- **Bẫy File Lock msvcrt khi debug / chạy `--dry-run`**:
  - `WindowsBatchGuard` dùng lock độc quyền `msvcrt.locking(LK_NBLCK)` trên file `.lock`. Nếu một tiến trình supervisor trước đó bị kill đột ngột hoặc cron đang tick dở, lệnh `--dry-run` sẽ ném ngay: `[GUARD] another instance or lock failure: [Errno 13] Permission denied`.
  - Phải kiểm tra tiến trình python đang chạy (`ps aux | grep python` hoặc `psutil`), nếu không có tiến trình supervisor nào đang chạy ngầm thì mới được xóa file lock để khôi phục.

---

## 3. Quản lý Mật khẩu: Cột PASS CHATGPT trong Workbook

- **Vị trí chuẩn**: Cột L (index 11 / cột thứ 12) trong file `D:\OneDrive\TaadaaData\kibe\taikhoan_dat_v2_updated .xlsx`, sheet `Tài Khoản`.
- **Cơ chế**:
  - `PASS MAIL`: Mật khẩu hòm thư Hotmail/Gmail hiện tại.
  - `PASS CHATGPT`: Mật khẩu dùng riêng để đăng ký và quản lý ChatGPT.
  - Cả tài khoản Gmail cũ và Hotmail đều được backfill vào cột này (`PASS CHATGPT = PASS MAIL` ban đầu nếu trống).
  - Khi reg ChatGPT: Resolver bắt buộc lấy mật khẩu từ cột `PASS CHATGPT`.
  - Khi chạy Stage 6 (`CHANGE_INFO`): Đổi mật khẩu Hotmail về **trùng khớp với `PASS CHATGPT`** để tiện quản lý lâu dài mà không bị lệch credential.

---

## 4. Microsoft Graph API OTP vs Browser Login

- **Đăng nhập Hotmail lên GPM**: Dùng trực tiếp Email + `PASS MAIL` trên `login.live.com` qua Playwright CDP. Microsoft OAuth refresh token không dùng để inject cookie browser.
- **Lấy OTP ChatGPT từ Hotmail**:
  - Không mở tab `mail.google.com` hay web Outlook lag giật.
  - Dùng Refresh Token + Client ID từ `hotmail_input.txt` gọi endpoint OAuth2 Microsoft (`https://login.microsoftonline.com/common/oauth2/v2.0/token`) để lấy `access_token`.
  - Gọi Microsoft Graph API (`https://graph.microsoft.com/v1.0/me/messages?$top=5&$select=subject,body,receivedDateTime`) để trích xuất OTP 6 số mới nhất từ OpenAI.

---

- **Bẫy Clock Skew khi Polling OTP qua Microsoft Graph API**:
  - Khi OpenAI gửi email OTP, email đến hòm thư Microsoft có thể mang timestamp sớm hơn vài giây so với đồng hồ hệ thống local do chênh lệch server clock (clock skew).
  - Nếu dùng `otp_started_at = datetime.now(timezone.utc)` mà không trừ độ trễ, điều kiện `received <= otp_started_at` sẽ loại nhầm chính email OTP vừa gửi đến, dẫn đến lỗi `FAIL_OTP_TIMEOUT`.
  - Luôn đặt dung sai: `otp_started_at = datetime.now(timezone.utc) - timedelta(minutes=1)` và nhớ `from datetime import timedelta`.

- **Bẫy `sys.path` khi cron chạy script từ thư mục khác**:
  - Khi script như `batch_gpm_5profiles_supervisor.py` được gọi từ cron wrapper (`~/AppData/Local/hermes/scripts/gpm_5profiles_supervisor_wrapper.py`) hoặc subprocess từ working directory khác ngoài repo root, lệnh `from src.gpm_client import ...` sẽ crash ngay với `ModuleNotFoundError: No module named 'src'`.
  - Khắc phục bắt buộc ở đầu mọi file script dưới `D:\Taadaa\GPM auto\scripts\`:
    ```python
    from pathlib import Path
    import sys
    ROOT_DIR = Path(__file__).resolve().parents[1]
    if str(ROOT_DIR) not in sys.path:
        sys.path.insert(0, str(ROOT_DIR))
    ```
  - **Kiểm tra sau sửa đổi**: Bắt buộc test cả CLI direct (`python scripts/<script>.py --help`) và wrapper trigger qua `cronjob action='run' job_id='...'` để verify exit code 0 thực tế trước khi kết luận hoàn tất.

- **Bẫy Script Login Hotmail hardcode thiếu CLI args**:
  - Script nền như `batch_gpm_hotmail_password_login.py` ban đầu chỉ có danh sách cứng 5 tài khoản mẫu trong hàm `main()`. Để supervisor điều phối được cho toàn bộ 403 tài khoản farm, script này bắt buộc phải bổ sung CLI arguments (`argparse`): `--profile-id`, `--email`, `--password`, `--proxy-port`, `--raw-proxy`, `--machine`, cho phép chạy độc lập từng tài khoản với exit code `0` khi thành công.

- **Bẫy nút "Tiếp" trên màn hình Điều khoản Microsoft (`account.live.com/tou/accrue`)**:
  - Khi đăng nhập tài khoản Hotmail mới, Microsoft thường hiển thị trang cập nhật điều khoản: `https://account.live.com/tou/accrue...` với nút bấm duy nhất mang chữ `"Tiếp"` (`class="btn btn-primary"`, `input[value*='Tiếp']` hoặc `button:has-text('Tiếp')`).
  - Nếu bộ selector chỉ tìm `"Tiếp tục"`, `"Tiếp theo"`, `"Next"` thì sẽ không khớp, và `inner_text()` trên thẻ `<input>` trả về chuỗi rỗng `""` dẫn đến timeout 5 vòng lặp.
  - Luôn bổ sung selector: `"input[value*='Tiếp']", "button:has-text('Tiếp')", ".btn-primary", "input[type='submit']"` và kiểm tra cả `btn.get_attribute("value")`.

- **Bẫy URL check false-negative `login.live.com in final_url`**:
  - URL trang điều khoản `https://account.live.com/tou/accrue?mkt=VI-VN&ru=https://login.live.com/...` chứa chuỗi `login.live.com` trong query parameter `ru=...`.
  - Nếu kiểm tra chuỗi đơn giản `"login.live.com" in final_url` thì sẽ bị nhận nhầm là tài khoản còn kẹt ở trang đăng nhập và trả về `status: BLOCKED`.
  - Bắt buộc dùng `urllib.parse.urlparse`: kiểm tra `netloc` (`account.live.com`, `account.microsoft.com`, `outlook.live.com`) và `path not in ['/', '/login.srf']` để nhận diện đăng nhập thành công.

- **Bẫy API GPM `POST /api/v3/profiles/create` body payload**:
  - Khi tạo profile bằng API v3 của GPMLogin: trường tên profile bắt buộc là `profile_name` (không phải `name`). Nếu gửi `{"name": ...}` API có thể trả về lỗi hoặc thiếu trường `id` trong `data`.

## 5. Các Bẫy Triển Khai Thực Tế (Production Pitfalls)

- **Cấm Tuyệt Đối Google SSO Khi Login/OAuth OpenAI (PROJECT_RULES.md Invariant)**:
  - Khi form đăng nhập OpenAI hoặc OAuth hiển thị nút "Tiếp tục với Google" / "Continue with Google", TUYỆT ĐỐI KHÔNG CLICK. Click vào SSO đối với tài khoản tạo bằng email sẽ kích hoạt cơ chế phòng thủ của OpenAI, chuyển hướng sang `https://auth.openai.com/add-phone` ngay lập tức.
  - Phải luôn chọn thẻ tài khoản trực tiếp hoặc dùng luồng Email + Password / OTP.

- **Bẫy Nuốt Lỗi (Silent Exit 0) Trong Script Verification & Supervisor Gán Nhầm COMPLETED**:
  - *Hiện tượng*: Khi script con (`codex_5sim_auto_verify.py`) chạy hết số lần thử hoặc gặp lỗi văng phiên (`invalid_auth_step`), nếu script chỉ `print(json)` mà không gọi `sys.exit(1)`, tiến trình Python mặc định kết thúc với returncode = 0.
  - *Hậu quả nghiêm trọng*: Supervisor (`batch_gpm_5profiles_supervisor.py`) kiểm tra `run_cmd() == True` sẽ hiểu nhầm là verify thành công, tự động gán timestamp `codex_oauth_at` và chuyển stage sang `WAIT_7D`. Báo cáo 6h và state hiển thị `FAILED: 0` và số nick hoàn thành tăng ảo, trong khi trên thực tế các tài khoản này chưa hề được cấp token trên OmniRoute!
  - *Khắc phục chuẩn hóa*:
    1. Script con bắt buộc kiểm tra `res.status == 'SUCCESS'` và có `connection_id` mới `sys.exit(0)`, mọi trường hợp khác bắt buộc `sys.exit(1)`.
    2. Supervisor khi `ok_codex` thất bại bắt buộc gán `status = "FAILED"`, `stage = "CODEX_OAUTH"`, detail ghi rõ lỗi, tuyệt đối không trả về COMPLETED.
    3. Đồng bộ tham số CLI: Khi cấu hình "1 quốc gia 3 lần, tối đa 3 quốc gia" (trần 9 lần), supervisor bắt buộc truyền `--max-attempts 9` thay vì trần cũ 5 hay 2.
    4. Đối soát định kỳ: Thường xuyên đối soát danh sách tài khoản mang cờ hoàn thành với SQLite OmniRoute (`SELECT email FROM provider_connections WHERE provider = 'codex'`) để lập tức thu hồi và đưa các tài khoản ảo về trạng thái `FAILED` để chạy lại.

- **Bẫy Số Điện Thoại 5sim & Quy Tắc Xoay Tua Đa Tầng (Dynamic Live Pool + 45s Timeout + 1 Nước 3 Lần, Max 3 Nước)**:
  - **Thuật Toán Điểm Cân Bằng (Balanced Score) & Quét Cron 6 Tiếng (Cache TTL = 6h - User Directive 2026-09-30)**:
    - **Không hardcode quốc gia, không blacklist cảm tính**: Script không ưu tiên cứng một nước nào và không tự ý chặn nước vì giả định WhatsApp (việc dính WhatsApp là ngẫu nhiên theo dải số). Cơ chế fail 3 lần tự trượt sang nước kế tiếp sẽ xử lý triệt để các số xịt. Hiện đầu số của một nước bị lỗi hôm nay không có nghĩa ngày mai nó cũng lỗi.
    - **Công thức Điểm Cân Bằng tự nhiên**:
      $$\text{Score} = \frac{\text{Rate24h} \times 0.7 + \text{Rate72h} \times 0.3}{\text{Cost}}$$
      Sắp xếp tự động theo `(-score, -rate24, cost)` để quốc gia nào có tỷ lệ OTP cao nhất trên mỗi đồng tiền bỏ ra sẽ tự động đứng đầu bảng (ví dụ: Việt Nam, Thái Lan, Argentina...).
    - **Quét định kỳ mỗi 6 giờ qua Cronjob `update-5sim-pools-6h` (`0 */6 * * *`, TTL = 6h)**: Tự động chạy ngầm cập nhật lại điểm và thứ hạng số vào `D:\Taadaa\runtime\kibe\cron-state\5sim_best_pools.json`. Mọi worker đọc cache siêu tốc, vừa thích ứng theo sự thay đổi kho số của carrier vừa chống Rate Limit 429.
    - **Cơ Chế Ưu Tiên Quốc Gia Vừa Thắng (Winning Country Priority - User Directive 2026-09-30)**:
      + Khi một profile ver thành công lấy được OTP và connection Codex, script tự động ghi nhận quốc gia đó vào `D:\Taadaa\runtime\kibe\cron-state\5sim_last_winning_country.json`.
      + Ở lượt chạy tiếp theo, script ưu tiên bốc quốc gia vừa thành công đó lên vị trí #1 (vượt lên trước thứ tự tổng điểm) để tiếp tục thừa hưởng đà nhận OTP của dải số đó.
      + Khi quốc gia ưu tiên bị fail (thử hết lượt không có OTP/hết số), script tự động xóa file state và lập tức quay về thứ tự ưu tiên theo tổng điểm cân bằng.
  - **Cơ Chế Bỏ Phạt Cooldown 24h Khi Thất Bại Codex OAuth & Tự Động Giải Phóng Hàng Đợi (User Directive 2026-10-01)**:
    - *Bản chất sự cố cũ*: Trước đây, khi một nick gặp lỗi ở stage `CODEX_OAUTH` (như văng phiên, hết số hoặc lỗi submit), supervisor đánh dấu `status: BLOCKED` và ép ngâm tĩnh `(now - fail_time) >= 24h`, đồng thời ghi `ip_action_history[port][stage] = now()` khóa cổng proxy 24h. Hậu quả là hơn 250 nick đã có ChatGPT sống sẵn bị đóng băng vĩnh viễn không được bốc lại ver số.
    - *Kỷ luật chuẩn hóa (User Directive)*:
      1. **Bỏ phạt 24h trên tài khoản**: Trong `select_candidates()`, toàn bộ tài khoản đã có `chatgpt_registered_at` mà chưa có `codex_oauth_at` được tự động chuyển ngay về `stage = "WAIT_24_48H", status = "PENDING"` để cron bốc xoay vòng liên tục, TUYỆT ĐỐI KHÔNG ép ngâm 24h.
      2. **Không khóa cổng proxy 24h cho CODEX_OAUTH**: Trong `tick()`, khi `result["stage"] == "CODEX_OAUTH"` gặp thất bại, KHÔNG ghi nhận cờ cooldown vào `ip_action_history[port]["CODEX_OAUTH"]` để các profile khác trên cổng proxy đó vẫn được tiếp tục bốc chạy.
      3. **Tự động khôi phục hàng đợi**: Khi phát hiện tài khoản kẹt `BLOCKED` ở `WAIT_24_48H`, script tự động unblock về `PENDING`.
  - **Bản Chất Phân Biệt Tuyệt Đối: Lỗi Ủy Quyền (`invalid_auth_step`) vs Ép WhatsApp (User Correction 2026-10-01)**:
    - *Chỉ lỗi ủy quyền mới cần lấy link mới*: DUY NHẤT khi OpenAI ném thông báo lỗi `invalid_auth_step` (Bước ủy quyền không hợp lệ) thì transaction ủy quyền backend mới bị hủy, và lúc đó runner mới gọi `reset_to_add_phone(page)` qua OmniRoute để lấy URL OAuth mới.
    - *Ép WhatsApp là do bản thân SIM, KHÔNG liên quan đến OAuth*: Ép WhatsApp là do OpenAI chặn SMS trên dải số/carrier đó của SIM. Phiên OAuth và form `add-phone` vẫn còn nguyên vẹn 100%. CẤM lú lẫn coi WhatsApp là lỗi ủy quyền. Khi dính WhatsApp, KHÔNG lấy link mới, chỉ gọi `cancel_number` hoàn tiền 100%, xóa ô nhập bằng `Control+A` + `Backspace` và thử tiếp số SIM khác cùng nước hoặc đổi đầu số.
  - **Cơ Chế Bền Vững Ưu Tiên Quốc Gia Vừa Thắng (Persistent Winning Country Priority - User Directive 2026-10-01)**:
    - Khi một quốc gia (như Philippines) vừa nhận OTP và kích hoạt Codex thành công, runner lưu cờ vào `D:\Taadaa\runtime\kibe\cron-state\5sim_last_winning_country.json`.
    - Ở mọi lượt chạy tiếp theo của supervisor/cron, runner tự động bốc quốc gia vừa thắng lên vị trí #1 để thử đầu tiên, thừa hưởng trọn vẹn đà nhận OTP của dải số đó.
    - CẤM tự ý xóa cờ ưu tiên chỉ vì 1 profile kế tiếp gặp 1-2 số SIM lỗi; cờ thắng được duy trì bền vững để phục vụ toàn đàn.
  - **Bẫy Bỏ Sót Cooldown IP Khi Thao Tác Thất Bại (Failed Action IP Cooldown Bug - User Correction 2026-09-30)**:
    - *Nguyên nhân sự cố lặp lỗi liên tục*: Nếu supervisor chỉ ghi nhận `ip_action_history[port][stage] = now()` khi `status == "COMPLETED"`, thì khi nick gặp lỗi (FAILED/BLOCKED do văng phiên, hết số hoặc lỗi submit), cổng proxy đó hoàn toàn KHÔNG được gắn cờ cooldown 24h và `updated_at` của nick không được reset.
    - *Hậu quả nghiêm trọng*: Mỗi chu kỳ cron 5 phút tiếp theo lại tiếp tục bốc lại chính nick đó lên chính cổng proxy đó, tạo vòng lặp lỗi liên tục làm crash profile GPM ("GPM-Browser didn't shut down correctly") và khiến OpenAI chặn dải IP.
    - *Khắc phục chuẩn hóa*: Trong hàm `tick()`, bất kể kết quả là `COMPLETED` hay `FAILED/ERROR/BLOCKED`, BẮT BUỘC cập nhật `ip_action_history[port][stage] = now()` và `info["updated_at"] = now()`, đưa tài khoản và IP vào ngâm tĩnh đúng 24h trước khi được bốc lại.
  - **Bằng Chứng Về Độ Ngấu Nick Trước Khi Codex OAuth (Không Cần Ngâm Đủ 24h)**:
    - Thực tế đối soát hệ thống chứng minh nick vừa reg ChatGPT xong 3-4 phút vẫn hoàn thành Codex OAuth bình thường (ví dụ: `raknidopack76@hotmail.com` cách nhau 3m57s, `evalynkintzle211148@hotmail.com` cách nhau 2m51s).
    - Việc bị `invalid_auth_step` là do bị OpenAI từ chối số / ép WhatsApp làm vỡ transaction OAuth trên server, KHÔNG PHẢI do thiếu thời gian ngâm nick. Một khi đã bị `invalid_auth_step` trên phiên đó, bắt buộc phải reset phiên sạch từ OmniRoute chứ không thể tiếp tục submit trên form cũ.
  - **Kiến Trúc Concurrency: Tại sao Ver Số Bắt Buộc Tuần Tự (Port 1455 Singleton Mutex)**:
    - OmniRoute (`:20129`) mở callback server PKCE tại cổng cố định `localhost:1455/auth/callback` dạng Singleton (`globalThis.__pkceCallbackStates["codex"]`).
    - Nếu 2 worker cùng lúc gọi `/api/oauth/codex/start-callback-server`, worker sau sẽ ghi đè `codeVerifier` và hủy phiên server của worker trước, gây lỗi `state mismatch` hoặc nuốt nhầm token của nhau.
    - Bắt buộc dùng `CodexOAuth1455Lock` (`codex_oauth_1455.lock`) tuần tự hóa khâu OAuth/Ver số (FIFO).
    - Ngược lại, khâu Hotmail Login và ChatGPT Reg chạy song song 5 worker bình thường vì tương tác độc lập với web và Microsoft Graph API.
  - **Bẫy Click Nhầm "Tiếp Tục" Trên Form Phone Rỗng (Premature Consent Click Pitfall)**:
    - Trên giao diện tiếng Việt của OpenAI (`auth.openai.com/add-phone`), nút bấm submit số điện thoại mang nhãn `"Tiếp tục"`.
    - Nếu script tìm `button:has-text("Tiếp tục")` để tự động bấm qua màn hình Consent mà **KHÔNG kiểm tra điều kiện URL** (`"consent" in page.url.lower() and "add-phone" not in page.url.lower()`), script sẽ bấm submit nhầm ngay khi form số điện thoại đang rỗng!
    - Hậu quả: OpenAI nhận request form rỗng $\rightarrow$ báo lỗi hoặc kích hoạt ngay `invalid_auth_step` hủy phiên OAuth.
    - **Khắc phục**: Tuyệt đối CHỈ click nút Consent khi URL chứa `consent` và KHÔNG chứa `add-phone`.
  - **Bẫy Thoát Toàn Bộ Script Sớm Khi 1 Lần Thử Thất Bại (Violating 1 Nước 3 Lần, Max 3 Nước)**:
    - Khi một số bị OpenAI từ chối hoặc gặp `invalid_auth_step`, trang web chuyển hướng ra khỏi màn hình `add-phone` về màn hình lỗi hoặc login.
    - Nếu trong vòng lặp thử số (`for c_try in range(1, country_tries + 1):`) mà đặt `if not is_phone_verification_page(page): return result`, script sẽ thoát ngay lập tức ở lần thử đầu tiên, bỏ qua hoàn toàn 2 lần thử còn lại của nước đó và bỏ qua toàn bộ các nước xếp sau!
    - **Khắc phục**: Khi `not is_phone_verification_page(page)`, phải thử khôi phục lại form bằng `page.goto(clean_auth_url)`. Nếu không khôi phục được thì dùng `break` để thoát inner loop và chuyển tiếp sang **quốc gia tiếp theo**, TUYỆT ĐỐI KHÔNG gọi `return result` ngắt ngang toàn bộ tiến trình.
  - **Quy Trình Khôi Phục Phiên Re-Auth Khi Bị `invalid_auth_step` (Cơ Chế Re-Auth Qua OmniRoute - User Directive 2026-10-01)**:
    - *Bản chất kỹ thuật đã kiểm chứng thực nghiệm & Phân Biệt Tuyệt Đối với WhatsApp (User Correction 2026-10-01)*:
      + **DUY NHẤT LỖI ỦY QUYỀN (`invalid_auth_step` - Bước ủy quyền không hợp lệ)**: Khi OpenAI báo `invalid_auth_step`, **transaction OAuth phía backend OpenAI đã bị hủy hoàn toàn**. Nếu script chỉ gọi `reset_to_add_phone()` bằng `page.goto("https://auth.openai.com/add-phone")`, browser vẫn tiếp tục bám vào transaction hỏng cũ, dẫn đến 100% các lần gõ số sau của mọi quốc gia đều tiếp tục văng `invalid_auth_step`. DUY NHẤT trong trường hợp này mới cần lấy link OAuth mới từ OmniRoute để làm mới session.
      + **SỐ DÍNH WHATSAPP KHÔNG LIÊN QUAN ĐẾN OAUTH**: Việc bị ép WhatsApp là do **chính từng số SIM cụ thể** (OpenAI chặn SMS trên SIM đó). Phiên OAuth và form `add-phone` vẫn sống nguyên vẹn 100%. CẤM TUYỆT ĐỐI lú lẫn gộp WhatsApp vào lỗi OAuth! Khi dính WhatsApp, KHÔNG lấy link OAuth mới, chỉ hủy số hoàn tiền, xóa ô nhập bằng `Control+A` + `Backspace` và thử tiếp số SIM khác cùng nước hoặc đổi đầu số.
    - *Quy trình khôi phục sạch 4 bước qua OmniRoute khi bị `invalid_auth_step` (Đã nghiệm thu trên GPM Profile & Đóng Đinh Test Case #20)*:
      1. **Bước 1 — Cấp link OAuth mới**: Gọi OmniRoute `GET /api/oauth/codex/start-callback-server` để sinh `authUrl` mới với singleton callback server cổng 1455.
      2. **Bước 2 — Điều hướng prompt=consent**: Điều hướng browser tới `clean_auth_url = auth_url.replace("prompt=login", "prompt=consent")`.
      3. **Bước 3 — Chọn lại thẻ tài khoản**: OpenAI nhận diện session cookie sẵn có trong profile GPM (`unified_session_manifest`, `oai-client-auth-info`), chuyển hướng tới `https://auth.openai.com/choose-an-account` ("Chọn một tài khoản để tiếp tục đến Codex"). Click thẻ tài khoản qua locator `button:has-text('@'), form button, [data-testid*='account']`.
      4. **Bước 4 — Nghiệm thu form add-phone sạch**: OpenAI tự động chuyển tiếp tới `https://auth.openai.com/add-phone`. Toàn bộ lỗi cũ biến mất, radio `(•) Tin nhắn văn bản` (SMS) được khôi phục về trạng thái mặc định, transaction OAuth mới được kích hoạt trơn tru để tiếp tục thử số SIM tiếp theo.
      + *Code chuẩn hóa trong `reset_to_add_phone(page)` (Bảo vệ bởi test case 20 trong `test_codex_closeout_regression.py`)*:
        ```python
        def reset_to_add_phone(page):
            try:
                print("     [*] Đang khôi phục lại trang add-phone qua OAuth URL mới từ OmniRoute...")
                cb = requests.get(f"{OMNIROUTE_BASE}/api/oauth/codex/start-callback-server", timeout=10).json()
                new_auth = (cb.get("authUrl") or "").replace("prompt=login", "prompt=consent")
                if new_auth:
                    page.goto(new_auth, wait_until="domcontentloaded", timeout=25000)
                    page.wait_for_timeout(3000)
                    acct = page.locator('button:has-text("@"), form button, [data-testid*="account"]').first
                    if acct.is_visible(timeout=4000):
                        acct.click(force=True)
                        page.wait_for_timeout(3000)
                if not is_phone_verification_page(page):
                    page.goto("https://auth.openai.com/add-phone", wait_until="domcontentloaded", timeout=15000)
                    page.wait_for_timeout(2000)
                return is_phone_verification_page(page)
            except Exception as e:
                print(f"WARN reset_to_add_phone failed: {e}")
                return False
        ```
    - *Bẫy Reset Cũ Chỉ Dùng `page.goto("https://auth.openai.com/add-phone")` Gây Lỗi Invalid Liên Hoàn (Cascade Invalidation)*:
      + Khi một lần submit bị lỗi ủy quyền `invalid_auth_step`, backend OpenAI đã đóng dấu transaction OAuth đó là hỏng.
      + Nếu script chỉ làm mới bằng `page.goto("https://auth.openai.com/add-phone")`, form trên UI vẫn tiếp tục bám vào transaction cũ đã chết, dẫn đến 100% các số điện thoại tiếp theo của tất cả các quốc gia đều bị OpenAI trả về `Bước ủy quyền không hợp lệ. error_code: invalid_auth_step`.
      + **Bẫy Nguy Hiểm: `is_phone_verification_page(page)` trả về True khi có thông báo `invalid_auth_step` (User Incident 2026-10-01)**:
        * Khi OpenAI hiển thị popup đỏ *"Bước ủy quyền không hợp lệ. error_code: invalid_auth_step"*, URL vẫn giữ nguyên `auth.openai.com/add-phone` và ô `input[type="tel"]` vẫn còn trên màn hình.
        * Nếu code chỉ kiểm tra thô: `if not is_phone_verification_page(page): reset_to_add_phone(page)`, hàm này trả về `True` $\rightarrow$ script rơi vào nhánh `else` chỉ `Control+A` + `Backspace` xóa ô text mà KHÔNG GỌI `reset_to_add_phone(page)`!
        * Hậu quả: Toàn bộ các lần thử tiếp theo (của cùng nước hoặc chuyển sang nước khác) đều bị gõ vào một backend transaction đã chết $\rightarrow$ 100% văng `invalid_auth_step` chỉ trong 2 phút rồi bị gán cờ `BLOCKED: Codex OAuth quet bu that bai`.
        * Kỷ luật chuẩn hóa (User Directive 2026-10-01): BẮT BUỘC kiểm tra cả ở đầu vòng lặp và sau khi phát hiện lỗi từ chối:
          ```python
          # 1. Ở đầu mỗi lần thử (trước khi mua số mới):
          if not is_phone_verification_page(page) or any(
              x in page.locator("body").inner_text(timeout=2000).lower()
              for x in ("invalid_auth_step", "bước ủy quyền không hợp lệ")
          ):
              reset_to_add_phone(page)

          # 2. Sau khi submit bị từ chối / dính WhatsApp / invalid_auth_step:
          is_invalid_auth = any(
              x in body_text.lower()
              for x in ("invalid_auth_step", "bước ủy quyền không hợp lệ")
          )
          if not is_phone_verification_page(page) or is_invalid_auth:
              reset_to_add_phone(page)
              log_telemetry_event("form_reset_performed", {"country": country, "c_try": c_try, "invalid_auth": is_invalid_auth})
          else:
              # Chỉ clear input khi phiên còn sống hoàn toàn (ví dụ dính WhatsApp nhưng chưa văng transaction)
              tel_input.click(force=True)
              page.keyboard.press("Control+A")
              page.keyboard.press("Backspace")
              tel_input.fill("")
          ```
        * **Kỷ luật ngân sách trần 9 lần thử (3 số/quốc gia × tối đa 3 quốc gia - User Directive 2026-10-01)**:
          KỂ CẢ KHI GẶP `invalid_auth_step` hay WhatsApp: Runner chỉ hủy số hoàn tiền 100% và gọi `reset_to_add_phone` lấy link mới từ OmniRoute, sau đó BẮT BUỘC dùng `continue` để thử tiếp số thứ 2, số thứ 3 của cùng quốc gia đó. TUYỆT ĐỐI CẤM dùng `break` bỏ quốc gia sớm khi chưa thử đủ 3 số của nước đó. Toàn bộ phiên duyệt đủ trần 9 lần thử (3 nước × 3 số) trước khi dừng phiên.
      + Bắt buộc phải thông qua `reset_to_add_phone(page)` gọi OmniRoute lấy link mới để tạo transaction mới toanh.
      + *Lưu ý*: Với số dính WhatsApp, transaction hoàn toàn bình thường, không kích hoạt cơ chế này mà chỉ clear input thử số khác.
    - *Bẫy Selector Premature Submit trên trang log-in*: Tuyệt đối CẤM ghép `button[type='submit']` vào cùng locator chọn tài khoản (`button:has-text('{email}')`). Nếu phiên cookie hết hạn rơi về `auth.openai.com/log-in`, việc click `button[type='submit']` khi ô email trống sẽ gây lỗi *"Cần nhập email"*. Phải kiểm tra thẻ email hiện diện trước khi click.
  - **Tiêu chuẩn giá & tỉ lệ (User Directive 2026-09-29)**: Chỉ chọn các số có giá dưới 0.12$ ($\le 0.11\$$), tồn kho $>20$ số và tỉ lệ nhận OTP $>0\%$.
  - **Quy tắc 1 quốc gia 3 lần, tối đa 3 quốc gia (`country_tries = 3`, `max_countries = 3` - User Directive 2026-09-29)**: Nhóm các candidate theo từng quốc gia. Mỗi quốc gia thử tối đa **3 lần liên tiếp** với các số khác nhau. Toàn bộ phiên chỉ xoay tua tối đa **3 quốc gia** (tổng ngân sách tối đa $3 \times 3 = 9$ lần thử). Chỉ khi 5SIM thực sự trả về số thành công mới tính là 1 quốc gia đã thử (không làm mất slot khi nước hết số).
  - **Bẫy OpenAI Rate-Limit Trên Màn Hình Add-Phone (Hard Limit 3 Lần/Session)**: Qua phân tích OCR screenshot hiện trường, trên 1 phiên OAuth, OpenAI chỉ cho phép thử tối đa **3 lần submit số**. Đến **lần thứ 4** là OpenAI lập tức hủy phiên và báo lỗi: `Rất tiếc, đã xảy ra lỗi không xác định! Bước ủy quyền không hợp lệ (invalid_auth_step)` và đá văng về login (`dom_gate_failed`). Nếu bị `invalid_auth_step`, bắt buộc hủy số hoàn tiền ngay và abort fail-fast, không thử tiếp trên session đã hỏng.
  - **Thiết Kế Chuẩn Xử Lý WhatsApp & Pre-Submit Fail-Fast (BẢO TOÀN THIẾT KẾ CỦA SẾP — CẤM TỰ PHÁ)**:
    - *Bản chất cơ chế OpenAI WhatsApp (User Correction 2026-09-30)*:
      - Việc OpenAI yêu cầu gửi mã qua **WhatsApp** (`Chúng tôi sẽ gửi mã dùng một lần đến số của bạn qua WhatsApp để xác minh...` hoặc `switched to WhatsApp`) là **DO CHÍNH TỪNG SỐ SIM CỤ THỂ** (số SIM đã có lịch sử đăng ký hoặc bị OpenAI gắn cờ spam SMS).
      - **TUYỆT ĐỐI KHÔNG PHẢI LỖI CỦA CẢ QUỐC GIA**: Không có chuyện một quốc gia bị cấm SMS vĩnh viễn; cùng 1 nước (như Philippines, Argentina, Nam Phi, Ba Lan...), số SIM này dính WhatsApp nhưng số SIM khác vẫn nhận SMS bình thường.
      - **QUY TẮC CẤM TỰ PHÁ**: CẤM TUYỆT ĐỐI dính WhatsApp là `break` bỏ quốc gia đó! Làm như vậy là phá vỡ hoàn toàn kỷ luật thử 3 số/quốc gia của Sếp.
    - *Quy trình xử lý chuẩn 3 bước*:
      1. **Bước 1 — Chọn SMS nếu có tùy chọn**: Sau khi chọn quốc gia, quét DOM tìm radio/nút chọn SMS (`label:has-text("Tin nhắn")`, `label:has-text("Text message")`, `input[type="radio"][value="sms"]`). Nếu có nút chọn SMS -> click chọn ngay để ép gửi qua SMS.
      2. **Bước 2 — Số bị ép WhatsApp 100% -> HỦY SỐ ĐÓ, THỬ TIẾP SỐ KHÁC CÙNG QUỐC GIA**:
         - Nếu số đó không có tùy chọn SMS hoặc sau submit OpenAI báo *"switched to WhatsApp / chuyển sang WhatsApp / invalid_auth_step"*:
         - Lập tức gọi `cancel_number(order_id)` để 5SIM hoàn tiền 100% vào ví.
         - Gọi `reset_to_add_phone(page)` để khôi phục form `add-phone` sạch.
         - **TIẾP TỤC THỬ SỐ TIẾP THEO CỦA CÙNG QUỐC GIA ĐÓ** (`continue` trong vòng lặp `c_try` để thử lần 2, lần 3).
         - **CHỈ CHUYỂN NƯỚC KHI VÀ CHỈ KHI**: Đã thử hết đủ cả 3 số khác nhau của quốc gia hiện tại mà đều fail.
      3. **Bước 3 — Khôi phục form `reset_to_add_phone(page)`**: Sau khi hủy số hoặc nếu trang bị văng khỏi `add-phone`, điều hướng lại `https://auth.openai.com/add-phone` chờ DOM nạp lại ô `input[type="tel"]` để tiếp tục thử số tiếp theo mà không làm crash hay ngắt script sớm.

  - **Kỷ Luật Ngân Sách Thử Số: 1 Nước 3 Lần, Tối Đa 3 Nước (CẤM DỪNG SỚM SAU 1 LẦN THỬ)**:
    - *Bẫy Dừng Quá Sớm Sau 1 Lần Thử (Premature Single-Attempt Abortion)*:
      - Khi số đầu tiên của một nước bị từ chối hoặc trang văng khỏi `add-phone` do lỗi submit/WhatsApp, nếu script xử lý bằng `if not is_phone_verification_page(page): return result`, script sẽ **thoát ngay lập tức ở lần thử đầu tiên**!
      - Hậu quả: Vi phạm nghiêm trọng chỉ đạo của User: *"Là sao mới thử số lần đầu fail đã dừng script? Cái đm bữa gặp WhatsApp tao đã thiết kế cách fix rồi sao mày cứ tự phá vậy!"*. Toàn bộ các lần thử còn lại và các quốc gia xếp sau bị bỏ qua hoàn toàn.
    - *Quy tắc bất biến*:
      1. Mỗi quốc gia thử tối đa 3 lần (`country_tries = 3`), toàn phiên duyệt tối đa 3 quốc gia (`max_countries = 3`, trần 9 lần thử).
      2. Chỉ tính tăng biến đếm quốc gia đã thử khi 5SIM thực sự trả về số thành công (`order_id` hợp lệ). Nước nào hết số (`no free phones`) tự động chuyển nước mà không làm mất slot.
      3. Nếu 1 số bị từ chối: Hủy số hoàn tiền 100% $\rightarrow$ nếu form còn thì xóa input thử số tiếp $\rightarrow$ nếu form văng thì gọi `reset_to_add_phone(page)`.
      4. CHỈ ĐƯỢC PHÉP DỪNG SCRIPT VÀ ĐƯA VÀO NGÂM 24H KHI:
         - Đã duyệt hết đủ cả **3 quốc gia** mà không lấy được OTP.
         - Hoặc dính Cloudflare Turnstile / Captcha cứng / IP proxy bị OpenAI chặn triệt để.
         - CẤM TUYỆT ĐỐI dừng toàn bộ runner chỉ vì 1 số điện thoại đơn lẻ bị OpenAI từ chối.
  - **Bẫy WAF OpenAI Trả Về HTML Thay Vì JSON (`Unexpected token '<' is not valid JSON`) & Cloudflare Turnstile**:
    - Khi submit số điện thoại qua proxy hoặc phiên bị gắn cờ nghi vấn/rate-limit, OpenAI WAF trả về response HTML `403` thay vì JSON payload. Client JavaScript trên giao diện OpenAI parse lỗi và crash: `Rất tiếc, đã xảy ra lỗi không xác định! Unexpected token '<', '<!DOCTYPE '... is not valid JSON`.
    - Ngay sau đó, trang web bị chuyển hướng sang màn hình Cloudflare Turnstile (`auth.openai.com`: "Thực hiện xác minh bảo mật - Trang web này sử dụng dịch vụ bảo mật để chống bot độc hại").
    - Gate `is_phone_verification_page(page)` sẽ phát hiện URL/DOM không còn ở `add-phone`, chụp screenshot `codex_dom_gate_failed_*.png` và kích hoạt fail-fast `phone_verification_dom_gate_failed`, ngăn chặn việc tiếp tục mua số lãng phí.
  - **Thời gian chờ SMS chuẩn 45 giây & Auto-Refund 100% (User Directive)**: Khi hết thời gian chờ 45s không thấy SMS, script gọi ngay API `/v1/user/cancel/{order_id}` của 5sim để được hoàn 100% tiền ngay lập tức vào ví. Lịch sử thực tế 5sim cho thấy nếu có SMS thì code luôn về trong 5s - 22s; chờ quá 45s là carrier nghẽn, cần hủy ngay để xoay số khác.
  - **Bẫy React Aria Dropdown Ảo Hóa (Virtualized DOM) & Tên Quốc Gia OpenAI**:
    - Trên màn hình `auth.openai.com/add-phone`, dropdown chọn quốc gia mặc định luôn là `United States (+1)`.
    - Dropdown dùng công nghệ ảo hóa React Aria (chỉ render ~14 items trong viewport tại 1 thời điểm). Nếu dùng DOM query `[role="option"][data-key="..."]` sẽ trả về rỗng vì các nước như Argentina, UK, Philippines, Ba Lan, Hy Lạp... hoàn toàn chưa có trong DOM nếu chưa cuộn tới.
    - Script cũ tìm không thấy element rồi bấm phím `Escape` làm đóng popover $\rightarrow$ **quốc gia bị giữ nguyên là United States (+1)**. Khi điền số ngoại vào form US, OpenAI báo lỗi đỏ *"Phone number is not valid"* và gửi SMS vào số US ảo, khiến 5sim không bao giờ nhận được OTP.
    - Tên quốc gia trên OpenAI khác với 5sim: 5sim gọi `england`, OpenAI gọi `United Kingdom (+44)`; 5sim gọi `usa`, OpenAI gọi `United States (+1)`.
    - **Quy trình chuẩn hóa 100% (Đã kiểm chứng thành công)**:
      1. Khai báo `OPENAI_COUNTRY_MAP` mapping chuẩn theo ISO: `GB` $\rightarrow$ `United Kingdom`, `US` $\rightarrow$ `United States`, `VN` $\rightarrow$ `Vietnam`, `AR` $\rightarrow$ `Argentina`, `PL` $\rightarrow$ `Poland`, `PH` $\rightarrow$ `Philippines`, `GR` $\rightarrow$ `Greece`, `TH` $\rightarrow$ `Thailand`...
      2. Mở dropdown (`dropdown_btn.click(force=True)`) $\rightarrow$ Gõ tên tiếng Anh chuẩn bằng typeahead: `page.keyboard.type(target_country, delay=40)` $\rightarrow$ `page.keyboard.press("Enter")`.
      3. **FAIL-FAST VALIDATION BẮT BUỘC**: Đọc lại text trên nút dropdown `sel_val = dropdown_btn.inner_text()`. BẮT BUỘC kiểm tra `f"+{pfx}" in sel_val`. Nếu vẫn là `United States (+1)` hoặc không khớp `+{pfx}` $\rightarrow$ Dừng ngay, hủy số hoàn tiền, tuyệt đối KHÔNG SUBMIT khi quốc gia bị lệch.
      4. Xóa sạch ô nhập số điện thoại bằng `page.keyboard.press("Control+A")` + `page.keyboard.press("Backspace")` trước khi `fill(local_num, force=True)`.
  - **Bẫy URL Consent Bỏ Qua Xác Minh Số (Direct OAuth Consent)**: Đối với các tài khoản đã có session hoặc tài khoản đã đủ độ ngấu (aged), sau khi bấm chọn thẻ tài khoản ở màn hình OAuth, OpenAI có thể chuyển hướng thẳng sang `https://auth.openai.com/sign-in-with-chatgpt/codex/consent` (chỉ có nút "Tiếp tục" / "Continue") và trả code về `localhost:1455` mà HOÀN TOÀN KHÔNG BẮT NHẬP SỐ ĐIỆN THOẠI. Script phải luôn kiểm tra xem URL hiện tại có phải consent/callback hay không trước khi cố tình điều hướng sang `add-phone` làm gián đoạn luồng ủy quyền.
  - **Bẫy Drift Model trên Cronjob Script-Only (`omni-activate-soaked-codex`)**:
    - Khi tạo cronjob chỉ để chạy script Python định kỳ (như script quét SQLite để kích hoạt lại tài khoản sau 48h ngâm), BẮT BUỘC phải đặt `no_agent=True` và truyền `script='...'`.
    - Nếu để `no_agent=False` (mặc định), Hermes sẽ cố gắng khởi tạo LLM agent cho cron. Khi mô hình toàn cục (global inference model) bị đổi hoặc drift (ví dụ từ Gemini sang Claude/Omni), Hermes sẽ chặn chạy cron với thông báo `Skipped to prevent unintended spend: global inference config drifted...` làm cronjob bị dừng hoạt động ngoài ý muốn.

- **Cơ Chế Hòm Thư Khôi Phục `@fviainboxes.com` (Temp Mail Công Khai)**:
  - Khi Microsoft đòi gửi OTP về hòm thư khôi phục domain `@fviainboxes.com`: Đây không phải hòm thư bị mất quyền truy cập. Domain `fviainboxes.com` là dịch vụ Temp Mail mở tại `https://fviainboxes.com/`.
  - Quy trình lấy OTP: Mở `https://fviainboxes.com/` $\rightarrow$ nhập prefix của email khôi phục (ví dụ `murtaghshandy1563pf`) vào ô textbox $\rightarrow$ bấm nút "Get Email" $\rightarrow$ Web hiển thị ngay hộp thư Inbox trực tiếp và tự động cập nhật email mã xác nhận từ Microsoft để mở khóa tài khoản.

- **Bẫy dấu cách tên file `taikhoan_dat_v2_updated .xlsx`**:
  - Tên file authoritative trên OneDrive có dấu cách trước phần mở rộng: `taikhoan_dat_v2_updated .xlsx`.
  - Nếu hardcode `taikhoan_dat_v2_updated.xlsx` (không có dấu cách), hàm `exists()` trả về `False`, khiến resolver không đọc được `PASS CHATGPT` và script tự động bỏ qua toàn bộ candidate Hotmail. Luôn khai báo danh sách candidates:
    ```python
    UPDATED_XLSX_CANDIDATES = [
        Path(r"D:\OneDrive\TaadaaData\kibe\taikhoan_dat_v2_updated .xlsx"),
        Path(r"D:\OneDrive\TaadaaData\kibe\taikhoan_dat_v2_updated.xlsx"),
    ]
    UPDATED_XLSX = next((p for p in UPDATED_XLSX_CANDIDATES if p.exists()), UPDATED_XLSX_CANDIDATES[0])
    ```
- **Bẫy Index cột trong sheet `Tài Khoản`**:
  - Header: `('Máy', 'Folder Video', 'ID', 'PASS', '2FA', 'GMAIL', 'PASS MAIL', 'NGÀY THÁNG NĂM SINH', 'NGÀY TẠO', 'device ID', None, 'PASS CHATGPT')`
  - Cột Email là index 5 (`GMAIL`), không phải index 1 (`Folder Video`).
  - Cột `PASS CHATGPT` là index 11.
- **Bẫy `Token expired` trên OmniRoute Quota Dashboard**:
  - Khi một tài khoản hiển thị thanh quota đầy (ví dụ `100% left` như dinhlan) nhưng có viền tối, switch tắt và chữ đỏ `Token expired`, tài khoản đó không phục vụ traffic được do refresh token upstream đã hết hạn/bị thu hồi, không phải do OmniRoute lỗi giao diện.
- **Bẫy `scan_pro_accounts.py` bỏ sót tài khoản Active**:
  - Mặc định `scan_pro_accounts.py` chỉ quét các tài khoản đang tắt (`isActive=False`). Phải truyền `--all` để quét đủ cả 16 tài khoản Pro (`g1-pro-tier`), tránh kết luận nhầm tổng số tài khoản là 15 (thiếu `dangmy30011996@gmail.com`).

- **Bẫy Đánh Giá "0 sự kiện trong 6h vừa qua" trong Báo Cáo 6h (`cron_hotmail_gpm_lifecycle_6h_report.py`)**:
  - Khi nhận báo cáo 6h với `⚡ Tiến độ xử lý trong 6h vừa qua: 0 sự kiện`, KHÔNG vội kết luận hệ thống bị treo hoặc cron hỏng.
  - *Nguyên nhân chuẩn*: Sau các đợt reg ChatGPT tập trung, hàng chục profile đồng loạt bước vào trạng thái ngâm an toàn `WAIT_24_48H` (đủ >= 24h mới chuyển tiếp Codex) và các cổng proxy giữ cooldown `24h/action`. Khi toàn bộ queue rơi vào cửa sổ ngâm, supervisor sẽ chủ động bỏ qua và ticker cron ghi nhận stdout rỗng (silent đúng chuẩn `no_agent`).
  - *Quy trình chẩn đoán O(1) an toàn (CẤM chạy `--live` trong foreground session)*:
    1. Kiểm tra nhanh candidate bằng `--dry-run` (không chạm browser hay lock):
       `python "D:\Taadaa\GPM auto\scripts\batch_gpm_5profiles_supervisor.py" --dry-run`
    2. Kiểm tra tiến trình ngâm trong state file:
       `D:\Taadaa\runtime\kibe\cron-state\batch_gpm_5profiles_supervisor_state.json` (soi trường `chatgpt_registered_at` và `WAIT_24_48H`).
    3. Kiểm tra GPM API liveness: `curl -s "http://127.0.0.1:19995/api/v3/profiles?page=1&limit=5"`.
    4. TUYỆT ĐỐI KHÔNG gọi `python batch_gpm_5profiles_supervisor.py --live` hoặc wrapper trực tiếp trong foreground session vì mỗi batch Playwright có thể kéo dài tới 30-40 phút, sẽ gây timeout terminal và tranh chấp `WindowsBatchGuard` với cron.

- **Bẫy Lệch Mật Khẩu Workbook vs File Mua Gốc Gây Rate-Limit Hotmail**:
  - Khi nick Hotmail bị `status: FAILED` ở `HOTMAIL_LOGIN`, dùng ngay `windows-native-ocr` trên ảnh post-login (`D:\Taadaa\Hotmail\outputs\screenshots\post_login_<machine>_<email>.png`) để xác định đúng nguyên nhân thực tế.
  - Ba dạng màn hình lỗi phổ biến:
    1. *Verify Email*: Microsoft yêu cầu nhập lại mã từ email khôi phục (cần gán recovery token / OTP Graph API).
    2. *Mật khẩu không chính xác*: Thường do mật khẩu trong `taikhoan_dat_v2_updated .xlsx` bị gõ sai hoặc bị backfill nhầm (ví dụ: gõ nhầm pass mặc định `Aa123456@` thay vì pass mua gốc trong `hotmail_all_60_bought.txt`).
    3. *Bạn đã cố gắng đăng nhập quá nhiều lần*: Hệ quả trực tiếp của việc supervisor retry tự động bằng mật khẩu sai khiến Microsoft tạm khóa form đăng nhập trong vài giờ.
  - Khi gặp lỗi sai mật khẩu hoặc rate-limit, lập tức đối chiếu email đó trong các file nguồn `D:\Taadaa\Hotmail\hotmail_input.txt` hoặc `hotmail_all_60_bought.txt` để cập nhật lại đúng cột `PASS MAIL` trong workbook trước khi mở lại cho supervisor chạy.

- **Bẫy Vòng Lặp Retry Mù Quáng (Infinite Blind-Retry) & Invariant Zero-Blind-Retry**:
  - *Sự cố nghiêm trọng*: Nếu hàm `select_candidates()` chỉ kiểm tra `if stage == "DONE" or info.get("status") == "WAITING": continue` mà quên loại trừ `FAILED`/`ERROR`/`BLOCKED`, supervisor mỗi chu kỳ cron (ví dụ 5 phút) sẽ tiếp tục chọn lại chính các tài khoản vừa đăng nhập thất bại.
  - *Hậu quả*: Mở browser lên và gõ lại mật khẩu sai liên tục hàng chục lần khiến Microsoft kích hoạt cơ chế bảo vệ nghiêm ngặt: tạm khóa đăng nhập ("Bạn đã cố gắng đăng nhập quá nhiều lần..."), bắt xác minh email khôi phục hoặc khóa tài khoản vĩnh viễn, gây thiệt hại tài sản tài khoản.
  - *Quy tắc Invariant bắt buộc*:
    1. **Candidate Exclusion Filter**: `select_candidates()` BẮT BUỘC bỏ qua triệt để:
       `if stage == "DONE" or info.get("status") in {"WAITING", "FAILED", "ERROR", "BLOCKED", "QUARANTINE"}: continue`
    2. **Chuyển thẳng sang BLOCKED**: Khi `execute()` trả về lỗi hoặc `HOTMAIL_LOGIN` thất bại, supervisor phải lập tức gán `info["status"] = "BLOCKED"` và ghi nhận chi tiết lỗi vào `last_result`. Tuyệt đối CẤM giữ `PENDING`/`FAILED` để cron tự động chạy lại mù quáng.
    3. **Báo Cáo 6h bắt buộc hiển thị khối Lỗi**: Script báo cáo định kỳ (`cron_hotmail_gpm_lifecycle_6h_report.py`) BẮT BUỘC phải trích xuất các tài khoản có `status in ["FAILED", "ERROR", "BLOCKED"]` thành khối riêng `🔴 DANH SÁCH TÀI KHOẢN GẶP LỖI CẦN XỬ LÝ` kèm máy, email và lý do cụ thể (OCR phát hiện), tuyệt đối không giấu lỗi trong thống kê tổng.

- **Xử Lý Thách Thức Mail Khôi Phục (Recovery Email Verification Challenge & Quy Tắc Khoale)**:
  - Xem chi tiết quy trình đối soát S7 và nguồn hàng BoxTaiKhoan tại `references/boxtaikhoan-hotmail-fviainboxes-and-s7-audit.md`.
  - Khi đăng nhập Hotmail bị Microsoft chặn ở màn hình "Verify your email / We'll send a code to [email]":
  - Dùng `windows-native-ocr` (hoặc WinRT OCR) đọc chuỗi email khôi phục bị ẩn (ví dụ `mu*****@fviainboxes.com` hay `kh*****@gmail.com`).
  - **Quy tắc bất biến (User Instruction & Farm Policy)**:
    1. **Mail khôi phục là `khoa...` (`khoale...`, `khoalee...`, `khoalemagic...`, `khoaleemagic...`)**: BẮT BUỘC BÁO LẠI VÀ BỎ QUA (SKIP / QUARANTINE). Tuyệt đối không can thiệp, không thử OTP, giữ cờ `BLOCKED` và báo cáo rõ cho User.
    2. **Mail khôi phục khác (ví dụ phôi mua bên bán `@fviainboxes.com`, tempmail)**: Báo cáo rõ domain khôi phục thực tế, đối soát với file phôi mua gốc hoặc giữ cờ `BLOCKED` chờ xử lý, tuân thủ Invariant Zero-Blind-Retry.
    3. **Quy trình đối soát session trên máy S7 (S7 Phone Audit Procedure)**:
       - Khi gặp Hotmail dính mail khôi phục bên bán, kiểm tra đối soát trên máy S7 vật lý tương ứng:
         + Android Account Manager: `adb -s <serial> shell dumpsys account | grep -E "Account \{name="` (kiểm tra tài khoản Gmail IMAP / Google).
         + App Outlook: Mở Outlook app, vào *Thiết đặt* -> *Tài khoản thư* chụp ảnh màn hình nghiệm thu danh sách tài khoản đã đăng nhập thực tế.
       - Nếu cả Android Accounts và Outlook đều không có tài khoản: Xác nhận tài khoản chưa từng đăng nhập trên máy S7 (không có session/token nội bộ), an toàn giữ cờ `BLOCKED` trên GPM supervisor để bỏ qua.

- **Bẫy Hardcode Loop Gán Stage Theo Máy Gây Phình Ảo Queue `WAIT_24_48H` & Mâu Thuẫn Số Liệu Báo Cáo 6h**:
  - *Sự cố*: Khi code supervisor chứa vòng lặp bảo lưu tài khoản kiểm tra theo điều kiện thô `if info.get("machine") in (2, 4, 8, 9, 10): info["stage"] = "WAIT_24_48H"`, nó sẽ quét trúng và gán nhầm TOÀN BỘ các tài khoản khác trên các máy đó vào `WAIT_24_48H` dù các nick này CHƯA HỀ đăng ký ChatGPT (thiếu `chatgpt_registered_at`).
  - *Hậu quả nghiêm trọng*:
    1. Báo cáo 6h bị mâu thuẫn số liệu: `Đã Reg thành công ChatGPT: 63` nhưng tổng `WAIT_24_48H: 43` + `WAIT_7D: 42` = 85 ($63 < 85$, số liệu đá nhau trực tiếp làm user phát hiện `?`).
    2. Các tài khoản chưa reg ChatGPT bị kẹt ảo trong trạng thái chờ Codex, khi tới lượt chạy Codex OAuth sẽ crash vì tài khoản ChatGPT chưa từng tồn tại.
  - *Khắc phục chuẩn hóa*:
    1. CẤM TUYỆT ĐỐI gán stage theo danh sách `machine`.
    2. Trong `load_state()`, bắt buộc kiểm tra điều kiện chuẩn:
       ```python
       for info in profiles.values():
           if info.get("stage") == "WAIT_24_48H" and not info.get("chatgpt_registered_at"):
               has_tok = info.get("email", "").strip().lower() in token_set
               info["stage"] = "CHATGPT_REG" if has_tok else "HOTMAIL_LOGIN"
               info["status"] = "PENDING"
       ```
       Đưa các nick bị gán nhầm trở về đúng vị trí (`CHATGPT_REG` nếu có token, hoặc `HOTMAIL_LOGIN` nếu không có token).

- **Quy Trình Xử Lý Hotmail Báo Sai Mật Khẩu: Phân Biệt `account.live.com/acsr` vs Khôi Phục Qua Mail Bảo Mật & Độc Lập TikTok Farm**:
  - Khi nick Hotmail bị Microsoft báo *"Mật khẩu đó không đúng"* (`#passwordError`) và user yêu cầu thử dùng mail khôi phục:
  - Bắt buộc dùng GPM Playwright probe click vào link `"Bạn quên mật khẩu?"` (`#idA_PWD_ForgotPassword` / `a:has-text("quên mật khẩu")`) để kiểm tra phản hồi thực tế của Microsoft:
    1. **Tài khoản CÓ mail khôi phục bảo mật**: Microsoft hiển thị *"Xác minh danh tính của bạn"* -> *"Gửi email đến [masked email]"*. Điền email khôi phục -> Microsoft gửi mã OTP 7 số để reset mật khẩu.
    2. **Tài khoản KHÔNG CÓ mail khôi phục bảo mật** (như `llamedroabv@hotmail.com` - M06, `LanaWiseley987754@hotmail.com` - M11): Microsoft chuyển hướng thẳng sang `https://account.live.com/acsr` (*Khôi phục tài khoản của bạn: Chúng tôi nên liên hệ bạn ở đâu? Nhập vào địa chỉ email liên lạc khác... Nhập các ký tự bạn nhìn thấy / Captcha*).
       - *Kỷ luật*: Trường hợp này KHÔNG THỂ khôi phục tự động qua script. Bắt buộc chụp ảnh màn hình lưu bằng chứng `recovery_<machine>_probe.png`, set trạng thái `BLOCKED: Cho user khoi phuc tay` trong state file để cách ly hoàn toàn, tuyệt đối không thử lại tự động.
    3. **Đối Soát Độc Lập TikTok Farm**: Khi Hotmail bị sai mật khẩu, ngay lập tức kiểm tra `taikhoan_dat_v2_updated .xlsx` và `taikhoan_run_safe.xlsx`:
       - Nếu tài khoản TikTok tương ứng đã có Password TikTok riêng biệt và đã kích hoạt **2FA Authenticator (TOTP)** trong hệ thống (như M06 `@llameojyavc`, M11 `@lanawakt0mv`), phiên TikTok trên máy điện thoại vật lý **hoàn toàn độc lập và an toàn 100%**. Việc đăng video và nuôi feed trên farm không bị ảnh hưởng bởi sự cố mật khẩu Hotmail.

- **Chẩn Đoán Tiến Độ 0 Sự Kiện (Supervisor PAUSED vs Cooldown/Soak Window)**:
  - Khi báo cáo 6h ghi nhận `⚡ Tiến độ xử lý trong 6h vừa qua: 0 sự kiện`:
  - Trước khi kết luận là hàng đợi đang ngâm cooldown 24h, BẮT BUỘC phải chạy `cronjob action='list'` để kiểm tra trường `state` của job `gpm-5profiles-lifecycle-supervisor` (`341f42ae292c`).
  - Nếu `state: paused`: Xác định supervisor đã bị tạm dừng khẩn cấp ở phiên trước mà chưa được resume lại. Cần kiểm tra dứt điểm nguyên nhân, nghiệm thu sạch sẽ trước khi gọi `cronjob action='resume'` để kích hoạt lại hệ thống.

- **Bẫy "Mật Khẩu Web Sai Nhưng OAuth Token Vẫn Sống 100%" (Quy Tắc: Token Còn Sống = Bên Bán Không Đổi Pass, Do Agent Ghi Sai Pass Vào Workbook)**:
  - *Quy luật bất biến trong kiến trúc Microsoft Account*: Khi người dùng hoặc bên bán thực hiện đổi mật khẩu tài khoản Microsoft, Microsoft **LẬP TỨC THU HỒI VÀ HỦY TOÀN BỘ OAuth2 Refresh Tokens** đã cấp trước đó (`AADSTS70000: The provided value for the input parameter 'refresh_token' or 'assertion' is not valid`).
  - *Hệ quả đối soát trực tiếp (User Correction)*: **NẾU REFRESH TOKEN VẪN SỐNG (đổi được Access Token, đọc được Graph API inbox Status 200), ĐIỀU ĐÓ ĐỒNG NGHĨA 100% BÊN BÁN KHÔNG HỀ ĐỔI PASS HAY THU HỒI TÀI KHOẢN!** Nguyên nhân duy nhất khiến web báo "Mật khẩu không chính xác" là do các session trước của Agent đã gán nhầm/hallucinate chuỗi pass vào cột Excel (ví dụ: Agent gán nhầm pass Row 8 `l_450f37` cho M06 thay vì pass mua gốc `97508Xv4327!`; Agent ghi nhầm `8Z30k72808` cho M11 thay vì pass mua gốc `pakdz33583`).
  - *Hiện tượng*: Một số tài khoản Hotmail cũ (như batch tháng 8) bị Microsoft báo sai mật khẩu web khi đăng nhập qua Playwright GPM. Nếu chỉ tra cứu trong file input hiện tại (`hotmail_input.txt`) hoặc state JSON, supervisor tưởng là loại thường (không có token) và đánh dấu FAILED.
  - *Quy trình xử lý chuẩn*:
    1. Khi phát hiện tài khoản báo sai pass web, tra cứu ngược lịch sử nạp (các bản backup Excel, session logs quá khứ) để tìm refresh token gốc và pass mua gốc từ đơn hàng.
    2. Chạy test O(1) kiểm tra token trực tiếp:
       ```python
       from chatgpt_gpm_direct_reg import MicrosoftGraphOTPProvider
       provider = MicrosoftGraphOTPProvider(refresh_token, client_id)
       access_token = provider.get_access_token()
       # Gọi GET https://graph.microsoft.com/v1.0/me/messages để xác minh đọc được thư thật
       ```
    3. Nếu token còn sống:
       - Xác nhận ngay mật khẩu mua gốc trong lịch sử là mật khẩu thật.
       - Nạp bù đầy đủ (email|pass_mua_gốc|token|client_id) vào `D:\Taadaa\Hotmail\hotmail_input.txt` và cập nhật lại đúng cột `PASS MAIL` / `PASS CHATGPT` trong `taikhoan_dat_v2_updated .xlsx`.
    4. Chuyển thẳng tài khoản sang `CHATGPT_REG`: Bỏ qua 100% việc đăng nhập web hay khôi phục pass, bốc OTP OpenAI trực tiếp qua Graph API để tiếp tục vòng đời bình thường.

- **Bẫy Mất Hàm Per-Profile Mutex Lock trong `src/gpm_client.py` (`ImportError: cannot import name 'is_profile_locked'`)**:
  - `batch_gpm_5profiles_supervisor.py` bắt buộc import `from src.gpm_client import is_profile_locked`.
  - Nếu `gpm_client.py` bị checkout/revert làm mất các định nghĩa lock tập trung, cronjob wrapper `gpm_5profiles_supervisor_wrapper.py` sẽ crash ngay lập tức ở đầu tiến trình với exit code 1 (`last_status: error`).
  - File `D:\Taadaa\GPM auto\src\gpm_client.py` BẮT BUỘC phải duy trì đầy đủ 3 hàm lock và thư mục lock:
    + `LOCK_DIR = Path(r"D:\Taadaa\runtime\kibe\cron-state\profile_locks")`
    + `acquire_profile_lock(profile_id: str, owner: str = "") -> bool`
    + `release_profile_lock(profile_id: str) -> None`
    + `is_profile_locked(profile_id: str) -> bool`
  - Trước khi kết thúc session sửa code GPM, bắt buộc kiểm tra `python -m py_compile "D:/Taadaa/GPM auto/src/gpm_client.py"` và `python "D:/Taadaa/GPM auto/scripts/batch_gpm_5profiles_supervisor.py" --dry-run` để đảm bảo exit code 0.

- **Quy Trình Chuẩn Hóa Mật Khẩu Toàn Đàn & Bẫy Trượt Dòng (Off-By-One) trong Excel**:
  - *Hiện tượng*: Khi nhiều tài khoản Hotmail báo lỗi sai pass rải rác trên farm (khiến `FAILED > 0`), nguyên nhân thường không phải do từng nick riêng lẻ mà do các đợt backfill Excel trước đó của Agent bị trượt dòng (off-by-one, ví dụ dòng 526 lấy pass dòng 525, 527 lấy pass 526, 528 lấy pass 527 trên M66), hoặc bị gán nhầm chuỗi placeholder (`Aa123456@`, `l_450f37`) hay bỏ trống `None`.
  - *Quy trình đối soát tự động toàn đàn (Farm-Wide Reconciliation)*:
    1. Tập hợp kho credentials gốc từ tất cả các file mua nguồn: `latest_bought_70.txt`, `hotmail_all_60_bought.txt`, `latest_bought_8_m76_79.txt`, và `gmail_clean_v2.xlsx`.
    2. Viết script Python quét sheet `Tài Khoản` trong `taikhoan_dat_v2_updated .xlsx`: đối chiếu `PASS MAIL` (Cột G / index 6) với kho credentials gốc theo email.
    3. Xác minh tính hợp lệ của OAuth Token: Với mỗi tài khoản có pass lệch hoặc trống, chạy kiểm tra `MicrosoftGraphOTPProvider` để xác nhận token còn sống và đọc được thư mục inbox (Status 200).
    4. Cập nhật đồng bộ 3 điểm dữ liệu:
       - Cập nhật cả `PASS MAIL` (Cột G) và `PASS CHATGPT` (Cột L) trong `taikhoan_dat_v2_updated .xlsx`.
       - Nạp chuỗi `email|password|refresh_token|client_id` vào `D:\Taadaa\Hotmail\hotmail_input.txt` (giúp supervisor nhận diện `has_token = True`).
       - Dọn sạch lỗi trong `batch_gpm_5profiles_supervisor_state.json`: xóa `error`, `last_result`, đưa stage về `CHATGPT_REG` và status về `PENDING`.
    5. Kiểm tra lại bằng `cron_hotmail_gpm_lifecycle_6h_report.py`: Đảm bảo con số `Tài khoản gặp lỗi (FAILED): 0/409` sạch bóng trước khi chốt.

- **Bẫy "FAILED = 0 nhưng còn Lỗi Dữ Liệu Tiềm Ẩn (Latent Errors)" khi Audit Khảo Sát Tài Khoản**:
  - *Hiện tượng & Sai lầm phổ biến*: Khi user hỏi "Còn acc nào lỗi không?", Agent thường chỉ chạy báo cáo hoặc kiểm tra `status in ("FAILED", "ERROR", "BLOCKED")` trong state JSON rồi vội vàng kết luận "hệ thống sạch 100%".
  - *Hậu quả*: Các tài khoản đang ở trạng thái `status: PENDING` ở stage `HOTMAIL_LOGIN` hoặc `CHATGPT_REG` nhưng lại bị **trống `PASS MAIL` hoặc trống `PASS CHATGPT`** trong file Master Excel `taikhoan_dat_v2_updated .xlsx` là các lỗi tiềm ẩn nguy hiểm. Khi supervisor bốc chúng vào chạy trong các tick tiếp theo, các nick này chắc chắn sẽ đăng nhập thất bại bằng mật khẩu rỗng, bị Microsoft tạm khóa hoặc crash supervisor.
  - *Quy trình kiểm tra 2 lớp bắt buộc trước khi kết luận "Hết lỗi"*:
    1. **Lớp 1 (Runtime State)**: Quét `batch_gpm_5profiles_supervisor_state.json` tìm tài khoản có `status in ("FAILED", "ERROR", "BLOCKED")`.
    2. **Lớp 2 (Data Integrity / Master Excel)**: Viết script Python quét cả 409 dòng trong `taikhoan_dat_v2_updated .xlsx` (cột G `PASS MAIL` và cột L `PASS CHATGPT`). Nếu có bất kỳ ô nào `None`, chuỗi rỗng `""` hoặc placeholder rác (`l_450f37`, `Aa123456@`), bắt buộc truy lục lại lịch sử đơn hàng / các file backup (`gmail_clean_v2.xlsx`, `latest_bought_*.txt`, `hotmail_all_*.txt`) để bù pass gốc trước khi xác nhận với User.

- **Bẫy Phân Biệt "Lỗi Tồn Đọng Lịch Sử (Quarantined/Blocked)" vs "Lỗi Mới Trong 6 Giờ" trong Báo Cáo 6h & Vị Trí Token 5SIM**:
  - *Hiện tượng*: Khi nhận báo cáo 6h với `🔴 DANH SÁCH 105 TÀI KHOẢN GẶP LỖI CẦN XỬ LÝ`, Coordinator dễ nhầm tưởng có sự cố hàng loạt vừa diễn ra trong phiên vừa qua và vội vã can thiệp hoặc hoang mang.
  - *Bản chất*: Script `cron_hotmail_gpm_lifecycle_6h_report.py` gom toàn bộ tài khoản có trạng thái `status in ["FAILED", "ERROR", "BLOCKED"]` trong state file từ trước đến nay (được Zero-Blind-Retry cách ly bảo vệ, ví dụ các nick văng phiên/hết số ngày 27/09). Để đánh giá hiệu năng và lỗi thực tế của 6 giờ vừa qua, BẮT BUỘC phải nhìn vào mục `⚡ Tiến độ xử lý trong 6h vừa qua`.
  - *Vị trí Token 5SIM*: Token 5SIM nằm ở file chuẩn `C:\Users\Kibe\.5sim_token` (không đọc qua `.env`). Khi kiểm tra số dư và rating của 5SIM, đọc trực tiếp token từ file này rồi gọi `https://5sim.net/v1/user/profile`.
  - *Kiểm tra tiến trình Supervisor*: Tránh dùng `psutil.process_iter(['cmdline'])` quét toàn bộ Windows vì dễ bị timeout > 30s. Dùng `tasklist | grep python` hoặc kiểm tra file lock `D:\Taadaa\runtime\kibe\cron-state\codex_oauth_1455.lock` / mtime state file để xác minh tính sống còn.

- **Bẫy Tài Khoản Đông Cứng Vĩnh Viễn Trong `BLOCKED` & Cơ Chế Auto Cooldown-Unblock 24h (User Directive 2026-09-30)**:
  - *Nguyên nhân cốt lõi*: Supervisor áp dụng Candidate Exclusion Filter nghiêm ngặt:
    `if stage == "DONE" or status in {"WAITING", "FAILED", "ERROR", "BLOCKED", "QUARANTINE"}: continue`
    Do đó, khi các tài khoản bị đánh dấu `BLOCKED` ở các phiên cũ (do lỗi mạng, hết số, hoặc OpenAI từ chối số), các nick này sẽ bị **đóng băng vĩnh viễn** trong state file mà KHÔNG BAO GIỜ được supervisor bốc lại, dù script con (`codex_5sim_auto_verify.py`) đã được vá lỗi hoàn thiện!
  - *Phân định bản chất Pool (Tránh nhầm lẫn Google vs ChatGPT)*: Báo cáo 6h liệt kê danh sách lỗi (ví dụ 105 đến 273 nick BLOCKED) là **100% thuộc pool Hotmail/ChatGPT** (không có acc Google/Gmail nào). Trong đó, đa số (239+ nick) **ĐÃ CÓ CHATGPT SỐNG SẴN**, chỉ bị kẹt duy nhất ở khâu mua số 5SIM lấy Token Codex OAuth.
  - *Cơ chế Tự Động Cooldown-Unblock Chuẩn Hóa trong `batch_gpm_5profiles_supervisor.py`*:
    1. **Auto-Unblock sau >= 24h ngâm trong `select_candidates()`**:
       ```python
       # Auto-unblock accounts with registered ChatGPT after >=24h soak for Codex OAuth retry
       if info.get("chatgpt_registered_at") and not info.get("codex_oauth_at") and stage != "WAIT_7D":
           fail_time = parse_time((info.get("last_result") or {}).get("at") or info.get("updated_at") or info.get("chatgpt_registered_at"))
           if fail_time and now_dt and (now_dt - fail_time).total_seconds() >= 24 * 3600:
               stage = info["stage"] = "WAIT_24_48H"
               status = info["status"] = "PENDING"
       ```
    2. **Khâu thực thi an toàn trong `execute()` cho `WAIT_24_48H`**:
       Bắt buộc bọc `pid = ensure_profile(info)` trước khi chạy `codex_5sim_auto_verify.py` để phòng ngừa `profile_id` bị trống.
       Chạy qua Mutex Lock cổng 1455 (`CodexOAuth1455Lock`) để tuần tự hóa an toàn.
       - *Thành công*: Gán `codex_oauth_at`, nạp token vào OmniRoute và chuyển sang `WAIT_7D`.
       - *Thất bại*: Hủy số hoàn tiền 5SIM ngay lập tức, trả về `status = "FAILED"`, `next_stage = "WAIT_24_48H"`.
    3. **Cập nhật mốc thời gian trong `tick()`**:
       Luôn gán `info["updated_at"] = now()` trong mọi kết quả (kể cả FAILED) để timer 24h cooldown được tính lại chuẩn xác từ thời điểm vừa thử.
    4. **Tuân thủ kỷ luật IP**: Luôn lọc qua `ip_action_history[port][stage] < 24h` để đảm bảo tối đa 1 nick / 1 proxy port / 1 ngày.

- **Bẫy Số Điện Thoại Dính WhatsApp & Cơ Chế Xoay Tua Tự Nhiên (User Directive 2026-09-30)**:
  - *Hiện tượng*: Đôi khi OpenAI yêu cầu gửi OTP qua WhatsApp thay vì SMS trên một số dải số (Ba Lan, Argentina...). 5SIM chỉ hỗ trợ SMS nên không nhận được mã.
  - *Kỷ luật xử lý*: Không chụp mũ hay blacklist cứng quốc gia đó. Cứ để thuật toán Điểm Cân Bằng xếp hạng tự nhiên. Nếu số đó không có OTP trong 45s hoặc OpenAI từ chối, script tự động hủy hoàn tiền 100% và thử tiếp; nếu fail đủ 3 lần trên quốc gia đó thì tự động trượt xuống quốc gia có Điểm Cân Bằng cao kế tiếp trong danh sách.

- **Bẫy Bỏ Sót Ghi Nhận Cooldown IP & Fail-Timer Khi Thất Bại (Infinite 5m Re-run Loop - User Correction 2026-09-30)**:
  - *Sự cố nghiêm trọng*: Trong `batch_gpm_5profiles_supervisor.py`, nếu khối xử lý kết quả chỉ gán `ip_action_history[port][stage] = now()` khi `status == "COMPLETED"`, thì khi tài khoản bị `FAILED` (do lỗi submit, văng phiên, hoặc OpenAI từ chối), `ip_action_history` hoàn toàn KHÔNG được cập nhật cho cổng proxy đó, và `info["updated_at"]` cũng không được gán mốc giờ mới.
  - *Hậu quả nguy hiểm*: Cứ mỗi chu kỳ cron (5 phút), hàm `select_candidates()` kiểm tra điều kiện auto-unblock: `(now_dt - fail_time) >= 24h`. Do `fail_time` vẫn giữ timestamp cũ từ quá khứ (ví dụ 2-3 ngày trước), tài khoản lập tức bị mở khóa ảo (`PENDING`), đồng thời cổng proxy đó không có cờ cooldown trong `ip_action_history`. Supervisor sẽ bốc lại chính tài khoản vừa thất bại lên chính cổng proxy đó chạy lại liên tục sau mỗi 5 phút! Điều này gây cháy IP, làm crash profile Chrome ("GPM-Browser didn't shut down correctly") và khiến OpenAI gắn cờ spam farm.
  - *Khắc phục chuẩn hóa invariant*:
    1. Trong vòng lặp ghi nhận kết quả của `tick()`: Bất kể kết quả là `COMPLETED` hay `FAILED`/`ERROR`/`BLOCKED`, BẮT BUỘC phải gán:
       ```python
       action_time = now()
       info["updated_at"] = action_time
       result["at"] = action_time
       info["last_result"] = result
       port = str(info.get("proxy_port") or "")
       if port:
           data.setdefault("ip_action_history", {}).setdefault(port, {})[result["stage"]] = action_time
       ```
    2. Đảm bảo cổng proxy đó bị khóa cứng 24h (`24 * 3600`) cho stage đó, và tài khoản đó bị ngâm tĩnh đúng 24h tính từ thời điểm vừa thất bại trước khi được xem xét chạy lại.

- **Bẫy Đổ Lỗi "Chưa Ngâm Đủ 24h" vs Bản Chất Hỏng Transaction OAuth Do WhatsApp (User Correction 2026-09-30)**:
  - *Sai lầm phán đoán*: Khi nick vừa reg ChatGPT xong vài phút nhảy vào ver Codex bị `invalid_auth_step`, dễ vội vàng kết luận "do nick chưa ngâm đủ 24h nên OpenAI chặn".
  - *Đối soát dữ liệu thực tế*: Lịch sử thực tế trong SQLite OmniRoute chứng minh nhiều tài khoản (như `raknidopack76`, `evalynkintzle`) vừa reg ChatGPT xong 3-4 phút là ver Codex OAuth thành công ăn ngay lập tức không cần ngâm 24h.
  - *Bản chất kỹ thuật thật sự*: Lỗi `invalid_auth_step` xảy ra là do OpenAI ném lỗi từ chối khi submit số (ví dụ số bị ép WhatsApp nhưng SIM ảo không nhận được), và một khi trên tab đó đã bị ném `invalid_auth_step` 1 lần thì **transaction ủy quyền OAuth trên máy chủ OpenAI đã bị hủy**. Mọi lần thử gõ số tiếp theo trên cùng form/URL đó đều sẽ bị `invalid_auth_step` đè lên tiếp. Không được đổ lỗi cảm tính cho việc ngâm nick khi chưa đối soát session OAuth.

- **Kỷ Luật Bất Biến Về WhatsApp & Ngân Sách Thử Số: 1 Nước 3 Lần, Tối Đa 3 Nước (CẤM TỰ CHẾ, CẤM DÙNG BREAK BỎ QUỐC GIA - User Directive 2026-09-30)**:
  - *Bản Chất Cốt Lõi Về WhatsApp (User Invariant)*:
    - **DÍNH WHATSAPP HOÀN TOÀN TƯƠNG ĐƯƠNG SỐ LỖI / KHÔNG VỀ OTP / TIMEOUT**:
      + OpenAI ép WhatsApp là do **CHÍNH TỪNG SỐ SIM CỤ THỂ** (số bị gắn cờ tái sử dụng/chặn SMS ở backend OpenAI), **TUYỆT ĐỐI KHÔNG PHẢI LỖI DO CẢ QUỐC GIA BỊ CẤM SMS**.
      + Cùng 1 nước (Argentina, Philippines, Nam Phi, Ba Lan...), số SIM 1 có thể dính WhatsApp nhưng số SIM 2, 3 vẫn nhận SMS bình thường.
      + **CẤM TUYỆT ĐỐI TỰ CHẾ LOGIC**: CẤM dùng `break` để bỏ quốc gia khi gặp thông báo WhatsApp hoặc lỗi submit! CẤM dừng sớm khi mới thử 1 số!
  - *Quy trình xử lý chuẩn 4 bước trong vòng lặp*:
    1. **Bước 1 — Chọn SMS Radio**: Sau khi chọn quốc gia, quét tìm tùy chọn SMS (`label:has-text("Tin nhắn")`, `label:has-text("Text message")`, `input[type="radio"][value="sms"]`). Nếu có -> click chọn ngay để ép gửi qua SMS.
    2. **Bước 2 — Submit & Bắt Lỗi (Dính WhatsApp / Từ Chối / Timeout = Fail Số Đó)**:
       - Nếu sau khi submit, OpenAI báo lỗi từ chối, `invalid_auth_step`, hoặc chuyển sang đòi WhatsApp (*"switched to WhatsApp"*, *"gửi mã qua WhatsApp"*), hoặc hết 45s không có OTP:
       - **Lập tức gọi `cancel_number(order_id)`** để 5SIM hoàn tiền 100% vào ví.
    3. **Bước 3 — Khôi phục form sạch (`reset_to_add_phone`) & Tiếp Tục Thử Số Cùng Nước**:
       - Nếu trang bị văng khỏi form `add-phone`, gọi `reset_to_add_phone(page)` (điều hướng lại `https://auth.openai.com/add-phone`).
       - Dọn sạch ô nhập `input[type="tel"]`.
       - **TIẾP TỤC THỬ SỐ THỨ 2, SỐ THỨ 3 CỦA CHÍNH QUỐC GIA ĐÓ** (`continue` trong vòng lặp `c_try = 1..3`, TUYỆT ĐỐI KHÔNG `break`).
    4. **Bước 4 — Chuyển nước & Kết thúc chu kỳ**:
       - **CHỈ ĐƯỢC CHUYỂN QUỐC GIA KHI**: Đã thử hết đủ **cả 3 số khác nhau** của quốc gia đó (`c_try` chạy hết 3 lượt) mà đều thất bại, HOẶC 5SIM báo hết sạch số (`no free phones`).
       - **CHỈ ĐƯỢC PHÉP DỪNG SCRIPT ĐỂ NGÂM COOLDOWN 24H KHI**: Đã duyệt hết đủ **cả 3 quốc gia** (trần 9 lần thử) mà không lấy được OTP, hoặc khi dính Cloudflare Turnstile bot detection không thể vào web.
       - CẤM dừng toàn bộ runner chỉ vì 1 số điện thoại đơn lẻ bị lỗi.
    - *Kỷ Luật Đóng Đinh Invariant Vào Repo Test Suite (Chống Tự Chế Bậy - User Directive 2026-09-30)*:
      - Khi một ca xử lý phức tạp (như WhatsApp, văng phiên, rate limit) đã được kiểm chứng thành công bằng thực nghiệm, BẮT BUỘC phải ghi nhận ngay thành **Test Case hồi quy cứng trong `tests/test_codex_closeout_regression.py`** và bổ sung vào `PROJECT_RULES.md`.
      - Tuyệt đối CẤM Agent ở các phiên sau tự ý "tự chế" lại luồng xử lý hoặc thêm các lệnh ngắt sớm (`break`, `return`) phá vỡ thiết kế gốc đã được nghiệm thu của Sếp. Mọi thay đổi logic bắt buộc phải pass 100% các test case kiểm tra invariant này trước khi được phép chạy.

- **Hiện Tượng DOM Pre-Submit Báo WhatsApp & Phản Hồi `invalid_auth_step` Khi Submit**:
  - *Hiện tượng hiện trường (Kiểm chứng OCR 2026-09-30)*:
    + Ngay khi script điền số điện thoại vào form `auth.openai.com/add-phone`, client DOM của OpenAI có thể lập tức đổi câu phụ đề từ *"Chúng tôi sẽ gửi mã dùng một lần để xác minh số này"* (SMS) thành *"Chúng tôi sẽ gửi mã dùng một lần đến số của bạn qua WhatsApp để xác minh"*.
    + Khi bấm Submit số đó, OpenAI backend không gửi được qua WhatsApp (do số ảo VoIP 5SIM không kích hoạt WhatsApp) và trả về lỗi: `Rất tiếc, đã xảy ra lỗi không xác định! Bước ủy quyền không hợp lệ. error_code: invalid_auth_step`.
  - *Kỷ luật trình bày bằng chứng cho User (Visual Evidence Protocol - User Directive 2026-09-30)*:
    + **Bẫy lệch màn hình**: User nhìn vào màn hình lỗi sau submit (`invalid_auth_step`) sẽ KHÔNG thấy chữ "WhatsApp" ở đâu và sẽ hỏi *"Lỗi chỗ WhatsApp đâu? Gửi kiểm tra"*.
    + **Kỷ luật hình ảnh bắt buộc**: Khi giải thích lỗi WhatsApp, Agent BẮT BUỘC:
      1. Lấy ảnh checkpoint **Pre-submit** (`attemptN_before_submit.png`), dùng PIL/ImageDraw vẽ khung đỏ (red box) nổi bật quanh câu *"qua WhatsApp để xác minh"*.
      2. Cắt cúp phóng to 2x (zoomed crop) khu vực form đó và gửi qua `MEDIA:` cùng với ảnh full để User xem rõ ngay trên Telegram điện thoại mà không cần phóng to.
         *Helper tự động hóa 1 lệnh*:
         `python "C:/Users/Kibe/AppData/Local/hermes/skills/productivity/windows-native-ocr/scripts/winrt_ocr.py" <path_anh_before> --highlight "WhatsApp" --zoom-crop "WhatsApp"`
         -> Tự động tạo 2 file `<path_anh>_annotated.png` (khoanh đỏ) và `<path_anh>_zoomed.png` (crop phóng to 2x) để gửi ngay qua `MEDIA:`.
      3. Giải thích trực quan 2 nhịp: Nhịp 1 (Pre-submit) OpenAI đã ép WhatsApp -> Nhịp 2 (Post-submit) số ảo 5SIM không có app WhatsApp nên OpenAI trả về lỗi `invalid_auth_step`.
  - *Bẫy Kho Ảo 5SIM (Ghost Inventory trên Virtual34)*:
    + Endpoint `/v1/guest/prices` của 5SIM có thể báo tồn kho lớn (`count > 200,000` cho `virtual34` ở Việt Nam, Thái Lan, Hy Lạp), nhưng khi gọi `/v1/user/buy/activation/...` API lại trả về HTTP 200 `no free phones`.
    + Script runner tự động nhận diện `no free phones` và chuyển tiếp sang các carrier/quốc gia tiếp theo trong danh sách đã xếp hạng theo Điểm Cân Bằng mà không tính vào số lần thử của quốc gia đó.
  - *Kỷ luật xử lý chuẩn*:
    + Script phát hiện chữ `qua whatsapp` hoặc `invalid_auth_step` sau submit: lập tức gọi `cancel_number(order_id)` để 5SIM hoàn tiền 100% về ví (bảo toàn số dư $4.12 và rating uy tín).
    + Gọi `reset_to_add_phone(page)` khôi phục lại trang `add-phone` sạch để tiếp tục thử số thứ 2, thứ 3 của cùng quốc gia đó (`continue` trong vòng lặp `c_try`).
    + Chỉ khi thử hết 3 số của 3 quốc gia (9 lần) mà đều bị từ chối, script mới kết thúc và supervisor ghi nhận `next_stage: WAIT_24_48H` để cơ chế Auto-Unblock tiếp tục mở khóa sau 24h ngâm.

- **Kỷ Luật Đọc Số Liệu Báo Cáo 6h: Con Số FAILED Là Metric Tích Lũy Của Toàn Queue**:
  - Khi báo cáo 6h hiển thị `Tài khoản gặp lỗi (FAILED): 286/415` (hoặc con số lớn tương tự), cần hiểu đây là con số tích lũy của toàn bộ các tài khoản từng gặp lỗi ở các phiên trước (được Zero-Blind-Retry giữ lại để bảo vệ tài khoản).
  - **Quy tắc phân rã 2 nhóm bắt buộc khi User hỏi "Ý là N acc lỗi là sao"**:
    * Không trả lời chung chung hoặc phỏng đoán. BẮT BUỘC chạy script O(1) đọc trực tiếp `batch_gpm_5profiles_supervisor_state.json` để phân rã 2 nhóm:
      1. **Nhóm A — ĐÃ CÓ CHATGPT SỐNG 100% (chiếm ~85-90% danh sách lỗi)**:
         - Đã có `chatgpt_registered_at`, tài khoản sống nguyên vẹn, profile GPM đã có cookie.
         - Chỉ bị gắn cờ `FAILED` do khâu mua SIM 5SIM lấy OTP Codex OAuth (hết số, timeout 45s, OpenAI ép WhatsApp, hoặc văng phiên). 5SIM đã hoàn tiền 100%.
         - Tự động được supervisor unblock thành `PENDING` ở mỗi tick cron để xoay vòng mua SIM tiếp theo các dải số tối ưu.
      2. **Nhóm B — Kẹt Login Hotmail Lịch Sử (chiếm ~10-15%)**:
         - Chưa reg được ChatGPT, kẹt ở `HOTMAIL_LOGIN` từ các đợt cũ do sai mật khẩu hoặc vướng mail khôi phục.
         - Được Zero-Blind-Retry cách ly an toàn (`BLOCKED`) để tránh Microsoft khóa form đăng nhập.
    * **Script O(1) phân rã tức thì**:
      ```python
      import json
      from pathlib import Path
      data = json.loads(Path(r"D:\Taadaa\runtime\kibe\cron-state\batch_gpm_5profiles_supervisor_state.json").read_text(encoding="utf-8"))
      profiles = data.get("profiles", {})
      failed = [v for v in profiles.values() if v.get("status") in ("FAILED", "ERROR", "BLOCKED") or (v.get("last_result") or {}).get("status") in ("FAILED", "ERROR", "BLOCKED")]
      has_gpt = sum(1 for v in failed if v.get("chatgpt_registered_at"))
      print(f"FAILED={len(failed)} | Has ChatGPT Live: {has_gpt}/{len(failed)} ({has_gpt/len(failed)*100:.1f}%) | No GPT: {len(failed)-has_gpt}")
      ```
  - Tuyệt đối không hoang mang nhầm lẫn con số FAILED tích lũy này với lỗi mới phát sinh trong phiên hay tài khoản bị die. Luôn khẳng định rõ tài sản thực tế (số lượng nick có ChatGPT sống).

- **Bẫy Nguy Hiểm: Fallback Sang Mật Khẩu TikTok Khi Trống PASS MAIL & Quy Trình Truy Vết Mật Khẩu Gốc Chuẩn Hóa (User Correction 2026-10-01)**:
  - *Sự cố phân tích*: Trong `batch_gpm_5profiles_supervisor.py` khi bốc tài khoản từ `taikhoan_dat_v2_updated .xlsx`:
    `"--password", info.get("mail_password") or info.get("password") or ""`
    Khi cột `PASS MAIL` (cột G) trong Excel bị trống, biểu thức `info.get("mail_password")` trả về rỗng, code tự động fallback sang `info.get("password")` vốn là **mật khẩu TikTok** (cột D / PASS).
  - *Hậu quả nghiêm trọng*: Supervisor dùng mật khẩu TikTok để gõ vào trang web Hotmail (`login.live.com`). Microsoft lập tức từ chối và supervisor đánh dấu tài khoản là `BLOCKED`, gây kẹt hàng loạt tài khoản.
  - *Bẫy giả định sai lầm (Hallucination Pitfall)*: Tuyệt đối CẤM Agent tự giả định toàn bộ một lô mua từ `boxtaikhoan.com` dùng chung một mật khẩu duy nhất. Mỗi tài khoản Hotmail từ đơn hàng boxtaikhoan đều có mật khẩu riêng biệt ngẫu nhiên.
  - *Phân Biệt Cơ Chế Lấy OTP Android App (ADB/UI Dump) vs Webmail Browser (GPM Playwright) & Nguyên Nhân Gốc Tài Khoản Trống PASS MAIL Vẫn Có TikTok (User Investigation 2026-10-01)*:
    1. **Tại sao tài khoản trống PASS MAIL vẫn có nick TikTok sống?**:
       - Trên điện thoại Android (Samsung S7 farm), TikTok Reg sử dụng cơ chế đọc mã OTP trực tiếp từ UI ứng dụng Gmail (`com.google.android.gm.legacyimap`) hoặc Outlook qua Android UI dump / ADB.
       - Khi tài khoản Hotmail đã được đăng nhập sẵn từ trước dưới dạng IMAP trên máy vật lý, script reg TikTok tự mở app lấy OTP thành công mà KHÔNG HỀ CẦN biết hay nhập mật khẩu web của Hotmail. Khi reg xong, script lưu vào `taikhoan_dat_v2_updated .xlsx` với `PASS` là pass TikTok, còn cột G `PASS MAIL` tiếp tục bị trống (`None`).
    2. **Tại sao GPM Supervisor trên PC bị kẹt?**:
       - GPM Supervisor trên PC chạy đăng ký ChatGPT / Codex bắt buộc phải đăng nhập trình duyệt web `login.live.com` qua proxy để lấy OTP hoặc chạy stage. Nó KHÔNG THỂ lấy OTP qua app điện thoại.
       - Khi cột `PASS MAIL` bị trống, GPM Supervisor đã lấy nhầm mật khẩu TikTok (`info.get("password")`) để thử đăng nhập web Microsoft, dẫn đến thất bại liên tục và nick bị chuyển sang `BLOCKED`.
    3. **Dấu Hiệu Nhận Biết Tài Khoản Cổ Mất Pass Web (Vụ Việc `yobifqtxkbhpzmxf@hotmail.com`)**:
       - Email dạng chuỗi 16 chữ cái ngẫu nhiên (`yobifqtxkbhpzmxf`, `kpfjvflzotmsalbg`...) tạo từ đầu năm 2026 (01/03/2026). Mỗi tài khoản trong lô này đều có một mật khẩu 10 chữ số/chữ cái ngẫu nhiên riêng biệt, tuyệt đối không dùng chung pass.
       - Đã bị ghi nhận trong các file kiểm toán lịch sử (như `live_on_machine_no_info_only_20260626.xlsx` & `mail_thieu_info_20260626.xlsx`: *"live on machine, not in source, and no PASS MAIL found in tracking"*).
  - *Quy trình truy vết mật khẩu gốc chuẩn xác khi Excel bị mất cột PASS MAIL*:
    1. **Kiểm tra Android Account Manager trên máy vật lý**: Chạy `adb -s <serial> shell dumpsys account` để xem mail có đang nằm trong `com.google.android.gm.legacyimap` hoặc Outlook hay không. Nếu có, phiên TikTok trên điện thoại hoàn toàn độc lập và an toàn 100%.
    2. **Truy vấn FTS SQLite Hermes (`state.db`)**: Tìm kiếm theo transaction ID đơn hàng (ví dụ `821P6a8977522f650`, `buyProduct`), hoặc các lần dump `hotmail_input.txt` trong lịch sử tool calls để lấy lại chuỗi `mail|pass|token|client_id` gốc lúc mua.
    3. **Truy vết qua các bản backup Excel lịch sử**: Soát ngược các file sao lưu trong `C:\Users\Kibe\AppData\Local\Taadaa\Tiktok_Reg\workbook-backups\` (`taikhoan_dat_v2_updated _before_batch_deferred_*`) và `D:\OneDrive\TaadaaData\kibe\workbook-backups\` (`gmail_clean_v2_before_*`).
    4. **Kỷ luật Invariant bắt buộc**: TUYỆT ĐỐI CẤM fallback sang `info.get("password")` khi chạy `HOTMAIL_LOGIN`. Nếu tài khoản thiếu `mail_password`, phải gán `status: BLOCKED` kèm lý do `MISSING_MAIL_PASSWORD` để cách ly an toàn, cấm tự ý lấy pass TikTok điền vào form đăng nhập Microsoft.
    5. **Xử lý tài khoản mất pass web hoàn toàn**: Nếu tài khoản tồn từ lâu không còn mật khẩu trong bất kỳ bản backup nào, giữ trạng thái `status: BLOCKED` trên GPM state để bảo vệ IP, và chủ động thay thế bằng một Hotmail mới toanh có đầy đủ credentials/OAuth token từ `hotmail_input.txt` để pipeline GPM tiếp tục chạy.

- **Bẫy Desynchronization Giữa Excel và Supervisor State JSON khi Sửa Mật Khẩu (load_state Excludes Credential Keys - User Incident 2026-10-01)**:
  - *Nguyên nhân kỹ thuật*: Trong `batch_gpm_5profiles_supervisor.py`, hàm `load_state()` có cơ chế bảo toàn state đang chạy:
    `profiles[key].update({k: v for k, v in account.items() if k not in {"password", "mail_password", "chatgpt_password"}})`
    Dòng code này **CHỦ ĐỘNG BỎ QUA KHÔNG ĐÈ** các trường credential (`mail_password`, `password`, `chatgpt_password`) từ Excel nếu tài khoản đã tồn tại trong `profiles` của `batch_gpm_5profiles_supervisor_state.json`.
  - *Hậu quả desync*: Khi Coordinator chỉ cập nhật `PASS MAIL` vào file Excel `taikhoan_dat_v2_updated .xlsx` mà không cập nhật trực tiếp `batch_gpm_5profiles_supervisor_state.json`, supervisor ở các chu kỳ cron tiếp theo vẫn giữ `mail_password: ""` (rỗng) trong RAM/JSON. Khi chạy `HOTMAIL_LOGIN`, script tiếp tục lấy pass rỗng/sai, thất bại và re-block tài khoản, khiến nỗ lực sửa Excel trở nên vô hiệu!
  - *Quy trình đồng bộ 3 bước bắt buộc khi sửa/chuẩn hóa mật khẩu Hotmail*:
    1. **Bước 1 (Master Excel)**: Cập nhật cột G `PASS MAIL` và cột L `PASS CHATGPT` trong `taikhoan_dat_v2_updated .xlsx` (nhớ tạo backup trước khi sửa).
    2. **Bước 2 (Supervisor State JSON)**: Mở trực tiếp `D:\Taadaa\runtime\kibe\cron-state\batch_gpm_5profiles_supervisor_state.json`, tìm key `M<machine>:<email>`, gán `mail_password` và `chatgpt_password` bằng mật khẩu chuẩn mới, đồng thời reset `status = "PENDING"`, pop bỏ `error` và `last_result`.
    3. **Bước 3 (Dual Verification Gate)**: Viết script test đối soát đồng thời cả 2 nguồn: kiểm tra ô Excel và kiểm tra dict trong JSON state. Bắt buộc 100% khớp mật khẩu mới và status là `PENDING` trước khi chốt phiên.
    4. **Xử lý tài khoản không tìm thấy mật khẩu gốc**: Nếu tài khoản tồn từ lâu không còn mật khẩu trong bất kỳ bản backup nào (ví dụ `yobifqtxkbhpzmxf@hotmail.com`), BẮT BUỘC giữ nguyên trạng thái `status: BLOCKED` (quarantine) trên cả Excel và JSON state để bảo vệ IP và tránh vòng lặp thử sai gây khóa form Microsoft.

- **Bẫy Giọng Nói Telegram Bị Dịch Sai Ngữ Cảnh & Kỷ Luật Neo Giữ Miền Vận Hành (Voice STT Transcription Drift Pitfall - User Incident 2026-10-01)**:
  - *Sự cố phân tích*: Khi User gửi tin nhắn voice qua Telegram, công cụ STT (Speech-to-Text) có thể phiên âm ra các câu chữ ngắt quãng, từ lóng hoặc từ đồng âm dễ gây hiểu nhầm sang lĩnh vực nấu ăn / đời sống (ví dụ: *"Mái à, trước chạy có vị như vậy không? Hàng bố ăn này bị"*, *"nước"*, *"ngâm"*, *"giòn"*).
  - *Hậu quả ảo giác nghiêm trọng (Hallucination Catastrophe)*: Model bị mất neo ngữ cảnh, tưởng User đang hỏi công thức nấu ăn, ngâm măng/dưa chua và trả lời lạc đề hoàn toàn, gây ức chế tột độ và làm đứt gãy luồng điều phối công việc của Farm.
  - *Kỷ luật bất biến neo giữ miền vận hành (Domain Anchoring Invariant)*:
    1. Khi đang trong phiên vận hành Farm, GPM, TikTok, Hotmail hay Codex: TUYỆT ĐỐI CẤM suy diễn câu chữ của User sang chuyện ẩm thực, đời sống hay gia đình.
    2. BẮT BUỘC dịch nghĩa các từ khóa theo đúng từ điển vận hành của Farm:
       + *"ngâm"* = ngâm tài khoản (trạng thái `WAIT_24_48H` hoặc `WAIT_7D`).
       + *"nước"* = quốc gia / country SIM phone pool trên 5SIM (Việt Nam, Thái Lan, Indonesia, Argentina...).
       + *"giòn"* / *"ăn"* = chạy mượt, nhận OTP thành công, nạp được token Codex vào OmniRoute.
       + *"vị"* = triệu chứng lỗi, hành vi bất thường của nền tảng (ví dụ: lỗi văng phiên, ép WhatsApp).
       + *"hàng bố ăn"* = lô tài khoản vừa mua / batch nick mới đang chạy.
    3. Nếu câu voice của User quá mập mờ hoặc câu từ rời rạc, chỉ được phép hỏi lại trong khuôn khổ công việc kỹ thuật đang chạy, CẤM TUYỆT ĐỐI trả lời sang chuyện nấu nướng.

- **Kỷ Luật Báo Cáo Không Gây Hiểu Nhầm Về WhatsApp & Form Clear Triệt Để (User Incident 2026-10-01)**:
  - *Sự cố giao tiếp gây ức chế*: Khi giải thích kết quả gặp WhatsApp, Agent dùng câu chữ mập mờ: *"hệ thống hủy ngang phiên ủy quyền OAuth"*. User nghe tưởng runner bị agent tự ý ngắt sớm bỏ cuộc giữa chừng và nổi giận *"Dính WhatsApp tao bắt thử số khác rồi mà? Sao lại tự hủy ngang?"*.
  - *Thực tế vận hành*: Runner vẫn chạy đúng 100% kỷ luật: hủy số đó hoàn tiền trên 5SIM, giữ nguyên form `add-phone` và mua tiếp số khác cùng nước (như Indonesia thử đủ 3 số, Philippines số thứ 3 nhảy thẳng vào màn hình nhập OTP SMS).
  - *Kỷ luật ngôn ngữ báo cáo bắt buộc*:
    1. TUYỆT ĐỐI CẤM dùng các cụm từ gây hiểu nhầm như *"hủy ngang phiên"*, *"bỏ cuộc"*, *"văng hủy phiên"*.
    2. Phải tường thuật rõ ràng 3 vế theo thời gian thực: *(1) Số X dính WhatsApp -> (2) Đã hủy số hoàn tiền trên 5SIM, giữ nguyên form trình duyệt -> (3) Đang tiếp tục mua số Y của cùng nước đó để thử*.
    3. Kỷ luật DOM Form: Khi số trước bị WhatsApp/từ chối, trước khi gõ số tiếp theo BẮT BUỘC clear triệt để tránh sót số cũ trong React Aria: `tel_input.click(force=True)` -> `Control+A` -> `Backspace` -> `tel_input.fill("")` rồi mới `fill(local_num, force=True)`.

- **Bẫy URL Standalone "auth.openai.com/log-in" Gây Lỗi Kẹt "invalid_state" & Bẫy Selector Chooser Trống (User Incident 2026-10-02)**:
  - *Hiện tượng*: Khi session ChatGPT trên profile GPM hết hạn, hàm `handle_auto_relogin` điều hướng tới `https://auth.openai.com/log-in`. Trình duyệt ngay lập tức bị chặn ở trang lỗi: *"Phiên đã kết thúc. Phiên đăng nhập của bạn không còn hợp lệ. Vui lòng bắt đầu lại để tiếp tục. error_code: invalid_state"*.
  - *Bản chất kỹ thuật*:
    1. Endpoint `auth.openai.com/log-in` yêu cầu transaction context PKCE (`client_id`, `state`, `code_challenge`, `redirect_uri`). Nếu truy cập trực tiếp độc lập không có query params, Auth0 backend coi state là rỗng/invalid và khóa form, hoàn toàn không xuất hiện ô nhập email/pass để script tự động đăng nhập lại.
    2. *Bẫy Selector Chooser rỗng*: Locator `acct_btn = page.locator(f"button:has-text('{email}'), form:has-text('{email}') button, button[type='submit']").first`. Chuỗi `, button[type='submit']` là OR selector không ràng buộc email, khiến script click nhầm nút "Tiếp tục" khi ô email còn trống -> form báo đỏ *"Cần nhập"* (Required) và làm sai lệch toàn bộ trạng thái.
    3. *Bẫy Check URL False Positive*: URL `auth.openai.com/oauth/authorize` chứa form login nhưng KHÔNG chứa chuỗi `log-in` hay `login`. Nếu chỉ kiểm tra `"log-in" not in cur_url and "login" not in cur_url` để gán `authenticated = True`, script sẽ nhận định nhầm là đã đăng nhập thành công trong khi form login vẫn đang nằm trơ trọi trên màn hình. BẮT BUỘC kiểm tra sự hiện diện của `input[type="email"], input#email-input`.
  - *Khắc phục chuẩn hóa*:
    1. Điểm vào khôi phục session: nếu `input[type="email"]` đã hiện diện sẵn ngay trên màn hình OAuth authorize, điền email và submit trực tiếp trong luồng để OpenAI redirect thẳng về callback/`add-phone`, không điều hướng đi đâu khác.
    2. Nếu cần tải lại trang đăng nhập, dùng `https://chatgpt.com/auth/login` (có session context) hoặc nạp lại canonical `authUrl` từ OmniRoute.
    3. Loại bỏ hoàn toàn `button[type='submit']` khỏi locator chọn tài khoản. Cấm click submit khi ô email chưa có dữ liệu.

- **Bẫy Nghẽn Đầu Hàng Đợi (Head-of-Line Blocking / Worker Starvation) Khi Auto-Unblock Thiếu Backoff & Cơ Chế Xoay Hàng Đợi FIFO (User Incident 2026-10-02)**:
  - *Hiện tượng*: Trong báo cáo 6h, chỉ có đúng 1 nick mới hoàn thành (`M56`) và 5 nick lỗi liên tục lặp lại (`M06`, `M34`, `M36`, `M40`, `M49`), trong khi 230+ tài khoản khác đang chờ trong queue `WAIT_24_48H` hoàn toàn không được đụng tới trong suốt 6 tiếng (`Tỉ lệ Codex OAuth trong 6h: 1/6`).
  - *Nguyên nhân cốt lõi*:
    1. Cơ chế Auto-unblock trong `select_candidates()` tự động gán `status = "PENDING"` cho toàn bộ nick có ChatGPT nhưng chưa có Codex OAuth mà không xét đến thời điểm vừa thất bại gần nhất.
    2. Cổng proxy không bị khóa cooldown 24h đối với stage `CODEX_OAUTH`.
    3. Thuật toán chọn ứng viên sort danh sách theo thứ tự cố định (`item[0]` / machine ID).
    -> Hậu quả: Đúng 5 nick lỗi đầu bảng liên tục chiếm trọn cả 5 concurrency worker slots ở MỌI chu kỳ cron 5 phút. Vòng lặp chạy -> fail -> unblock -> bốc lại đúng 5 nick đó đã phong tỏa hoàn toàn 230+ tài khoản phía sau.
  - *Khắc phục chuẩn hóa (Đã triển khai [L2-surgery] Commit 233c911)*:
    1. Sắp xếp candidate theo nguyên tắc Least-Recently-Attempted (`_attempt_ts`), ưu tiên nick chưa từng thử (`_attempt_ts == 0.0`) hoặc có lượt thử cũ nhất lên đầu:
       ```python
       def _attempt_ts(it):
           lr = it[1].get("last_result") or {}
           t_str = lr.get("at") or it[1].get("updated_at")
           t_dt = parse_time(t_str)
           return t_dt.timestamp() if t_dt else 0.0

       sorted_items = sorted(
           profiles.items(),
           key=lambda item: (
               0 if item[1].get("email", "").lower() in oauth_emails else 1,
               _attempt_ts(item),
               item[0],
           ),
       )
       ```
    2. Áp dụng Cooldown Backoff tối thiểu 30 phút (`1800s`) tính từ `last_result['at']` trước khi một nick vừa thử xong được xem xét lại, giải phóng ngay 5 slot cho toàn bộ hàng đợi 230+ tài khoản khác xoay vòng liên tục.

- **Bẫy Exit Code 0 Khống Trong `chatgpt_gpm_direct_reg.py` & Cơ Chế Tự Động Bù Reg ChatGPT Trước Codex (User Incident 2026-10-02)**:
  - *Hiện tượng*: Một số tài khoản Hotmail trong state JSON có `chatgpt_registered_at` nhưng khi mở browser lên form đăng nhập OpenAI thì báo *"Incorrect email address or password"* và nếu mở form đăng ký thì OpenAI chuyển sang *"Nhập mã xác minh ... để tạo tài khoản của bạn"* -> Chứng tỏ tài khoản CHƯA TỪNG được tạo trên OpenAI!
  - *Nguyên nhân*: Hàm `main()` trong `chatgpt_gpm_direct_reg.py` luôn `return 0` bất kể `res['status']` là `SUCCESS` hay `FAIL_PASSWORD_NOT_FOUND` hoặc không tìm thấy candidate. Lệnh `run_cmd()` trong supervisor kiểm tra `returncode == 0` liền nhận định nhầm là đã reg thành công và gán `chatgpt_registered_at = now()`.
  - *Khắc phục chuẩn hóa*:
    1. Trong supervisor nhánh `if stage == "WAIT_24_48H"`: Bắt buộc gọi `run_cmd([sys.executable, str(CHATGPT_REG_SCRIPT), "--provider", "hotmail", "--profile-id", pid, "--email", info["email"]], 300)` để tự động kiểm tra/tạo tài khoản ChatGPT qua Hotmail Graph OTP trước khi nhảy vào `CODEX_OAUTH_SCRIPT`.
    2. Trong `chatgpt_gpm_direct_reg.py`: Khi submit email, OpenAI có thể chuyển hướng thẳng sang `email-verification` (URL có chứa `email-verification` nhưng text DOM có thể chưa nạp kịp). Phải bổ sung vòng lặp chờ `email-verification` trong URL (tối đa 8s) để nhận diện chuyển thẳng bước OTP, tránh bị rơi nhầm vào `FAIL_PASSWORD_NOT_FOUND`.

- **Kỷ Luật Fail-Fast Nhất Quán Trạng Thái Giữa Provisioning và OAuth (Consistency Gate - User Incident 2026-10-02)**:
  - *Hiện tượng & Rủi ro*: Trong supervisor nhánh `WAIT_24_48H`, nếu `run_cmd(CHATGPT_REG_SCRIPT)` trả về `False` (tạo/kiểm tra ChatGPT thất bại) mà supervisor chỉ log cảnh báo rồi vẫn nhắm mắt gọi `run_cmd(CODEX_OAUTH_SCRIPT)`, thì:
    1. Trạng thái tài khoản bị không đồng nhất (inconsistent state): tài khoản chưa có phiên ChatGPT nhưng vẫn bị đẩy vào form Codex OAuth.
    2. Gây lãng phí số tiền mua SIM 5SIM vô ích và làm hỏng transaction ủy quyền OAuth (`invalid_state` / `invalid_auth_step`).
  - *Kỷ luật bắt buộc*:
    ```python
    ok_reg = run_cmd([sys.executable, str(CHATGPT_REG_SCRIPT), "--provider", "hotmail", "--profile-id", pid, "--email", info["email"]], 300)
    if not ok_reg:
        return {"key": key, "status": "FAILED", "stage": "CHATGPT_REG", "next_stage": "WAIT_24_48H", "detail": "ChatGPT provisioning failed"}
    info["chatgpt_registered_at"] = now()
    # Chỉ khi ok_reg == True mới tiếp tục chạy CODEX_OAUTH_SCRIPT
    ```
    Bắt buộc dừng ngay (fail-fast), ghi nhận `stage = "CHATGPT_REG"`, giữ `next_stage = "WAIT_24_48H"` để chờ retry đúng quy trình, tuyệt đối không nhảy cóc sang OAuth.

- **Kỷ Luật Telemetry & Test Regression Phục Vụ Closeout Gate (Audit Standard >= 85/100)**:
  - Khi thêm cơ chế điều phối candidate (cooldown, FIFO, lọc proxy):
    1. *Telemetry rõ ràng*: Bắt buộc bổ sung log định danh có tag cấu trúc:
       `[SCHEDULER_COOLDOWN] Skip {key} on port {port} (cooldown 30m active)`
       để reviewer và operator theo dõi được chính xác lý do từng profile bị skip hoặc bốc chạy.
    2. *Bao phủ Edge-Case Unit Tests*: Mọi thay đổi thuật toán `select_candidates()` và `execute()` BẮT BUỘC phải đi kèm unit test bao phủ các nhánh biên:
       + Trùng proxy port giữa nhiều profile (đảm bảo không bao giờ bốc 2 profile cùng port trong 1 tick).
       + Giới hạn tối đa trần candidate (trần 5 profile/tick).
       + Dữ liệu corrupt / timestamp rác / thiếu trường (scheduler không crash).
       + Fail-safe khi script con fail (trả về FAILED chuẩn xác, không phá vỡ state).
