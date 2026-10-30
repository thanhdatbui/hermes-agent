# Bẫy Tường Trình Khống Không Đính Kèm Ảnh (Evidence Claim Omission Trap) & Kỷ Luật Xuất Thẻ MEDIA Trong Cùng Turn Báo Cáo

## 1. Ngữ cảnh & Sự cố thực tế (Incident Context)
- **Tình huống:** Trong phiên điều phối xử lý tự động đăng nhập Meta/Facebook và Muse AI trên profile GPM kẹp Proxy US, Coordinator đã dùng WinRT OCR và các lệnh probe chụp được màn hình các bước:
  - Bị Facebook đòi 2FA qua WhatsApp số lạ (`D:/fb_search_email.png`).
  - Facebook văng popup chặn `Invalid request` khi submit mật khẩu (`D:/fb_after_pass_entered.png`).
  - Màn hình Muse AI bị kẹt tại thử thách chọn ảnh reCAPTCHA Enterprise (`D:/muse_step4_recaptcha_clicked.png`).
- **Lỗi vi phạm nghiêm trọng:** Coordinator viết báo cáo bằng văn bản rất chi tiết, mô tả cặn kẽ *"Bằng chứng thật"*, *"Ảnh fb_search_email.png"*, *"Ảnh fb_after_pass_entered.png"*, nhưng **QUÊN / KHÔNG ĐÍNH KÈM THẺ `MEDIA:<path>`** trong lượt phản hồi đó.
- **Hậu quả:** User phản hồi bức xúc ngay lập tức bằng câu hỏi duy nhất: *"Hình đâu"*. Mọi lý giải văn bản dù chính xác đến đâu đều trở nên vô giá trị khi thiếu ảnh trực quan chứng minh thực tế tại chỗ.

---

## 2. Quy tắc cốt lõi (Core Invariant)
1. **Tuyệt đối cấm báo cáo mồm về ảnh:** Nếu trong tin nhắn có nhắc đến *"ảnh chụp màn hình"*, *"bằng chứng thực tế"*, *"kết quả hiển thị"*, hoặc đề cập đến file ảnh, Coordinator **BẮT BUỘC PHẢI XUẤT THẺ `MEDIA:<path>` NGAY TRONG LƯỢT PHẢN HỒI ĐÓ**.
2. **Kỷ luật Soi Mắt trước khi gửi:**
   - Trước khi xuất thẻ `MEDIA:<path>`, BẮT BUỘC gọi `browser_vision` (mở qua URL `file:///...`) để kiểm tra ảnh:
     - Đúng màn hình đích.
     - Không bị màn hình đen / rỗng.
     - Đúng trạng thái mới nhất.
   - Kèm câu xác nhận ngắn gọn nội dung đã thấy qua vision trong tin nhắn.
3. **Cấm hoãn gửi ảnh sang turn sau:** Tuyệt đối không được mô tả lỗi trước rồi chờ User hỏi *"Hình đâu"* mới bắt đầu gửi ảnh. Bằng chứng thị giác phải đi liền với kết luận lỗi trong cùng một tin nhắn.
