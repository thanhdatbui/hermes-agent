# Quy Tắc Phân Định Subpage Toàn Màn Hình vs Permission Dialog Trong Benign Popup Registry (Case 92)

## Vấn Đề (Anti-Pattern)
Khi xây dựng các handler trong `benign_popup_registry.py`:
- Dialog xin quyền hệ thống/app (ví dụ: `_detect_facebook_friends_email_permission`, priority 92) thường có priority cao hơn các screen/overlay gợi ý (ví dụ: `follow_friends_suggestion_popup`, priority 81).
- Nếu detector của dialog xin quyền chỉ so khớp chuỗi lỏng lẻo (ví dụ `facebook` + `bạn bè` / `friends`), nó sẽ bắt nhầm các subpage toàn màn hình như "Tìm Bạn bè" (chứa dòng menu "Tìm bạn bè trên Facebook").
- Khi bị bắt nhầm, handler của permission dialog cố tìm nút từ chối / target profile nhưng không thấy trong XML, dẫn đến fail-closed `navigation target profile not found in XML` và làm dừng phiên chạy.

## Giải Pháp Chuẩn
1. **Thắt chặt Detector có Priority cao:**
   - Yêu cầu bắt buộc phải có decision control (nút từ chối: `không cho phép`, `don't allow`, `từ chối`, `tu choi`...) HOẶC câu hỏi cấp quyền rõ ràng (`?` đi kèm `cho phép`, `allow`, `quyền truy cập`, `permission`).
2. **Chuẩn Hóa Khử Dấu (NFD Accent Stripping):**
   - Khi so khớp text tiếng Việt trong XML/OCR, luôn chuẩn hóa bằng NFD (`unicodedata.normalize('NFD', s)`) để loại bỏ dấu thanh (`category != 'Mn'`), giúp nhận diện chính xác cả khi UI XML/OCR bị mất dấu hoặc font chữ biến dạng.
3. **Fallback Tap An Toàn (Case 93 Pattern):**
   - Khi modal có 2 nút lựa chọn (ví dụ: "Không cho phép" bên trái và "Mở cài đặt" bên phải), ưu tiên vòng 1 chỉ tìm chính xác nhãn nút từ chối; chỉ sang vòng 2 tìm generic cancel/hủy khi không thấy nút từ chối cụ thể. Tránh tap nhầm vào nút mở Settings gây mất focus.
