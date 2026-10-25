# Farm Silent Freeze Triage: Stagger Bounds, Excel Invariant Halt & Off-Hours Lock Collision

## 1. Hiện Tượng Nhận Diện (Farm Treo > 2 Tiếng Không Chạy Feed)
Khi Operator chất vấn *"Lý do treo 2 tiếng rồi"* hoặc nhóm Telegram Nuôi Acc hoàn toàn vắng bóng báo cáo phiên chạy:
1. **Kiểm tra tiến trình đang chạy O(1) qua `psutil`:**
   ```python
   import psutil
   print([(p.pid, p.name(), p.cmdline()[:3]) for p in psutil.process_iter(['pid', 'name', 'cmdline']) if 'python' in p.name().lower()])
   ```
   Xác định có tiến trình nào đang chiếm ADB (`adb.exe`), runner 2FA, hoặc PowerShell feed runner hay không.
2. **Kiểm tra tình trạng Cronjobs (`cron/jobs.json`):**
   Kiểm tra trường `last_status` và `last_error` của các cronjob huyết mạch:
   - `taikhoan-run-safe-sync`: Nếu `status: error`, kiểm tra ngay lỗi `[PREFLIGHT_VALIDATOR_FAIL]`.
   - `phase9-runner-tiktok-feed`: Kiểm tra `last_run_at`.
   - `tiktok-feed-session-watchdog`: Kiểm tra có gửi tin nhắn nào trong ca hay im lặng hoàn toàn.
3. **Kiểm tra Sổ cái Runner & Thư mục Live:**
   Đối soát `runtime/kibe/cron-state/runner_simple_state.json` (`last_window`) với sự tồn tại của thư mục artifact thực tế `runtime/kibe/live/<YYYY-MM-DD>`. Nếu state ghi nhận đã chạy window nhưng thư mục ngày hôm nay không có run nào $\rightarrow$ Tiến trình thi công con đã bị crash ngay từ giây đầu tiên!

---

## 2. Cạm Bẫy 1: Lệch Ranh Giới Tham Số Stagger Gây Crash Ngầm (Silent Child Crash)
- **Cơ chế nổ:**
  - `tiktok_runner.py` truyền tham số khởi động máy con: `"-MachineStartStaggerMs", "3000,10000"`.
  - Script thi công PowerShell `scripts/run-feed-session.ps1` (dòng 147) kiểm tra ràng buộc an toàn cứng:
    ```powershell
    if ($minStaggerMs -lt 2000 -or $maxStaggerMs -gt 8000) {
        throw "LocalRun machine start stagger must be bounded as min,max in the 2000..8000 ms range."
    }
    ```
  - Vì `10000 > 8000`, PowerShell ném Exception và thoát `exit(1)` ngay lập tức sau 0.1 giây.
  - Tuy nhiên, `tiktok_runner.py` gọi subprocess với `stderr=subprocess.DEVNULL` và ghi nhận ngay `"last_window": "<date>T<hour>"` vào sổ cái.
  - Hậu quả: Runner tưởng ca đã hoàn tất, các tick 15 phút sau đó đều bỏ qua (`_already_ran == True`), khiến cả ca sáng 2–4 tiếng bị đóng băng hoàn toàn mà không ai hay biết.
- **Quy chuẩn sửa đổi:**
  - Ranh giới stagger cho `-LocalRun` BẮT BUỘC nằm trong khoảng `[2000, 8000]` ms:
    `"-MachineStartStaggerMs", "2000,8000"`.
  - Luôn đồng bộ 3 nơi: Git deploy (`deploy/hermes-home/scripts/tiktok_runner.py`), OneDrive sync shared, và Kibe AppData scripts.

---

## 3. Cạm Bẫy 2: Lỗi Công Thức Excel Đơn Lẻ Chặn Cứng Cả Chuỗi Sync
- **Cơ chế nổ:**
  - Công thức trong `Tik{slot}.xlsx`:
    - `FolderVideo` (cột 4): `(máy - 1) * 8 + slot` (độc bản trên toàn farm).
    - `VideoGốc` (cột 5): `(slot - 1) * 80 + máy` (độc bản trên cùng ca).
  - Khi kỹ sư nhập dữ liệu gõ nhầm giá trị của FolderVideo (ví dụ `602`) sang cả cột VideoGốc của Máy 76 Slot 2 (kỳ vọng `(2 - 1) * 80 + 76 = 156`), công cụ `excel_preflight_validator.py` phát hiện sai lệch và kích hoạt `EarlyExitException`.
  - Cronjob `taikhoan-run-safe-sync` dừng khẩn cấp với mã lỗi 1 (`[PREFLIGHT_VALIDATOR_FAIL] Hủy sync runtime do Excel vi phạm Invariant`).
  - Hậu quả: `taikhoan_run_safe.xlsx` không được sinh mới, các runner phụ thuộc vào safe workbook (như picker hoặc feed runner) bị văng lỗi hoặc đọc dữ liệu cũ.
- **Quy trình xử lý O(1):**
  1. Chạy validator định danh vị trí sai phạm:
     ```bash
     python D:/Taadaa/tools/excel_preflight_validator.py --excel-dir D:/OneDrive/TaadaaData/kibe --exit-on-error
     ```
  2. Dùng `openpyxl` sửa chính xác ô vi phạm theo đúng công thức `(slot - 1) * 80 + máy`.
  3. Kích hoạt lại `taikhoan-run-safe-sync` qua `cronjob(action='run', job_id='95f8cd3f4e52')` để cập nhật đủ 640 dòng an toàn.

---

## 4. Cạm Bẫy 3: 2FA Chạy Ngoài Giờ Tranh Chấp Device Lock Hàng Loạt
- **Cơ chế nổ:**
  - Cronjob `night-tiktok-2fa-watchdog` được cấu hình chu kỳ `*/15 * * * *`. Khi vừa bước qua mốc 09:30 (kết thúc cửa sổ chặn buổi sáng `(5, 5) -> (9, 30)`), watchdog lập tức kích hoạt `run_batch_live_2fa.py`.
  - Nếu có 2 tiến trình 2FA cùng chạy (ví dụ 1 instance từ Python 3.12 và 1 instance từ venv `automation`), cả 2 sẽ cùng lúc chiếm `device-locks` của 15–20 máy farm trong thư mục `~/.codex/device-locks/`.
  - Các máy bị lock cứng khiến runner nuôi feed chính thức không thể kết nối hoặc buộc phải skip toàn bộ.
- **Quy trình xử lý O(1):**
  1. Kiểm tra và dọn dẹp các lock chết: Chạy cronjob `reap-dead-owner-locks` (`job_id='b63730cc5c85'`).
  2. Quét các lock còn sót lại trong `C:/Users/Kibe/.codex/device-locks/`:
     Kiểm tra `psutil.pid_exists(lock['pid'])`. Nếu PID không còn tồn tại, xóa file lock tương ứng.
  3. Đảm bảo các watchdog phụ trợ ban đêm không bao giờ được chạy lấn sang cửa sổ ca nuôi chính ban ngày.
