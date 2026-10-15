# Preflight 3-Shift Sentinel Shift Partition & In-Flight Lock Skip Protocol (2026-10-15)

## 1. Sự Cố Thực Tế (15/10/2026) — Bẫy Sentinel Theo Ngày Khi Đổi Sang Lịch 3 Ca
- **Hiện tượng:** 
  - Lịch reboot đã cấu hình đúng 3 mốc: `05:20` (Ca 1 Sáng), `11:20` (Ca 2 Trưa), `17:20` (Ca 3 Tối).
  - Ca sáng 05:20 reboot thành công và tạo file cờ `C:\Taadaa_Service\reboot_sentinel_2026-10-15.flag`.
  - Đến mốc 11:20 trưa, log báo:
    `[2026-10-15 11:20:01] [SKIP] Hom nay da reboot (reboot_sentinel_2026-10-15.flag). Thoat 0, khong reboot lap.`
  - Hậu quả: Trưa không reboot, bus USB EHCI không được giải phóng thanh ghi trước Ca 2, các máy rớt kết nối và nghẽn buffer kéo dài.

## 2. Nguyên Nhân Gốc Rễ
- File `farm_preflight_daily_reset.py` được thiết kế từ giai đoạn cũ khi farm chỉ reboot 1 lần/ngày.
- Tên file sentinel cũ chỉ dựa vào ngày:
  `reboot_sentinel_{time.strftime('%Y-%m-%d')}.flag`
- Khi nâng cấp lịch lên 3 ca/ngày (`05:20`, `11:20`, `17:20`), sentinel cũ tự triệt tiêu 2 mốc trưa và tối.

## 3. Kiến Trúc Chuẩn Hóa
1. **Sentinel Phân Vùng Theo Ca (Shift Partitioning):**
   ```python
   def get_current_shift_name() -> str:
       hour = time.localtime().tm_hour
       if hour < 9:
           return "morning"   # Mốc 05:20
       elif hour < 15:
           return "noon"      # Mốc 11:20
       else:
           return "evening"   # Mốc 17:20

   def sentinel_path_for_today() -> Path:
       shift = get_current_shift_name()
       return SENTINEL_DIR / f"reboot_sentinel_{time.strftime('%Y-%m-%d')}_{shift}.flag"
   ```
   Mỗi ca sở hữu một cờ riêng biệt (`reboot_sentinel_YYYY-MM-DD_morning.flag`, `noon.flag`, `evening.flag`), độc lập hoàn toàn.

2. **Bảo Vệ Tránh Cắt Ngang Ca Đang Chạy (`has_active_device_locks`):**
   Nếu tại thời điểm kích hoạt reboot (11:20 hoặc 17:20) mà farm đang có batch/ca chạy dở chưa kết thúc:
   - Quét `~/.codex/device-locks/*.lock.json`.
   - Nếu có file mang `status == 'running'` và `psutil.pid_exists(pid)` $\rightarrow$ chủ động `[SKIP]`, không reboot chen ngang làm hỏng dở phiên nuôi.

3. **Đồng Bộ Hai Nơi Bắt Buộc:**
   - Git repo SSOT: `D:\Taadaa\tools\services\Taadaa_Service\farm_preflight_daily_reset.py`
   - Runtime Windows Task Scheduler: `C:\Taadaa_Service\farm_preflight_daily_reset.py`
