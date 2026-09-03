# Case 53 Triage: False-Positive Startup-Ad / Search-Landing on Samsung Launcher & Fail-Closed Recovery

## 1. Triệu chứng & Bối cảnh
- Khi TikTok bị crash hoặc văng về Samsung Launcher (`com.sec.android.app.launcher`) trong quá trình lướt feed / swipe.
- Máy rơi vào trạng thái dừng phiên giữ hiện trường với lỗi: `unknown TikTok state; swipe recovery (2 swipes) still stuck`.

## 2. Nguyên nhân gốc rễ (Root Cause)
1. **False-Positive Startup-Ad từ Screenshot:**
   - Bộ nhận diện ảnh (image classifier) khi chụp màn hình Launcher nhận diện nhầm icon/widget thành quảng cáo khởi động (`manual-needed:startup-ad`).
   - Hàm `_merge_xml_classification` không kiểm tra `focused_package`/`focus_package`, dẫn tới ghi đè kết quả XML yếu thành `startup-ad`.
2. **False-Positive Search-Landing Overlay:**
   - Widget "Tìm trên điện thoại" (`app_search_edit_text`, `Tìm trên điện thoại`) trên Launcher có cấu trúc `EditText` + icon tìm kiếm khiến `detect_search_landing_page` nhận diện nhầm thành trang tìm kiếm TikTok.
   - Thiếu ràng buộc fail-closed về package TikTok trong detector.
3. **Kẹt Swipe Recovery:**
   - Hàm `_swipe_recovery_on_stuck` gửi lệnh vuốt màn hình `input swipe` trực tiếp trên Launcher (thay vì relaunch TikTok), dẫn tới sau 2 lượt vuốt vẫn kẹt và dừng phiên.

## 3. Quy tắc Fix chuẩn (Fail-Closed & Recovery Relaunch)
- **Exclusion cho Launcher trong Popup Detectors:**
  - Trong `detect_search_landing_page` và `benign_popup_registry`, bắt buộc kiểm tra loại trừ danh sách Launcher (`com.sec.android.app.launcher`, `app_search_edit_text`, `Tìm trên điện thoại`).
  - Nếu XML có thuộc tính `package` mà không chứa bất kỳ TikTok package nào (`com.ss.android.ugc.trill`, `com.zhiliaoapp.musically`, `com.ss.android.ugc.aweme`) -> Return `None` (fail-closed).
- **Chặn ghi đè trong `_merge_xml_classification`:**
  - Không cho phép ảnh screenshot ghi đè thành `startup-ad` nếu `focused_package` hoặc `focus_package` là Launcher (`com.sec.android.app.launcher`) hoặc `SystemUI`.
- **Launcher Focus Check trước Swipe Recovery:**
  - Trong `_swipe_recovery_on_stuck`, trước khi thực hiện swipe phải kiểm tra `_is_launcher_focus_loss`:
    - Nếu mất focus về Launcher: kích hoạt `_relaunch_and_poll_tiktok_focus` (với bounded polling loop) để relaunch TikTok an toàn.
    - Nếu focus là ứng dụng bên ngoài khác (không phải Launcher cũng không phải TikTok): fail-closed ngay lập tức, không vuốt và không relaunch mù.
- **Fail-Closed khi ADB Swipe mất `ok`:**
  - Khi kiểm tra kết quả `swipe = ctx.adb.shell(...)`, mặc định fallback phải là `getattr(swipe, "ok", False)` để đảm bảo nếu object không có `ok` thì không coi là thành công.
