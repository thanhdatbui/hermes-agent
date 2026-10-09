# NGUYÊN NHÂN & QUY TẮC BẢO VỆ: MÀN HÌNH KHÔNG TẮT & APP TREO KHÔNG FORCE-STOP

## 1. HIỆN TƯỢNG PHÁT SINH
- Hàng loạt máy cụm Kibe (1–80) và toàn bộ máy cụm Admin (201–280) bị sáng màn hình liên tục không tự tắt sau 10 phút nhàn rỗi.
- Một số máy (như Máy 220) bị treo app TikTok trên màn hình, không tự động đóng app và về màn hình chính HOME sau khi kết thúc phiên hoặc khi phiên gặp lỗi.

---

## 2. NGUYÊN NHÂN GỐC RỄ (ROOT CAUSE)

### A. Vấn đề màn hình không tự tắt sau 10 phút:
1. **Thủ phạm ghi đè `2147483647`:**
   - Trong quá trình chạy session nuôi feed/follow/upload hoặc auto-login, khi UI bị giật lag, runner kích hoạt `dump_ui_xml`, `capture_persistent_ui` hoặc `reset_atx_agent`.
   - Stub test APK `com.github.uiautomator` được khởi chạy bởi `atx-agent` có mã nội bộ tự động thực thi:
     `Settings.System.putInt(..., SCREEN_OFF_TIMEOUT, Integer.MAX_VALUE)` (tức **`2147483647` ms = 24.85 ngày**).
2. **Lỗ hổng cấu trúc trong Teardown:**
   - Cấu hình chuẩn 10 phút (`configure_device_screen_stay_on`, `screen_off_timeout = 600000`) chỉ được gọi **1 lần duy nhất ở preflight đầu phiên** (`device_prepare.py`).
   - Trong khối `finally: teardown` khi kết thúc phiên (`multi_machine_feed_session.py`), code **KHÔNG có bước set trả `screen_off_timeout = 600000`**.
   - Bất kỳ máy nào từng kích hoạt uiautomator trong ngày đều bị ghim giá trị 25 ngày vĩnh viễn, khiến màn hình thức liên tục làm nóng máy, chai pin và lưu ảnh màn hình (burn-in).

### B. Vấn đề app TikTok bị treo không tự đóng:
1. **Thiếu Remote Host trong ADB Fallback:**
   - Hàm `_force_stop_tiktok_and_home` khi fallback sang `subprocess.run` chỉ gọi:
     `subprocess.run([resolved_adb, "-s", serial, "shell", "am", "force-stop", target_package])`
     mà **hoàn toàn thiếu tham số `-H 192.168.110.119 -P 5037`** cho các máy Admin (`machine >= 200`).
   - Lệnh ADB từ máy Kibe tìm serial Admin trong ADB daemon cục bộ -> báo `device not found`, app không hề bị tắt.
2. **Nghẽn cổ chai Remote ADB Server:**
   - Chạy 40 workers đồng thời sang Remote ADB Server `192.168.110.119:5037` gây nghẽn socket/timeout. Lệnh `am force-stop` và `input keyevent 187` bị timeout 15s.
   - Khối `try...except: pass` nuốt ngoại lệ im lặng, bỏ mặc thiết bị ở trạng thái treo.
3. **Các ca sau bỏ qua không dọn dẹp:**
   - Nếu ca sau (Row 4, Row 6) máy không có tài khoản trong file Excel (`taikhoan_run_safe.xlsx`), runner bỏ qua máy (`account empty, skipping`) và không thực hiện bất kỳ thao tác cleanup nào.

---

## 3. INVARIANT BẮT BUỘC: TEARDOWN RESTORE CHO MỌI REPO RUNNER

Mọi luồng automation can thiệp thiết bị (Feed session, Follow, Upload, Reg, Login, Avatar) BẮT BUỘC tuân thủ:

### Invariant 1: Khối Teardown bắt buộc khôi phục Screen Timeout 10 phút
Trong khối `finally:` của mọi runner (sau khi đã chụp xong ảnh nghiệm thu):
```python
# 1. Force-stop app & về HOME
_force_stop_tiktok_and_home(child_ctx, serial=account.serial, machine=account.machine)

# 2. Khôi phục chuẩn timeout 10 phút cho màn hình
restore_cmds = [
    ["settings", "put", "system", "screen_off_timeout", "600000"],
    ["settings", "put", "global", "stay_on_while_plugged_in", "0"],
    ["svc", "power", "stayon", "false"],
]
for cmd in restore_cmds:
    try:
        child_ctx.adb.shell(cmd, timeout=10)
    except Exception:
        pass
```

### Invariant 2: ADB Fallback phải nhận diện Dual-Cluster Host
Mọi hàm gọi ADB trực tiếp theo serial phải tự động chèn `-H 192.168.110.119 -P 5037` nếu `machine >= 200` hoặc nếu serial thuộc cluster Admin:
```python
def get_adb_cmd_for_machine(machine: int, serial: str) -> list[str]:
    cmd = [ADB_BIN]
    if machine >= 200:
        cmd.extend(["-H", "192.168.110.119", "-P", "5037"])
    cmd.extend(["-s", serial])
    return cmd
```

### Invariant 3: Chống nuốt lỗi Teardown & Có Watchdog dọn app rác
- Không được để `except Exception: pass` nuốt chửng lỗi teardown mà không có retry tối thiểu 1 lần với timeout ngắn.
- Duy trì script watchdog định kỳ quét các máy rảnh (idle, không giữ device lock), nếu phát hiện foreground package là TikTok hoặc app bên thứ ba thì tự động gửi `am force-stop` và `input keyevent 3`.
