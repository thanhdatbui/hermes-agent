# Dynamic Shift-Pool (Row 0), Stagger Boundary & Silent One-Shot Cron Launch

## 1. Bẫy Spam Chat Khi Tạo One-Shot Helper Cronjob (Deliver 'local' Invariant)
- **Vấn đề:** Khi cần kích hoạt gấp một script chạy nền hoặc chạy bù qua cron (`launch_compensatory_*.py`), nếu gọi `cronjob action='create'` mà bỏ quên tham số `deliver` (hoặc để `deliver='origin'`), Hermes Scheduler mặc định auto-deliver toàn bộ stdout về chat Telegram của User.
- **Hậu quả:** Toàn bộ log stdout (ví dụ 160 dòng ping telemetry phần cứng thiết bị của 2 cụm Kibe & Admin) sẽ đổ dồn dập vào DM của User, gây spam nghiêm trọng làm User ức chế.
- **Quy tắc bất di bất dịch:**
  * Mọi helper / one-shot cronjob dùng để kích hoạt batch ngầm **BẮT BUỘC PHẢI TRUYỀN `deliver='local'`**.
  * Chạy xong bắt buộc gọi ngay `cronjob action='remove'` để dọn sạch hàng đợi.
  * Chỉ khi nào script là watchdog báo cáo định kỳ theo giờ chẵn và đã có bộ lọc tóm tắt ngắn gọn mới được deliver về Telegram channel/chat tương ứng.

---

## 2. Bẫy Crash Ngầm Row 0 (Dynamic Shift-Pool Machine Discovery)
- **Vấn đề:** Khi Farm chuyển sang cơ chế Dynamic Shift-Pool (`USE_DYNAMIC_FEED=1`, chạy `-Row 0 -ShiftCa <N>`), script điều phối `run-feed-session.ps1` gọi hàm Python để liệt kê danh sách máy:
  ```powershell
  from core.feed_session_workbook import list_feed_session_machines
  list_feed_session_machines(workbook, device_map, row_index=0)
  ```
- **Điểm nổ:** Trong `python_runner/core/feed_session_workbook.py` trước đây có chốt chặn cứng:
  ```python
  if row_index < 1:
      raise RuntimeError("--account-row-index must be >= 1")
  ```
- **Hậu quả:** PowerShell văng terminating error `Could not resolve machines from the safe account workbook` và dừng phiên ngay lập tức.
- **Giải pháp chuẩn hóa:**
  * Cho phép `row_index >= 0`.
  * Với `row_index == 0`: Trả về danh sách tất cả các máy có ít nhất 1 slot có serial/account hợp lệ trên 8 slot:
    ```python
    if row_index == 0:
        return sorted(
            machine
            for machine, serials in serials_by_machine.items()
            if any(SERIAL_PATTERN.fullmatch(s) for s in serials if s)
        )
    ```

---

## 3. Bẫy Giới Hạn Stagger Khởi Động Máy (2000..8000 ms)
- **Vấn đề:** Trong `run-feed-session.ps1`, tham số `-MachineStartStaggerMs` có kiểm tra an toàn nghiêm ngặt:
  ```powershell
  if ($minStaggerMs -lt 2000 -or $maxStaggerMs -gt 8000 -or $minStaggerMs -gt $maxStaggerMs) {
      throw "LocalRun machine start stagger must be bounded as min,max in the 2000..8000 ms range."
  }
  ```
- **Cạm bẫy:** Nếu script launcher (`tiktok_runner.py`) truyền dải vượt quá 8000ms (ví dụ `3000,10000`), PowerShell sẽ throw exception và chết ngay trong 0.1 giây.
- **Nguy cơ tàng hình:** Vì `tiktok_runner.py` redirect `stderr: DEVNULL`, lỗi crash này bị nuốt trọn trong bóng tối. Script tưởng PowerShell đã chạy nên lưu trạng thái `last_window` vào `runner_simple_state.json`, khiến phiên nuôi bị bỏ qua hoàn toàn mà không hề có máy nào chạy.
- **Quy tắc:** Luôn giữ `-MachineStartStaggerMs` trong giới hạn chuẩn `2000,8000`.

---

