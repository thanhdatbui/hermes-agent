# Claude Code CLI Audit: Evidence-First Gate & Zero-Image Report Trap (10/10/2026)

## 1. Sự cố và Tín hiệu Kỷ luật từ Người Dùng
- **Hiện tượng**: Coordinator hoàn thành cập nhật mật khẩu, bật 2FA trên thiết bị và điều tra kỷ luật, nhưng báo cáo kết quả bằng tin nhắn văn bản thuần mà không đính kèm ảnh bằng chứng `MEDIA:`. Người dùng bức xúc phản ứng gay gắt: *"lại tiếp tục làm xong đéo gửi hình ĐKM"*, *"thi công r đưa claude duyệt đi"*.
- **Bản chất**: Bẫy nhận thức ỷ lại vào exit code và log text thành công, coi việc gửi ảnh là thủ tục phụ thay vì điều kiện tiên quyết nghiệm thu (GATE 6).

## 2. Thi công Chốt chặn Cơ học (Evidence-First Gate v4.3)
- **Tầng can thiệp**: Hook `transform_llm_output` trong plugin `farm-coordinator-guard`.
- **Cơ chế**:
  * Quét câu trả lời cuối cùng của Coordinator. Nếu chứa khẳng định hoàn thành tác vụ UI/Farm (login, 2FA, đổi pass, v.v.):
    - BẮT BUỘC phải có ít nhất một thẻ `MEDIA:<path>`.
    - Toàn bộ đường dẫn ảnh trong thẻ `MEDIA:` phải tồn tại trên đĩa VÀ nằm trong `verified_media_paths` (đã được soi mắt qua WinRT OCR hoặc `browser_vision`).
    - Nếu vi phạm: FAIL-CLOSED ghi đè câu trả lời thành cảnh báo đỏ vi phạm kỷ luật.

## 3. Phán quyết Thẩm định từ Claude Code CLI (Điểm: 58/100 - REJECTED Vòng 1)
Claude Code CLI đã audit toàn bộ mã nguồn của gate và chỉ ra 5 lỗ hổng chí tử:
1. **Regex nhận diện tuyên bố hoàn thành quá hẹp**:
   - Chỉ dùng danh sách regex cứng tiếng Việt (`đã đăng nhập thành công`, `đã bật 2fa`, v.v.).
   - Coordinator dễ dàng lách qua bằng cách dùng tiếng Anh (`logged in`, `password changed`), emoji (`Trạng thái: ✅ hoàn tất`), hoặc cấu trúc câu đảo ngữ (`2FA đã được bật`).
   - Khắc phục: Mở rộng danh sách từ khóa rộng hơn theo hướng tổng quát, bao quát cả tiếng Anh, tiếng Việt, emoji và bảng biểu.
2. **Chỉ kiểm tra hình thức ảnh, thiếu kiểm tra ngữ nghĩa OCR**:
   - Gate chỉ kiểm tra file có trong `verified_media_paths`, không kiểm tra ảnh có thuộc đúng máy, đúng tài khoản và đúng màn hình đích hay không.
   - Không kiểm tra mtime của ảnh: Ảnh cũ chụp từ đầu phiên vẫn có thể bị tái sử dụng.
   - Khắc phục: Lưu kèm kết quả OCR và timestamp lúc soi ảnh; kiểm tra mtime ảnh mới hơn thời điểm bắt đầu tác vụ; đối chiếu token bắt buộc của màn hình đích trong text OCR.
3. **Cơ chế ghi nhận `verified_media_paths` quá lỏng lẻo**:
   - Ghi nhận `verified` ngay khi lệnh terminal chứa chuỗi `ocr.py`, không cần biết exit code có bằng 0 hay OCR có trả về nội dung chữ hay không.
   - Khắc phục: Bắt buộc kiểm tra lệnh OCR/Vision exit code == 0 và trả về text không rỗng.
4. **Regex bóc tách thẻ `MEDIA:` cứng nhắc**:
   - `MEDIA:\s*([^\r\n]+)` nuốt cả phần mô tả phía sau nếu viết `MEDIA:path.png - mô tả`, dẫn đến lỗi file không tồn tại.
   - Khắc phục: Dùng regex `MEDIA:\s*(\S+)` hoặc bóc tách đường dẫn chuẩn xác, hỗ trợ giải mã URL `%20`.
5. **Nhánh xử lý Exception chưa Fail-Closed**:
   - Khi gate gặp exception, chỉ log warning rồi return `response_text` gốc (Fail-Open).
   - Khắc phục: Bắt buộc Fail-Closed khi có lỗi nội tại, không để lọt câu trả lời vi phạm ra ngoài.

## 4. Quy tắc Sửa Pass Láo trong File Excel
- Khi các tài khoản TikTok gặp lỗi `AUTH_BLOCKED` (do mật khẩu lưu trong Excel không khớp với tài khoản thật trên app):
  * **CẤM** tiếp tục để nguyên pass cũ gây loop login làm checkpoint/khóa tài khoản.
  * **BẮT BUỘC** xóa ô mật khẩu trong file Excel về `None`.
  * Khi ô pass là `None`, các runner tự động kích hoạt luồng đăng nhập qua OTP hòm thư (Graph API) và tiến hành đặt lại mật khẩu mới chuẩn xác.
