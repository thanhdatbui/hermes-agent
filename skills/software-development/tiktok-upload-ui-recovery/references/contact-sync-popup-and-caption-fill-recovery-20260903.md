# Contact Sync Popup ("Thêm bạn bè, dùng TikTok thêm vui") & Benign Popup Recovery in Upload Flow (Case 78, 2026-09-03)

## Hiện tượng & Triệu chứng (Máy 74, Samnga2403)
- Script: `tiktok-video` (run_post / batch upload Tik3.xlsx)
- Lỗi: `upload_subprocess_nonzero`
- Log: `Caption field not found via selectors` sau 3 lần retry tại bước `CAPTION_FILL`.
- Thực tế trên máy: Sau khi chọn video và bấm `Tiếp`, video được đẩy/xuất bản trực tiếp về Feed; đồng thời TikTok bật popup in-app:
  - **Tiêu đề / Body:** *"Thêm bạn bè, dùng TikTok thêm vui. Khi đồng bộ danh bạ điện thoại, bạn có thể tìm thấy những người bạn có thể biết và được họ tìm thấy."*
  - **Nút:** `OK` (trên) và `Không cho phép` (dưới).

## Nguyên nhân gốc (Root Cause)
1. **Tầng Phân loại XML (`automation_core.tiktok.benign_popup`):**
   - Detector `detect_contact_sync_dialog` cũ chỉ so khớp cụm từ cố định `"thêm bạn bè, dùng tiktok thêm vui"` mà thiếu các biến thể text phổ biến ("đồng bộ danh bạ điện thoại", "khi đồng bộ danh bạ", mojibake utf-8).
   - Bộ chọn nút từ chối (`deny`) dùng `_find_clickable_text` thay vì ưu tiên `_find_exact_label_element` với nhãn `Không cho phép` / `Don't allow`.
2. **Tầng Engine chung (`automation_core.tiktok_popup`):**
   - `TIKTOK_POPUP_RULES` thiếu rule regex cho cụm từ `"đồng bộ danh bạ"` / `"thêm bạn bè, dùng tiktok thêm vui"`.
3. **Tầng Consumer Workflow (`tiktok-video/scripts/tiktok_workflow/state_machine.py`):**
   - Khi `_handle_caption_fill` không tìm thấy ô nhập caption (`_find_caption_field` trả None), script lập tức fail UI attempt thay vì thử dismiss popup lành tính (`_dismiss_core_benign_popup` / `_deny_tiktok_contacts_settings_prompt`).
   - Tương tự, trong `_handle_video_pick`, sau khi tap `Tiếp` trên editor mà composer chưa kịp lộ do popup che khuất, flow cũng cần giải phóng popup trước khi timeout.

## Giải pháp chuẩn hóa đã áp dụng
1. **`automation_core/tiktok/benign_popup.py` (`detect_contact_sync_dialog`):**
   - Mở rộng `body_terms` gồm: `"thêm bạn bè, dùng tiktok thêm vui"`, `"đồng bộ danh bạ điện thoại"`, `"đồng bộ danh bạ"`, `"khi đồng bộ danh bạ"`, `"Add friends, use TikTok for more fun"`, `"sync your phone contacts"`, `"sync contacts"` (bọc `_with_utf8_mojibake`).
   - Mở rộng `ok_terms` (`"OK"`, `"Cho phép"`, `"Allow"`, `"Đồng bộ"`, `"Sync"`, `"Tiếp tục"`).
   - Mở rộng `deny_terms` (`"Không cho phép"`, `"Don't allow"`, `"Từ chối"`, `"Deny"`, `"Hủy"`, `"Cancel"`).
   - Kiểm tra an toàn `has_sensitive_marker(root)` để fail-closed trên màn hình nhạy cảm.
2. **`automation_core/tiktok_popup.py`:**
   - Thêm `contacts_sync_vi` và `contacts_sync_en` vào `TIKTOK_POPUP_RULES` và `_find_target_element`.
3. **`Tiktok-video/scripts/tiktok_workflow/state_machine.py`:**
   - Trong `_handle_caption_fill`, bọc vòng lặp thử tối đa 5 lần: nếu chưa thấy caption field, gọi `_dismiss_core_benign_popup` hoặc `_deny_tiktok_contacts_settings_prompt` để tự động hạ popup rồi recapture XML trước khi gõ caption.
   - Trong `_handle_video_pick`, bổ sung auto-dismiss popup lành tính sau khi tap editor Next.
