# GemPhoneFarm Injected `verify-bar-close` & False-Positive `manual_challenge marker detected` (2026-09-19)

## 1. Hiện tượng & Triệu chứng
- **Alert:** Hệ thống watchdog gửi alert khẩn cấp:
  `⚠️ [P0 CẢNH BÁO MẤT PHIÊN / VĂNG ACCOUNT]: Phát hiện máy MX: manual_challenge marker detected`.
- **Thực tế kiểm tra thiết bị:**
  - TikTok vẫn đang mở và phát feed bình thường, không có màn hình captcha, trượt mảnh ghép hay yêu cầu xác minh bảo mật thủ công nào.
  - Kiểm tra Profile và Account Switcher: Cả 7-8 nick đều đang đăng nhập đầy đủ, không nick nào bị văng session.

## 2. Root Cause Cơ chế Phân loại (Classifier Mechanism)
- Trong `python_runner/core/classifier.py` (dòng 650-705):
  ```python
  if "verify-bar-close" in resource_ids:
      _verify_bar_challenge_terms = tuple(
          term.lower() for term in (*manual_challenge_terms, *_CAPTCHA_PUZZLE_TEXT_TERMS)
      )
      if any(
          any(term in value.lower() for term in _verify_bar_challenge_terms)
          for value in [*texts, *descs]
      ):
          known_popup = detect_allowed_generic_popup(root)
          if known_popup is not None:
              return ScreenClassification(screen="manual-needed:popup", ...)
          return ScreenClassification(
              screen="manual-needed:manual_challenge",
              confidence=0.98,
              reasons=["resource-id verify-bar-close present with challenge/verification text"],
              manual_needed=True,
          )
  ```
- **Tác nhân gây nhiễu:**
  1. Element `verify-bar-close` được phần mềm điều khiển nông trại **GemPhoneFarm** chạy nền inject vào Accessibility hierarchy (`Thông báo của Hệ thống Android: GemPhone đang chạy ngầm`). Nó có thể tồn tại thường trực hoặc xuất hiện thoáng qua trong hierarchy ngay cả trên màn hình feed bình thường.
  2. Từ khóa `manual_challenge_terms` bao gồm chuỗi `"xác minh"`, `"Xác minh"`.
  3. Khi video trên Home Feed tình cờ chứa từ "xác minh" trong caption, hashtag, mô tả bài đăng (bio), hoặc thông báo đẩy hệ thống (push notification) xuất hiện trên đỉnh màn hình, tổ hợp này lập tức kích hoạt nhãn `manual-needed:manual_challenge`.
  4. Trong `python_runner/core/safety.py`:
     ```python
     "manual-needed:manual_challenge": "manual_challenge marker detected"
     ```
     khiến watchdog gán cờ sự cố nghiêm trọng P0.

## 3. Quy trình Kiểm chứng Canary O(1) Cho Coordinator
Khi nhận cảnh báo `manual_challenge marker detected` trên Máy N:
1. **Tuyệt đối cấm thao tác tay ADB vuốt/chạm ad-hoc làm mất hiện trường.**
2. **Wake screen & Kiểm tra Foreground:**
   ```bash
   adb -s <SERIAL> shell "input keyevent 224 && input keyevent 82"
   adb -s <SERIAL> shell "dumpsys window | grep -E 'mCurrentFocus|mFocusedApp'"
   ```
3. **Chụp screencap & Chạy WinRT OCR kiểm tra màn hình thật:**
   ```bash
   adb -s <SERIAL> exec-out screencap -p > D:/Taadaa/reports/m<N>_live.png
   python C:/Users/Kibe/AppData/Local/hermes/skills/productivity/windows-native-ocr/scripts/winrt_ocr.py D:/Taadaa/reports/m<N>_live.png
   ```
4. **Mở Switcher và Đối soát Danh tính Toàn bộ Nick:**
   - Điều hướng sang tab Profile (tọa độ `972, 1857` hoặc ATX node `:id/oly`).
   - Vuốt nhẹ 400px (`input swipe 540 1200 540 800 200`) -> tap sticky header giữa đỉnh (`500, 140`) để bung sheet "Chuyển đổi tài khoản".
   - Chụp screencap `m<N>_switcher.png` và chạy WinRT OCR đối soát 100% tài khoản với `taikhoan_run_safe.xlsx`.
5. **Đưa ra kết luận:**
   - Nếu đủ 100% nick và không có captcha trên màn hình: Xác định là False Positive do transient collision của `verify-bar-close` + text feed.
   - Gửi `input keyevent 3` (HOME) đưa thiết bị về trạng thái an toàn và mở khóa batch tiếp tục chạy.

## 4. Dọn sạch code & Triệt tiêu hoàn toàn tàn dư GemPhone (`verify-bar-close`)
Theo chỉ đạo dẹp toàn bộ tàn dư GemPhone khỏi codebase:
1. **`classifier.py`**:
   - Xóa bỏ hoàn toàn khối `if "verify-bar-close" in resource_ids: ... return ScreenClassification(screen="manual-needed:manual_challenge"...)`.
   - Lọc nguồn text cho `_is_manual_challenge_match`: Bỏ qua các node có `resource-id` kết thúc bằng `(":id/desc", ":id/title", ":id/comment_text")` (caption, tiêu đề, comment video) và node thuộc package `com.android.systemui`.
   - Feed detail gate: Nếu `_has_feed_detail_controls(elements)` là `True` (có các controls Thích, Bình luận, Chia sẻ, Bookmark), KHÔNG ĐƯỢC phân loại thành `manual-needed:verification` hoặc `manual-needed:manual_challenge`.
2. **`feed_swipe_smoke.py`**:
   - Xóa bỏ rule `verify_bar_close` khỏi `GEMPHONEFARM_BLIND_POPUP_RULES`.
3. **Pitfall điều tra codebase trên farm repo**:
   - Tuyệt đối KHÔNG chạy blanket `grep -rn` từ repo root vì thư mục `.ai-runs/` chứa hàng nghìn file `.jsonl` lớn gây timeout 180s làm cạn tool budget. Luôn chỉ định folder đích (`python_runner/core/`, `python_runner/flows/`) hoặc dùng Python script quét chọn lọc.

