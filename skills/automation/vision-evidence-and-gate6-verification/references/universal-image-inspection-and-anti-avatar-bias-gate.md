# Universal Image Inspection & Anti-Avatar-Bias Gate Architecture

## 1. Bối Cảnh & Phê Bình Trực Tiếp Từ User (User Correction)
Trong phiên làm việc 2026-10-28, khi hệ thống điều tra Farm Alert và gặp lỗi gián đoạn do Media Gate, User đã trực tiếp chỉ ra lỗi thiết kế cốt lõi của `guard_media_vision_gate.py`:
> *"Cái vision guard gate mục đích của tao là ép AI khi gửi ảnh thì phải đọc lại ảnh kiểm tra suy luận của nó tránh việc nó gửi ảnh 1 kiểu còn nó bịa ra 1 kiểu. Thì thiết kế v t thấy k ổn, tự nhiên chỉ mỗi ava là chịu đọc lại ảnh"*

## 2. Phân Tích Ba Lỗi Thiết Kế Ngớ Ngẩn Của Gate Cũ
1. **Thiên Vị Avatar (Anti-Avatar-Bias):**
   - Phiên bản cũ chỉ ép buộc `browser_vision` (soi mắt) đối với các file ảnh mang tên `avatar`, `proposal`, `canvas`.
   - Với các ảnh UI hệ thống khác (màn hình lỗi, đăng nhập, cài đặt wifi, switcher, popup, captcha), gate chỉ kiểm tra token OCR lỏng lẻo hoặc bỏ qua.
   - Hậu quả: AI có thể gửi ảnh màn hình báo lỗi đỏ (`Mật khẩu sai`, `Lỗi mạng`, `Không có Internet`) nhưng trong text lại tự bịa ra là *"đã hoàn thành / mọi thứ bình thường"*, gate hoàn toàn không bắt được vì ảnh không mang tên "avatar".
2. **Bẫy Từ Khóa Mù Quáng (Keyword Trapping):**
   - `is_visual_claim` quét mù các từ tiếng Việt thông thường như `"de xuat"`, `"phuong an"` khiến các tin nhắn trao đổi kế hoạch kỹ thuật, báo cáo phương án xử lý bị nhận diện nhầm thành claim mỹ thuật về tranh ảnh, chặn đứng tin nhắn hợp lệ.
3. **Cơ Chế Phản Hồi Degraded Gây Phẫn Nộ:**
   - Khi gate chặn tin nhắn, thay vì inject prompt buộc AI đọc lại ảnh và sửa lại suy luận (forced re-reasoning loop), gate ở tầng egress lại nuốt mất tin nhắn và ném chuỗi kỹ thuật robot `Trạng thái: DEGRADED | Mã: ...` ra Telegram cho User.

## 3. Kiến Trúc Chuẩn Hóa Mới (Universal Inspection & Entity Grounding)
1. **Bình Đẳng Cho Mọi Ảnh Gửi Ra (`MEDIA:`):**
   - Bất kỳ ảnh nào đính kèm thẻ `MEDIA:<path>` (dù là avatar, switcher, màn hình login, popup lỗi hay setting), AI **BẮT BUỘC** phải có thao tác đọc ảnh thật (`browser_vision` hoặc `WinRT OCR`) còn tươi trong vòng 300s.
2. **Cross-Check Thực Thể Cốt Lõi (Entity Grounding):**
   - Khi AI khẳng định thao tác trên một thực thể (tên tài khoản `@username`, mã máy `M261`, tên SSID Wi-Fi `admin 1`): Text của OCR/Vision BẮT BUỘC phải chứa hoặc khớp với thực thể đó.
   - Khi AI khẳng định "Thành công / Bình thường" nhưng ảnh chứa các cụm từ lỗi rõ ràng (`Mật khẩu sai`, `Không có kết nối Internet`, `Tài khoản bị khóa`, `Captcha`): Gate FAIL-CLOSED ngay lập tức vì bịa đặt bằng chứng.
3. **Chống Rò Rỉ Degraded Template:**
   - Tuyệt đối cấm xuất chuỗi `Trạng thái: DEGRADED` ra chat Telegram của User. Mọi mâu thuẫn phải được đưa về luồng re-reasoning nội bộ để AI tự đính chính phát ngôn theo đúng những gì nhìn thấy trên ảnh.
