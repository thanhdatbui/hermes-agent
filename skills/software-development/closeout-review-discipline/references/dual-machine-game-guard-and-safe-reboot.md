# Dual-Machine Game Guard & Safe Scheduled Reboot Architecture

## 1. Mục Đích & Lịch Kích Hoạt
- **Mục đích:** Tự động reboot làm sạch RAM và bus USB 2.0 EHCI định kỳ cho cả 2 máy (Kibe PC và Admin PC `admin-farm`), ngăn chặn hiện tượng rụng cổng ADB / kẹt transport USB trước các ca nuôi feed.
- **Lịch kích hoạt:** Windows Task Scheduler (`Taadaa_Farm_Daily_Reboot_1135`) kích hoạt 3 ca hàng ngày:
  * **05:20** (Trước Ca 1 Sáng 06:00)
  * **11:20** (Trước Ca 2 Trưa 12:00)
  * **17:20** (Trước Ca 3 Tối 18:00)
- **File production:** `C:\Taadaa_Service\farm_preflight_daily_reset.py` (đồng bộ từ `D:\Taadaa\tools\services\Taadaa_Service\farm_preflight_daily_reset.py`).

## 2. Quy Tắc Bất Biến Game Guard (TFT & Warcraft 3)
BẮT BUỘC quét trên **CẢ 2 MÁY**: Kibe PC (local `psutil`) và Admin PC (remote SSH `admin-farm: tasklist /FO CSV /NH`).

### A. Teamfight Tactics (ĐTCL / League of Legends)
- **IN-MATCH (TRONG TRẬN THẬT 3D) $\rightarrow$ CHẶN REBOOT TUYỆT ĐỐI (ABORT mã 1):**
  * `league of legends.exe` (Engine trận 3D LMHT / ĐTCL client Riot).
  * `tftclient-win64-shipping.exe` (Engine trận ĐTCL standalone / bản 64-bit mới).
- **LOBBY / CLIENT / SẢNH CHỜ $\rightarrow$ VẪN CHO PHÉP REBOOT LÀM SẠCH:**
  * `LeagueClient.exe`, `LeagueClientUx.exe`, `LeagueClientUxRender.exe` (Client ngoài sảnh).
  * `RiotClientServices.exe`, `RiotClientCrashHandler.exe` (Riot Client nền).
  * `TFTAcademy.exe` (Phần mềm giáo án / bổ trợ TFTAcademy).

### B. Warcraft 3 (War3)
- **CHẶN TUYỆT ĐỐI BẤT KỲ LÚC NÀO APP MỞ (ABORT mã 1):**
  * `war3.exe`, `w3l.exe`, `warcraft iii.exe`, `frozen throne.exe`.
  * Chỉ cần phát hiện 1 trong các process trên đang chạy trên Kibe hoặc Admin -> HỦY BỎ REBOOT NGAY LẬP TỨC.

### C. Cơ Chế Fail-Safe Khi Mất Kết Nối
- Nếu lệnh SSH sang Admin PC timeout hoặc lỗi exit code $\rightarrow$ Tự động xem như **đang có trận game (Fail-safe True)**, hủy lệnh reboot để bảo vệ ván chơi của User.

## 3. Kiến Trúc Vận Hành An Toàn (Fail-Closed & Atomic)
1. **Khóa Single-Instance Chống Chạy Đồng Thời:**
   * Sử dụng OS-level file lock (`msvcrt.locking` trên Windows) tại `C:\Taadaa_Service\farm_preflight_daily_reset.lock`.
   * Nếu có một instance khác đang chạy, instance sau tự động thoát mã 0 với cờ `skipped_concurrent_run`.
2. **Kiểm Tra Device Locks Của Ca Nuôi Feed:**
   * Quét `.codex/device-locks/*.lock.json`. Nếu có lock `status == "running"` với PID hợp lệ đang sống $\rightarrow$ Bỏ qua reboot (`skipped_active_device_lock`).
   * File lock JSON bị hỏng, rỗng hoặc PID lỗi $\rightarrow$ Fail-safe coi như có lock, chặn reboot.
3. **Bảo Toàn Session Hermes Chạy ĐẦU TIÊN (Fail-Closed):**
   * `preserve_in_flight_sessions(lookback_minutes=20)` được kích hoạt **TRƯỚC** khi gửi bất kỳ lệnh reboot nào (cả Admin lẫn Kibe).
   * Đóng gói truy cập an toàn qua `_session_db_raw_access()`.
   * Nếu DB lỗi hoặc exception $\rightarrow$ Ném ngoại lệ, dừng toàn bộ chuỗi reboot (`aborted_preserve_failed`) để bảo vệ phiên chat dở dang của User.
   * Chỉ xóa file cờ `.clean_shutdown` khi `marked > 0`.
4. **Sentinel Độc Lập Cho Từng Máy:**
   * `reboot_sentinel_<date>_<shift>_admin.flag` và `reboot_sentinel_<date>_<shift>_kibe.flag`.
   * Ghi nhận sentinel ngay khi lệnh reboot của máy đó được phát thành công.
   * Nếu Admin reboot thành công nhưng Kibe gặp sự cố, lần chạy kế tiếp trong cùng ca sẽ nhận diện `admin_done=True`, bỏ qua Admin và chỉ thử lại Kibe.
5. **Telemetry Kiểm Toán Có Cấu Trúc:**
   * Mỗi lần chạy kết thúc với dòng log JSON duy nhất:
     `[SUMMARY] {"admin": "dispatched", "admin_sentinel": "written", "check_only": false, "kibe": "dispatched", "kibe_sentinel": "written", "outcome": "complete"}`.
