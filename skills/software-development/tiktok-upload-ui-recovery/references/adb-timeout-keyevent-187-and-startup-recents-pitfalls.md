# Pitfalls: Timeout ADB Input 187 (APP_SWITCH) & Startup Recents Verification

**Incident Date:** 2026-09-05  
**Context:** Taadaa Phone Farm / `Tiktok-video` (`scripts/tiktok_workflow/state_machine.py`)  
**Symptom:** `[FAILED] [CONNECT_DEVICE_ERROR] adb command timed out: ('C:\\Program Files (x86)\\xiaowei\\tools\\adb.exe', '-s', '<serial>', 'shell', 'input', '<redacted>', '187')` trên Máy 80 (`ce061606cd45950405`).

---

## 1. Bản chất Pitfall: `AdbClient.shell(..., check=False)` KHÔNG chặn Transport Timeout

Trong `automation_core.adb.AdbClient`:
```python
# AdbClient.run:
completed = self._execute(args, timeout=timeout, include_serial=include_serial, text=True)
result = AdbResult(...)
if check and not result.ok:
    raise ADBError(...)
return result
```
Bên trong `_execute`:
```python
except subprocess.TimeoutExpired as exc:
    # Sau các lượt retry và opt-in reboot recovery:
    raise ADBError(f"adb command timed out: {self.safe_args(command)}") from exc
```

- Cờ `check=False` **chỉ** ngăn việc throw khi process trả về non-zero exit code (`returncode != 0`).
- Khi command bị timeout (`subprocess.TimeoutExpired`), `AdbClient` **LUÔN NÉM `ADBError`**.
- **Sai lầm phổ biến:** Nghĩ rằng `recent = adb.shell(["input", "keyevent", "187"], timeout=10, check=False)` an toàn không bao giờ throw. Khi ADB daemon bị nghẽn hoặc máy phản hồi chậm, `ADBError` bung ra ngoài làm sập luồng gọi.

### Quy tắc bất biến (Invariant):
Mọi lệnh ADB mang tính chất kiểm tra bổ trợ / fallback / dọn dẹp trong consumer PHẢI được bọc `try...except Exception`:
```python
try:
    recent = adb.shell(["input", "keyevent", "187"], timeout=10, check=False)
    if not getattr(recent, "ok", False):
        return False
except Exception as exc:
    logger.warning("[VERIFY_RECENTS] input 187 / shell failed: %s", exc)
    return False
```

---

## 2. Uncaught Exception làm nhảy cóc (Bypass) Recovery Ladder 3 Bước

Trong `state_machine.py` hàm `_handle_connect_device()`:
```python
startup = prepare_android_for_automation(self.context.adb_client, timeout=60, recovery_package=None)
if not startup.ok:
    if self._verify_localized_empty_recents(self.context.adb_client):
        logger.warning("[ANDROID_STARTUP] Core chưa nhận empty Recent Samsung; xác nhận hợp lệ tại consumer")
    else:
        # ---- B1: ATX-kill (uiautomator recovery) ----
        ...
        # ---- B2: relaunch (retry prepare) ----
        ...
        # ---- B3: soft reboot ----
        ...
```

- Khi `_verify_localized_empty_recents()` ném `ADBError` không được bắt, `_handle_connect_device()` bị crash ngay lập tức.
- **Hậu quả:** Toàn bộ ladder 3 bước (B1 ATX-kill $\rightarrow$ B2 relaunch $\rightarrow$ B3 soft reboot) bị bỏ qua hoàn toàn. State machine kết luận job thất bại sớm mà không kịp phục hồi.
- **Quy tắc:** Các hàm helper / verify khi startup fail BẮT BUỘC phải fail-safe (trả về `False` khi lỗi), để code tự nhiên trôi xuống ladder B1 $\rightarrow$ B2 $\rightarrow$ B3.

---

## 3. Không kiểm tra Recent Apps khi lỗi bắt nguồn từ Wake/Unlock

Quy trình `prepare_android_for_automation()` chạy tuần tự:
1. `_wake_and_unlock()` (mở màn hình, kiểm tra power)
2. `lock_portrait_rotation()` (khóa xoay dọc)
3. `close_all_recent_apps()` (đóng app gần đây)

Khi máy bị trễ ADB power dumpsys (`wake_unlock_read_state: manual-needed`):
- Bước 3 (`close_all_recent_apps`) **chưa từng được chạy**.
- Việc gọi `_verify_localized_empty_recents()` (bấm phím 187 APP_SWITCH và dump UI) lên máy chưa qua được bước mở khóa là sai logic, vừa gây nhiễu UI vừa dễ dính timeout lặp lại.

### Pattern chuẩn cho Consumer:
```python
if not startup.ok:
    # Chỉ xác nhận Recent Samsung nếu lỗi THỰC SỰ chỉ nằm ở bước close_recent_apps
    recents_failed_only = (
        any(s.name == "close_recent_apps" and s.result == "failed" for s in startup.steps)
        and all(s.result == "success" for s in startup.steps if s.name != "close_recent_apps")
    )
    if recents_failed_only and (
        self._recents_empty_via_dumpsys(self.context.adb_client)
        or self._verify_localized_empty_recents(self.context.adb_client)
    ):
        logger.warning("[ANDROID_STARTUP] Core chưa nhận empty Recent Samsung; xác nhận hợp lệ tại consumer")
    else:
        # Thực hiện đủ B1 ATX-kill -> B2 relaunch -> B3 soft reboot
```
Ưu tiên `_recents_empty_via_dumpsys()` trước `_verify_localized_empty_recents()`: Dumpsys nhanh, nhẹ và không làm thay đổi trạng thái giao diện điện thoại.
