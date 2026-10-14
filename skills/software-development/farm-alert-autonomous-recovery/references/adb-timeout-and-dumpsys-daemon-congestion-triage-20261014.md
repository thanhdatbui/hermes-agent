# False Hardware Offline Triage via ADB Timeout and Dumpsys Daemon Congestion

> Ref: Sự cố rụng 33 máy Kibe + 28 máy Admin báo offline giả trong Ca 2 (2026-10-14).

## 1. Bản Chất Kỹ Thuật (Mechanism of False Offline)
- Khi chạy đồng thời 25–30 worker trên farm (hoặc remote ADB qua socket `192.168.110.119:5037`), hai cơ chế sau tạo thành bẫy "offline giả":
  1. **Strict Timeout Without Retry:** Lệnh `adb shell settings get global http_proxy` đặt timeout `3.0s` không có retry. Khi hàng đợi ADB bị trễ > 3s, ngoại lệ `TimeoutExpired` bị bắt và quy chụp thành `ConsumerPreflightError: device is offline or ADB/USB disconnected`.
  2. **Unbuffered Dumpsys Flooding:** Lệnh `dumpsys window` (3MB) và `dumpsys activity activities` (2MB) đẩy hàng megabyte text thô qua cáp USB. Nhiều máy cùng dump làm tê liệt daemon `adb.exe`, gây nghẽn bus và kéo theo timeout dây chuyền trên các máy khác.

## 2. Quy Tắc Phòng Vệ & Sửa Đổi Bắt Buộc (Invariant Patterns)
- **Quy tắc 1 (Safe Read Timeout & Retry Loop):**
  Mọi lệnh đọc trạng thái Android (`settings`, `dumpsys battery`) trên farm đa luồng BẮT BUỘC đặt timeout `>= 8.0s` và bọc vòng lặp retry 2 lần (`range(2)`) với sleep 1.0s nếu gặp timeout/connection-lost tạm thời trước khi đưa ra quyết định fail-closed.
- **Quy tắc 2 (On-device Grep Filtering):**
  Ưu tiên lọc ngay trên shell Android: `sh -c "dumpsys window | grep -E 'mCurrentFocus|mFocusedApp|mFocusedWindow|mTopFullscreenOpaque'"` thay vì dump toàn bộ window ra USB. Giữ `dumpsys window` làm fallback cuối cùng trong danh sách candidates để bảo toàn tương thích OEM.
- **Quy tắc 3 (Closeout Gate Test Discovery):**
  `closeout_gate.py` tự động ánh xạ source `python_runner/core/<name>.py` sang `python_runner/tests/test_<name>.py`. Không đặt tên test chệch quy ước khiến reviewer Sol High từ chối vì thiếu bằng chứng test suite trực tiếp.
