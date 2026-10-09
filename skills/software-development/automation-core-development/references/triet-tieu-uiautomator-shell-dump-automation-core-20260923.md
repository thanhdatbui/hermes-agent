# Triệt Tiêu Shell UiAutomator Dump Fallback Trong Automation-Core (2026-09-23)

## 1. Bản chất vấn đề & Câu hỏi của User
- **Câu hỏi của User**: *"Tại sao lại có uiautomator, t xoá sạch thay bằng atx agent r mà????"*
- **Sự thật hiện trường**: User đã xóa sạch các lệnh gọi `adb shell uiautomator dump` và thay bằng `atx-agent` (port 7912) trong các repo nghiệp vụ (`Tiktok_Reg`, `tiktok-luot nuoi acc`), NHƯNG khi chạy batch farm vẫn phát hiện tiến trình `com.github.uiautomator` chạy ngầm và dính lỗi `SHELL_EXIT_137` OOM-kill làm treo subprocess 600s!
- **Nguyên nhân gốc rễ**: Nằm ở thư viện control plane dùng chung `D:/Taadaa/automation-core/src/automation_core/ui.py`:
  - Tham số mặc định của hàm `_dump_current_ui_unlocked()` là `provisioning_policy = ProvisioningPolicy.ALLOW_LEGACY_SHELL_ONLY`.
  - Khi `atx-agent` gặp sự cố thoáng qua hoặc trả về XML rỗng (`ATX_SESSION_EMPTY_XML`), luồng code không dừng lại mà tự động rơi xuống vòng lặp fallback `try_shell()`:
    ```python
    for attempt in range(1, max(1, retries) + 1):
        for mode in ("normal", "compressed"):
            text = try_shell(attempt, mode)   # <-- ĐÂY LÀ CHỖ GỌI SHELL UIAUTOMATOR DUMP!
    ```
  - Trên Samsung Galaxy S7 (Android 7/8), việc chạy `adb shell uiautomator dump` trên màn hình có cấu trúc view sâu (như TikTok 47.x) làm cạn kiệt bộ nhớ và bị kernel Android kill ngay lập tức (`SHELL_EXIT_137`). Tiến trình shell treo nghẽn ADB daemon và để lại process `com.github.uiautomator` zombie.

---

## 2. Bản vá Hard-Guard Trong `automation-core/src/automation_core/ui.py`
1. **Ép cứng Policy mặc định**:
   - Trong `_dump_current_ui_unlocked()`:
     `provisioning_policy: ProvisioningPolicy | str = ProvisioningPolicy.REQUIRE_PROVISIONED`
   - Trong `dump_current_ui()`:
     `kwargs.setdefault("provisioning_policy", ProvisioningPolicy.REQUIRE_PROVISIONED)`
2. **Chặn cứng hàm `try_shell()`**:
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
       permitted = DEFAULT_CIRCUIT_BREAKER.permit(...)
   ```
3. **Quy trình dọn dẹp Zombie UiAutomator Process trên máy Farm**:
   - Nếu máy đã dính process uiautomator ngầm (`u0_a... com.github.uiautomator`), lệnh `pkill` sẽ bị `Operation not permitted`.
   - **BẮT BUỘC dùng lệnh `am force-stop`**:
     `adb -s <serial> shell "am force-stop com.github.uiautomator && am force-stop com.github.uiautomator.test"`
