# Night & Evening Watchdog Chaining & Adaptive Lock Chaining Rules

Quy tắc chuẩn hóa cho các Watchdog chạy sau từng ca nuôi acc (Ca 1 Sáng, Ca 2 Trưa, Ca 3 Tối, Ca 4 Đêm):

## 1. Loại Bỏ Hoàn Toàn Giờ Cố Định (Fixed Timestamp Anti-Pattern)
- CẤM chạy các tác vụ sau ca (Dọn cache, Up avatar, GPM login, Reg Gmail, 2FA) bằng cron mốc giờ tĩnh cố định (như `0 4 * * *` hay `0 22 * * *`).
- Các ca nuôi có độ lệch hoàn thành tuỳ thuộc vào mạng, uiautomator dump XML, uiautomator restart, và queue pair gap.
- **Pattern chuẩn**: Cron chạy mỗi 5 - 10 phút trong khung giờ cửa sổ, kiểm tra 4 điều kiện:
  1. `in_window`: Nằm trong dải giờ cho phép (vd: Ca đêm 01:00 - 05:30).
  2. `not already_ran_today`: Kiểm tra file state JSON (`last_success_date == today_str`).
  3. `is_target_shift_finished`: Đọc `feed_session_reported.json` (kiểm tra key `{today}_{ca}_phien2` hoặc `{today}_{ca}`).
  4. `not has_active_device_locks`: Quét cả `~/.codex/device-locks` và `~/AppData/Local/automation-core/device-locks`, kiểm tra trạng thái lock (`active`, `running`, `queued`, `queued_v2`, hoặc `blocked` còn active).
  5. Đạt đủ 4 điều kiện $\rightarrow$ kích hoạt batch thật, ghi nhận state ngày hôm đó để đảm bảo idempotency.

## 2. Chuỗi Tác Vụ Từng Ca
- **Sau Ca 1 (Sáng 08:30 - 11:30):** `post-morning-gmail-2fa-watchdog`:
  - Thăm dò Ca 1 hoàn tất $\rightarrow$ Bật 2FA Gmail cho acc ngâm đủ tuổi (>= 24-48h).
  - Quét candidate từ `D:\OneDrive\TaadaaData\kibe\master_gmail_manager.xlsx` và `gmail_clean_v2.xlsx`.
- **Sau Ca 2 (Trưa 14:30 - 17:30):** `post-noon-chain-watchdog`:
  - Thăm dò Ca 2 hoàn tất $\rightarrow$ Reg Gmail $\rightarrow$ Add 2FA TikTok.
- **Sau Ca 3 (Tối 18:30 - 23:45 - Cơ chế Cuốn Chiếu Từng Phiên):**
  - `post-evening-avatar-watchdog`: Polling thường trực từ 18:30. Máy nào xong phiên (Phiên 1 hoặc Phiên 2) nhả lock là vào chạy upload avatar cuốn chiếu ngay cho các nick chưa có avatar trên máy đó.
  - `post-evening-gpm-login-watchdog`: Polling thường trực từ 18:30 (CẤM gò cứng sau 21:30 và CẤM bắt đợi avatar). Máy nào xong phiên nhả lock là bốc vào login GPM ngay theo cơ chế cuốn chiếu (5-10 workers song song).
  - **Tích hợp Dual OAuth:** Khi login Gmail lên GPMLogin thành công:
    1. Bước 1: Duyệt Google Prompt trên S7 để nạp OAuth Antigravity lên OmniRoute (:20129).
    2. Bước 2: Nối tiếp ngay `batch_dual_oauth_5workers.py --email <email>` trích xuất session/access token để nạp `chatgpt-web` và `codex` lên OmniRoute.
- **Sau Ca 4 (Đêm 01:00 - 05:30):** `cron_clear_tiktok_cache.py`:
  - Canh Ca 4 hoàn tất và toàn farm đã nhả lock $\rightarrow$ kích hoạt 20–40 luồng dọn dẹp cache TikTok qua intent / UI widget.

## 3. Cạm Bẫy Thực Thi Cần Tránh (Implementation Pitfalls)
1. **Cạm bẫy cấu trúc `feed_session_reported.json`:**
   - File JSON này thường có dạng `{"reported_sessions": ["2026-09-14_ca1_phien2", ...]}` hoặc list trực tiếp `[...]`.
   - **Lỗi phổ biến:** Dùng `k in data` khi `data` là dict $\rightarrow$ chỉ kiểm tra key cấp cao nhất (chỉ có key `"reported_sessions"`), khiến kết quả luôn là `False` dù phiên đã hoàn tất.
   - **Cách xử lý đúng:**
     ```python
     reported_list = data.get("reported_sessions", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
     # Kiểm tra xem bất kỳ session string nào trong list chứa target key hay không
     is_done = any(any(k in str(item) for k in target_keys) for item in reported_list)
     ```

