# Case 92: Phân Định Màn Hình Toàn Trang "Tìm Bạn Bè" (Find Friends Subpage) & Cô Lập Khỏi Dialog Quyền Facebook/Email

## Hiện tượng & Nguyên nhân
- Khi chạy feed hoặc chuyển hướng tab Hồ sơ, TikTok có thể rơi vào màn hình toàn trang **"Tìm Bạn bè" / "Find Friends"** chứa các row:
  - "Sử dụng mã QR"
  - "Mời bạn bè"
  - "Tìm bạn bè trong danh bạ"
  - "Tìm bạn bè trên Facebook"
- **Bug Root Cause:** Detector `_detect_facebook_friends_email_permission` (priority 92) match chuỗi lỏng lẻo `"facebook"` + `"bạn bè"` nên bắt nhầm màn hình này, cướp lượt xử lý của `follow_friends_suggestion_popup` (priority 81).
- Displayer của dialog Facebook đi tìm nút từ chối hoặc target profile không tồn tại -> quăng lỗi fail-closed `navigation target profile not found in XML` và dừng phiên.

## Quy tắc chuẩn hóa
1. **Thắt chặt Permission Dialog Detectors:** Mọi permission detector có priority cao (như Facebook/Email permission) bắt buộc phải kiểm tra dấu hiệu dialog thực sự:
   - Có Decision Control (nút từ chối: `"không cho phép"`, `"don't allow"`, `"từ chối"`, `"tu choi"`).
   - HOẶC có câu hỏi cấp quyền rõ ràng (`"?"` kết hợp `"cho phép"` / `"allow"` / `"quyền truy cập"` / `"permission"`).
2. **Accent-Insensitive Normalization (NFD Stripping):** Khi so khớp text UI từ OCR hoặc UiAutomator XML, bắt buộc chuẩn hóa qua:
   ```python
   import unicodedata
   def _strip_accents(s: str) -> str:
       return "".join(
           c for c in unicodedata.normalize("NFD", s)
           if unicodedata.category(c) != "Mn"
       )
   ```
   Điều này ngăn ngừa triệt để lỗi miss text do font chữ, OCR mất dấu hoặc locale biến dạng.
3. **Handler Map:** Màn hình Tìm Bạn bè toàn trang phải map về `follow_friends_suggestion_popup` (priority 81) để dismisser gửi phím `BACK` thoát về feed an toàn.
