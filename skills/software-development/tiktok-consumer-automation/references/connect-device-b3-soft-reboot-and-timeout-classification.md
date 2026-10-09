# B3 Soft Reboot Recovery tại CONNECT_DEVICE & Phân loại ADB Timeout

## 1. Vấn đề Adapter chưa khởi tạo tại CONNECT_DEVICE
- Trong state machine của TikTok consumer (`Tiktok-video`), `self.context.adapter` chỉ được khởi tạo sau khi Android prepare và startup hoàn tất thành công.
- Nếu `_soft_reboot_recovery_allowed(error_code)` kiểm tra:
  ```python
  if not self.context.adapter or not self.context.adb_client:
      return False
  ```
  thì tại trạng thái `CONNECT_DEVICE`, điều kiện này luôn trả về `False`. Kết quả: B3 Soft Reboot bị chặn hoàn toàn, máy không thể tự reboot để phục hồi UI/ADB mà bị đẩy thẳng ra `MANUAL_REVIEW`.

### Giải pháp chuẩn
- Trong `_soft_reboot_recovery_allowed`:
  - Nếu `self.current_state == WorkflowState.CONNECT_DEVICE`: chỉ yêu cầu `self.context.adb_client`.
  - Các state khác: yêu cầu cả `self.context.adapter` và `self.context.adb_client`.
- Trong quy trình reboot (`_maybe_soft_reboot_recovery`): nếu `self.context.adapter` chưa có nhưng `self.context.adb_client` sẵn sàng, khởi tạo lazy `TikTokAdapter(adb_client=self.context.adb_client, ...)` để các hàm hậu kiểm (`_soft_reboot_recovery`, `_package_is_foreground`, `_wait_for_feed`) có thể thực thi bình thường.

---

## 2. Phân loại Transient ADB Timeout vs DEVICE_STARTUP_MANUAL
- Khi `prepare_android_for_automation` fail, `startup.manual_needed` có thể bị đánh dấu `True` từ automation-core ngay cả khi nguyên nhân gốc rễ chỉ là ADB command timeout (`"timed out"` trong `startup.stop_reason`).
- Nếu gán nhầm thành mã lỗi vĩnh viễn `DEVICE_STARTUP_MANUAL`, recovery ladder bị coi là lỗi thủ công và chặn ladder B3.

### Quy tắc phân loại
```python
is_timeout = "timed out" in str(startup.stop_reason or "").lower()
code = "DEVICE_STARTUP_FAILED" if is_timeout else (
    "DEVICE_STARTUP_MANUAL" if startup.manual_needed else "DEVICE_STARTUP_FAILED"
)
```
- Khi `is_timeout=True`, giữ code là `DEVICE_STARTUP_FAILED` để recovery ladder (B1 ATX-kill -> B2 prepare retry -> B3 soft reboot) được phép kích hoạt và giải phóng máy tự động.