2. **Cạm bẫy đường dẫn Device Lock lỗi thời:**
   - **Lỗi phổ biến:** Kiểm tra `D:\Taadaa\runtime\device_locks\*.lock` (định dạng file `.lock` cũ).
   - **Vị trí lock thực tế:** Phải quét đồng thời cả 2 thư mục:
     + `~/.codex/device-locks`
     + `%LOCALAPPDATA%\automation-core\device-locks`
   - File có đuôi `*.lock.json`. Bắt buộc đọc nội dung JSON để kiểm tra status `active`, `running`, `queued`, `queued_v2`, hoặc `blocked` với `owner_active != False` và `pid_exists(pid)`.

3. **Cạm bẫy CLI của `batch_dual_oauth_5workers.py`:**
   - Script batch mặc định quét toàn bộ profile GPM. Khi watchdog `post_evening_gpm_login_watchdog.py` kích hoạt sau khi login xong 1 máy, bắt buộc `batch_dual_oauth_5workers.py` phải hỗ trợ tham số `--email <email>` để xử lý đúng duy nhất profile đó, tránh kích hoạt quét toàn bộ farm gây xung đột browser.

4. **Kỷ luật đồng bộ 3 vị trí (Master Git - AppData - OneDrive Shared):**
   - Khi chỉnh sửa hoặc thêm mới watchdog script:
     1. `D:\Taadaa\Hermes\deploy\hermes-home\scripts\` (Master git repo)
     2. `%LOCALAPPDATA%\hermes\scripts\` (Runtime local của daemon)
     3. `D:\OneDrive\Taadaa_Sync_Shared\hermes-cron\scripts\` (Sync dùng chung toàn farm)
   - Bắt buộc copy đồng bộ đủ cả 3 nơi và chạy `python -m py_compile` để nghiệm thu cú pháp.

5. **Kỷ luật Tool-Budget & Tránh Bị Cắt Phiên Giữa Chừng (Tool Limit Awareness):**
   - Khi thực hiện sửa đổi liên quan đến chuỗi script cron (sửa script A, thêm CLI cho script B, nối vào script C và đồng bộ 3 thư mục):
     + Phải phân bổ số lần gọi tool hợp lý, tuyệt đối không dùng hết lượt gọi tool cho việc đọc file hoặc tìm kiếm diện rộng (`find` timeout, đọc lặp các file đã biết).
     + Nhận diện ngay đường dẫn các script cốt lõi: master git repo `D:\Taadaa\Hermes\deploy\hermes-home\scripts\`, runtime `%LOCALAPPDATA%\hermes\scripts\`, shared `D:\OneDrive\Taadaa_Sync_Shared\hermes-cron\scripts\`.
     + Đọc định vị đúng đoạn cần sửa, patch trực tiếp và đồng bộ file nhanh chóng để hoàn tất bàn giao mã nguồn trong ngân sách lượt gọi cho phép.

## 4. Kỷ Luật Cuốn Chiếu Sau Từng Phiên (Rolling Post-Session Execution) — Cập nhật 16/09/2026:
- **Tử huyệt "Gò khung giờ đêm cố định" (21:30 - 23:45):** 
  * Sai lầm nghiêm trọng khi gom toàn bộ tác vụ GPM Login, Avatar vào cuối ca tối và ép điều kiện tĩnh (`now.hour >= 22` hoặc bắt đợi `post-evening-avatar-watchdog` xong).
  * Điều này gây lãng phí lớn tài nguyên: Các máy chạy Phiên 1 Ca tối đã rảnh từ `18:45 - 19:15` bị bỏ không, đến đêm lại dồn tải, chạm trần proxy 2 acc/cổng/ngày hoặc xung đột với Ca 4 Đêm (00:00).
- **Quy tắc Vàng Cuốn Chiếu Sau Phiên (User Invariant):** *Bất kỳ cron nào cài đặt sau các phiên nuôi acc BẮT BUỘC set cuốn chiếu theo từng máy / từng phiên nhả lock:*
  1. **Lịch Polling Thường Trực:** Cron schedule phải chạy từ sớm (khung `18,19,20,21,22,23 * * *` với chu kỳ `*/2` hoặc `*/5`).
  2. **Bỏ Chặn Giờ Cứng & Bỏ Đợi Nhau:** Xóa bỏ hoàn toàn hàm hardcode `is_within_time_window()` ép giờ đêm và xóa bỏ điều kiện bắt cron này phải đợi cron kia (`is_avatar_done()`).
  3. **Kiểm tra Lock Từng Máy (`is_machine_idle(mid)`):** Máy nào trong phiên vừa nhả device lock và có đệm an toàn tới slot tiếp theo $\ge 30 - 45$ phút $\rightarrow$ Worker bốc máy đó vào chạy cuốn chiếu ngay lập tức (chạy song song 5–10 workers).
  4. **Giữ Vững Safety Gates:** Duy trì giới hạn proxy (tối đa 2 acc/port/ngày), giới hạn máy (1 lần/ngày), và cơ chế báo cáo tổng kết duy nhất 1 lần khi hoàn tất toàn ca để giữ im lặng (silent watchdog).
