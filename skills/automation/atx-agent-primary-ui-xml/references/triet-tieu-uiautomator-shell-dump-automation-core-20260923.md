# Triệt Tiêu Shell UiAutomator Dump Fallback trong Automation Core (2026-09-23)

## 1. Bản chất sự cố
- Mặc dù User đã chỉ đạo chuyển đổi 100% sang `atx-agent` (port 7912) và cấm `uiautomator dump` trên Samsung S7 (Android 7/8), batch nuôi acc / feed session (`tiktok-luot nuoi acc`) và upload video (`Tiktok-video`) vẫn phát sinh lỗi OOM-kill `SHELL_EXIT_137` và làm treo subprocess / worker timeout 600s.
- **Nguyên nhân cốt lõi**:
  Thư viện dùng chung `automation-core` (`automation_core/ui.py`) có default parameter:
  `provisioning_policy: ProvisioningPolicy | str = ProvisioningPolicy.ALLOW_LEGACY_SHELL_ONLY`
  Khi `atx-agent` dump gặp trục trặc tạm thời hoặc trả về XML rỗng (`ATX_SESSION_EMPTY_XML`), luồng code ngầm nhảy vào vòng lặp fallback `try_shell()`:
  `args = ["uiautomator", "dump"] + ...`
  Lệnh này gọi trực tiếp `adb shell uiautomator dump /sdcard/window_dump_...xml`. Trên các màn hình phân cấp sâu hoặc DOM lớn của TikTok 47.x, kernel lập tức kill tiến trình (`EXIT=137`), kẹt `com.github.uiautomator` ngầm và làm đơ toàn bộ adapter.

## 2. Giải pháp Hard-Guard (Đã áp dụng vào automation-core/src/automation_core/ui.py)
1. **Ép cứng Policy mặc định**:
   Chuyển `provisioning_policy = ProvisioningPolicy.REQUIRE_PROVISIONED` ở cả `_dump_current_ui_unlocked()` và `dump_current_ui()`.
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
       ...
   ```
3. **Dọn dẹp process uiautomator kẹt trên thiết bị**:
   Nếu thiết bị đã lỡ dính process uiautomator ngầm (u0_a200 `com.github.uiautomator`), lệnh `pkill` sẽ bị `Operation not permitted`.
   **BẮT BUỘC dùng lệnh AM**:
   `adb -s <serial> shell "am force-stop com.github.uiautomator && am force-stop com.github.uiautomator.test"`

## 3. Bản vá JSON-RPC Error & Rediscovery trong `automation_core/persistent_ui.py`
Khi gọi endpoint `/session/<pid>:com.github.uiautomator/jsonrpc/2.0`, nếu ATX agent trả về response dạng `{"jsonrpc": "2.0", "error": {"code": -32001, "message": "Session expired"}}`:
- Response này là một dictionary hợp lệ nhưng KHÔNG chứa `result` (XML).
- Nếu chỉ kiểm tra `if response is None:`, mã sẽ bỏ qua khối retry, lấy `xml = response.get("result")` là `None` rồi crash ở `verify_ui_xml`.
- **Bản vá chuẩn (Commit 47f954f)**:
  ```python
  if response is None or (isinstance(response, dict) and "error" in response):
      if isinstance(response, dict) and "error" in response:
          entry["jsonrpc_error"] = response["error"]
      if serial:
          _SESSION_PID_CACHE.pop(serial, None)
      pid = _discover_session_pid(adb, timeout, entry)
      ...
  ```
  Đồng thời trong khối retry try/except:
  ```python
  except Exception as retry_exc:
      entry["retry_fallback_trigger"] = type(retry_exc).__name__
      response = _request_via_device_curl(adb, "POST", session_path, dump_payload, timeout)
  ```
  Giúp hệ thống ghi nhận telemetry đầy đủ và tự động fallback sang `_request_via_device_curl` an toàn mà không bao giờ rơi xuống shell uiautomator.

