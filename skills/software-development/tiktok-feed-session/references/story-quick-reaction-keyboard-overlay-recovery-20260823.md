# TikTok Story Quick Reaction & Soft Keyboard Overlay Recovery (2026-08-23)

## Vấn đề
Khi chạy feed session (`feed-session-smoke` hoặc `multi-machine-feed-session`), nếu gặp video dạng TikTok Story (Tin) hoặc chạm trúng thanh "Nhắn tin cho [user]...", giao diện bật popup 8 quick reactions và focus vào ô input khiến bàn phím ảo (Samsung Keyboard) mở lên ở nửa dưới màn hình (Y: 1000 - 1920).

## Hậu quả
1. **Swipe blocked:** Lệnh vuốt feed chuẩn (`input swipe 540 1600 540 400`) rơi trúng bàn phím ảo nên không cuộn được video.
2. **Classifier misclassification:** Giao diện bị bàn phím che khuất khiến `classify_tiktok_screen()` không tìm thấy marker feed chuẩn -> trả về `unknown TikTok state`.
3. **Swipe recovery thất bại:** Cơ chế swipe recovery 2 lần tiếp tục chạm trúng bàn phím -> rơi vào `unknown TikTok state; swipe recovery (2 swipes) still stuck` và dừng phiên giữ hiện trường.

## Giải pháp kiến trúc
1. **Classifier Precedence (`python_runner/core/classifier.py`):**
   - Bổ sung nhóm từ khóa `story_reply_terms`: `("Nhắn tin cho", "nhắn tin cho", "Send a message", "send a message", "Reply to", "reply to", "Gửi tin nhắn", "gửi tin nhắn")`.
   - Phân loại thành `manual-needed:popup` với confidence `0.88`, lý do `"story reply / quick reaction overlay marker present"`.

2. **Benign Popup Registry Handler (`python_runner/flows/benign_popup_registry.py`):**
   - Đăng ký entry `story_reply_overlay` với Priority `76` (ngay dưới `sound_detail_overlay` - 78).
   - Detector `_detect_story_reply`: kiểm tra sự xuất hiện của các marker soạn tin/nhắn tin nhanh trong XML/OCR.
   - `_is_story_input_node`: nhận diện `EditText` có direct marker tiếng Việt (`nhắn tin cho`, `gửi tin nhắn cho`) ngay cả khi resource-id là ID động/opaque (`input_box`, `e_4`), đồng thời loại trừ rõ các ID thuộc DM/chat (`_DM_EXCLUSION_TERMS`: `message_input`, `chat_room`, `im_title_bar`, `im_root`, `chat_input`).
   - Dismisser `_dismiss_story_reply`: thực hiện `KEYCODE_BACK` 2 lần cách nhau 0.5s (lần 1 hạ bàn phím ảo, lần 2 đóng panel quick reaction overlay) để đưa app trở lại Feed an toàn.

## Pitfall đã xử lý (2026-08-23)
- **Opaque Resource-ID trên TikTok Tiếng Việt:** Trên các bản TikTok Tiếng Việt thực tế (như trên máy 56, Samsung S7), thanh input không dùng ID `story_reply_input` mà dùng `input_box` hoặc ID rút gọn. Nếu chỉ kiểm tra `resource-id` sẽ bỏ sót overlay, khiến classifier phân loại thành `unknown TikTok state` và vuốt recovery chạm trúng bàn phím ảo gây kẹt phiên.
- **Phân biệt với Generic DM:** Bắt buộc loại trừ các container chat/DM (`message_input`, `chat_room`, `im_title_bar`) để tránh nhận nhầm màn hình chat riêng tư sang story reply.
