# Sự Cố Bỏ Qua Reboot Do Active Lock Kép & Chia Rẽ Cổng ADB 5038 (21/10/2026)

## 1. Hiện Trường Sự Cố
- **Hiện tượng:** Tại Ca 3 - Phiên 2/2 (Tối 20:00 ngày 21/10/2026, Row 3), Farm Kibe (M1-80) báo fail 35 máy:
  * 24 máy báo "Mất kết nối ADB/USB".
  * 10 máy báo "Lỗi mở/focus App TikTok".
  * 1 máy báo "Lỗi App TikTok/Script".
  * 45 máy còn lại (100% thuộc chế độ Dưỡng Sinh) thành công trọn vẹn.
- **Nghi vấn ban đầu:** Người dùng đặt câu hỏi: *"Lý do văng USB lắm vậy? Máy Kibe có reboot trước phiên chạy chưa?"*

## 2. Kết Quả Điều Tra Gốc Rễ (Root Cause Investigation)

### A. Máy Kibe & Admin Chưa Hề Được Reboot Trước Ca 2 (Trưa) & Ca 3 (Tối)
- **Uptime thực tế:** Cả Kibe PC lẫn Admin PC đều có `boot_time` từ **05:21 sáng ngày 21/10/2026**. Thời gian hoạt động liên tục đã đạt **17.5 tiếng**.
- **Log `C:\Taadaa_Service\daily_reset.log`:**
  ```text
  [2026-10-21 11:20:04] [SKIP] Dang co tien trinh nuoi acc giu active device lock. Bo qua reboot de khong cat ngang ca chay.
  [2026-10-21 17:20:04] [SKIP] Dang co tien trinh nuoi acc giu active device lock. Bo qua reboot de khong cat ngang ca chay.
  ```
- **Bản chất kỹ thuật:** Hàm `has_active_device_locks()` trong `farm_preflight_daily_reset.py` quét thư mục `~/.codex/device-locks/` phát hiện có tiến trình cuốn chiếu xen ca đang giữ máy (`status: running`, PID còn sống) nên đã chủ động hủy bỏ (`SKIP`) lệnh reboot ở cả 2 mốc 11:20 và 17:20 để tránh cắt ngang ca chạy. Hậu quả là bus USB 2.0 EHCI không được reset trong suốt 17.5 tiếng.

### B. Tiến Trình Tiểu Vi (XiaoWei) Chiếm Giữ Cổng ADB 5038 Lúc 16:38
- **Điều tra tiến trình:**
  * Lúc **16:38:23**, tiến trình ADB thứ 2 được kích hoạt:
    `PID: 15812 | tools/adb -P 5038 nodaemon server start`
  * Tiến trình GUI `xiaowei.exe` (PID 5580) được mở sau đó.
- **WinUSB Exclusive Hijacking:**
  * Trình điều khiển WinUSB trên Windows có cơ chế khóa endpoint độc quyền cho tiến trình ADB đầu tiên claim thiết bị.
  * Daemon ADB 5038 đã claim và giam giữ **34 máy** của Kibe.
  * Cổng ADB chuẩn 5037 chỉ còn lại đúng **46 máy** (trùng khớp với 45 máy Success + M75).
  * Toàn bộ 34 máy bị giam giữ trên port 5038 hoàn toàn biến mất khỏi `adb devices` cổng 5037 (`device not found`).

### C. Bẫy Watchdog Phân Loại Nhầm "Lỗi Mở/Focus App TikTok"
- Khi runner nuôi acc phát lệnh mở TikTok trên các máy bị mất kết nối, lệnh kiểm tra activity (`dumpsys window`) trả về `None`/`unknown`. Runner ghi nhận `prepare-tiktok failed to focus TikTok after launch`.
- Watchdog `feed_session_watchdog.py` dùng bộ lọc phân loại lỗi chuỗi: do lỗi không chứa cụm từ *"device not found"*, watchdog tự động fallback xếp 10 máy (M8, M12, M17, M18, M23, M31, M33, M53, M55, M62) vào danh mục **"Lỗi mở/focus App TikTok"**.
- Trích xuất O(1) qua `inspect_machine.py <N>` chứng minh: Các máy này thực chất bị `adb.EXE: device '<serial>' not found`, 100% không có app TikTok nào bị lỗi.

## 3. Quy Trình Đối Soát & Phục Hồi Nhanh O(1)

1. **Kiểm tra Uptime & Lịch sử Reboot:**
   ```python
   import psutil, datetime
   bt = psutil.boot_time()
   print("Boot time:", datetime.datetime.fromtimestamp(bt))
   ```
   Đọc `C:\Taadaa_Service\daily_reset.log` kiểm tra xem mốc 11:20 hoặc 17:20 bị `[SKIP]` hay `[ABORT]` do game/active lock.

2. **Kiểm tra Xung Đột Cổng 5038 (XiaoWei):**
   ```python
   import psutil
   listeners = [c for c in psutil.net_connections(kind='tcp') if c.laddr.port in (5037, 5038) and c.status == 'LISTEN']
   for c in listeners:
       print(f"Port {c.laddr.port} owned by PID {c.pid} ({psutil.Process(c.pid).name()})")
   ```

3. **Cứu Hộ Phẫu Thuật O(1) Không Cần Reboot:**
   - Nếu phát hiện ADB 5038 đang chạy:
     `taskkill /F /PID <pid_5038>` hoặc `adb -P 5038 kill-server`.
   - Toàn bộ thiết bị bị giam giữ sẽ tự động quay về port 5037 nguyên vẹn sau 1 giây.
