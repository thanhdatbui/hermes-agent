# Canary B4 Preflight, Row Mapping & Stale Lock Handling

## 1. Xác định `-Row` từ `taikhoan_run_safe.xlsx`
- File: `D:/OneDrive/TaadaaData/kibe/taikhoan_run_safe.xlsx`
- Sheet: `Accounts` (Header: `May`, `Device ID`, `ID`, `Video Đã Đăng`)
- **Quy tắc mapping Row**:
  - Mỗi máy (`May`) sở hữu tối đa 8 dòng / slot tài khoản trong sheet.
  - Tham số `-Row <N>` trong `run-feed-session.ps1` nhận giá trị từ `1` đến `8`, tương ứng với **thứ tự slot của máy đó** (1-indexed slot within the machine), **KHÔNG PHẢI** số dòng tuyệt đối của file Excel.
  - Ví dụ: Nick `tolmavhj12k` của Máy 8 nằm ở dòng Excel 58 nhưng là tài khoản đầu tiên của Máy 8 trong danh sách -> dùng `-Row 1`.

## 2. Giải phóng Stale Device Lock
- Vị trí lock: `C:\Users\Kibe\.codex\device-locks\`
  - `machine_<N>.lock.json`
  - `serial_<SERIAL>.lock.json`
- Triệu chứng kẹt:
  - Khi runner trước đó bị crash, ngắt đột ngột, hoặc kết thúc ở trạng thái manual-needed/blocked, file lock vẫn lưu `status: "blocked"` và `owner_active: false`.
  - Runner tiếp theo khởi động sẽ bị chặn ngay lập tức với lỗi: `device lock active: status=blocked`.
- Thao tác dọn dẹp an toàn:
  - Kiểm tra xem PID trong lock có còn tiến trình thực thi tương ứng không.
  - Nếu PID không còn chạy hoặc tiến trình cũ đã dừng:
    ```bash
    rm -f "/c/Users/Kibe/.codex/device-locks/machine_<N>.lock.json" "/c/Users/Kibe/.codex/device-locks/serial_<SERIAL>.lock.json"
    ```
  - Sau khi kết thúc Canary run nếu kết quả là manual-needed / blocked, cũng cần dọn sạch file handoff lock để giải phóng thiết bị cho các cron batch tiếp theo.

## 3. Auto-Login Recovery Timeout (900s)
- Khi runner phát hiện profile username không khớp sau 2 lần switch tài khoản (`profile username still mismatched after switch`), runner sẽ tự động kích hoạt `reconcile_tiktok_accounts.py`.
- Quá trình reconcile tự động này có timeout nội bộ là 900s (15 phút).
- Khi chạy Canary qua terminal với `timeout=600`, lệnh foreground có thể chạm timeout CLI trước khi reconcile hoàn tất, trong khi tiến trình background (`powershell.exe`, `python.exe`, `adb.exe`) vẫn tiếp tục chạy trên máy chủ cho đến khi chạm mốc 900s.
- Cần kiểm tra process (`Get-CimInstance Win32_Process`) và file `summary.txt` / `log.jsonl` trong thư mục run để xác định trạng thái kết thúc thực tế thay vì vội vàng can thiệp adb bằng tay.
