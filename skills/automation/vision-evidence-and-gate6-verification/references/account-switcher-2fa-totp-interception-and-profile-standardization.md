# Bài Học Thực Chiến: Multi-Account Profile Switcher & Bẫy Chặn 2FA/TOTP Khi Chuẩn Hóa

## 1. Hiện Tượng & Bối Cảnh
- **Mục tiêu:** Chuẩn hóa profile (Tên, Bio, Avatar, Pin) cho tài khoản TikTok Farm trên thiết bị chạy multi-slot (ví dụ Máy 244 có 8 slot tài khoản).
- **Diễn biến sự cố:**
  1. Khi điều khiển ADB vào Máy 244, TikTok đang ở Profile của nick thuộc slot khác (`vokhanh0353` / `hanng015008`).
  2. Coordinator mở Account Switcher để chọn nick mục tiêu `@angthanhkhoa5528`.
  3. Sau khi bấm chọn nick trong Switcher, màn hình không chuyển ngay vào Profile mà TikTok kích hoạt chốt chặn bảo mật: **`Thiết lập xác minh 2 bước — Ứng dụng xác thực (TOTP)`** (yêu cầu nhập mã 6 số từ Authenticator).
  4. Nếu Coordinator vội vàng chụp ảnh màn hình hoặc dùng ảnh cũ lưu trong máy để báo cáo "đã hoàn tất chuẩn hóa", Coordinator sẽ phạm vào tội danh nghiêm trọng nhất: **Gửi ảnh mù / Báo cáo sai sự thật / Vi phạm Gate 6**.

---

## 2. Quy Tắc Đối Soát Switcher & Nhận Diện Chặn 2FA

### A. Quy Trình Chuyển Đổi Tài Khoản An Toàn (Safe Account Switch)
1. **Kiểm tra Profile hiện tại:**
   - Đọc OCR màn hình Profile: nếu handle `@...` không khớp nick mục tiêu, bắt buộc mở Account Switcher.
   - Bấm vào tên hiển thị ở góc trên bên trái màn hình (`input tap 250 320`) để mở danh sách tài khoản.
2. **Chọn đúng nick theo Bounds:**
   - Dùng `uiautomator dump` hoặc OCR xác định tọa độ chính xác của nick cần chuyển (ví dụ `angthanhkhoa5528` ở `[254,1446][709,1491]`, tap `400 1460`).
3. **Bắt Buộc Chụp Ảnh & OCR Đọc Trạng Thái Phản Hồi Ngay Sau Khi Tap:**
   - Tap xong PHẢI chờ 2–3s và chụp lại màn hình ngay.
   - Quét WinRT OCR để phân loại màn hình:
     * **Trường hợp A (Thành công):** Vào thẳng Profile của nick mới $\rightarrow$ Bắt đầu thi công chuẩn hóa.
     * **Trường hợp B (Bị chặn 2FA/TOTP):** OCR phát hiện các từ khóa:
       `Thiết lập xác minh 2 bước`, `Ung dung xac thuc`, `Authenticator`, `Ma da duoc gui den ung dung xac thuc`.
     * **Trường hợp C (Bị đăng xuất / Session expired):** OCR phát hiện màn hình Đăng nhập.

---

## 3. Kỷ Luật Xử Lý Khi Kẹt Màn Hình 2FA (TOTP Interception Discipline)

1. **FAIL-CLOSED Ngay Lập Tức:**
   - Khi phát hiện màn hình 2FA TOTP: **CẤM TUYỆT ĐỐI** báo cáo "Đã chuẩn hóa xong".
   - **CẤM TUYỆT ĐỐI** lấy ảnh cũ trong thư mục tạm (`user_img*.jpg`, `reports/`) gửi thay thế.
   - **CẤM TUYỆT ĐỐI** tap bừa 6 số hoặc mò mẫm qua mặt 2FA.
2. **Báo Cáo Hiện Trường Kèm Bằng Chứng Thị Giác (`MEDIA:`):**
   - Chụp ngay ảnh màn hình 2FA hiện tại (`m244_p244.png`).
   - Chạy `run_winrt_ocr.py` để lấy receipt hợp lệ.
   - Báo cáo rõ ràng: Nick đang kẹt màn hình 2FA TOTP (yêu cầu mã 6 số), đính kèm ảnh bằng chứng thật để chứng minh lý do task chưa thể hoàn thành.
3. **Bảo Vệ Phần Cứng:**
   - Nhấn `input keyevent 223` (hoặc đưa về Sleep) để tắt màn hình bảo vệ nhiệt độ và pin thiết bị trong lúc chờ giải quyết 2FA.
