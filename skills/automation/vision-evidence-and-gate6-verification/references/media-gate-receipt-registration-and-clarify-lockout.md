# Đăng Ký Receipt cho Media Gate & Xử Lý Chặn Clarify khi Hand-off Active

## 1. Cơ Chế Bảo Vệ Của `guard_media_vision_gate.py`
- Hook `guard_media_vision_gate.py` can thiệp vào tầng Gateway Telegram của Hermes, bắt buộc mọi ảnh đính kèm cú pháp `MEDIA:<path>` phải được soi mắt/nhận diện thực tế trước đó.
- Nếu gửi ảnh mà chưa có receipt hợp lệ trong `D:/Taadaa/runtime/vision_receipts.json`, Gateway sẽ chặn tin nhắn hoặc cảnh báo vi phạm Gate 6.
- Quy trình đăng ký receipt hợp lệ:
  ```bash
  python D:/Taadaa/tools/guard_media_vision_gate.py --register-receipt "<path_anh>" --ocr "<chuoi_token_nhan_dien>"
  ```
  - Output chuẩn: JSON chứa `receipt_id`, `sha256`, `mtime`, `signature`, và `reason_code: "OK"`.
  - TTL của receipt là 300 giây (5 phút). Ảnh phải tồn tại và không được chỉnh sửa sau thời điểm đăng ký.
- Tiền kiểm tra tin nhắn trước khi gửi:
  ```bash
  python D:/Taadaa/tools/guard_media_vision_gate.py --check-message "<toan_bo_tin_nhan_kem_MEDIA>"
  ```
  Nếu kết quả `passed: true`, tin nhắn chắc chắn không bị hook chặn ở tầng Gateway.
- **Tiêu chuẩn phản hồi kèm bằng chứng mắt thấy (What I See):**
  Trong tin nhắn gửi User kèm `MEDIA:<path>`, BẮT BUỘC mô tả ngắn gọn và chính xác các chi tiết đã thấy tận mắt qua `browser_vision` (tên hiển thị, username, bio, số lượng bài đăng, follower, layout có bị che/lỗi không). TUYỆT ĐỐI CẤM gửi đối phó chỉ quăng link ảnh mà không có bằng chứng đối soát.

## 2. Bẫy Gọi `clarify` Khi Hand-off Lock Đang Active
- Khi hệ thống có Strike 3 trượt Closeout Gate trên một repository nào đó, file cờ `D:/Taadaa/runtime/handoff_lock_active.json` sẽ được tạo ra để chuyển giao cho Claude CLI / Agy CLI.
- Trong thời gian này, công cụ `clarify` bị hook chặn cơ học:
  `[HARD GATE - CLOSEOUT DISCIPLINE] LỆNH 'clarify' BỊ CHẶN: Strike-3 Reviewer Hand-off đang active`
- **Cách xử lý đúng của Coordinator:**
  - TUYỆT ĐỐI KHÔNG thử gọi lại `clarify` để hỏi ý kiến User.
  - Phải trình bày đầy đủ các phương án (Option 1, 2, 3...) cùng phân tích ưu/nhược điểm và phương án khuyến nghị trực tiếp trong phần văn bản trả lời User.
  - Chờ User phản hồi bằng tin nhắn thường trong cuộc trò chuyện rồi tiếp tục thực thi.
