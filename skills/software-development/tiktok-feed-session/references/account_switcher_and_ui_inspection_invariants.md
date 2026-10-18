# Quy Chuẩn Kiểm Thử Account Switcher & Đọc Màn Hình Farm (Invariants)

## 1. QUY TẮC NGHIỆM THU ĐÚNG TARGET (CHỐNG TEST CHỆCH SCOPE)
- **Cấm test vuốt khi sửa switcher:** Khi sửa lỗi liên quan đến `account-switcher`, `profile-switch-anchor`, hoặc nhận diện tài khoản, **CẤM TUYỆT ĐỐI** chỉ chạy lệnh feed swipe thông thường (vuốt feed 3 lần) rồi kết luận hoàn thành.
- **Lệnh test thực tế chuẩn xác:** BẮT BUỘC phải chạy flow có kích hoạt nhánh chuyển tài khoản từ workbook:
  ```bash
  python "D:/Taadaa/tiktok-luot nuoi acc/python_runner/run_tiktok.py" \
    --mode multi-machine-feed-session \
    --machines <N> \
    --account-workbook "D:/OneDrive/TaadaaData/kibe/taikhoan_run_safe.xlsx" \
    --account-row-index <Row> \
    --max-workers 1 \
    --config "D:/Taadaa/tiktok-luot nuoi acc/python_runner/config.example.yaml" \
    --allow-navigation-only \
    --allow-feed-swipe \
    --allow-benign-popup-dismiss \
    --prepare-tiktok \
    --recovery-test-swipes 1
  ```
- **Bằng chứng thị giác bắt buộc (Visual Evidence):**
  1. Ảnh chụp bước `profile_preflight_switcher_*_guard`: Bắt buộc soi mắt (Vision/OCR) thấy rõ popup bottom sheet "Chuyển tài khoản" bung lên từ dưới, danh sách các tài khoản đang login và nút `+ Thêm tài khoản`.
  2. Ảnh chụp bước `verify_profile` sau khi switch: Bắt buộc xác nhận đúng profile tài khoản mới đã được chọn.
  3. Log JSONL: Phải có đủ 2 action thành công: `tap_profile_switch_anchor | success` và `tap_expected_account | success`.

## 2. KỶ LUẬT ĐỌC MÀN HÌNH 2 TẦNG (CẤM TUYỆT ĐỐI UIAUTOMATOR DUMP)
- **Tầng 1 (Primary - WinRT OCR Native 0-Token, 0.2s):**
  * Ưu tiên số 1 cho mọi kiểm tra trạng thái màn hình: kiểm tra text, chờ loading spinner (`tux_loading_hud`) biến mất, kiểm tra banner, đọc username/nickname, kiểm tra popup.
  * Tận dụng `media_verify.py` hoặc `ocr_boxes.ps1`.
- **Tầng 2 (Secondary Fallback - ATX-Agent port 7912):**
  * Sử dụng qua `_capture_xml_text()` và `capture_required_ui()` của `automation-core`.
  * Chỉ dùng khi cần phân tích UI Tree đầy đủ để lấy Bounding Rect / tọa độ click chính xác.
- **Vùng cấm tuyệt đối (Zero Tolerance):**
  * CẤM chạy `adb shell uiautomator dump`.
  * CẤM gọi `ctx.adb.dump_ui()` hoặc để sót trong bất kỳ hàm helper nào (như `_wait_for_profile_loading_spinner`).
  * Trên dòng máy Samsung Galaxy S7 Android 7 của Farm, `uiautomator dump` gây treo cứng `UiAutomationService` và exit code `137 Killed`.

## 3. CƠ CHẾ CHỌN ANCHOR MỞ ACCOUNT SWITCHER (ROOT CAUSE & FIX)
- **Đặc điểm UI TikTok:** Nút mở bottom sheet tài khoản là dòng tên hiển thị lớn trên cùng (resource-id `com.ss.android.ugc.trill:id/t7l`), không phải dòng username `@...` ở bên dưới.
- **Quy tắc lọc retry anchor (`_select_profile_retry_anchor`):**
  * BẮT BUỘC loại trừ các node username có resource-id kết thúc bằng `:id/t3y`, `:id/pkh`, `:id/pau`, `:id/s9b`, hoặc `tv_content_name`.
  * Chỉ chấp nhận candidate có tọa độ center hợp lệ và `attrib["clickable"] == "true"`.
  * Nếu không tìm thấy anchor an toàn -> Fail-closed ngay lập tức (`manual-needed`), cấm click mò mẫm vào các vùng khác gây trôi màn hình.
