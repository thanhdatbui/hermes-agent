# Vietnamese Profile Entropy & 7-Day Rename Discipline

## 1. Kết Quả Kiểm Toán Thực Tế 587 Tài Khoản Farm (2026-10-15)

Đối soát thực tế toàn bộ 587 nick trên farm Kibe:
- **172 nick (29.3%):** Đạt chuẩn danh tính người thật $\ge 2$ từ, viết hoa tự nhiên hoặc Tên + Nickname (*Thanh Hà Dương, Linh Bông, Vy Miu, Hoàng Như Vy, Mỹ Ngọc*...).
- **415 nick (70.7%):** Bị rập khuôn bot/shop:
  1. Trùng username thô có đuôi số: `lieuhoan03`, `luutuoi02`, `buithudung2011`, `bronsontruss38` (320+ nick).
  2. Nối chữ không dấu cách: `tranngan`, `vophuc7`, `ninhy0510`, `lequynh20` (70+ nick).
  3. Tên cụt lủn 1 từ: `Hà`, `Đạt`, `An` (20+ nick).

## 2. Phân Bổ Danh Tính Entropy Tự Nhiên (30% Nickname + 70% Họ Đệm Tên)
- **Nhóm 30% Tên + Biệt danh đời thường:**
  - Cấu trúc: `<Tên chính> <Nickname thân mật>`
  - Ví dụ: *Linh Bông, Vy Miu, An Kem, Đạt Còi, Chi Cún, Mai Bơ, Nhi Nấm, Hoàn Bơ, Tươi Bơ, Tươi Miu...*
- **Nhóm 70% Họ + Đệm + Tên / Đệm + Tên:**
  - Cấu trúc: `<Họ> <Đệm> <Tên>`
  - Ví dụ: *Hoàn Liễu, Tươi Lưu, Trần Minh Đạt, Nguyễn Hoài An, Ngọc Linh, Khánh Vy, Thanh Thảo...*

## 3. Quy Tắc Kỹ Thuật Đổi Tên Qua ADB & State Machine
1. **AdbKeyboard Base64 Input:**
   Luôn encode UTF-8 Base64 chuỗi có dấu trước khi bắn broadcast vào điện thoại:
   ```bash
   adb shell am broadcast -a ADB_INPUT_B64 --es msg "<base64_string>"
   ```
2. **Xử lý Popup Modal 7 Ngày:**
   TikTok có hạn chế cứng: Chỉ cho phép đổi biệt danh 1 lần / 7 ngày. Khi tap Lưu, luôn xuất hiện dialog xác nhận:
   - OCR bắt các từ khóa: `biệt danh`, `7 ngày`, `Xác nhận`.
   - Tap nút `Xác nhận` để lưu và kiểm tra lại màn Profile.
3. **Unit Test Assertions (`is_target`):**
   - Không dùng so khớp chuỗi lỏng lẻo (SequenceMatcher ratio $\ge 0.6$) khi không kiểm tra độ dài từ.
   - Bắt buộc kiểm tra `len(words) >= 2` để tránh việc từ đơn lẻ (`"Tươi"`) bị nhận nhầm thành tên đầy đủ (`"Tươi Lưu"`).
