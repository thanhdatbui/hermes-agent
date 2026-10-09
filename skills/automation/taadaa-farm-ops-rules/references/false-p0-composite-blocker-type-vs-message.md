# False P0 Batch Alert Dissection: Composite Blocker Type vs Message

## Sự Cố Thực Tế (2026-09-20)
- **Cảnh báo Telegram:** `[BATCH ALERT: LỖI HỆ THỐNG] P0 CẢNH BÁO MẤT PHIÊN / VĂNG ACCOUNT` trên Máy 35: `manual_challenge marker detected`.
- **Thực tế:** 8/8 account trên Máy 35 đều LIVE, app TikTok tự thoát về launcher, không hề mất phiên hay văng nick.

## Cơ Chế Gây Lỗi (Root Cause)
1. **Runner tạo nhãn composite:**
   Runner gộp toàn bộ lỗi liên quan đến xác thực / thử thách / login thành `blocker_type = "login-gms-verification"`.
2. **Batch Aggregator quét gộp chuỗi:**
   Trong `batch_aggregator.py`, logic phân loại trước đây quét `SESSION_LOST_KEYWORDS` (chứa từ khóa `"login"`) trên chuỗi ghép `f"{m.error_type} {m.error_message}"`.
3. **Hệ quả False P0:**
   Mặc dù `error_message` là `"manual_challenge marker detected"` (chỉ là captcha/thử thách tạm thời), nhưng vì `error_type` chứa chữ `"login"`, máy lập tức bị phân loại vào `session_lost_failures` và kích hoạt còi báo động đỏ P0 mất phiên.

## Bài Học Điều Phối & Quy Chuẩn (Coordinator Rules)
1. **Tuyệt đối không hỏi User đòi cung cấp code khi đã có đầy đủ công cụ truy cập codebase local:**
   - Khi user phát lệnh "Fix đi", Coordinator phải chủ động xác định vị trí file lỗi qua các repo đã biết (`automation-core`, `tiktok-luot nuoi acc`), không bao giờ hỏi ngược lại user "gửi giúp đường dẫn repo hay tên script".
2. **Thứ tự phân loại bất biến trong `batch_aggregator.py`:**
   - **Ưu tiên 1 (Challenge/Captcha):** Kiểm tra `CHALLENGE_KEYWORDS` trước nếu `error_message` chứa từ khóa challenge/captcha hoặc `error_type` thuần challenge (ngoại trừ nhãn gộp `login-gms-verification`).
   - **Ưu tiên 2 (Session Lost P0):** Chỉ xếp vào `session_lost_failures` đối với các lỗi còn lại thực sự khớp từ khóa mất phiên (`logged out`, `văng`, `session expired`, `login screen`...).
