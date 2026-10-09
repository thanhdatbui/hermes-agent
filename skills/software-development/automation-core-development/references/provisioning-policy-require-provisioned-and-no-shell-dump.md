# Triệt Tiêu Shell UiAutomator Dump trong Automation Core (Provisioning Policy Invariant)

## 1. Bản Chất Vấn Đề
- Trên thiết bị Samsung Galaxy S7 (Android 7/8), việc gọi `adb shell uiautomator dump` sẽ dẫn đến lỗi kernel OOM-kill (`EXIT=137`), làm kẹt tiến trình `com.github.uiautomator` (chạy dưới `u0_a200`), chiếm dụng `UiAutomationService` và khiến toàn bộ các lệnh đọc giao diện tiếp theo (kể cả qua `atx-agent`) bị timeout.
- User Invariant: **100% farm Android chuyển sang dùng `atx-agent` (port 7912)**, cấm tuyệt đối uiautomator dump.
- Trong `automation-core/src/automation_core/ui.py`, tham số mặc định trước đây là `provisioning_policy = ProvisioningPolicy.ALLOW_LEGACY_SHELL_ONLY`. Khi ATX Agent gặp lỗi tạm thời (ví dụ XML rỗng), code ngầm nhảy vào vòng lặp fallback `try_shell()` -> gọi `adb shell uiautomator dump`.

## 2. Bản Vá Bắt Buộc (Invariant)
1. **Ép cứng Policy mặc định**:
   - `_dump_current_ui_unlocked(..., provisioning_policy=ProvisioningPolicy.REQUIRE_PROVISIONED)`
   - `dump_current_ui()`: `kwargs.setdefault("provisioning_policy", ProvisioningPolicy.REQUIRE_PROVISIONED)`
   - `capture_ui_xml()`: `kwargs.setdefault("provisioning_policy", ProvisioningPolicy.REQUIRE_PROVISIONED)`
2. **Hard Guard trong `try_shell()`**:
   ```python
   def try_shell(attempt_number: int, mode: str, *, recovery: str = "",
                 meaningful_recovery: bool = False) -> str | None:
       if policy == ProvisioningPolicy.REQUIRE_PROVISIONED:
           entry = {"backend": "shell", "attempt": attempt_number, "mode": mode,
                    "recovery": recovery, "failure_signature": "SHELL_DISABLED_BY_POLICY",
                    "suppressed": True}
           attempts.append(entry)
           journal.add("BACKEND_SUPPRESSED", **entry)
           return None
   ```
3. **Cách dọn tiến trình kẹt uiautomator**:
   Khi bị kẹt process zombie `com.github.uiautomator`, `pkill` sẽ bị `Operation not permitted`.
   Bắt buộc force-stop bằng Activity Manager:
   `adb -s <serial> shell "am force-stop com.github.uiautomator && am force-stop com.github.uiautomator.test"`
