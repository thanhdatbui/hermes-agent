# Pitfall & Root Cause: follow_friends_suggestion_popup Misdetection

## Triệu chứng
- Error: `failed_dismiss_overlay_before_navigation: follow_friends_popup_no_close_control`
- Điểm dừng: Trước khi chạm navigation target (như Profile/Hồ sơ hoặc Feed), `tap_navigation_target` trong `calibrate_screens.py` quét overlay qua `find_matching_handler(xml_text, "")`.
- Phát hiện nhầm: `find_matching_handler` match entry `follow_friends_suggestion_popup` (priority 81) do hàm `_detect_follow_friends` / `detect_follow_friends_suggestion_popup` so khớp các text/content-desc chứa marker bạn bè.

## Nguyên nhân gốc rễ (Root Cause)
1. Trên màn hình Feed chính của TikTok, thanh top tab bar thường chứa tab **"Bạn bè"** (hoặc "Bạn bè" kèm badge số thông báo) song song với tab **"Đề xuất"** (For You).
2. `_detect_follow_friends` trong `benign_popup_registry.py` và `detect_follow_friends_suggestion_popup` trong `benign_popup.py` duyệt toàn bộ text/desc của XML hierarchy mà không loại trừ top tab bar của Feed chính.
3. Khi bị nhận diện nhầm là popup, hàm `dismiss_follow_friends_suggestion_popup` cố gắng tìm nút đóng ngữ nghĩa X / Đóng (`_find_follow_friends_semantic_close_control`). Do đây là giao diện Feed chính, không có nút X/Đóng nào, dẫn đến trả về `follow_friends_popup_no_close_control`.
4. `calibrate_screens.py` nhận kết quả dismiss thất bại và ném `failed_dismiss_overlay_before_navigation: follow_friends_popup_no_close_control`.

## Hướng xử lý chuẩn
1. **Thêm guard kiểm tra Feed chính**:
   - Nếu màn hình đang có top tab "Đề xuất" / "Dành cho bạn" / "For You" hoặc tab bar chính của Feed, BỎ QUA không kích hoạt detector `follow_friends_suggestion_popup` trừ khi có modal/card riêng biệt nổi lên phía trên.
2. **So khớp ngữ cảnh (Contextual Matching)**:
   - Các marker như `"Bạn bè với"`, `"Mời bạn bè"`, `"Tìm bạn bè"` chỉ coi là popup khi nằm trong modal/card/dialog, không được match nhầm tab bar header.
3. **Kỷ luật điều tra tool calls**:
   - Tuyệt đối KHÔNG dùng `grep -rn` quét diện rộng thư mục gốc hoặc toàn bộ repo vì sẽ chạm timeout 900s do cây thư mục lớn và `.ai-runs`.
   - Chỉ grep trực tiếp file cụ thể hoặc các file trong `flows/*.py`.
