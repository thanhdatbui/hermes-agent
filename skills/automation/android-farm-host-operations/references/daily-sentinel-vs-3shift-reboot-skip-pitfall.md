# Pitfall: Daily Sentinel Name Skips Shift 2 (11:20) and Shift 3 (17:20) Reboots

## 1. Triệu Chứng Hiện Trường (15/10/2026)
- **Hiện tượng:** Sau Ca 1 (Sáng), đến Ca 2 (Trưa 12:00 / 14:00), hàng loạt máy bắt đầu rụng ADB (`device not found`, `failed_transport`, `prepare-tiktok failed to focus TikTok after launch`).
- **Kiểm tra uptime host (`psutil.boot_time()`):** Host PC Kibe & Admin đã có uptime > 6–7 tiếng liên tục (từ 05:21 sáng), thanh ghi USB 2.0 EHCI bị nghẽn buffer.
- **Kiểm tra log `C:\Taadaa_Service\daily_reset.log`:**
  ```text
  [2026-10-15 05:20:07] [KIBE] Kich hoat reboot Kibe PC sau 5 giay...
  [2026-10-15 05:20:07] [SENTINEL] Da ghi reboot_sentinel_2026-10-15.flag.
  [2026-10-15 06:15:19] [SKIP] Hom nay da reboot (reboot_sentinel_2026-10-15.flag). Thoat 0, khong reboot lap.
  [2026-10-15 11:20:01] === BAT DAU KIEM TRA PREFLIGHT DAILY REBOOT (TRUOC CA TRUA) ===
  [2026-10-15 11:20:01] [SKIP] Hom nay da reboot (reboot_sentinel_2026-10-15.flag). Thoat 0, khong reboot lap.
  ```

## 2. Nguyên Nhân Gốc Rễ (Configuration & Design Drift)
- Lịch Task Scheduler đã được cập nhật thành **3 mốc trước 3 Ca chính**:
  1. `05:20` (trước Ca 1 Sáng)
  2. `11:20` (trước Ca 2 Trưa)
  3. `17:20` (trước Ca 3 Tối)
- Tuy nhiên, trong script `farm_preflight_daily_reset.py`, hàm sentinel vẫn giữ logic dạng ngày:
  ```python
  def sentinel_path_for_today() -> Path:
      return SENTINEL_DIR / f"reboot_sentinel_{time.strftime('%Y-%m-%d')}.flag"
  ```
- **Hậu quả:** Ngay khi mốc 05:20 reboot thành công, file `reboot_sentinel_YYYY-MM-DD.flag` được tạo. Đến 11:20 và 17:20 cùng ngày, script kiểm tra `sentinel.exists()` thấy file cờ này nên lập tức **`[SKIP]`**, khiến host KHÔNG BAO GIỜ được reboot làm sạch ở Ca trưa và Ca tối!

## 3. Giải Pháp & Quy Chuẩn Khắc Phục (Per-Shift Sentinel)
1. **Chuyển cờ Sentinel theo Ca (`reboot_sentinel_YYYY-MM-DD_shift{1,2,3}.flag`) hoặc kiểm tra TTL cooldown (ví dụ: tối thiểu cách lần reboot trước 4.5–5 tiếng):**
   ```python
   def get_current_shift_name() -> str:
       now = datetime.now()
       hour = now.hour
       if 4 <= hour < 10:
           return "morning_0520"
       elif 10 <= hour < 16:
           return "noon_1120"
       elif 16 <= hour < 22:
           return "evening_1720"
       return "ad_hoc"
   ```
2. **Cứu hộ tức thời khi host bị `[SKIP]` trưa/tối:**
   Xóa file cờ `C:\Taadaa_Service\reboot_sentinel_<today>.flag` trước khi phát lệnh hoặc chạy script reset để trigger lại chu kỳ reboot làm sạch cho 2 trạm Kibe & Admin.
