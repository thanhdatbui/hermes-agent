# Xiaowei Focus-Based Idle Tracking & Multi-Host Sync (16/10/2026)

## 1. Bẫy Đo Idle Toàn Cục (System-Wide GetLastInputInfo Pitfall)
- **Thiết kế ban đầu:** Watchdog `xiaowei_idle_auto_close_watchdog.py` dùng Windows API `GetLastInputInfo` để đo thời gian không thao tác chuột/bàn phím.
- **Tử huyệt thực tế:** `GetLastInputInfo` đo thời gian nhàn rỗi trên toàn bộ Windows session.
  * Khi người dùng mở Tiểu Vi (牧卫/攸卫/XiaoWei) lên soi nhanh 1-2 phút, sau đó chuyển sang chơi game (TFT / League of Legends), gõ Telegram hoặc duyệt web trên các cửa sổ khác, chuột và bàn phím liên tục phát sinh sự kiện.
  * Bộ đếm idle toàn cục liên tục bị reset về 0 (đo được chỉ 20-50 giây).
  * **Hậu quả:** Tiểu Vi bị bỏ quên chạy ngầm ở dưới nền vĩnh viễn, kéo theo tiến trình `adb.exe -P 5038` giằng xé 27-40 thiết bị WinUSB khỏi cổng 5037 và làm nghẽn microframe USB 2.0 suốt cả ca nuôi.

---

## 2. Kiến Trúc Focus-Based Activity Tracking (Đo Theo Tiêu Điểm Cửa Sổ)
Nâng cấp cơ chế đo nhàn rỗi từ **System-Wide Idle** sang **Focus-Based Activity Tracking**:
1. **Kiểm tra Tiêu Điểm Cửa Sổ (`is_xiaowei_foreground()`):**
   * Gọi `user32.GetForegroundWindow()`.
   * Lấy tiêu đề cửa sổ qua `GetWindowTextW`: so khớp các từ khóa định danh (`xiaowei`, `牧卫`, `效卫`, `投屏`, `com.xiaowei`).
   * Truy vấn tên tiến trình sở hữu cửa sổ qua `GetWindowThreadProcessId` + `QueryFullProcessImageNameW`: kiểm tra `xiaowei.exe` hoặc `msedgewebview2.exe`.
2. **Cơ chế State Machine Theo Dõi Tương Tác:**
   * Lưu mốc thời gian tương tác cuối cùng vào file trạng thái:
     `STATE_FILE = os.path.join(os.environ.get('TEMP', r'C:\Windows\Temp'), 'xiaowei_idle_activity.ts')`
   * **Nhánh 1 (Đang thao tác trên Tiểu Vi):**
     Nếu `is_xiaowei_foreground() == True` VÀ `system_idle < 60s` (người dùng đang thực sự click/gõ trên Tiểu Vi):
     $\rightarrow$ Ghi đè `now` vào `STATE_FILE`, trả về `idle = 0.0`.
   * **Nhánh 2 (Tiểu Vi bị bỏ quên dưới nền):**
     Nếu `is_xiaowei_foreground() == False` (người dùng đang ở app khác):
     $\rightarrow$ `unfocused_idle = now - last_active`. Thời gian nhàn rỗi tích lũy tăng dần theo thời gian Tiểu Vi mất tiêu điểm.
   * **Nhánh 3 (Tiểu Vi để trên cùng nhưng rời máy):**
     Nếu `is_xiaowei_foreground() == True` NHƯNG `system_idle >= 600s` (rời bàn máy):
     $\rightarrow$ `idle = max(unfocused_idle, system_idle) >= 600s`.
3. **Ngưỡng hành động chuẩn hóa:**
   * Ngưỡng mặc định: `IDLE_THRESHOLD_SECONDS = 600` (10 phút, hỗ trợ override qua `os.environ.get('XIAOWEI_IDLE_THRESHOLD', '600')`).
   * Khi `idle >= 600s`: kích hoạt đóng Tiểu Vi an toàn (`taskkill` fallback CIM `Terminate`) và dọn sạch cổng 5038.

---

## 3. Vòng Đời Dọn Dẹp Khi Người Dùng Bấm Nút X Bằng Tay
- Khi người dùng chủ động bấm **X** tắt giao diện Tiểu Vi:
  * Tiến trình `xiaowei.exe` biến mất nhưng `adb.exe -P 5038` vẫn bị mồ côi (orphan).
  * Watchdog định kỳ 2 phút (`*/2 * * * *`) phát hiện `not is_xiaowei_running()`:
    1. Gọi `_clear_idle_state()` xóa sạch `STATE_FILE` để lần mở kế tiếp không bị đóng oan do thời gian tích lũy cũ.
    2. Gọi `cleanup_orphan_xiaowei_adb()` bắn `adb -P 5038 kill-server` (fallback CIM Terminate).
    3. Toàn bộ thiết bị bị 5038 chiếm giữ tự động trả tự do về cổng 5037 trong 1-2 giây.

---

## 4. Quy Chuẩn Đồng Bộ Đa Cụm (Multi-Host Sync Invariant)
- Khi nâng cấp watchdog trên Kibe PC:
  * **BẮT BUỘC** đồng bộ ngay sang cả Admin PC (`192.168.110.119`) tại `%LOCALAPPDATA%\hermes\scripts\xiaowei_idle_auto_close_watchdog.py`.
  * Phương thức truyền: Chuyển dữ liệu Base64 chia chunk 3000 bytes qua `admin_ssh.py`.
  * **Hậu kiểm Readback SHA-256:** Đối soát hash sha256 và file size giữa Local và Admin PC để xác nhận 100% toàn vẹn trước khi hoàn tất.
