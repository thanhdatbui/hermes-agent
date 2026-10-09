# Chống Rò Rỉ Sáng Màn Hình (screen_off_timeout = 2147483647) & Treo App TikTok Cụm Admin (Remote ADB)

## 1. Hiện Tượng Thực Tế (Phát hiện 2026-09-24)
- **Hiện tượng 1:** Toàn bộ dàn máy Admin (201-280) mở sáng màn hình liên tục, không tự tắt sau 10 phút như thiết kế của farm.
- **Hiện tượng 2:** Một số máy (ví dụ Máy 220) bị treo app TikTok trên màn hình hàng loạt từ ca trước sang ca sau, không tự force-stop và không về HOME.

---

## 2. Root Cause Kỹ Thuật

### Nguy Nhân 1: `atx-agent` & `uiautomator` test APK tự động gán `screen_off_timeout = 2147483647` (24.85 ngày)
1. **Cơ chế APK:** Khi bất kỳ flow nào kích hoạt dump XML UI qua endpoint `/uiautomator` hoặc khi hàm `reset_atx_agent` khởi động lại stub, mã Java bên trong APK test tự động thực thi:
   `Settings.System.putInt(getContentResolver(), Settings.System.SCREEN_OFF_TIMEOUT, Integer.MAX_VALUE)` (tức `2147483647` ms ~ 25 ngày) để chống tắt màn hình làm đứt phiên automation.
2. **Lỗ hổng vòng đời session (`multi_machine_feed_session.py`):**
   - Hàm `configure_device_screen_stay_on` (đặt về 10 phút `600000`) chỉ được gọi tại thời điểm **preflight** lúc chuẩn bị thiết bị (`device_prepare.py`).
   - Trong quá trình phiên chạy, `atx-agent` / `uiautomator` đã âm thầm ghi đè lại thành `2147483647`.
   - Tại khối `finally: teardown` của session, code **KHÔNG CÓ BƯỚC KHÔI PHỤC LẠI TIMEOUT**.
   - Hậu quả: Sau khi cày xong phiên, máy bị bỏ mặc với `screen_off_timeout = 2147483647`, Android lên lịch 24 ngày sau mới tắt màn hình (`Message 0: { when=+24d... what=1 }`), khiến màn hình sáng xuyên ngày đêm.

### Nguyên Nhân 2: Teardown `_force_stop_tiktok_and_home` thiếu Remote Host trên cụm Admin (201+)
1. **Nghẽn Remote ADB Server:** Runner Kibe chạy `--max-workers 40`, bắn đồng thời hàng loạt lệnh sang Remote ADB `192.168.110.119:5037`. Khi có độ trễ mạng hoặc tải cao, một số máy bị timeout lệnh ADB.
2. **Lỗi Fallback subprocess thiếu `-H`:**
   - Trong `_force_stop_tiktok_and_home` (`multi_machine_feed_session.py`), nhánh 1 dùng `child_ctx.adb`. Nếu lệnh này timeout hoặc `child_ctx` lỗi, nhánh 2 fallback sang:
     ```python
     subprocess.run([resolved_adb, "-s", serial, "shell", "am", "force-stop", target_package], timeout=15)
     ```
   - Đoạn này **thiếu hoàn toàn tham số `-H 192.168.110.119 -P 5037`** khi thao tác với máy Admin (`machine >= 200`)! Nó gọi ADB cục bộ trên Kibe tìm serial Admin -> báo `device not found`, rơi vào `except: pass` im lặng.
   - Hậu quả: App TikTok vẫn treo nguyên vẹn trên màn hình.
3. **Cơ chế Skip Row không dọn thiết bị:**
   - Các phiên chạy tiếp theo (ví dụ Row 4 lúc 14h, Row 6 lúc 18h) nếu máy không có tài khoản (empty account) thì runner ghi nhận `"account row is empty... skipping"` và bỏ qua ngay từ đầu.
   - Không có tiến trình nào dọn dẹp máy, khiến app TikTok bị treo suốt nhiều ca làm việc.

---

## 3. Invariants Bắt Buộc Khi Thiết Kế & Sửa Code

### Quy Tắc 1: Bắt Buộc Re-apply Screen Timeout 10 Phút Tại TEARDOWN
Trong mọi runner / worker kết thúc phiên (kể cả thành công, thất bại hay timeout), khối `finally:` bắt buộc phải gọi khôi phục:
```python
# Teardown: Restore standard 10-minute screen timeout & disable stay-on
try:
    if child_ctx is not None and hasattr(child_ctx, "adb"):
        child_ctx.adb.shell(["settings", "put", "system", "screen_off_timeout", "600000"], timeout=10)
        child_ctx.adb.shell(["settings", "put", "global", "stay_on_while_plugged_in", "0"], timeout=10)
        child_ctx.adb.shell(["svc", "power", "stayon", "false"], timeout=10)
except Exception:
    pass
```

### Quy Tắc 2: Fallback ADB Bắt Buộc Giữ Remote Host/Port
Khi gọi subprocess ADB fallback cho các hàm teardown / force-stop:
```python
cmd = [resolved_adb]
# Phải xác định nếu là cụm Admin hoặc ctx có adb_server_socket / host:
if getattr(adb_client, "host", None):
    cmd.extend(["-H", adb_client.host, "-P", str(getattr(adb_client, "port", 5037) or 5037)])
elif machine >= 200 or serial in admin_serials:
    cmd.extend(["-H", "192.168.110.119", "-P", "5037"])
cmd.extend(["-s", serial, "shell", "am", "force-stop", target_package])
```

### Quy Tắc 3: Lệnh Khôi Phục Nhanh Khi Phát Hiện Màn Sáng Hàng Loạt
Khi phát hiện cụm Admin bị ghim sáng màn hình hoặc treo app TikTok, dùng lệnh đồng loạt qua PowerShell / Bash:
```powershell
# Set lại 10 phút và force-stop TikTok cho toàn bộ cụm Admin
$adb = 'C:\Program Files (x86)\xiaowei\tools\adb.exe'
$devices = & $adb -H 192.168.110.119 devices | Select-String "`tdevice" | ForEach-Object { ($_ -split "`t")[0] }
foreach ($dev in $devices) {
    & $adb -H 192.168.110.119 -s $dev shell settings put system screen_off_timeout 600000
    & $adb -H 192.168.110.119 -s $dev shell settings put global stay_on_while_plugged_in 0
    & $adb -H 192.168.110.119 -s $dev shell svc power stayon false
    & $adb -H 192.168.110.119 -s $dev shell am force-stop com.ss.android.ugc.trill
    & $adb -H 192.168.110.119 -s $dev shell input keyevent 3
}
```