## 4. Bẫy Mất Report Ca Chạy Bù Do Cửa Sổ Giờ Watchdog & State Reported Ảo
- **Hiện tượng:** Ca chạy bù hoàn tất thành công trên dàn máy nhưng trên Telegram nhóm không thấy báo cáo tổng kết, chỉ thấy các cảnh báo lỗi đơn lẻ.
- **2 Nguyên nhân cốt lõi:**
  1. *Lệch cửa sổ giờ cố định:* `feed_session_watchdog.py` quét theo 3 ca cố định (Ca 1: 07:30–09:30, Ca 2: 11:45–13:30, Ca 3: 17:45–19:30). Một phiên chạy bù lúc 10:54 sáng nằm ngoài khung giờ này nên cronjob định kỳ 5 phút sẽ im lặng (`silent: empty output`).
  2. *Transient Delivery Timeout làm kẹt State:* Khi bước vào cửa sổ quét (vd 12:28), watchdog quét ra kết quả ca bù nhưng nếu lệnh gửi Telegram vướng timeout mạng/proxy tạm thời (`httpx.ProxyError`), state `feed_session_reported.json` có thể đã lỡ ghi nhận session key (vd `2026-10-25_ca1_phien2`). Hậu quả là các lần chạy sau coi như phiên đã báo cáo xong và bỏ qua vĩnh viễn.
- **Xử lý nhanh O(1):**
  * Kiểm tra `D:/Taadaa/runtime/kibe/cron-state/feed_session_reported.json`.
  * Nếu session key bị ghi nhận sớm khi tin nhắn chưa tới nhóm, xóa key đó khỏi mảng `reported_sessions` rồi kích hoạt lại watchdog: `cronjob action='run', job_id='1d62cb3562e0'`.

---

## 5. Bẫy Sai Công Thức Video Gốc TikN.xlsx Khóa Cứng Pipeline Sync
- **Vấn đề:** Khi nhập tay hoặc copy sheet Excel, ô cột Video Gốc (cột E) bị sai công thức (ví dụ ô E77 máy 76 Tik2 bị gõ `602` thay vì `(2-1)*80 + 76 = 156`).
- **Hậu quả:** `excel_preflight_validator.py` phát hiện vi phạm Invariant sẽ abort toàn bộ pipeline sync (`taikhoan-run-safe-sync`), khiến `taikhoan_run_safe.xlsx` không cập nhật và `phase9-staging-picker` văng lỗi hàng loạt.
- **Quy tắc:** Công thức Video Gốc cho máy `M` trên `TikN`:
  $$\text{Video Gốc} = (N - 1) \times 80 + M$$
  Khi có cảnh báo preflight, kiểm tra và sửa đúng giá trị số nguyên vào ô bị sai trong `TikN.xlsx`, sau đó chạy lại validator để kiểm chứng pass 100%.

---

## 6. Giải Pháp Kiến Trúc: Two-Phase Commit & Auto-Retry Giữa Watchdog và Hermes Scheduler
- **Cơ chế phân phối stdout của Hermes Cron:**
  * Script chạy chế độ `no_agent: True`: Script hoàn tất -> in stdout -> Scheduler dùng `httpx` POST payload sang API Telegram.
  * Nếu gặp lỗi mạng tạm thời (`httpx.ProxyError: Host unreachable`), Hermes chỉ ghi nhận `last_delivery_error` trên object của job trong `jobs.json`, **hoàn toàn không có hàng đợi retry (delivery queue)**.
- **Điểm yếu Commit State trước trong script watchdog cũ:**
  * Script watchdog (`feed_session_watchdog.py`) từng ghi đè `feed_session_reported.json` (tick session đã báo cáo) **trước khi in stdout hoặc trước khi tầng mạng xác nhận giao hàng**.
  * Hậu quả: Giao hàng thất bại 1 lần duy nhất $\rightarrow$ lần tick 5 phút sau script đọc file state thấy key đã tồn tại $\rightarrow$ script trả về stdout rỗng (silent) $\rightarrow$ Hermes không phát tin nữa $\rightarrow$ **Báo cáo biến mất vĩnh viễn vào hố đen**.
- **Cơ chế Giao Tin 2 Pha (Two-Phase Commit & Auto-Retry) chuẩn hóa:**
  1. *Pha 1 (Pending Claim):* Khi có báo cáo mới, watchdog lưu vào khối `"pending_delivery"` gồm `session_key` và `message`, **TUYỆT ĐỐI CHƯA tick vào `reported_sessions`**, sau đó mới in `message` ra stdout.
  2. *Pha 2 (Hermes Telemetry Verification):* Ở lượt quét kế tiếp:
     * Watchdog kiểm tra `jobs.json` (`_get_hermes_delivery_error(mode)`).
     * **Nếu phát hiện `last_delivery_error`:** Watchdog giữ nguyên pending state, tự động in lại nội dung cũ (`print(pending['message'])`) để Hermes kích hoạt retry gửi lại Telegram ngay lập tức!
     * **Chỉ khi `last_delivery_error is None`:** Watchdog mới chính thức chuyển `session_key` vào `reported_sessions` và dọn sạch `pending_delivery`.
  3. *Khôi phục khẩn cấp thủ công:* Nếu cần ép gửi lại một session đã lỡ bị tick trước đó: xóa session key khỏi `reported_sessions` trong `feed_session_reported.json` rồi kích hoạt lại watchdog.

