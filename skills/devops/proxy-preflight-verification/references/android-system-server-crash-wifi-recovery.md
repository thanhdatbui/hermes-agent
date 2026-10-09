# Android `system_server` Crash Ngầm & Cơ chế Auto Guarded Reboot (Wi-Fi Recovery)

## 1. Bản chất & Hiện tượng Sự cố (Root Cause)
- **Triệu chứng báo lỗi:** Farm Alert báo `blocked-proxy-vpn` với lý do `required router proxy is unreachable ... dumpsys connectivity: Wi-Fi not connected` hoặc `wlan0: state DOWN`.
- **Cạm bẫy ngộ nhận:** Người vận hành hoặc AI Agent thường nghi ngờ Router Wi-Fi sập sóng, hoặc proxy server (`test.taadaa.click:51xx` / `192.168.110.2:200xx`) bị hỏng. Nhưng khi test curl proxy trực tiếp từ máy host (`curl -x http://<proxy> ...`) thì proxy vẫn SỐNG 100%.
- **Chẩn đoán O(1) qua ADB:**
  * `adb -s <serial> shell "dumpsys wifi | head -n 3"`
  * `adb -s <serial> shell "dumpsys window | head -n 3"`
  * Trả về kết quả:
    ```text
    Can't find service: wifi
    Can't find service: window
    ```
  * Hoặc khi chạy `adb -s <serial> shell svc wifi enable` trả về exit code `135` / `139` (SIGBUS/SIGSEGV).
- **Cơ chế kỹ thuật:** Tiến trình cốt lõi `system_server` của Android Framework bị crash ngầm. Kernel Linux và daemon `adbd` (chạy qua cáp USB) vẫn sống, nhưng toàn bộ subsystem quản lý Wi-Fi, WindowManager, ActivityManager đã chết hoàn toàn. Giao diện mạng `wlan0` bị ngắt (`state DOWN`) và các lệnh quản lý mềm (`svc wifi enable`, `cmd wifi`) hoàn toàn mất tác dụng.

---

## 2. Giải pháp Tự động hóa trong Runner (`python_runner/core/vpn_preflight.py`)

User chỉ đạo: *"tóm lại đang chạy mà gặp lỗi wifi thì xử lý sao ... thì handle vào script đi"*.
Cơ chế tự phục hồi tự động đã được tích hợp trực tiếp vào hàm `require_proxy_connected()`:

### Luồng xử lý 2 tầng (Two-Tier Recovery):
1. **Tầng 1 (Bật lại Wi-Fi mềm):**
   * Script gọi `adb.shell(["svc", "wifi", "enable"], timeout=5, check=False)`.
   * Chờ 2s và kiểm tra lại `check_android_vpn`. Nếu Wi-Fi kết nối lại bình thường -> tiếp tục chạy.
2. **Tầng 2 (Phát hiện Dead Service & Tự động Guarded Reboot):**
   * Bắt output hoặc exit code từ lệnh `svc wifi enable`:
     ```python
     wifi_output = (str(getattr(wifi_res, "stdout", "") or "") + str(getattr(wifi_res, "stderr", "") or "")).lower()
     exit_code = getattr(wifi_res, "exit_code", getattr(wifi_res, "returncode", 0))
     is_service_dead = "can't find service" in wifi_output or exit_code in (135, 139)
     ```
   * Nếu phát hiện `is_service_dead` và chưa từng thử reboot (`getattr(adb, "_wifi_reboot_attempted", False) is not True`):
     1. Đánh dấu cờ chống lặp: `setattr(adb, "_wifi_reboot_attempted", True)`.
     2. Gửi lệnh reboot: `adb.run(["reboot"], timeout=15, check=False)`.
     3. Đợi thiết bị tái kết nối: `adb.run(["wait-for-device"], timeout=90, check=False)`.
     4. Polling trạng thái boot hoàn tất: vòng lặp kiểm tra `adb.shell(["getprop", "sys.boot_completed"]) == "1"` (timeout 90s, mỗi 3s probe 1 lần).
     5. Đệm 5.0s cho Wi-Fi association tự động kết nối lại router.
     6. Tái kiểm tra preflight: `reboot_status = check_android_vpn(adb, required=True, interface=interface, timeout=10.0)`.
     7. Nếu `reboot_status.allowed` -> Trả về kết quả thành công, batch tiếp tục chạy bình thường mà không cần con người can thiệp.

---

## 3. Quy tắc Loop Guard & Fail-Closed
- **Chống lặp reboot vô hạn:** Biến trạng thái `_wifi_reboot_attempted` đảm bảo trong 1 phiên preflight của 1 thiết bị chỉ được reboot tối đa **1 lần duy nhất**.
- **Fail-closed an toàn:** Nếu sau khi reboot mà Wi-Fi vẫn không kết nối (do lỗi phần cứng thực sự hoặc router mất điện), runner lập tức fail-closed `ConsumerPreflightError` để nhả lease cho máy khác, không treo thread pool.

---

## 4. Focused Unit Test Nghiệm thu
File test: `python_runner/tests/test_vpn_preflight_router.py`
```python
@patch("time.sleep", return_value=None)
@patch("python_runner.core.vpn_preflight.serial_is_mapped_in_workbook", return_value=True)
@patch("python_runner.core.vpn_preflight._proxy_server_live", return_value=True)
@patch("python_runner.core.vpn_preflight.check_android_vpn")
def test_dead_service_triggers_guarded_reboot_and_recovers(
    self, mock_check, mock_proxy_live, mock_is_mapped, mock_sleep
):
    ...
```
Chạy test nghiệm thu:
`python -m pytest python_runner/tests/test_vpn_preflight_router.py -v` (21/21 passed).
