# Wi-Fi Disconnect Preflight, Keyguard Screen Lockout & Alert-Claims De-duplication

## 1. Triệu Chứng & Cơ Chế Phát Sinh Lỗi Mất Wi-Fi
- **Hiện tượng:** Máy đứng im tại màn hình khóa (Keyguard `showing=true`), không chạy batch, file `device-locks/machine_<N>.lock.json` ghi nhận `status: "blocked"`, `owner_active: false`.
- **Nguyên nhân gốc:**
  1. Khi máy bị mất kết nối Wi-Fi (`dumpsys connectivity: Wi-Fi not connected` / `mWifiInfo: DISCONNECTED`):
     - Hàm `require_vichanger_connected(adb_path, serial)` ném ngoại lệ trong bước preflight.
     - Runner `multi_machine_feed_session.py` ghi nhận `final_status: "blocked-vichanger-vpn"` và chuyển trạng thái lock sang `blocked`.
  2. Do tiến trình feed kết thúc ngay tại preflight, thiết bị không được giữ wake-lock màn hình (`mHoldingDisplaySuspendBlocker: false`). Sau 600s timeout màn hình của hệ điều hành, máy tự động tắt màn hình và kích hoạt Keyguard.

## 2. Cơ Chế Alert Claims De-duplication (`_claim_machine_alert_once`)
- **Vị trí lưu trữ:** `D:/Taadaa/runtime/kibe/live/alert-claims/<session_key>/machine_<N>.claimed` (ví dụ `2026-09-03-row3/machine_64.claimed`).
- **Quy tắc 1-Alert-Per-Session:**
  - Hệ thống chỉ gửi đúng **1 Telegram Farm Alert duy nhất** cho mỗi máy trong 1 ca/phiên logic.
  - File `.claimed` được tạo nguyên tử trước khi gọi bot Telegram.
  - Nếu máy tiếp tục gặp lỗi mạng ở các lần rerun/batch kế tiếp trong cùng ca, runner phát hiện file `.claimed` đã tồn tại và tự động nuốt/bỏ qua bước bắn tin nhắn để tránh làm ngập (spam) kênh Telegram.

## 3. Quy Trình Khôi Phục & Tái Kích Hoạt Thiết Bị (Recovery Checklist)
1. **Bật lại Wi-Fi qua ADB:**
   ```bash
   adb -s <serial> shell svc wifi enable
   ```
2. **Kiểm tra Preflight Proxy/Wi-Fi:**
   ```python
   from core.vpn_preflight import require_vichanger_connected
   require_vichanger_connected("C:/Program Files (x86)/xiaowei/tools/adb.exe", "<serial>")
   ```
   Đảm bảo trả về `AndroidVpnPreflight(connected=True, proxy_ip=...)`.
3. **Mở khóa màn hình (Dismiss Keyguard):**
   ```bash
   adb -s <serial> shell "input keyevent 224 && input keyevent 82 && wm dismiss-keyguard"
   ```
4. **Kiểm tra & Gỡ Stale Blocked Lock nếu cần:**
   - File `C:/Users/Kibe/.codex/device-locks/machine_<N>.lock.json` có thể được dọn dẹp hoặc ghi đè bằng canary run có thẩm quyền.
