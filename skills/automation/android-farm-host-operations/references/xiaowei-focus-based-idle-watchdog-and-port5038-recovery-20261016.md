# XiaoWei Focus-Based Idle Watchdog & Port 5038 Recovery (16/10/2026)

## 1. Vấn Đề Thực Tế: Bẫy Đo Idle Toàn Hệ Thống (`GetLastInputInfo`)
- **Hiện tượng:**
  * Người dùng mở phần mềm chiếu màn hình XiaoWei (牧卫/效卫/极卫) lên soi màn hình farm 1-2 phút, sau đó để cửa sổ đó và chuyển sang chơi game (TFT / League of Legends) hoặc lướt web, chat Telegram.
  * Sau nhiều giờ, Tiểu Vi vẫn mở chìm dưới nền, tiếp tục chiếm giữ 80 luồng stream USB và giữ chặt tiến trình mồ côi `adb.exe -P 5038` chia rẽ dàn máy (khiến 27+ máy bị kẹt ở cổng 5038 và mất kết nối với các script chạy trên cổng 5037).
- **Nguyên nhân gốc rễ:**
  * Script watchdog cũ (`xiaowei_idle_auto_close_watchdog.py`) đo thời gian nhàn rỗi bằng API Windows `GetLastInputInfo`.
  * `GetLastInputInfo` đo thời gian kể từ lần rê chuột / gõ phím cuối cùng trên **TOÀN BỘ WINDOWS**.
  * Khi người dùng chơi game hoặc gõ bàn phím ở bất kỳ cửa sổ nào khác, bộ đếm idle liên tục bị reset về 0 (đo được chỉ ~40–50 giây), khiến watchdog không bao giờ chạm ngưỡng timeout để tự động đóng Tiểu Vi.

---

## 2. Kiến Trúc Đo Tiêu Điểm Cửa Sổ (Focus-Based Window Idle Tracking)
- **Quy tắc vận hành chuẩn:** Thời gian nhàn rỗi BẮT BUỘC phải đo theo **thao tác thực tế trên chính cửa sổ Tiểu Vi**, không được tính thao tác trên các ứng dụng khác.
- **Cơ chế 2 tầng:**
  1. **Nhận diện tiêu điểm (Foreground Detection):**
     * Gọi `GetForegroundWindow()`.
     * Kiểm tra tiêu đề cửa sổ chứa các chuỗi: `('xiaowei', '牧卫', '效卫', '投屏', 'com.xiaowei')`.
     * Đồng thời truy vấn process image name của cửa sổ active: kiểm tra `xiaowei.exe` hoặc `msedgewebview2.exe` (với command line thuộc xiaowei).
  2. **Bộ đếm thời gian phân tầng:**
     * **Trường hợp 1 (Người dùng đang soi Tiểu Vi):** Cửa sổ Tiểu Vi ở Foreground VÀ `GetLastInputInfo` < 60s $\rightarrow$ Cập nhật `last_active_ts = now` vào file trạng thái `STATE_FILE` (`%TEMP%\xiaowei_idle_activity.ts`), trả về `idle_seconds = 0.0`.
     * **Trường hợp 2 (Tiểu Vi bị bỏ rơi ở Background):** Người dùng đang dùng app khác (như TFT, Chrome, Telegram) $\rightarrow$ Cửa sổ active không phải Tiểu Vi. Bộ đếm tính `unfocused_idle = now - last_active_ts`.
     * **Trường hợp 3 (Người dùng rời máy tính - AFK):** Tiểu Vi ở Foreground nhưng người dùng rời máy đi nơi khác $\rightarrow$ `GetLastInputInfo` tăng cao, `idle_seconds = max(unfocused_idle, system_idle)`.
- **Ngưỡng chuẩn hóa:** **10 phút (600 giây)** (biến môi trường: `XIAOWEI_IDLE_THRESHOLD=600`).
  * Quá 10 phút không đụng vào Tiểu Vi $\rightarrow$ Watchdog tự động kích hoạt `taskkill /F /IM xiaowei.exe` (hoặc CIM Terminate) và dọn sạch cổng 5038.
- **Cơ chế khi tắt bằng tay (Manual Close):**
  * Khi người dùng bấm dấu **X** tắt Tiểu Vi bằng tay: Trong vòng tối đa 2 phút, watchdog quét `not is_xiaowei_running()`, tự động xóa sạch `STATE_FILE` và bắn `adb -P 5038 kill-server` dọn sạch tiến trình con mồ côi, trả 100% thiết bị về lại cổng 5037.

---

## 3. Triển Khai & Kiểm Thử Nghiêm Ngặt
- **File nguồn:** `D:\Taadaa\Hermes\deploy\hermes-home\scripts\xiaowei_idle_auto_close_watchdog.py`
- **Bộ kiểm thử:** `D:\Taadaa\Hermes\tests\test_xiaowei_idle_auto_close_watchdog.py` (12 unit tests passed 100%).
- **Đồng bộ runtime:** Chạy `python D:/Taadaa/Hermes/deploy/hermes-home/scripts/cron_sync_watchdog.py --force` để đồng bộ ngay lập tức sang `%LOCALAPPDATA%\hermes\scripts` và OneDrive Shared.
