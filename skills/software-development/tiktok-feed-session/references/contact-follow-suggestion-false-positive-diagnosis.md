# TikTok Contact Follow Suggestion vs Sensitive Marker False Positive

## 1. Hiện tượng & Triệu chứng
Trong ca nuôi feed (feed-session-smoke hoặc multi-machine-feed-session), TikTok xuất hiện card/overlay gợi ý danh bạ / bạn bè:
- Tiêu đề: `"Tài khoản được đề xuất"` / `"Suggested accounts"`
- Nút tương tác: `"Follow lại"` (`:id/che`), nút đóng X (`:id/fwi` nhãn `"Đóng"`), hoặc `"Không quan tâm"`.

Hệ thống báo động dừng khẩn cấp:
```json
{
  "result": "manual-needed",
  "error": "login/account screen detected",
  "blocker_type": "login-gms-verification",
  "reasons": ["login/account/credential marker present"]
}
```
Khiến Coordinator nhận alert P0 mất phiên / văng account dù nick hoàn toàn an toàn và đã swipe bình thường trước đó.

## 2. Nguyên nhân gốc rễ
1. `SENSITIVE_POPUP_TERMS` trong `automation-core/src/automation_core/tiktok/benign_popup.py` chứa cụm `"tài khoản"`.
2. Card có text `"Tài khoản được đề xuất"` khớp chuỗi con `"tài khoản"`, đồng thời chứa nút đóng X có nhãn `"Đóng"` (thuộc `sensitive_action_terms`).
3. Điều này làm `has_sensitive_marker(root)` trả về `True`.
4. Trong `classifier.py`, `has_sensitive_marker(root)` được kiểm tra TRƯỚC khi gọi `detect_allowed_generic_popup(root)` (hoặc kiểm tra popup cho phép), dẫn đến kết quả trả về `manual-needed:login` thay vì xử lý popup lành tính `contact_follow_suggestion`.

## 3. Quy tắc điều phối & Khắc phục
- **Điều phối (Coordinator):**
  - Tuyệt đối KHÔNG gõ ADB logout hay xóa data nick cũ khi thấy alert này.
  - Kiểm tra log `profile_identity` và bước swipe trước đó trong artifact `live/YYYY-MM-DD/row-N-...`. Nếu profile đã xác thực danh tính đúng và đã swipe được video -> 100% là false-positive trên overlay tab bạn bè / feed.
- **Sửa code (Worker subagent Patch Contract):**
  - Trong `benign_popup.py` (`automation-core` & `python_runner`): Ngoại lệ `has_sensitive_marker()` khi `detect_contact_follow_suggestion(root)` trả về match (tương tự như pattern đã làm với `detect_add_phone_popup(root)`).
  - Đảm bảo `detect_contact_follow_suggestion(root)` được ưu tiên xử lý trước khi kích hoạt `manual-needed:login`.
