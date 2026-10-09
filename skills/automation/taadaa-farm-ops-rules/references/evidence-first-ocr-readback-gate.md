# Evidence-First OCR Readback Gate & Anti-Blind-Inference Protocol

## 1. Bối cảnh & Nguyên nhân sự cố (Case Study 16/09/2026)
- **Sự cố:** Khi đăng nhập tài khoản TikTok trên Máy 30, Agent chụp ảnh hiện trường màn hình bị kẹt. Trên ảnh thực tế có dòng chữ cảnh báo màu đỏ rất rõ:
  `"Số lần nhập sai tài khoản hoặc mật khẩu đã đạt giới hạn. Hãy thử lại sau 29m."`
- **Lỗi của Agent:** Agent chỉ nhìn vào accessibility XML (vốn không chứa text đỏ do giao diện vẽ bằng Canvas/WebView nội bộ SparkActivity), không dùng OCR đọc lại chính bức ảnh vừa chụp. Dẫn đến suy luận mù và kết luận sai lệch rằng "nút Tiếp bị mất callback JavaScript trong SparkActivity".
- **Người dùng chấn chỉnh:** Yêu cầu thiết lập cơ chế ép buộc Agent: **Đã chụp ảnh thì BẮT BUỘC phải chạy OCR đọc ảnh đối soát trước khi kết luận**, cấm suy đoán xàm.

## 2. Quy trình bắt buộc: "Screenshot -> WinRT OCR Readback -> Match -> Conclusion"
Tuyệt đối không được bỏ qua bước đọc ảnh. Luồng thực thi duy nhất:
```text
SCREENSHOT (Ảnh đóng băng hiện trường)
  └──> WinRT OCR READBACK (winrt_ocr.py)
        └──> KEYWORD SCAN (sai, giới hạn, thử lại sau, limit, lock, error)
              └──> SO KHỚP KẾT LUẬN (Ưu tiên số 1: Text người dùng nhìn thấy)
                    └──> PHÁT NGÔN / GỬI MEDIA:
```

## 3. Lệnh OCR chuẩn trên Windows (Zero-install)
Sử dụng script có sẵn trong skill `windows-native-ocr`:
```bash
python C:/Users/Kibe/AppData/Local/hermes/skills/productivity/windows-native-ocr/scripts/winrt_ocr.py "D:/Taadaa/m30_screen.png" --lang vi-VN
```

## 4. Checklist 3 câu hỏi tự kiểm tra (BẮT BUỘC trước khi trả lời User)
1. **Tôi đã chạy WinRT OCR trên chính file ảnh vừa chụp chưa?**
   - Nếu CHƯA -> DỪNG NGAY. Cấm phát ngôn về nguyên nhân lỗi.
2. **OCR có phát hiện thông báo đỏ, từ khóa lỗi hay thời gian đếm ngược không?**
   - Các từ khóa nhạy cảm: `nhập sai`, `giới hạn`, `thử lại sau`, `sai mật khẩu`, `incorrect password`, `limit`, `bắt buộc xác minh`, `captcha`.
   - Nếu CÓ -> BẮT BUỘC trích nguyên văn thông báo đó vào báo cáo làm bằng chứng cốt lõi.
3. **Kết luận của tôi có mâu thuẫn với nội dung hiển thị trên ảnh không?**
   - CẤM TUYỆT ĐỐI bịa lỗi kỹ thuật trừu tượng (như "lỗi callback JS", "kẹt layout") khi chưa loại trừ hoàn toàn các thông báo người dùng thấy được trên UI.
