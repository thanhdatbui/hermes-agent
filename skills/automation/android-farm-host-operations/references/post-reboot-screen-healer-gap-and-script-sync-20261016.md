# Post-Reboot Screen Healer Gap, 25-Day Timeout Drift & Cron Script Sync Invariant (16/10/2026)

## 1. Hiện Tượng Thực Tế
Sau mốc Auto-Reboot Ca trưa (11:20 AM), người dùng mở công cụ chiếu màn hình (Phóng Vệ / XiaoWei v9.11) lúc 11:47 AM phát hiện:
- Toàn bộ 80 máy Admin (M201–M280) và phần lớn máy Kibe (M1–M80) đều đang **bật sáng toàn bộ màn hình** ở Launcher / Home Screen.
- Mặc dù hệ thống đã có cronjob `farm-idle-screen-and-app-healer` chạy mỗi 15 phút (`*/15 * * * *`).

## 2. Nguyên Nhân Gốc Rễ (Triple-Factor Root Cause)

### A. Bản chất khởi động lại của Android OS
- Khi 160 máy S7 hoàn tất reboot lúc 11:20 AM, hệ điều hành Android tự động kích hoạt display power (`state=ON`, `mWakefulness=Awake`) để nạp Launcher.
- Mọi thiết bị đều bắt đầu ở trạng thái màn hình sáng.

### B. Bẫy toán tử `<=` trong `is_near_reboot_window` gây SKIP kép (30 phút điểm mù)
- Cronjob chạy theo chu kỳ 15 phút: `11:00, 11:15, 11:30, 11:45`.
- Hàm kiểm tra an toàn né reboot:
  ```python
  def is_near_reboot_window(buffer_minutes: int = 10) -> bool:
      ...
      for rm in reboot_minutes:  # [05:20, 11:20, 17:20]
          if abs(cur_m - rm) <= buffer_minutes:
              return True
      return False
  ```
- Diễn biến tại mốc 11:20:
  * **Nhịp 11:15:** `abs(11:15 - 11:20) = 5 <= 10` $\rightarrow$ `True` $\rightarrow$ **SKIP** (Hợp lý để tránh xung đột ADB khi máy đang tắt nguồn).
  * **Nhịp 11:30:** `abs(11:30 - 11:20) = 10 <= 10` $\rightarrow$ `True` $\rightarrow$ **BỊ SKIP TIẾP**!
- **Hệ quả:** Suốt từ 11:15 đến 11:45 (30 phút, trong đó có 25 phút sau khi máy đã boot xong), healer hoàn toàn không chạy lần nào. Màn hình máy rảnh giữ nguyên trạng thái sáng.

### C. Lệch phiên bản Script trong Cron Runtime (`~/.hermes/scripts/`)
- Hermes Cron thực thi script đặt tại: `~/.hermes/scripts/farm_idle_screen_and_app_healer.py`.
- File tại đây bị kẹt ở bản cũ ngày 25/09/2026:
  * **Bản cũ:** Chỉ gán `settings put system screen_off_timeout 600000` (10 phút) một cách thụ động, hoàn toàn không có bước quét `dumpsys power` để phát `input keyevent 223` (KEYCODE_SLEEP) ép tắt màn hình ngay lập tức.
  * **Bản mới tại `D:/Taadaa/tools/`:** Có đầy đủ kiểm tra `dumpsys power` $\rightarrow$ `keyevent 223` và `pidof` dập TikTok, nhưng chưa được đồng bộ sang deploy repo và thư mục runtime của Hermes.

### D. Trôi `screen_off_timeout` thành 25 ngày (`2147483647` ms)
- Các tool kiểm thử giao diện / stub UI của `uiautomator` / `atx-agent` khi chạy tự động gán `Settings.System.putInt(..., SCREEN_OFF_TIMEOUT, Integer.MAX_VALUE)` ($2^{31}-1 = 2147483647$ ms $\approx 24.85$ ngày) để chống tắt màn hình trong lúc automation.
- Nếu không có healer chủ động ghi đè lại `600000`, Android sẽ đếm ngược 25 ngày mới tự tắt màn hình.

## 3. Quy Trình Khắc Phục & Vận Hành Bắt Buộc

### 1. Kích hoạt Healer tại chỗ cứu nóng
Chạy trực tiếp bản chuẩn từ tools:
```bash
python D:/Taadaa/tools/farm_idle_screen_and_app_healer.py
```
- Khôi phục `screen_off_timeout = 600000` và `stay_on_while_plugged_in = 0`.
- Dập tắt app TikTok treo ngầm bằng `pidof` $\rightarrow$ `am force-stop` $\rightarrow$ `keyevent 3` về HOME.
- Ép toàn bộ màn hình rảnh đang sáng về sleep bằng `keyevent 223`.

### 2. Quy Chuẩn Đồng Bộ Script Cron (SSOT Invariant)
Khi cập nhật script watchdog / healer trong `D:/Taadaa/tools/`:
1. BẮT BUỘC copy file sang repo deploy:
   ```bash
   cp "D:/Taadaa/tools/farm_idle_screen_and_app_healer.py" "D:/Taadaa/Hermes/deploy/hermes-home/scripts/farm_idle_screen_and_app_healer.py"
   cp "D:/Taadaa/tools/farm_idle_screen_and_app_healer.py" "D:/OneDrive/Taadaa_Sync_Shared/hermes-cron/scripts/farm_idle_screen_and_app_healer.py"
   ```
2. Chạy watchdog đồng bộ để nạp vào runtime:
   ```bash
   python "D:/Taadaa/Hermes/deploy/hermes-home/scripts/cron_sync_watchdog.py"
   ```
3. Đối soát mã băm MD5 giữa `D:/Taadaa/tools/` và `~/.hermes/scripts/` để đảm bảo khớp 100%.
