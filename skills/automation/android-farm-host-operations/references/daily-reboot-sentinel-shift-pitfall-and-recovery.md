# Bẫy Sentinel Flag Theo Ngày Khi Reboot 3 Ca & Cơ Chế Phân Định Ca (2026-10-15)

## 1. Bản Chất Sự Cố Trưa 11:20 Bị Bỏ Qua (Skipped Reboot)
- **Triệu chứng:** Task Scheduler `Taadaa_Farm_Daily_Reboot_1135` trên Windows đã được cấu hình đủ 3 trigger chuẩn (`05:20:00`, `11:20:00`, `17:20:00`), nhưng đến 11:20 trưa máy hoàn toàn không reboot.
- **Log thực tế (`C:\Taadaa_Service\daily_reset.log`):**
  ```text
  [2026-10-15 05:20:07] [KIBE] Kich hoat reboot Kibe PC sau 5 giay...
  [2026-10-15 05:20:07] [SENTINEL] Da ghi reboot_sentinel_2026-10-15.flag.
  ...
  [2026-10-15 11:20:01] === BAT DAU KIEM TRA PREFLIGHT DAILY REBOOT (TRUOC CA TRUA) ===
  [2026-10-15 11:20:01] [SKIP] Hom nay da reboot (reboot_sentinel_2026-10-15.flag). Thoat 0, khong reboot lap.
  ```

## 2. Nguyên Nhân Gốc Rễ (Root Cause)
- Trong `farm_preflight_daily_reset.py`, hàm tạo sentinel:
  ```python
  def sentinel_path_for_today() -> Path:
      return SENTINEL_DIR / f"reboot_sentinel_{time.strftime('%Y-%m-%d')}.flag"
  ```
- File flag đặt tên duy nhất theo ngày `reboot_sentinel_YYYY-MM-DD.flag`.
- Khi ca 05:20 sáng hoàn tất, file flag của ngày đã được tạo. Đến các mốc 11:20 và 17:20, script kiểm tra `sentinel.exists()` thấy file flag hôm nay đã có -> Kết luận nhầm là "hôm nay đã reboot rồi" và `[SKIP]` toàn bộ các ca còn lại!

## 3. Quy Chuẩn Sửa Đổi & Phân Định Ca Sentinel (Shift Sentinel Protocol)
1. **Phân rã Sentinel theo Khung Giờ / Ca Chạy:**
   - Thay vì 1 file cho cả ngày, sentinel phải gắn liền với ca chạy hoặc mốc giờ:
     * `reboot_sentinel_YYYY-MM-DD_0520.flag` (Ca sáng)
     * `reboot_sentinel_YYYY-MM-DD_1120.flag` (Ca trưa)
     * `reboot_sentinel_YYYY-MM-DD_1720.flag` (Ca tối)
   - Hoặc xác định ca dựa trên giờ hiện tại (`now.hour`):
     ```python
     def get_current_shift_slot() -> str:
         hour = time.localtime().tm_hour
         if 4 <= hour < 9:
             return "morning_0520"
         elif 10 <= hour < 15:
             return "noon_1120"
         elif 16 <= hour < 21:
             return "evening_1720"
         return f"adhoc_{hour:02d}"
     ```
2. **Khóa Cooldown Tối Thiểu 3 Tiếng Giữa 2 Lần Reboot:**
   - Ngoài kiểm tra sentinel ca, kiểm tra `uptime = time.time() - psutil.boot_time()`.
   - Nếu máy vừa reboot cách đây `< 10800` giây (3 tiếng) thì mới an toàn skip để tránh reboot lặp. Nếu uptime $\ge 4$ tiếng và đúng mốc trigger -> Bắt buộc cho phép reboot.

## 4. Bẫy Thấu Thị: Phân Biệt Sập Bus USB vs "Script Không Tự Fix Được"
- **Tại sao script có retry mà vẫn fail `prepare-tiktok failed to focus`:**
  - Script `device_prepare.py` đã có retry 10 lần (`PREPARE_FOCUS_MAX_ATTEMPTS = 10`), có cơ chế relaunch `monkey` ở lần 4 và 7, có `dismiss_tiktok_popups()`.
  - Tuy nhiên khi 80 máy đồng loạt chạy, 2 controller USB 2.0 EHCI bị nghẽn buffer. Lệnh `dumpsys window` để đọc focus qua ADB bị timeout liên tục -> hàm trả về `None`.
  - Script không thể phân biệt giữa "app không lên" và "ADB shell đọc focus bị timeout do bus USB kẹt", dẫn tới fail-closed sau 10 lần thử.
  - Đây là lý do chu kỳ reboot giải phóng bus USB trước mỗi ca chạy là **BẮT BUỘC**, không thể thay thế thuần túy bằng retry mềm trong code script.
