# Follow-Friends Reason Normalization, Profile Guard, and Clean Review Scripting (06/09/2026)

## 1. Mismatch Reason giữa UI Back Target Tap vs Hardware Keyevent Back
Khi triển khai cơ chế fallback navigation dismiss cho các popups/subpages phức tạp (như gợi ý kết bạn, tìm bạn bè `follow_friends_suggestion_popup` trong `benign_popup.py`), hàm dismiss thường có 2 nhánh đóng fallback:
1. **Nhánh 1: Tap vào nút điều hướng quay lại trên giao diện UI** (các node có `:id/back`, `:id/bq7`, `desc="quay lại"`, `text="back"`).
2. **Nhánh 2: Gửi phím cứng Back qua ADB** (`send_device_back_key(ctx)` / `input keyevent 4`).

### Cạm bẫy Gate 2 Unit Test Mismatch
Các unit test hồi quy có sẵn (ví dụ: `test_dismiss_follow_friends_button_with_low_x_and_back_target` trong `test_benign_popup_registry.py`) assert chính xác chuỗi kết quả `res.reason`:
- Khi tap nút quay lại trên UI thành công: `reason` BẮT BUỘC phải giữ chuẩn:
  `followed_{count}_friends_and_dismissed`
- CHỈ KHI dùng phím cứng Back qua thiết bị mới đặt:
  `followed_{count}_friends_and_dismissed_via_back`

Nếu lập trình viên gộp chung cả 2 nhánh và gán hậu tố `_via_back` cho cả thao tác tap UI, unit test Gate 2 sẽ ném `AssertionError`:
```text
AssertionError: 'followed_1_friends_and_dismissed_via_back' != 'followed_1_friends_and_dismissed'
- followed_1_friends_and_dismissed_via_back
?                                 ---------
+ followed_1_friends_and_dismissed
```

## 2. Profile Guard Chống False-Positive Cho Detector Overlay
- **Bản chất vấn đề:** Các chuỗi văn bản như *"Tìm bạn bè"*, *"Mời bạn bè"*, *"Bạn bè với"* là các nhãn chức năng tĩnh mặc định nằm trên giao diện Profile cá nhân và menu điều hướng của TikTok.
- **Hiện tượng lỗi:** Khi flow chuyển cảnh sang trang cá nhân (Profile tab), detector `detect_follow_friends_suggestion_popup` bắt trúng các chuỗi này và nhận diện nhầm màn hình cá nhân là popup gợi ý kết bạn bị kẹt. Sau đó, dismiser không tìm thấy nút X đóng popup và fail-closed cứng với lỗi `failed_dismiss_overlay_before_navigation: follow_friends_popup_no_close_control`.
- **Quy tắc chuẩn hóa:**
  1. Thêm hàm kiểm tra `_is_main_feed_or_profile_screen(xml_root, ocr_text)` nhận diện các dấu hiệu Profile ("sửa hồ sơ", "edit profile", "đang follow", "follower", "thêm tiểu sử") và Main Feed.
  2. Nếu màn hình thuộc Profile hoặc Main Feed, BẮT BUỘC kiểm tra có modal popup thực sự hay không (`android.app.Dialog` hoặc semantic close control / dialog container bounds). Nếu không có, `return False` ngay lập tức.

## 3. Tạo Script Review Độc Lập Ngoài Git Working Tree Chống Bẩn Repo
- Khi Coordinator chuẩn bị payload gửi Gate 1 Plan-Review:
  - CẤM tạo file script `tmp_run_review.py` trực tiếp trong thư mục repo vì sẽ làm bẩn `git status` (untracked file) hoặc kích hoạt false-rejection do Git index mtime trên Windows chưa refresh.
  - Luôn tạo script tạm tại thư mục user ngoài repo (ví dụ: `C:/Users/Kibe/run_review_gate1.py`).
  - Gửi tới OmniRoute (:20129) với `model: review` (route tới Claude Opus 4.6 Thinking / Sonnet 4.6) kèm socket timeout 300s để đảm bảo model thinking đủ thời gian suy luận và không bị timeout giữa chừng.
  - Xóa sạch file script tạm ngay sau khi nhận được verdict.
