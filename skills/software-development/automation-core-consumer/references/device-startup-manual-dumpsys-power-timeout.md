# DEVICE_STARTUP_MANUAL: Dumpsys Power Timeout & Soft Reboot Ladder Block at CONNECT_DEVICE

## 1. Hiện tượng & Triệu chứng thực tế
- Khi chạy workflow (ví dụ: TikTok video upload trên máy Samsung, cụ thể máy 71 `ce12160c204c390105`), run dừng tại trạng thái `CONNECT_DEVICE` với mã lỗi:
  ```json
  {
    "status": "MANUAL_REVIEW",
    "reason": "[DEVICE_STARTUP_MANUAL] adb command timed out: ('C:\\Program Files (x86)\\xiaowei\\tools\\adb.exe', '-s', 'ce12160c204c390105', 'shell', 'dumpsys', 'power')"
  }
  ```
- Màn hình máy thực tế không bị khóa mật khẩu (không có PIN hay secure keyguard), nhưng workflow vẫn báo `MANUAL_REVIEW` và dừng lại mà không thực hiện soft reboot recovery.

---

## 2. Phân tích Root Cause 2 tầng

### Tầng 1: Nhận nhầm lỗi Timeout ADB thành `manual_needed` trong `automation-core`
- Trong `automation_core.startup` (`_wake_and_unlock`):
  ```python
  state = _read_wake_unlock_state(adb, timeout=timeout)
  if state.error or state.screen_on is None:
      reason = state.error or "screen power state unknown"
      steps.append(_state_step("wake_unlock_read_state", state, "manual-needed", reason))
      return StartupResult(False, True, tuple(steps), reason)
  ```
- Khi lệnh `adb shell dumpsys power` bị timeout hoặc delay truyền thông tạm thời, `_read_wake_unlock_state` trả về `WakeUnlockState` mang `error="adb command timed out: ..."`.
- `_wake_and_unlock` lập tức gắn nhãn bước này là `manual-needed` và trả về `StartupResult(ok=False, manual_needed=True, ...)`.
- Consumer (`state_machine.py`) căn cứ vào cờ `startup.manual_needed` để map error code:
  ```python
  code = "DEVICE_STARTUP_MANUAL" if startup.manual_needed else "DEVICE_STARTUP_FAILED"
  ```
- **Hậu quả:** Lỗi mạng/transport ADB tạm thời bị coi nhầm là màn hình khóa bảo mật cần can thiệp tay, kích hoạt luồng cảnh báo sai bản chất.

---

### Tầng 2: Vô hiệu hóa B3 Soft Reboot tại `CONNECT_DEVICE` do `adapter` chưa khởi tạo
- Theo quy tắc vận hành (PROJECT_RULES 3-step ladder), khi gặp lỗi chuẩn bị thiết bị hoặc UI dump fail, workflow phải thử đủ 3 bước:
  - B1: ATX-kill (`_recover_uiautomator`)
  - B2: Relaunch / Re-prepare (`prepare_android_for_automation`)
  - B3: Soft reboot có bằng chứng (`_maybe_soft_reboot_recovery`)
- Tuy nhiên, trong `state_machine.py`:
  ```python
  def _soft_reboot_recovery_allowed(self, error_code: str) -> bool:
      state = self.current_state
      if state not in self.SOFT_REBOOT_RECOVERABLE_STATES:
          return False
      if not self.context.adapter or not self.context.adb_client:
          return False
      ...
  ```
- Tại trạng thái `CONNECT_DEVICE`, `self.context.adapter` (`TikTokAdapter`) **chỉ được tạo SAU KHI** `startup.ok` thành công:
  ```python
  startup = prepare_android_for_automation(...)
  if not startup.ok:
      # B1, B2 ...
      if self._maybe_soft_reboot_recovery():  # <-- Tại đây adapter vẫn là None!
          ...
      return False
  self.context.adapter = TikTokAdapter(...)
  ```
- **Hậu quả:** Do `self.context.adapter is None`, hàm `_soft_reboot_recovery_allowed()` luôn trả về `False` ngay lập tức. Bước B3 bị chặn đứng, workflow không bao giờ reboot thiết bị để tự phục hồi mà bị đẩy thẳng sang `MANUAL_REVIEW`.

---

## 3. Quy tắc Fix & Best Practices cho Consumer & Core

### Quy tắc 1: Bảo đảm điều kiện cho B3 Soft Reboot tại `CONNECT_DEVICE`
- Trong `_soft_reboot_recovery_allowed()`:
  - Cho phép trạng thái `CONNECT_DEVICE` được chạy soft reboot nếu có `self.context.adb_client` và `self.context.device_transport` (hoặc khởi tạo sẵn `self.context.adapter` trước khi gọi `prepare_android_for_automation`).
  - Đảm bảo các hàm recovery sau reboot không phụ thuộc vào các thuộc tính chỉ có sau khi login/app ready.

### Quy tắc 2: Phân tách Transient ADB Timeout và Secure Keyguard
- Trong `automation_core.startup` hoặc wrapper tại Consumer:
  - Chỉ đánh dấu `manual_needed = True` khi `keyguard_secure is True` (xác thực màn hình có PIN/Pattern/Password).
  - Các lỗi do `adb command timed out` đối với `dumpsys power` hoặc `dumpsys window` phải được xếp vào nhóm `DEVICE_STARTUP_FAILED` / transient I/O error, có cơ chế retry hoặc fallback đánh thức bằng phím cứng (keyevent 224 / 82) trước khi từ bỏ.

### Quy tắc 3: Fallback Wakeup khi `dumpsys power` bị lag
- Trên các máy Samsung cũ (S7/S7 Edge Android 8), dịch vụ `dumpsys power` đôi khi bị nghẽn (binder deadlock / high CPU).
- Nếu `dumpsys power` timeout, thử gửi trực tiếp:
  1. `input keyevent 224` (Wake up)
  2. `wm dismiss-keyguard`
  3. `input keyevent 82` (Menu/Unlock)
  Sau đó kiểm tra lại bằng dump UI hoặc `dumpsys window` thay vì coi máy cần manual unlock.
