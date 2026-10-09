# Quy Tắc Bất Biến Codex 5SIM Auto-Verify (INVARIANT CODEX 5SIM)

## 1. Bản chất sự cố WhatsApp trên OpenAI Add-Phone
- **Nguyên nhân cốt lõi**:
  - Việc OpenAI yêu cầu gửi OTP qua WhatsApp (`Chúng tôi sẽ gửi mã dùng một lần đến số của bạn qua WhatsApp...` hoặc thông báo `switched to WhatsApp`) là **DO CHÍNH TỪNG SỐ SIM CỤ THỂ** (số SIM đã từng được đăng ký/dùng SMS hoặc bị hệ thống OpenAI gắn cờ spam/recycled).
  - **TUYỆT ĐỐI KHÔNG PHẢI LỖI DO CẢ QUỐC GIA**: Không có chuyện một quốc gia bị cấm SMS vĩnh viễn. Trong cùng một quốc gia (Philippines, Argentina, Nam Phi, Ba Lan, Thái Lan...), số SIM 1 có thể dính WhatsApp nhưng số SIM 2, số SIM 3 vẫn nhận SMS bình thường.
  - **ĐỐI XỬ CHUẨN XÁC**: Dính WhatsApp tương đương 100% với số lỗi / không về OTP / timeout.

## 2. Quy tắc vận hành & Vòng lặp thử số (3 số/nước, tối đa 3 nước)
- **Quy trình xử lý chuẩn khi submit số**:
  1. **Bước 1 — Chọn SMS Radio**: Sau khi chọn quốc gia, quét tìm tùy chọn SMS (`label:has-text("Tin nhắn")`, `label:has-text("Text message")`, `input[type="radio"][value="sms"]`). Nếu có -> click chọn ngay để ưu tiên SMS.
  2. **Bước 2 — Submit & Bắt lỗi WhatsApp / Từ chối / Timeout**:
     - Nếu sau khi submit, OpenAI báo lỗi từ chối, `invalid_auth_step`, hoặc chuyển sang đòi WhatsApp (*"switched to WhatsApp"*, *"gửi mã qua WhatsApp"*), hoặc hết 45s không có OTP:
     - **Lập tức gọi `cancel_number(order_id)`** để 5SIM hoàn tiền 100% vào ví.
  3. **Bước 3 — Khôi phục form sạch (`reset_to_add_phone`) & Tiếp tục thử số cùng nước**:
     - Nếu trang bị văng khỏi form `add-phone`, gọi `reset_to_add_phone(page)` (điều hướng lại `https://auth.openai.com/add-phone`).
     - Dọn sạch ô nhập `input[type="tel"]`.
     - **TIẾP TỤC THỬ SỐ THỨ 2, SỐ THỨ 3 CỦA CHÍNH QUỐC GIA ĐÓ** (`continue` trong vòng lặp `c_try = 1..3`).
     - **CẤM TUYỆT ĐỐI `break` BỎ QUỐC GIA KHI GẶP WHATSAPP**.
  4. **Bước 4 — Chuyển nước & Kết thúc chu kỳ**:
     - **CHỈ ĐƯỢC CHUYỂN QUỐC GIA KHI**: Đã thử hết đủ **cả 3 số khác nhau** của quốc gia đó (`c_try` chạy hết 3 lượt) mà đều thất bại, HOẶC 5SIM báo hết sạch số (`no free phones`).
     - **CHỈ ĐƯỢC PHÉP DỪNG SCRIPT ĐỂ NGÂM COOLDOWN 24H KHI**: Đã duyệt hết đủ **cả 3 quốc gia** (trần 9 lần thử) mà không lấy được OTP, hoặc khi dính Cloudflare Turnstile bot detection không thể vào web.
     - CẤM dừng toàn bộ runner chỉ vì 1 số điện thoại đơn lẻ bị lỗi.

## 3. Kỷ luật lưu trữ: Khóa cứng vào Repo, CẤM lưu Memory cá nhân
- **Chỉ thị của User (2026-09-30)**:
  - *"K khoá vào memory. Khoá ở dự án thôi"*
  - Mọi quy tắc và ca xử lý hồi quy BẮT BUỘC phải được khóa cứng trực tiếp vào:
    1. **`PROJECT_RULES.md`** (Mục 5 - Invariant Codex 5SIM).
    2. **`tests/test_codex_closeout_regression.py`** (Test suite kiểm tra cấu hình trần 9 lần, 3 số/nước, cấm break khi gặp WhatsApp, mock runtime cancel và reset form).
  - Không lưu các quy tắc này vào persistent memory của Hermes Agent.
