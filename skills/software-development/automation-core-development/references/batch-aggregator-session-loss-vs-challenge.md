# Phân định Cảnh Báo Mất Phiên (Session Loss) vs Thách Thức Tạm Thời (Challenge/Captcha) trong batch_aggregator.py

## 1. Bối cảnh & Vấn đề gốc
Trong module `automation_core.batch_aggregator`:
- Trước đây, `AUTH_CRITICAL_KEYWORDS` gom chung các từ khóa xác minh (`verification`, `manual_challenge`, `checkpoint`) cùng với lỗi mất session thật sự (`login`, `văng`).
- Hậu quả: Khi 1 máy gặp captcha hoặc xuất hiện marker xác minh tạm thời (như `manual_challenge marker detected`), hệ thống quy chụp thành `⚠️ [P0 CẢNH BÁO MẤT PHIÊN / VĂNG ACCOUNT]`, gây báo động giả (false alarm) và hoang mang cho operator rằng account đã bị die / văng phiên, trong khi thực tế chỉ cần giải captcha hoặc vượt checkpoint tạm thời.

## 2. Quy tắc phân định từ khóa chuẩn (Keyword Partitioning)

### a. Mất phiên thật sự / Văng nick (`SESSION_LOST_KEYWORDS`)
Chỉ kích hoạt `⚠️ [P0 CẢNH BÁO MẤT PHIÊN / VĂNG ACCOUNT]` khi gặp đúng các dấu hiệu mất phiên, bắt buộc phải login lại từ đầu:
- `'logged out'`
- `'signed out'`
- `'văng'`
- `'session expired'`
- `'phiên đã hết hạn'`
- `'login screen'`
- `'đăng nhập lại'`
- `'require_login'`

*Lưu ý:* Không dùng chuỗi chung chung `'login'` vì dễ match nhầm step name, hàm login, hay thông báo phụ.

### b. Thách thức / Captcha / Xác minh tạm thời (`CHALLENGE_KEYWORDS`)
Chỉ cảnh báo mức `⚠️ [CẢNH BÁO XÁC MINH / CAPTCHA TẠM THỜI]`, tuyệt đối KHÔNG dùng tag `P0 MẤT PHIÊN / VĂNG ACCOUNT`:
- `'verification'`
- `'manual_challenge'`
- `'checkpoint'`
- `'captcha'`
- `'verify'`

## 3. Logic xử lý trong `evaluate_batch` & `format_alert_message`

1. **Phân loại độc lập & ưu tiên Session Lost:**
   - Máy có lỗi thuộc `SESSION_LOST_KEYWORDS` đưa vào `session_lost_failures`.
   - Máy lỗi thuộc `CHALLENGE_KEYWORDS` và **chưa nằm trong `session_lost_failures`** đưa vào `challenge_failures`.
2. **Kích hoạt cảnh báo (`should_alert`):**
   - Kích hoạt khi có cụm lỗi hệ thống (`systemic`), hoặc có máy mất phiên (`session_lost_failures`), hoặc có máy gặp challenge (`challenge_failures`).
3. **Định dạng thông điệp Telegram:**
   - Nếu có `session_lost_failures`: Giữ cảnh báo `⚠️ <b>[P0 CẢNH BÁO MẤT PHIÊN / VĂNG ACCOUNT]:</b>`.
   - Nếu có `challenge_failures`: Thêm khối `⚠️ <b>[CẢNH BÁO XÁC MINH / CAPTCHA TẠM THỜI]:</b> Phát hiện X máy dính checkpoint/captcha tạm thời:`.
   - Nếu máy chỉ dính challenge, không bao giờ xuất hiện chữ `P0 CẢNH BÁO MẤT PHIÊN` trong thông điệp.
