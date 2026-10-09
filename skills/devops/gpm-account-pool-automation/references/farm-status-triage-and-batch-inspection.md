# Triage Farm Status Checklist (Điều tra tiến độ & ca chạy Farm)

## 1. Khi User hỏi: "R xong hết chưa", "Xong hết chưa", "Tình hình sao rồi"
Tuyệt đối KHÔNG suy đoán từ một watchdog hay một job đơn lẻ rồi vội vàng kết luận "đã xong hết". Bắt buộc đối soát 3 lớp hiện trường theo thứ tự:

### Lớp 1: Kiểm tra Process Python đang chạy trên Host
```powershell
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Select-Object ProcessId, CommandLine | Format-Table -Wrap -AutoSize"
```
- Phân loại tiến trình:
  - **Dịch vụ thường trực (Daemon / Server)**: Dashboard port 1905, proxy server... (đây là daemon, không tính là batch chưa xong).
  - **Batch runner đang chạy dở**: Ví dụ `run_batch_chatgpt_link_today.py`, `feed_session_runner`, `batch_dual_oauth`...
  - Nếu có script batch đang chạy -> Xác định rõ PID, thời gian bắt đầu, số máy mục tiêu và tiến độ hiện tại.

### Lớp 2: Kiểm tra Device Locks & Trạng thái Cron State
- Kiểm tra lock đang giữ thiết bị:
  - Thư mục lock: `~/.codex/device-locks/` hoặc `D:/Taadaa/runtime/kibe/cron-state/`.
- Đọc file state của các ca tối / ngày:
  - `post_evening_gpm_login_state.json`: Xem `finished: true`, tỷ lệ thành công / thất bại, lý do dừng (`proxy_limit`).
  - `post_evening_avatar_state.json`: Xem `running_batch` (PID còn sống hay đã thoát).
  - `feed_session_reported.json`: Xem ca feed hiện tại đã kết thúc chưa.

### Lớp 3: Kiểm tra Hiện trường Thiết bị Thật (ADB O(1))
- Nếu phát hiện script đang chạy can thiệp trên máy (như batch ChatGPT S7):
  ```bash
  adb -s <serial> shell "dumpsys window | grep -E 'mCurrentFocus|mFocusedApp'"
  ```
  - Xác định app đang focus trên máy mục tiêu (ví dụ: `com.google.android.gm` đang mở lấy OTP hay Chrome đang chạy).
  - Báo cáo rõ ràng: Máy nào đang làm gì, còn lại bao nhiêu máy, dự kiến thời gian hoàn thành.

## 2. Format Báo cáo Trả lời User
1. **Phần đã xong**: Liệt kê rõ các ca/batch đã hoàn tất (`GPM login: Hoàn tất ca tối...`, `Avatar: Đã xong...`).
2. **Phần đang chạy**: Nêu rõ script, PID, đối tượng máy đang xử lý tại hiện trường thực tế, và ước lượng thời gian còn lại.
3. **Tuyệt đối ngắn gọn, trực diện**, không lan man lý thuyết.
