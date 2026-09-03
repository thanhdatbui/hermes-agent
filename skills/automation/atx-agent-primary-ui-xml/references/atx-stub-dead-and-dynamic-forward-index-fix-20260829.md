# ATX Session Stub Dead & Dynamic Forward Index Fix (2026-08-29)

## 1. Context & Incident (Máy 74)
- **Triệu chứng:** Phiên nuôi nick dừng đột ngột ở bước probe UI/blind popup (`swipe_3_after_back_recheck_gemphonefarm_blind_popup_close_all_desc_probe_2`) với lỗi `capture-invalid: ATX_SESSION_UNAVAILABLE`.
- **Hệ quả:** Runner lock máy với trạng thái `blocked` (TTL 2h), các ca/phiên sau skip máy 74.

## 2. Root Cause Analysis
1. **Index bug trong `persistent_ui.py::_ensure_forward`**:
   - Khi tạo dynamic port (`adb forward tcp:0 tcp:7912`), output của `adb forward --list` là:
     `<serial> <local_port> <remote_port>`
   - Line 455 đọc nhầm `parts[2]` (cổng remote `tcp:7912`) gán vào `local_port` thay vì `parts[1]` (`tcp:63018`).
   - Request HTTP JSON-RPC gửi tới `127.0.0.1:7912` thay vì cổng local động được cấp -> Lỗi kết nối hoặc đụng độ máy khác.
2. **`reset_atx_agent` thiếu fallback monkey**:
   - `reset_atx_agent` chỉ gọi `atx-agent curl POST /uiautomator`.
   - Trên Galaxy S7 (Android 7/8), daemon atx-agent có thể báo `<nil>` nhưng không thực sự spawn được tiến trình `com.github.uiautomator` do giới hạn service chạy ngầm.
   - `ps -A` không có stub -> `ATX_SESSION_STUB_NOT_RUNNING` -> `UIDumpError("ATX_SESSION_UNAVAILABLE")`.

## 3. Standard Code Fix
1. **`automation-core/src/automation_core/persistent_ui.py`**:
   - `_ensure_forward`: Sửa `local_port = int(parts[1].split(":")[1])`.
   - `reset_atx_agent`: Bổ sung polling 8s `ps -A`. Nếu chưa thấy stub thì chạy `adb shell "monkey -p com.github.uiautomator 1"` và poll tiếp 5s.
2. **`tiktok-luot nuoi acc/python_runner/core/ui_capture.py`**:
   - Sau khi gọi `reset_atx_agent`, bổ sung fallback monkey trực tiếp nếu reset trả `False`.
   - Nâng số lần retry sau reset lên 3 lần (`post_attempt 1..3`).

## 4. User Invariant ("Fix máy = Sửa script, không chạy tay cho qua")
- Khi nhận yêu cầu "fix máy XX", bắt buộc:
  1. Phân tích nguyên nhân lỗi thật trên máy/log.
  2. Sửa trực tiếp vào codebase (`automation-core`, `python_runner`, flows...).
  3. Cập nhật `docs/farm-automation-cases.md` (Gate 0.5).
  4. Chạy unit test + live canary chứng minh script tự động hoạt động `success`.
  5. Tuyệt đối không chỉ thao tác cứu vãn ad-hoc bằng tay rồi báo xong mà không lưu code.