---

## 7. Cơ Chế Phân Bổ Dynamic Shift-Pool 4 Ngày Chuẩn (4-Tier Funnel, Cooldown 48h Success-Only & Zero Follow Dưỡng Sinh)
- **Ranh Giới Pool Cố Định Theo Từng Ca (Bất Biến):**
  * 🌅 **Ca 1 (Sáng: 06:00 & 08:00):** Từng máy CHỈ ĐƯỢC CHỌN trong Pool **`{Row 1, Row 2, Row 7}`**.
  * ☀️ **Ca 2 (Trưa: 12:00 & 14:00):** Từng máy CHỈ ĐƯỢC CHỌN trong Pool **`{Row 3, Row 4, Row 8}`**.
  * 🌙 **Ca 3 (Tối: 18:00 & 20:00):** Từng máy CHỈ ĐƯỢC CHỌN trong **`{Row 5, Row 6} + 1 Row động`**.
  * 🔒 **S2 bám S1 (100%):** Phiên 2 trong cùng ca luôn bám chặt và chạy đúng nick mà Phiên 1 của máy đó đã chọn.

- **Thứ Tự Phễu Sức Khỏe 4 Tầng Khi Bốc Nick Trong Pool:**
  1. 🚀 **Tầng 1 (Đề xuất):** Nick cắn đề xuất (`is_account_boosted`) $\to$ Ưu tiên số 1 để đăng video giữ đà.
  2. 💪 **Tầng 2 (Nick khỏe):** Nick có chỉ số tương tác tốt, nhiều follow/tim, view đều đặn.
  3. 🩹 **Tầng 3 (Dưỡng thương):** Nick bị TikTok nhả follow / dính cooldown follow $\to$ lướt feed xả phạt, làm ấm session để hồi phục.
  4. 🌱 **Tầng 4 (Nick non):** Nick có số lượng video ít nhất $\to$ đăng video tích lũy nội dung.

- **Luật Cooldown 48h Trong Nội Bộ Chu Kỳ (Chỉ Kích Hoạt Khi SUCCESS Thật):**
  * **Chạy Thất bại / Lỗi / Timeout / Skip:** **TUYỆT ĐỐI KHÔNG DÍNH COOLDOWN**. Nick đề xuất hoặc nick khỏe nếu gặp sự cố hạ tầng (rớt USB, timeout, app kẹt) sẽ tiếp tục được ưu tiên bốc lại ở các ca/ngày kế tiếp cho đến khi đạt được **ít nhất 1 lần SUCCESS trọn vẹn trong chu kỳ**.
  * **Chỉ khi SUCCESS thành công:** Lúc đó nick mới chính thức ăn Cooldown 48h trong nội bộ chu kỳ hiện tại, ép máy phải luân phiên sang các nick còn lại trong Pool, triệt tiêu việc cày dồn 1 nick.
  * **Reset Cứng Khi Sang Chu Kỳ Mới (D0):** Cooldown 48h chỉ khoanh vùng trong nội bộ chu kỳ 4 ngày (`cycle_idx`). Khi bước sang Ngày 1 (D0) của chu kỳ mới, toàn bộ cờ cooldown được **xóa sạch 100% về 0** (kể cả nick vừa chạy ở Ca 3 Ngày 3 hoặc Ngày 4 dưỡng sinh thì sáng D0 vẫn sạch cờ và được ưu tiên chạy bình thường).

- **Kỷ Luật Dưỡng Sinh (Ca 3 Ngày 3 & Toàn Bộ Ngày 4):**
  * **Thời điểm:** Ca 3 tối Ngày 3 (D2) và toàn bộ các ca của Ngày 4 (D3).
  * **Kỷ luật:** CHỈ lướt feed nuôi tài khoản + Đăng video giữ nhịp kênh.
  * **NGẮT 100% MỌI THAO TÁC FOLLOW:** Tự động kích hoạt `rest_day_no_follow: true` (`TAADAA_REST_DAY_NO_FOLLOW=1`), tắt hoàn toàn follow chéo và follow tự nhiên để tài khoản được nghỉ ngơi dưỡng sinh, triệt tiêu rủi ro checkpoint/spam.
