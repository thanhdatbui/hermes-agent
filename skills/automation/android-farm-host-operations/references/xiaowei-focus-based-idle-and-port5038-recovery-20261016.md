# Focus-Based Idle Tracking & XiaoWei Auto-Close Architecture (2026-10-16)

## 1. Vấn Đề Thiết Kế Cũ: Whole-System Idle vs App Focus
- **Hạn chế của `GetLastInputInfo`:**
  - `GetLastInputInfo` của Win32 API trả về thời điểm phát sinh thao tác chuột/phím cuối cùng trên **toàn bộ hệ điều hành Windows**, không phân biệt ứng dụng nào đang nhận input.
  - **Hệ quả thực tế:** Khi người dùng mở Tiểu Vi (XiaoWei / 牧卫) lên soi màn hình một lúc rồi chuyển sang chơi game (TFT / Liên Minh), lướt web hoặc chat Telegram, chuột và bàn phím liên tục phát sinh sự kiện $\rightarrow$ `GetLastInputInfo` đo idle luôn < 1 phút.
  - Tiểu Vi bị kẹt mở dưới nền vô thời hạn, duy trì kết nối stream video và daemon ADB port 5038, chia rẽ thiết bị với cổng 5037 và gây nghẽn bus USB 2.0 trong suốt ca nuôi acc.

## 2. Kiến Trúc Focus-Based Idle Tracking Chuẩn
- **Nguyên lý đo lường:**
  1. Kiểm tra tiêu điểm cửa sổ hiện tại: `hwnd = user32.GetForegroundWindow()`.
  2. Phân loại chính xác tiến trình sở hữu (`_foreground_process_name`) và tiêu đề cửa sổ:
     - `proc_name == 'xiaowei.exe'` hoặc tiêu đề chứa (`xiaowei`, `牧卫`, `效卫`, `com.xiaowei`) $\rightarrow$ Tiểu Vi đang nhận tiêu điểm.
     - `proc_name == 'msedgewebview2.exe'` VÀ tiêu đề chứa (`投屏`, `xiaowei`) $\rightarrow$ Khung WebView2 của Tiểu Vi.
     - Các ứng dụng khác (Chrome, TFT, Telegram...) $\rightarrow$ Trả về `False`.
  3. Quản lý trạng thái tương tác (`xiaowei_idle_activity.ts`):
     - **Khi Tiểu Vi đang Foreground:**
       Cập nhật mốc `last_active = now - system_idle` và trả về đúng `system_idle`. Nếu người dùng buông tay khi đang ngắm Tiểu Vi quá ngưỡng $\rightarrow$ đóng an toàn.
     - **Khi Tiểu Vi bị mất Foreground (Unfocused / Background):**
       Đọc mốc `last_active` từ state file (nếu chưa có thì tạo mới ghi `now`). Trả về `now - last_active` (thời gian Tiểu Vi bị bỏ quên dưới nền).
  4. Ngưỡng chuẩn: Cấu hình mặc định **10 phút (600 giây)** (hoặc override qua biến môi trường `XIAOWEI_IDLE_THRESHOLD`).

## 3. Dọn Dẹp Trạng Thái & Giải Phóng Port 5038
- Khi đóng Tiểu Vi (qua `close_xiaowei()`):
  - Gửi lệnh `taskkill /F /IM xiaowei.exe`.
  - Xóa file trạng thái `xiaowei_idle_activity.ts`.
  - Gọi ngay `cleanup_orphan_xiaowei_adb()` để dập tắt daemon ADB port 5038 mồ côi (`adb -P 5038 kill-server`), trả toàn bộ thiết bị về cổng 5037.
- Khi người dùng tự tay bấm nút X tắt Tiểu Vi:
  - Watchdog ở chu kỳ quét kế tiếp (2 phút/lần) phát hiện `not is_xiaowei_running()` sẽ tự động dọn sạch state file và kill server 5038.
- Khi đồng bộ sang Admin PC:
  - Dùng SSH nạp thẳng vào `%LOCALAPPDATA%\hermes\scripts\xiaowei_idle_auto_close_watchdog.py` và đối soát SHA256 hai đầu.
