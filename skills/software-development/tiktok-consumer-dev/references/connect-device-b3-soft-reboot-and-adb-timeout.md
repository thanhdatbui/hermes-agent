# B3 Soft Reboot tại CONNECT_DEVICE & Phân loại ADB Timeout (state_machine.py)

## 1. B3 Soft Reboot bị chặn do thiếu adapter tại CONNECT_DEVICE
- **Hiện tượng**: Tại state `CONNECT_DEVICE`, khi startup prepare gặp lỗi UI/dump (dù đã chạy qua B1 ATX-kill và B2 relaunch retry), B3 soft reboot (`_maybe_soft_reboot_recovery()`) vẫn không bao giờ được kích hoạt, máy bị đẩy thẳng ra `MANUAL_REVIEW`.
- **Root Cause**: `_soft_reboot_recovery_allowed(self, error_code)` kiểm tra:
  ```python
  if not self.context.adapter or not self.context.adb_client:
      return False
  ```
  Nhưng ở `CONNECT_DEVICE`, `self.context.adapter` chưa được khởi tạo (chỉ gán sau khi startup thành công). Dù `WorkflowState.CONNECT_DEVICE` nằm trong `SOFT_REBOOT_RECOVERABLE_STATES`, điều kiện trên luôn trả về `False`.
- **Giải pháp chuẩn**:
  - Tại `_soft_reboot_recovery_allowed`: Với state `CONNECT_DEVICE`, chỉ yêu cầu `self.context.adb_client` (không bắt buộc `self.context.adapter`).
  - Trong `_maybe_soft_reboot_recovery`: Nếu `self.context.adapter` chưa có nhưng `self.context.adb_client` sẵn sàng, lazy initialize:
    ```python
    if not self.context.adapter and self.context.adb_client:
        self.context.adapter = TikTokAdapter(
            adb_client=self.context.adb_client,
            dry_run=self.context.dry_run,
            screenshot_fn=self._capture_profile_grid_screenshot,
        )
    ```
    Nhờ đó các hàm hậu kiểm (`_soft_reboot_recovery`, `_package_is_foreground`, `_wait_for_feed`) có đầy đủ adapter để thực thi.

## 2. Phân loại Transient ADB Timeout vs DEVICE_STARTUP_MANUAL
- **Hiện tượng**: Khi `prepare_android_for_automation` fail do ADB command timeout (`"timed out"` trong `startup.stop_reason`), automation-core có thể gán cờ `startup.manual_needed = True`.
- **Hậu quả**: State machine gán code `DEVICE_STARTUP_MANUAL` (mã lỗi vĩnh viễn cần can thiệp tay), làm hỏng luồng tự hồi phục.
- **Giải pháp chuẩn**:
  ```python
  is_timeout = "timed out" in str(startup.stop_reason or "").lower()
  code = "DEVICE_STARTUP_FAILED" if is_timeout else (
      "DEVICE_STARTUP_MANUAL" if startup.manual_needed else "DEVICE_STARTUP_FAILED"
  )
  ```
  Khi gặp ADB timeout, coi là transient failure (`DEVICE_STARTUP_FAILED`) để recovery ladder (B1 ATX-kill -> B2 retry -> B3 soft reboot) có thể tự giải phóng máy.

## 3. Unit Test Fixture Pitfall (`_handle_connect_device`)
- **Bẫy `DEVICE_OFFLINE`**: `_handle_connect_device` kiểm tra device presence ở đầu hàm:
  ```python
  device_id = self.context.config.get("device_id", "")
  devices = self.context.adb_client.list_devices()
  if device_id not in devices:
      raise WorkflowError(WorkflowState.CONNECT_DEVICE, f"Device {device_id} không online...", "DEVICE_OFFLINE")
  ```
  Nếu fixture không set `config["device_id"]` hoặc `adb_client.list_devices()` không trả về `device_id` đó, test sẽ crash với `DEVICE_OFFLINE` trước khi chạm tới `prepare_android_for_automation` hay ladder B3.
- **Fixture chuẩn khi viết test cho `_handle_connect_device`**:
  ```python
  class FakeAdb:
      serial = "emulator-5554"
      def list_devices(self):
          return ["emulator-5554"]
  ...
  context = StateContext(
      config={"device_id": "emulator-5554", ...},
      adb_client=FakeAdb(),
      ...
  )
  ```

