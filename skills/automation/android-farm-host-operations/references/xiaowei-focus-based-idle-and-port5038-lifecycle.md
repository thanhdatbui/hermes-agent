# XiaoWei Focus-Based Idle Tracking & Port 5038 Lifecycle Governance

## 1. Bối Cảnh & Tử Huyệt Của Cơ Chế Idle Cũ (GetLastInputInfo)
- **Cơ chế cũ:** `xiaowei_idle_auto_close_watchdog.py` đo thời gian không thao tác bằng Windows API `GetLastInputInfo`.
- **Tử huyệt (Global OS Idle vs App-Specific Idle):**
  * `GetLastInputInfo` đo thời gian kể từ thao tác chuột/phím cuối cùng trên **toàn bộ hệ điều hành**.
  * Khi người dùng mở Tiểu Vi (攸卫/牧卫/XiaoWei) lên soi màn hình farm vài chục giây, sau đó chuyển cửa sổ sang chơi game (TFT/League of Legends), chat Telegram, hoặc lướt web: chuột và bàn phím liên tục phát sinh sự kiện.
  * Hậu quả: Bộ đếm idle toàn cục không bao giờ vượt qua ngưỡng, Tiểu Vi bị bỏ quên chạy ngầm vĩnh viễn dưới nền.
  * Khi Tiểu Vi chạy ngầm: nó liên tục stream 80 luồng video màn hình qua USB 2.0 (ngốn 100-150 Mbps) và daemon `adb.exe -P 5038` giam giữ 25-30 máy điện thoại, khiến ca nuôi acc (chạy trên port 5037) bị nghẽn bus, timeout socket và văng hàng loạt lỗi app ảo.

## 2. Kiến Trúc Focus-Based Idle Tracking Mới (10 Phút Ngưỡng Chuẩn)
- **Nguyên tắc cốt lõi (User Invariant):** Chỉ tính là đang thao tác khi người dùng **thực sự tương tác trên cửa sổ Tiểu Vi**.
- **Cơ chế đo đạc 2 trạng thái:**
  1. **Khi Tiểu Vi là Foreground Window (`is_xiaowei_foreground() == True`):**
     * Trả về thời gian không đụng tay trong chính cửa sổ Tiểu Vi (`system_idle`).
     * Cơ chế Throttling I/O: Chỉ ghi đĩa (`STATE_FILE`) khi mốc hoạt động thay đổi `>= 1.0s` (`abs(last_active - active_at) >= 1.0`), triệt tiêu hoàn toàn việc ghi đĩa spam ở mỗi chu kỳ polling 1-2 phút.
  2. **Khi Tiểu Vi chìm xuống nền (`is_xiaowei_foreground() == False`):**
     * Người dùng đang làm việc ở app khác (TFT, browser, Telegram).
     * Thời gian không tương tác được tính bằng `now - last_active` (đọc từ file state).
     * Khi thời gian chìm dưới nền liên tục chạm ngưỡng **10 phút (600 giây)**: Watchdog tự động kích hoạt đóng Tiểu Vi (`close_xiaowei()`) và dọn dẹp port 5038.

## 3. Nhận Diện Cửa Sổ Tiêu Điểm Chuẩn Xác (Precision Focus Detection)
- Để tránh false-positive nhận diện nhầm các ứng dụng WebView2 khác (như Edge, Teams, GPM-Browser) là Tiểu Vi:
  * Kiểm tra process name của Foreground Window: nếu là `xiaowei.exe` $\rightarrow$ `True`.
  * Kiểm tra tiêu đề cửa sổ: nếu chứa các từ khóa định danh đặc thù (`'xiaowei'`, `'牧卫'`, `'效卫'`, `'com.xiaowei'`) $\rightarrow$ `True`.
  * Nếu process là `msedgewebview2.exe`: BẮT BUỘC tiêu đề cửa sổ phải đi kèm từ khóa `'投屏'` hoặc `'xiaowei'` mới tính là Tiểu Vi.
  * Các trường hợp process khác (Chrome, TFT, Telegram) $\rightarrow$ trả về `False` ngay lập tức.
- Trong `main()`: Bắt buộc lấy `is_fg = is_xiaowei_foreground()` đúng **1 lần duy nhất** và truyền vào `get_idle_seconds(is_fg=is_fg)` để triệt tiêu race condition làm sai lệch nhãn telemetry (`reason="foreground_idle"` vs `reason="unfocused_background_idle"`).

## 4. Vòng Đời Giải Phóng Cổng 5038 Khi Người Dùng Bấm Tắt Bằng Tay (Nút X)
- **Tình huống:** Người dùng chủ động click dấu **X** đóng cửa sổ Tiểu Vi trên màn hình Desktop.
- **Hiện tượng mồ côi (Orphan Daemon):** Framework Tauri của Tiểu Vi đóng GUI `xiaowei.exe` nhưng **không tự động kill tiến trình con `adb.exe -P 5038`** do nó sinh ra. Tiến trình này tiếp tục chạy ngầm vô thời hạn và giữ chân 25–40 máy điện thoại trên driver WinUSB.
- **Cơ chế tự động giải phóng (Auto-Purge trong <= 2 phút):**
  * Watchdog `xiaowei-idle-auto-close-kibe` và `xiaowei-idle-auto-close-admin` chạy định kỳ 2 phút/lần (`*/2 * * * *`).
  * Ở mỗi chu kỳ quét, nếu phát hiện `not is_xiaowei_running()` (người dùng đã tắt Tiểu Vi):
    1. Tự động xóa mốc state idle cũ (`_clear_idle_state()`) để lần mở sau không bị đóng oan.
    2. Kích hoạt hàm `cleanup_orphan_xiaowei_adb()`:
       - Kiểm tra socket listening trên port 5038.
       - Gửi lệnh phẫu thuật `adb -P 5038 kill-server`.
       - Fallback hard CIM/WMI terminate nếu tiến trình bị treo socket.
    3. Ngay khi daemon 5038 thoát, 100% thiết bị bị chiếm giữ lập tức tự động quay về cổng chuẩn 5037 trong vòng 1–2 giây mà không làm gián đoạn các batch nuôi acc đang chạy trên port 5037.
- **Đồng bộ đa cụm (Kibe & Admin):**
  * Cả 2 máy Kibe và Admin đều chạy phiên bản script đồng bộ.
  * Khi cập nhật code, dùng `cron_sync_watchdog.py` cho local/OneDrive và deploy qua SSH sang Admin PC tại `%LOCALAPPDATA%\hermes\scripts\xiaowei_idle_auto_close_watchdog.py`.
