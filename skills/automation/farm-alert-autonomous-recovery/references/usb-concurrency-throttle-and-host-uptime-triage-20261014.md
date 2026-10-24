# USB Bus Concurrency Throttle & Host Uptime Triage Protocol (2026-10-14)

## 1. Hiện tượng & Bối cảnh
- Khi chạy batch lớn (ví dụ `tiktok-luot nuoi acc` trên cụm 80 máy), hệ thống đột ngột văng alert hàng loạt thiết bị (tỷ lệ lỗi > 50%):
  * **Cụm 1:** `device is offline or ADB/USB disconnected for <serial>: adb.exe: device '<serial>' not found` (hơn 25-30 máy).
  * **Cụm 2:** `focus-device-issue:prepare-tiktok failed to focus TikTok after launch` (khoảng 10 máy).
- Nhưng chỉ ít phút sau (hoặc sau khi kiểm tra lại), hầu hết các máy tự nhiên quay trở lại trạng thái `device` bình thường mà không cần thao tác từng máy.

---

## 2. Bản chất kỹ thuật: USB Bus Saturation & Cascade Failure
- **Phần cứng:** 80 máy cắm qua các hub USB multiplexed về chung controller EHCI (chipset Intel X99).
- **Nguyên nhân gốc rễ:**
  * Script cấu hình số luồng chạy song song quá cao (`MaxWorkers = 25`) kết hợp khoảng giãn cách khởi động quá hẹp (`MachineStartStaggerMs = 2000,8000`).
  * Khi 25 luồng đồng thời gọi `monkey launch`, `dumpsys window`, `uiautomator dump` và chụp ảnh màn hình, lưu lượng I/O và gói tin USB bị bão hòa (packet saturation).
  * Bộ điều khiển USB hub bị sụt áp / nghẽn buffer, ngắt hàng loạt cổng kết nối vật lý $\rightarrow$ hàng chục máy rơi vào `device not found`.
  * Daemon `adb.exe` bị bão socket (socket storm) dồn dập xử lý ngắt kết nối $\rightarrow$ các máy còn lại bị nghẽn hàng đợi lệnh $\rightarrow$ vượt timeout 15s sinh lỗi `failed to focus TikTok`.

---

## 3. Triage Invariant: Đối soát Host Uptime khi thiết bị tự phục hồi
- **Bẫy tư duy:** Khi thấy thiết bị tự online trở lại mà tưởng lầm "máy không reboot vẫn tự hết" $\rightarrow$ dẫn đến phán đoán sai rằng lỗi chỉ là chập chờn mạng hoặc phần mềm ảo.
- **Quy tắc bắt buộc:** Kiểm tra ngay thời điểm boot của host PC:
  ```python
  import psutil, time
  boot_time = psutil.boot_time()
  print(f"Uptime: {int((time.time() - boot_time) // 60)} phút (Booted at {time.ctime(boot_time)})")
  ```
- **Đối soát mốc thời gian:**
  * Nếu thời điểm batch kết thúc và thời điểm boot cách nhau vài phút: Khẳng định 100% PC vừa trải qua System Reboot.
  * System Bus Reset từ BIOS sau reboot đã giải phóng sạch thanh ghi EHCI USB bị kẹt, đưa toàn bộ fleet lên xanh.

---

## 4. Giải pháp điều chỉnh chuẩn hóa (Hardening Limits)
Để ngăn chặn triệt để tái diễn hiện tượng sụt hub USB trong các ca nuôi tiếp theo:
1. **Hạ trần Concurrency an toàn (`MaxWorkers`):**
   * Giảm từ `25` xuống **`16`** trong `run-feed-session.ps1`.
   * Ngưỡng 16 workers đảm bảo băng thông USB 2.0 và buffer của daemon ADB trên Windows luôn dưới 70% tải đỉnh.
2. **Nới rộng nhịp khởi động (`MachineStartStaggerMs`):**
   * Đổi từ `2000,8000` thành **`3000,10000`** (giãn cách 3s - 10s giữa các máy).
   * Áp dụng đồng bộ tại:
     * `scripts/run-feed-session.ps1`
     * `scripts/hermes_cron/tiktok_runner.py`
     * `run_74machines.bat`
3. **Cô lập máy lỗi vật lý đơn lẻ:**
   * Sau khi 78/80 máy đã lên xanh sau reboot, các máy còn lại (ví dụ M10 `988627464e374e3234`) là lỗi tiếp xúc cáp/cổng sạc vật lý riêng lẻ $\rightarrow$ cách ly để cắm lại tay, không can thiệp đồng loạt toàn farm.
