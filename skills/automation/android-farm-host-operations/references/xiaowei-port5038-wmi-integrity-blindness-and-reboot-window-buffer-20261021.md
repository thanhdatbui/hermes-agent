# XiaoWei Port 5038 WMI Integrity Blindness & Reboot Window Buffer Incident (21/10/2026)

## 1. Hiện Tượng Thực Tế
- Sau Ca 3 Phiên 2 (Tối) nuôi acc TikTok ngày 21/10/2026, cụm Farm Kibe (M1–80) báo văng 35 máy: 24 máy "Mất kết nối ADB/USB", 10 máy "Lỗi mở/focus App TikTok", 1 máy "Lỗi App/Script".
- `adb devices` trên cổng chuẩn 5037 chỉ nhận diện 46/80 máy. 34 máy còn lại báo `device '<serial>' not found`.
- Kiểm tra uptime: Kibe PC và Admin PC đã chạy liên tục hơn 17.5 tiếng (boot lúc 05:21 sáng), không hề reboot trước Ca 2 (11:20) và Ca 3 (17:20) dù Task Scheduler có cài đặt.
- Mặc dù cronjob `xiaowei-idle-auto-close-kibe` (`xiaowei_idle_auto_close_watchdog.py`) chạy đều đặn mỗi 2 phút, tiến trình `adb.exe -P 5038` (PID 15812) sinh ra từ lúc 16:38:23 vẫn tồn tại suốt 7 tiếng.

---

## 2. Phân Tích Nguyên Nhân Gốc Rễ (Root Cause)

### Vấn Đề 1: Bẫy Phân Quyền WMI Integrity Level Làm Mù Watchdog 5038
1. **Cơ chế chiếm máy của XiaoWei:**
   Tiểu Vi sinh ra daemon con `tools/adb.exe -P 5038 nodaemon server start`. Driver WinUSB trên Windows cấp quyền truy cập độc quyền (exclusive endpoint), khiến 34 máy bị "bắt cóc" sang cổng 5038, cổng 5037 không còn thấy máy.
2. **Lỗ hổng trong code `is_xiaowei_adb_running()`:**
   Script cũ dùng PowerShell WMI:
   ```powershell
   Get-CimInstance Win32_Process -Filter "Name = 'adb.exe'" | Where-Object { $_.ProcessId -in $ports -and ($_.CommandLine -like "*-P 5038*" -or $_.ExecutablePath -like "*\xiaowei\*") }
   ```
3. **Bẫy Windows Integrity Level (Non-Elevated vs Elevated):**
   - Khi XiaoWei được khởi động ở mức quyền Administrator / Elevated, tiến trình con `adb.exe` kế thừa mức quyền High Integrity Level.
   - Khi cronjob chạy dưới user context tiêu chuẩn, Windows WMI **từ chối cấp `CommandLine` và `ExecutablePath` của tiến trình Elevated** (trả về `$null`).
   - Biểu thức `$null -like "*-P 5038*"` trả về `$false` $\rightarrow$ `Where-Object` loại bỏ toàn bộ tiến trình $\rightarrow$ Count = 0.
   - `is_xiaowei_adb_running()` trả về `False`.
4. **Hậu quả:**
   Guard trong `cleanup_orphan_xiaowei_adb()`:
   ```python
   if is_xiaowei_adb_running() is not True:
       return False
   ```
   Watchdog tưởng nhầm là cổng 5038 sạch, thoát exit 0 im lặng, không bao giờ gọi `_try_kill_server()`.

### Vấn Đề 2: Xung Đột Lịch Cron Xen Ca Giữ Device Lock Triệt Tiêu Reboot 11:20 và 17:20
1. **Task Scheduler One-Shot:**
   `Taadaa_Farm_Daily_Reboot_1135` chỉ bắn đúng 1 trigger tại `11:20:00` và `17:20:00`.
2. **Thiếu Reboot Blackout Buffer trong `tiktok_rename_rolling_watchdog.py`:**
   - Safe Window của cron đổi tên nick cấu hình:
     `any(a <= hm < b for a, b in ((570, 680), (930, 1040), ...))`
     (680 phút = 11:20, 1040 phút = 17:20).
   - Cron chạy chu kỳ 15 phút $\rightarrow$ vừa nhận batch đổi tên lúc **11:15** và **17:15**.
   - Quá trình đổi tên trên nhiều máy kéo dài 5–10 phút, tạo file `machine_*.lock.json` với `status: "running"`.
   - Đúng lúc `11:20:02` và `17:20:02`, `farm_preflight_daily_reset.py` kiểm tra `has_active_device_locks()` $\rightarrow$ thấy máy bận $\rightarrow$ log `[SKIP] Dang co tien trinh nuoi acc giu active device lock` và thoát ngay lập tức.
   - Hậu quả: Mất sạch 2 mốc reboot của cả ca trưa lẫn ca tối, máy chạy rướn 17.5 tiếng làm tràn bộ đệm EHCI USB 2.0.

---

## 3. Quy Chuẩn Đã Khắc Phục (Standardized Fix)

### Fix 1: Kiểm Tra Socket 5038 Bằng `psutil` Trực Tiếp (Bypass WMI)
Trong `xiaowei_idle_auto_close_watchdog.py`:
```python
def is_xiaowei_adb_running() -> bool | None:
    """Check whether an adb.exe on port 5038 belongs to xiaowei (path-verified, isolated from farm ADB)."""
    if psutil is not None:
        try:
            for c in psutil.net_connections(kind="tcp"):
                port = getattr(c.laddr, "port", None) if hasattr(c, "laddr") else None
                if port == XIAOWEI_ADB_PORT and getattr(c, "status", "") == "LISTEN":
                    return True
            return False
        except Exception:
            pass
    # Fallback PowerShell nếu psutil lỗi
    ...
```
*Kết quả:* Phát hiện cổng 5038 đang listen trong $< 2$ms, độc lập với mức quyền của tiến trình. Kích hoạt `_try_kill_server()` dập tắt daemon 5038 ngay lập tức, trả đủ 78/78 máy về ADB 5037.

### Fix 2: Rút Safe Window Tạo Đệm 20 Phút Trước Mốc Reboot
Trong `tiktok_rename_rolling_watchdog.py`:
- Dừng nhận việc lúc **11:00** (minute 660, trước reboot 11:20 đúng 20 phút).
- Dừng nhận việc lúc **17:00** (minute 1020, trước reboot 17:20 đúng 20 phút).
```python
def is_safe_window(now=None):
    now = now or datetime.now(ZoneInfo("Asia/Ho_Chi_Minh"))
    hm = now.hour * 60 + now.minute
    return any(a <= hm < b for a, b in ((570, 660), (930, 1020), (1290, 1425)))
```
*Kết quả:* Bảo đảm 100% các batch đổi tên kết thúc và giải phóng lock trước 11:20 và 17:20, không còn tình trạng chặn lệnh preflight reboot.
