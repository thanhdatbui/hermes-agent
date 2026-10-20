# Focus Device Issue: Cold Start S7, SystemUI Occlusion & Auto-Healing Relaunch (2026-10-20)

## 1. Hiện tượng & Triệu chứng
- **Alert Signature:** `focus-device-issue:prepare-tiktok failed to focus TikTok after launch`.
- **Bối cảnh:** Xảy ra trên các máy Samsung S7 (SM-G930) chạy cụm Admin Farm (M201-280) dưới tải concurrency 25 workers đồng thời.
- **Biểu hiện:** Toàn bộ 10 attempts của `verify_tiktok_focus` báo `focused package is com.sec.android.app.launcher`. TikTok không hiển thị ở foreground kịp thời gian chờ, dẫn đến kết luận fail-closed của runner.

## 2. Phân tích nguyên nhân gốc (Root Cause)
1. **Độ trễ Cold-start dưới tải cao:** Khi 25 workers đồng thời khởi chạy qua Remote ADB (port 5037) và proxy xoay vòng, thời gian tải SO libraries, Bytedance security SDK và init mạng của TikTok trên chip Exynos 8890 kéo dài từ 18s - 22s.
2. **Cửa sổ chờ focus quá hẹp:** Cấu hình cũ `PREPARE_FOCUS_MAX_ATTEMPTS = 10` và delay `1.5s` chỉ cho tối đa 15s chờ, khiến runner bỏ cuộc trước khi app kịp render SplashActivity.
3. **Bẫy `keyevent 4 (BACK)` trong SystemUI Occlusion:** Trong quá trình app load, Android 8 đôi khi giữ `com.android.systemui` (status bar transition). Khi đó hàm `recover_systemui_occlusion` gửi phím BACK (`input keyevent 4`), vô tình hủy tiến trình launch của TikTok và trả máy về `com.sec.android.app.launcher`.
4. **Auto-healing thiếu bước Intent Relaunch:** Khối auto-healing cũ khi reconnect ADB chỉ check lại `read_focus()`. Nếu máy đã rớt về launcher, reconnect không tự kéo app lên lại được.

## 3. Bản vá O(1) Chuẩn hóa (`flows/device_prepare.py`)
1. **Nâng trần chờ focus:**
   - `PREPARE_FOCUS_MAX_ATTEMPTS = 12`
   - `PREPARE_FOCUS_RETRY_DELAY_SECONDS = 1.8`
   - Tổng trần chờ mở rộng lên **21.6s**, phù hợp với đặc tính phần cứng Samsung S7.
2. **Bổ sung Intent Relaunch trong Auto-healing:**
   - Khi reconnect ADB xong mà `recheck_pkg != package_name`, phát lệnh explicit intent:
     `am start -a android.intent.action.MAIN -c android.intent.category.LAUNCHER -p <package>`
   - Nghỉ 1.5s và đọc lại `read_focus()`. Nếu thành công, trả về `"prepare-tiktok-app completed after reconnect"`.

## 4. Quy trình Khám nghiệm & Nghiệm thu
- **Triage O(1):** Dùng `python D:/Taadaa/tools/inspect_machine.py <N>` kiểm tra focus và serial.
- **Canary Safe Execution:** Mọi can thiệp ADB ghi trên máy thật bắt buộc bọc qua `operator_device_lock(machine=N, serial=...)`.
- **Verification Evidence:**
  - Chạy focused pytest: `pytest python_runner/tests/test_device_prepare.py -k "test_prepare_tiktok_app"` (< 2s).
  - Nghiệm thu màn hình thật qua WinRT OCR và Vision kiểm tra tab For You / Trang chủ trước khi teardown về HOME.
