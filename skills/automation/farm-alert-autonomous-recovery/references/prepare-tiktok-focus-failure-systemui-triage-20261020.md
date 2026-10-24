# Prepare-TikTok Focus Failure & SystemUI Occlusion Back-Key Triage (2026-10-20)

## 1. Hiện tượng & Triệu chứng (Symptoms)
- **Signature lỗi:** `focus-device-issue:prepare-tiktok failed to focus TikTok after launch`
- **Tần suất / Ngữ cảnh:** Xuất hiện trong các batch nuôi lớn (80 máy, concurrency 25 workers) trên cụm Admin Remote (M201-M280).
- **Hành vi quan sát được:**
  - `launch_tiktok` thành công qua `monkey` intent launcher.
  - Vòng lặp `verify_tiktok_focus` chạy 10 lần (mỗi lần 1.5s) đều thất bại với lỗi `focused package is com.sec.android.app.launcher`.
  - Trong `log.jsonl`, xuất hiện bước `systemui_occlusion_recovery` với `action="close_system_dialogs"` và `fallback_used=True` ngay trước khi xác thực focus thất bại.

## 2. Nguyên nhân gốc (Root Cause)
1. **Nghẽn tải ADB Socket & Cold Start Delay:** Trên Samsung Galaxy S7 (Android 8.0, Exynos 8890) kết nối qua ADB Server Remote (`192.168.110.119:5037`) và proxy xoay vòng, khi chạy 25 workers đồng loạt, thời gian khởi động nguội (cold start) TikTok sau `am force-stop` kéo dài từ 15 đến 25+ giây.
2. **SystemUI Transient & Back-Key Race Condition:**
   - Trong quá trình mở app, SystemUI (status bar / transition window) có thể xuất hiện thoáng qua trong foreground.
   - Hàm `recover_systemui_occlusion()` trong `flows/device_prepare.py` phát hiện `com.android.systemui` và gửi broadcast `android.intent.action.CLOSE_SYSTEM_DIALOGS`.
   - Nếu SystemUI chưa kịp nhả, fallback của hàm gửi `input keyevent 4` (KEYCODE_BACK). Phím BACK này vô tình đóng luôn cửa sổ TikTok vừa khởi động, đẩy thiết bị quay trở lại `com.sec.android.app.launcher`.
   - Toàn bộ 10 lần kiểm tra focus sau đó chỉ thấy Launcher, dẫn đến việc kết luận sai là app không mở được.

## 3. Quy trình Khám nghiệm & Canary Chuẩn O(1)
1. **Tra cứu O(1) không lock:** Dùng `python D:/Taadaa/tools/inspect_machine.py <N>` kiểm tra ngay trạng thái nguồn, pin, Wi-Fi, proxy và `mCurrentFocus`. Nếu thấy `SplashActivity` hoặc `LauncherActivity`, kiểm tra xem app có bị đóng do teardown hay đang treo.
2. **Canary an toàn với Operator Device Lock:**
   ```python
   from automation_core.device_lock import operator_device_lock
   from automation_core.adb import AdbClient

   with operator_device_lock(machine=N, serial='<serial>', timeout=10.0) as lease:
       adb = AdbClient(host="192.168.110.119", port=5037, serial='<serial>')
       adb.shell(["monkey", "-p", "com.ss.android.ugc.trill", "-c", "android.intent.category.LAUNCHER", "1"])
       # Chờ app render đủ 3-5s
       sc_res = adb.exec_out(["screencap", "-p"])
       with open(screenshot_path, "wb") as f:
           f.write(sc_res.stdout_bytes if hasattr(sc_res, "stdout_bytes") else sc_res.stdout)
   ```
3. **Soi mắt nghiệm thu qua Vision / WinRT OCR:** Bắt buộc dùng `browser_vision` hoặc `run_winrt_ocr.py` (lưu ý đường dẫn Windows backslashes `\\`) xác nhận giao diện For You / Trang chủ hiển thị đầy đủ, không bị popup hay mất phiên trước khi kết luận.
4. **Teardown sạch sẽ:** `am force-stop` và gửi `input keyevent 3` (HOME) để đưa máy về trạng thái rảnh an toàn.
5. **Chuẩn báo cáo Telegram Farm Alert:**
   - Dòng 1: `MEDIA:<đường_dẫn_tuyệt_đối>`
   - Dòng 2: `### [MÁY XX] - <Tiêu đề>`
   - Dòng 3+: Tóm tắt OCR/Vision readback và kết luận.
