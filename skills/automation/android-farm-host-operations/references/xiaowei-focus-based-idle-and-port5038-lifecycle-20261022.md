# XiaoWei Focus-Based Idle Tracking & Port 5038 Lifecycle Governance (22/10/2026)

## 1. Bản Chất Bẫy Đo Idle Toàn Cục (GetLastInputInfo Pitfall)
- **Cơ chế cũ:** Sử dụng hàm Windows API `GetLastInputInfo` đo thời gian kể từ thao tác chuột/phím cuối cùng trên toàn bộ hệ điều hành.
- **Tử huyệt thực tế:** Khi người dùng mở Tiểu Vi lên soi vài giây rồi chuyển sang chơi game (TFT/League of Legends) hoặc lướt web/chat:
  * Chuột và bàn phím vẫn hoạt động liên tục ở các ứng dụng khác.
  * Bộ đếm `GetLastInputInfo` luôn duy trì ở mức thấp (< 60s), không bao giờ chạm ngưỡng idle 10–20 phút.
  * Hậu quả: Tiểu Vi bị bỏ quên dưới nền chạy vĩnh viễn, kéo theo tiến trình `adb.exe -P 5038` giằng xé 25–40 thiết bị với cổng 5037 suốt ca nuôi.

## 2. Kiến Trúc Đo Tiêu Điểm Riêng Biệt (Focus-Based Activity Tracking)
- **Mục tiêu:** Chỉ tính là "đang sử dụng" khi cửa sổ Tiểu Vi thực sự là Foreground Window có tương tác.
- **Quy trình chuẩn hóa:**
  1. **Nhận diện chính xác Foreground Tiểu Vi (`is_xiaowei_foreground()`):**
     * Lấy `hwnd = GetForegroundWindow()` và `GetWindowThreadProcessId(hwnd)`.
     * Kiểm tra `proc_name == 'xiaowei.exe'`: Chắc chắn là Tiểu Vi.
     * Kiểm tra tiêu đề cửa sổ chứa các định danh duy nhất: `'xiaowei'`, `'牧卫'`, `'效卫'`, `'com.xiaowei'`.
     * Với tiến trình con WebView2 (`msedgewebview2.exe`): BẮT BUỘC kết hợp điều kiện tiêu đề chứa `'投屏'` hoặc `'xiaowei'` để tránh false-positive với các app dùng WebView2 khác.
  2. **Trạng thái hoạt động (`get_idle_seconds()`):**
     * Khi Tiểu Vi đang ở Foreground: Trả về thời gian system idle thuần túy, ghi nhận mốc `last_active = now - system_idle`.
     * Khi Tiểu Vi chìm xuống nền (Unfocused): Bộ đếm unfocused idle bắt đầu tích lũy `unfocused_idle = now - last_active`.
  3. **Ngưỡng hành động chuẩn hóa:**
     * Ngưỡng mặc định: **10 phút (600 giây)**.
     * Khi Tiểu Vi bị bỏ rơi ở background > 10 phút: Watchdog tự động kích hoạt `close_xiaowei()` và dọn sạch cổng 5038.
     * Dọn sạch cờ state khi app đã đóng để lần mở kế tiếp không bị đóng oan.

## 3. Quy Trình Giải Phóng Port 5038 Khi Người Dùng Bấm Nút X
- Khi người dùng bấm nút **X** tắt Tiểu Vi bằng tay, Windows chỉ đóng giao diện `xiaowei.exe`, để lại tiến trình mồ côi `adb.exe -P 5038`.
- Watchdog định kỳ 2 phút (`xiaowei-idle-auto-close-kibe` và `xiaowei-idle-auto-close-admin`):
  * Phát hiện `is_xiaowei_running() == False`.
  * Lập tức gọi `cleanup_orphan_xiaowei_adb()` bắn `adb -P 5038 kill-server` (kèm CIM fallback).
  * Trong vòng 1–2 giây, toàn bộ thiết bị đang bị kẹt ở port 5038 tự động hồi sinh về lại port 5037 nguyên vẹn.
