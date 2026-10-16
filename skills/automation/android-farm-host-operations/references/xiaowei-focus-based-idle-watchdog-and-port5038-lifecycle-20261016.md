# XiaoWei Focus-Based Idle Watchdog & Port 5038 Lifecycle Governance (16/10/2026)

## 1. Vấn Đề Cốt Lõi: Global Input Idle vs Focus-Based Idle
- **Bẫy `GetLastInputInfo` toàn cục:**
  * Ban đầu watchdog `xiaowei_idle_auto_close_watchdog.py` đo idle bằng Windows API `GetLastInputInfo`.
  * Hàm này đếm thời gian kể từ lần rê chuột hoặc gõ phím cuối cùng trên **toàn bộ hệ điều hành Windows**.
  * **Hệ quả thực tế:** Khi người dùng bật Tiểu Vi (XiaoWei / 牧卫 / 攸卫) lên soi màn hình vài chục giây, sau đó chuyển sang chơi game (TFT / League of Legends), chat Telegram hoặc làm việc trên browser, chuột và phím vẫn liên tục phát sinh sự kiện. Bộ đếm idle toàn cục luôn duy trì ở mức < 1 phút, khiến Tiểu Vi **không bao giờ chạm ngưỡng idle và kẹt mở ngầm vĩnh viễn**.
- **Tác hại đối với Phone Farm:**
  * Tiểu Vi chạy ngầm liên tục kéo 80 luồng stream minicap làm nghẽn bus USB 2.0 (trần 35 MB/s) trên bo mạch X99 EHCI.
  * Tiến trình con `adb.exe -P 5038` của Tiểu Vi giằng xé endpoint WinUSB, chiếm giữ 27–42 thiết bị khiến runner nuôi acc (port 5037) văng lỗi `device not found` / `prepare-tiktok failed to focus`.

---

## 2. Kiến Trúc Đo Idle Theo Tiêu Điểm Cửa Sổ (Focus-Based Tracking)
Để giải quyết triệt để yêu cầu *"chỉ khi nào thao tác chuột/phím vào màn hình Tiểu Vi mới tính là đang dùng"*, kiến trúc watchdog được chuyển đổi sang **Focus-Based Activity Tracking**:

1. **Nhận diện tiêu điểm chính xác (`is_xiaowei_foreground()`):**
   - Lấy window handle đang active: `hwnd = user32.GetForegroundWindow()`.
   - Lấy process name từ PID:
     * Nếu `proc_name == 'xiaowei.exe'`: Chắc chắn là Tiểu Vi đang ở tiêu điểm (`True`).
     * Nếu `title` chứa cụm định danh: `('xiaowei', '牧卫', '效卫', 'com.xiaowei')` $\rightarrow$ `True`.
     * Nếu `proc_name == 'msedgewebview2.exe'` và `title` chứa `'投屏'` hoặc `'xiaowei'` $\rightarrow$ `True`.
     * Ngược lại: Trả về `False` (loại bỏ hoàn toàn false-positive từ các app WebView2 hoặc app cast khác).

2. **State Machine đo thời gian nhàn rỗi (`get_idle_seconds()`):**
   - Sử dụng file lưu mốc thời gian: `STATE_FILE = %TEMP%\xiaowei_idle_activity.ts`.
   - **Khi Tiểu Vi đang ở Foreground (`is_fg == True`):**
     * Thời gian nhàn rỗi chính là `system_idle` (người dùng đang nhìn Tiểu Vi nhưng không chạm phím chuột).
     * Cập nhật `last_active = now - system_idle` vào `STATE_FILE`.
     * Trả về `system_idle`.
   - **Khi Tiểu Vi bị chìm xuống nền (`is_fg == False`):**
     * Đọc `last_active` từ `STATE_FILE` (nếu chưa có thì khởi tạo `now`).
     * Thời gian nhàn rỗi tích lũy: `unfocused_idle = now - last_active`.
     * Trả về `unfocused_idle`.
   - **Ngưỡng đóng tự động:** Chuẩn hóa **10 phút (600 giây)**. Khi Tiểu Vi bị bỏ quên dưới nền quá 10 phút, watchdog lập tức kích hoạt đóng app.

---

## 3. Vòng Đời Cổng ADB 5038 Khi Người Dùng Tắt Bằng Tay (Nút X)
- **Hành vi nút X:** Tiểu Vi viết bằng Tauri/Rust, khi người dùng click nút X đóng cửa sổ GUI, Windows hạ sát `xiaowei.exe` nhưng **tiến trình con `adb.exe -P 5038` bị mồ côi (orphan)**, vẫn tiếp tục chiếm WinUSB endpoints.
- **Cơ chế dọn dẹp tự động trong <= 2 phút:**
  * Watchdog chạy chu kỳ `*/2 * * * *`.
  * Khi quét thấy `not is_xiaowei_running()`:
    1. Xóa sạch file mốc `STATE_FILE` (chống tích lũy idle sai cho lần mở kế tiếp).
    2. Gọi `cleanup_orphan_xiaowei_adb()`: bắn `adb -P 5038 kill-server`.
    3. Fallback WMI/CIM nếu server bị treo: hạ sát PID `adb.exe` lắng nghe port 5038 thuộc thư mục `xiaowei`.
  * Toàn bộ 27–42 thiết bị tự động bàn giao về lại cổng 5037 trong vòng 1–2 giây mà không cần khởi động lại ADB chính.

---

## 4. Quy Chuẩn Đồng Bộ Đa Host Farm (Kibe PC & Admin PC)
- **Quy tắc Invariant:** Mọi bản vá logic watchdog Tiểu Vi bắt buộc phải đồng bộ song song cho cả cụm:
  * **Kibe PC:** `%LOCALAPPDATA%\hermes\scripts\xiaowei_idle_auto_close_watchdog.py`.
  * **Admin PC (`192.168.110.119`):** Đẩy qua SSH (`admin_ssh.py`) hoặc script staging `deploy_xiaowei_admin.py` vào `%LOCALAPPDATA%\hermes\scripts\`.
  * **Kho lưu trữ Git & OneDrive:** `D:\Taadaa\Hermes\deploy\hermes-home\scripts\` và `D:\OneDrive\Taadaa_Sync_Shared\hermes-cron\scripts\`.
- **Hậu kiểm bọc hash SHA-256:** Bắt buộc đối soát hash SHA-256 trên cả 2 host sau khi copy để xác nhận tính toàn vẹn 100% trước khi nghiệm thu.
