# Kiến Trúc Focus-Based Idle Tracking Tiểu Vi & Quy Chuẩn Thẩm Định Closeout Gate (22/10/2026)

## 1. Hiện Tượng & Bẫy Kỹ Thuật (Bản Chất Yêu Cầu Người Dùng)
- **Bẫy đo nhàn rỗi toàn hệ thống (OS-Wide Idle):**
  * Script cũ `xiaowei_idle_auto_close_watchdog.py` dùng Windows API `GetLastInputInfo` để đo thời gian người dùng không đụng chuột/bàn phím.
  * **Hậu quả:** Khi người dùng mở Tiểu Vi (XiaoWei / 牧卫) lên soi vài giây rồi chuyển sang chơi game (TFT/LoL), lướt web hoặc chat Telegram, chuột và bàn phím vẫn di chuyển liên tục trên máy tính. Bộ đếm idle toàn cục không bao giờ chạm mốc 20 phút $\rightarrow$ Tiểu Vi kẹt mở vĩnh viễn ở dưới nền.
  * Khi Tiểu Vi kẹt mở ngầm, 80 luồng stream màn hình liên tục ăn băng thông USB 2.0 EHCI (trần 35 MB/s) và tiến trình `adb.exe -P 5038` chia rẽ WinUSB, làm mất 20–40 máy khỏi cổng chuẩn 5037, gây ra lỗi app/runner hàng loạt trong ca nuôi acc.
- **Hành vi khi người dùng tắt bằng tay (Nút X):**
  * Tiểu Vi viết bằng Tauri/Rust, khi đóng giao diện GUI bằng nút X thì tiến trình con `adb.exe -P 5038` bị mồ côi (orphan process).
  * Watchdog chạy ngầm định kỳ 2 phút phát hiện `not is_xiaowei_running()` và tự động bắn `adb -P 5038 kill-server`. Trong vòng 1–2 giây, toàn bộ thiết bị đang bị chiếm giữ tự động quay về cổng 5037 nguyên vẹn.

---

## 2. Kiến Trúc Focus-Based Activity Tracking Chuẩn Xác
1. **Đo tiêu điểm cửa sổ (Focus-based Tracking):**
   * Sử dụng `GetForegroundWindow()` kết hợp `_foreground_process_name(user32, hwnd)`.
   * Nhận diện chính xác Tiểu Vi:
     - Tiến trình chứa `'xiaowei'` (bao gồm `xiaowei.exe`).
     - Hoặc tiêu đề chứa các nhãn gốc: `'xiaowei'`, `'牧卫'`, `'效卫'`, `'com.xiaowei'`.
     - Hoặc tiến trình `msedgewebview2.exe` VÀ tiêu đề chứa `'投屏'` hoặc `'xiaowei'` (tránh nhận nhầm các webview của ứng dụng khác).
   * **Chống False-Positive:** Từ khóa `'投屏'` đơn lẻ trên các tiến trình lạ (`chrome.exe`, `msedge.exe`, `notepad.exe`, `explorer.exe`) BẮT BUỘC trả về `False`.
2. **Khóa cứng mốc 10 phút (600 giây):**
   * Khi người dùng chuyển sang làm việc khác / chơi game, Tiểu Vi bị chìm xuống nền (unfocused) $\rightarrow$ bộ đếm thời gian bắt đầu tích lũy. Quá 10 phút không tương tác lại Tiểu Vi $\rightarrow$ tự động đóng và dọn sạch cổng 5038.
   * Nếu người dùng để Tiểu Vi trên cùng nhưng rời máy đi quá 10 phút (`system_idle >= 600`) $\rightarrow$ cũng tự động đóng.
3. **Throttling Ghi Đĩa & Khử TOCTOU:**
   * Trong `get_idle_seconds()`: chỉ ghi đĩa cập nhật `_write_last_active()` khi độ lệch thời gian `abs(last_active - active_at) >= 1.0s`, triệt tiêu hoàn toàn hiện tượng spam ghi file đĩa ở mỗi chu kỳ polling khi foreground.
   * Trong `main()`: gọi `is_fg = is_xiaowei_foreground()` đúng 1 lần duy nhất rồi truyền vào `get_idle_seconds(is_fg=is_fg)`, loại bỏ hoàn toàn khả năng lệch nhãn `reason` do gọi 2 lần riêng biệt.
4. **Structured JSON Telemetry:**
   * Ghi nhận rõ ràng trường `reason` (`foreground_idle` / `unfocused_background_idle`) và `is_foreground` trong cả sự kiện thành công (`XIAOWEI_CLOSE_TRIGGERED`) lẫn thất bại (`XIAOWEI_CLOSE_FAILED_SUMMARY`).

---

## 3. Quy Chuẩn Vượt Closeout Gate & Sol Auditor
Khi đưa các thay đổi vào Closeout Gate để đạt điểm >= 85:
1. **Bắt buộc có log thực thi Pytest Verbatim:** Reviewer Sol High fail-closed nếu chỉ có diff mà không kèm log thực thi test thực tế (chống "khai test mõm"). Bắt buộc chạy `python -m pytest tests/test_... -v` và ghép stdout vào file review package trước khi gọi gate.
2. **Regression Test Phủ Ranh Giới Thu Hẹp:** Khi thu hẹp bất kỳ điều kiện match chuỗi nào (như bỏ `'投屏'` khỏi title-only), bắt buộc phải có test đối chứng chứng minh các process ngoại lai (`chrome.exe`, `msedge.exe`) không bị nhận diện nhầm.
3. **Parse Object JSON Trong Test Telemetry:** CẤM chỉ assert `assert 'XIAOWEI_CLOSE_TRIGGERED' in out`. Bắt buộc dùng `json.loads(line)` bóc tách từng event và assert đích danh `r['reason']` và `r['is_foreground']`.
4. **Đồng Bộ Hai Cụm Bắt Buộc:** Mọi chỉnh sửa trên `deploy/hermes-home/scripts/xiaowei_idle_auto_close_watchdog.py` bắt buộc chạy `deploy_xiaowei_admin.py` qua SSH và đối soát mã hash SHA256 khớp tuyệt đối 100% với Admin PC.
