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
