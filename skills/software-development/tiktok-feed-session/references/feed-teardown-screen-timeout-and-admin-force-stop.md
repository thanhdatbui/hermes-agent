# NGUYÊN NHÂN & CONTRACT KHẮC PHỤC: MÀN HÌNH KHÔNG TẮT & APP TIKTOK TREO CUỐI PHIÊN

## 1. PHÂN TÍCH HIỆN TRƯỜNG KỸ THUẬT
Trong các đợt chạy `multi_machine_feed_session` trên cả cụm Kibe (1–80) và cụm Admin (201–280):
- **Hiện tượng 1:** Nhiều máy (hoặc toàn bộ cụm Admin) giữ màn hình sáng rực (`Display Power: state=ON`, `screen_off_timeout = 2147483647`), không tự động tắt sau 10 phút nhàn rỗi dù preflight đã set 10 phút.
- **Hiện tượng 2:** Một số máy (như Máy 220) bị treo app TikTok trên màn hình, không tự động đóng app và về launcher HOME sau khi phiên dừng.

---

## 2. NGUYÊN NHÂN GỐC RỄ (ROOT CAUSES)

### A. Cơ chế `screen_off_timeout = 2147483647` (24.85 ngày):
1. **Lệnh ghi đè của Uiautomator / Atx-Agent:**
   - Khi có máy bị giật lag, miss element hoặc cần recovery, runner gọi `dump_ui_xml`, `capture_persistent_ui` hoặc `reset_atx_agent`.
   - Tiến trình test APK `com.github.uiautomator` của atx-agent khi được spawn sẽ tự động chạy lệnh Java hệ thống:
     `Settings.System.putInt(..., SCREEN_OFF_TIMEOUT, Integer.MAX_VALUE)` (tức **`2147483647`** ms).
2. **Khuyết thiếu Teardown Restore:**
   - Trong `device_prepare.py`, hàm `configure_device_screen_stay_on` (đặt 10 phút `600000`) chỉ được gọi **lúc chuẩn bị chạy ở đầu phiên**.
   - Trong khối `finally:` kết thúc phiên của `multi_machine_feed_session.py`, code **KHÔNG có bước hoàn trả `screen_off_timeout` về `600000`**.
   - Bất kỳ thiết bị nào bị kích hoạt uiautomator thì timeout bị đổi thành 25 ngày và giữ nguyên vĩnh viễn.

### B. Cơ chế App TikTok không bị kill và treo màn hình:
1. **Thiếu Remote Host trong Fallback `_force_stop_tiktok_and_home`:**
   - Tại dòng ~2086 `multi_machine_feed_session.py`:
     ```python
     subprocess.run([resolved_adb, "-s", serial, "shell", "am", "force-stop", target_package], timeout=15)
     ```
     Đoạn này gọi trực tiếp ADB cục bộ trên Kibe, **thiếu `-H 192.168.110.119 -P 5037`**. Khi gọi serial của cụm Admin (201–280), ADB cục bộ trả về lỗi `device not found`, app không bị đóng.
2. **Nghẽn cổ chai Remote ADB Server gây timeout:**
   - 40 workers đồng loạt bắn lệnh ADB qua LAN sang máy Admin (`192.168.110.119:5037`).
   - Lệnh chụp màn hình và `am force-stop` bị timeout sau 15s. Khối `try...except: pass` nuốt lỗi im lặng.
3. **Bỏ qua thiết bị ở các ca trống (Empty Row):**
   - Khi ca sau (Row 4 lúc 14h, Row 6 lúc 18h) máy không có nick trong `taikhoan_run_safe.xlsx`, runner log `account row X is empty... skipping` và không dọn dẹp app của ca trước còn treo.

---

## 3. PATCH CONTRACT CHO WORKER IMPLEMENTATION

### File cần can thiệp: `python_runner/flows/multi_machine_feed_session.py`

#### Patch 1: Sửa hàm `_force_stop_tiktok_and_home` nhận diện Remote Host
```python
def _force_stop_tiktok_and_home(
    child_ctx: Any | None,
    *,
    serial: str | None = None,
    machine: int | None = None,
    adb_path: str | None = None,
) -> None:
    target_package = "com.ss.android.ugc.trill"
    if child_ctx is not None and hasattr(child_ctx, "config") and isinstance(child_ctx.config, dict):
        target_package = str(child_ctx.config.get("tiktok_package", target_package))

    # 1. Via child_ctx.adb nếu khả dụng
    adb_client = getattr(child_ctx, "adb", None) if child_ctx is not None else None
    if adb_client is not None and hasattr(adb_client, "shell"):
        try:
            adb_client.shell(["am", "force-stop", target_package], timeout=15)
        except Exception:
            pass
        try:
            adb_client.shell(["input", "keyevent", "3"], timeout=10)
        except Exception:
            pass
        return

    # 2. Fallback via serial: BẮT BUỘC nhận diện cụm Admin nếu machine >= 200
    if serial:
        resolved_adb = adb_path or r"C:/Program Files (x86)/xiaowei/tools/adb.exe"
        cmd_base = [resolved_adb]
        if machine is not None and machine >= 200:
            cmd_base.extend(["-H", "192.168.110.119", "-P", "5037"])
        cmd_base.extend(["-s", serial])
        try:
            subprocess.run(cmd_base + ["shell", "am", "force-stop", target_package], timeout=15, capture_output=True)
        except Exception:
            pass
        try:
            subprocess.run(cmd_base + ["shell", "input", "keyevent", "3"], timeout=10, capture_output=True)
        except Exception:
            pass
```

#### Patch 2: Bổ sung Screen Timeout Restore vào Teardown
Trong khối `finally:` của `_run_child_process_feed_session` (quanh dòng 5018):
```python
        # Teardown 1: Force-stop TikTok và đưa máy về HOME
        try:
            _force_stop_tiktok_and_home(child_ctx, serial=account.serial, machine=account.machine)
        except Exception:
            pass

        # Teardown 2: Khôi phục chuẩn 10 phút tự tắt màn hình (chống uiautomator ép sáng 25 ngày)
        try:
            restore_cmds = (
                ["svc", "power", "stayon", "false"],
                ["settings", "put", "global", "stay_on_while_plugged_in", "0"],
                ["settings", "put", "system", "screen_off_timeout", "600000"],
            )
            adb_client = getattr(child_ctx, "adb", None) if child_ctx is not None else None
            for rcmd in restore_cmds:
                if adb_client is not None and hasattr(adb_client, "shell"):
                    adb_client.shell(rcmd, timeout=10)
                elif account.serial:
                    cmd_base = [r"C:/Program Files (x86)/xiaowei/tools/adb.exe"]
                    if account.machine >= 200:
                        cmd_base.extend(["-H", "192.168.110.119", "-P", "5037"])
                    cmd_base.extend(["-s", account.serial, "shell"] + rcmd)
                    subprocess.run(cmd_base, timeout=10, capture_output=True)
        except Exception:
            pass
```
