# Codex 5SIM Auto-Verify & WhatsApp Invariants (Kỷ Luật Chống Tự Chế Bậy)

## 1. Bản Chất Hiện Tượng WhatsApp Khi Xác Minh Codex OAuth
- **WhatsApp là do TỪNG SỐ SIM CỤ THỂ, KHÔNG PHẢI DO QUỐC GIA**:
  - Khi OpenAI hiển thị thông báo: *"Chúng tôi sẽ gửi mã dùng một lần đến số của bạn qua WhatsApp để xác minh..."* hoặc *"We couldn't send a text message to this phone number, so we switched to WhatsApp"*, đây là do **số SIM đó đã từng được đăng ký/dùng SMS hoặc bị backend OpenAI gắn cờ tái sử dụng/spam SMS**.
  - **Không có quốc gia nào bị cấm SMS vĩnh viễn**: Trong cùng một quốc gia (như Argentina, Philippines, Nam Phi, Ba Lan, Thái Lan...), số SIM 1 có thể bị ép WhatsApp, nhưng số SIM 2 hoặc SIM 3 vẫn nhận SMS bình thường.
  - **CẤM TUYỆT ĐỐI TỰ CHẾ BẬY**: Tuyệt đối CẤM Agent tự ý chèn lệnh `break` để bỏ luôn cả quốc gia khi gặp thông báo WhatsApp. Làm như vậy là phá vỡ hoàn toàn kỷ luật thử 3 số/nước của Sếp.

## 2. Quy Tắc Bất Biến 4 Bước Trong Vòng Lặp Mua Số (Strict Retry Invariant)
1. **Bước 1 — Chọn SMS Radio**: Sau khi chọn quốc gia, quét tìm tùy chọn SMS (`label:has-text("Tin nhắn")`, `label:has-text("Text message")`, `input[type="radio"][value="sms"]`). Nếu có -> click chọn ngay để ưu tiên gửi qua SMS.
2. **Bước 2 — Submit & Bắt Lỗi (Dính WhatsApp / Từ Chối / Timeout 45s = Thất Bại Số Đó)**:
   - Dính WhatsApp hoàn toàn tương đương số không về OTP hoặc số bị OpenAI từ chối.
   - Lập tức gọi `cancel_number(order_id)` để 5SIM hoàn tiền 100% vào ví ngay tại chỗ.
3. **Bước 3 — Khôi Phục Form Sạch (`reset_to_add_phone`) & Tiếp Tục Thử Số Cùng Nước**:
   - Nếu OpenAI đá văng khỏi form `add-phone`, gọi `reset_to_add_phone(page)` (điều hướng lại `https://auth.openai.com/add-phone`).
   - Dọn sạch ô nhập `input[type="tel"]`.
   - **BẮT BUỘC `continue` ĐỂ MUA TIẾP SỐ THỨ 2, SỐ THỨ 3 CỦA CHÍNH QUỐC GIA ĐÓ** (`c_try = 1..3`). Tuyệt đối CẤM `break` nhảy nước.
4. **Bước 4 — Chuyển Nước & Dừng Cooldown 24h**:
   - **CHỈ CHUYỂN NƯỚC KHI**: Đã thử hết đủ cả **3 số khác nhau** của nước đó (`c_try` chạy hết 3 lượt) mà đều thất bại, HOẶC 5SIM báo hết số (`no free phones`).
   - **CHỈ DỪNG SCRIPT ĐỂ NGÂM COOLDOWN 24H KHI**: Đã duyệt hết đủ cả **3 quốc gia** (trần 9 lần thử) mà không lấy được OTP, hoặc khi dính Cloudflare Turnstile bot detection cứng. CẤM dừng toàn bộ runner chỉ vì 1 số điện thoại đơn lẻ bị lỗi.

## 3. Kỷ Luật Đóng Đinh Invariant Vào Repo Test Suite (Chống Tự Chế)
- Mọi quy tắc và ca xử lý đã được kiểm chứng thành công bằng thực nghiệm BẮT BUỘC phải được viết thành **Test Case hồi quy cứng trong `D:\Taadaa\GPM auto\tests\test_codex_closeout_regression.py`** và bổ sung vào `PROJECT_RULES.md`:
  + `test_whatsapp_treated_as_number_failure_not_country_break`
  + `test_strict_3_numbers_per_country`
  + `test_price_threshold_strict`
  + `test_supervisor_records_codex_failure`
- Mọi thay đổi logic sau này bắt buộc phải pass 100% bộ test hồi quy này (`pytest tests/test_codex_closeout_regression.py`) trước khi được phép chạy hay nghiệm thu.
