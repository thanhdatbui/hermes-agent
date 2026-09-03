# Chẩn đoán lỗi báo nhầm "Sai mật khẩu" (False-Positive Wrong Password) — 2026-08-21

## Bối cảnh & Hiện tượng (Máy 44 & Máy 70)
- **Sự cố:** 2 tài khoản `MaralynGroener6977@hotmail.com` và `TerraRau76115@hotmail.com` bị hệ thống báo sai mật khẩu (`Mật khẩu đó không đúng...`) và đưa vào danh sách yêu cầu shop bảo hành. Tuy nhiên, shop đăng nhập kiểm tra trên web thì mật khẩu hoàn toàn chính xác.
- **Yêu cầu kiểm tra lại:** Khóa máy an toàn (`device_lock`), kiểm tra và đăng nhập lại bằng tay/script từng bước.

## Nguyên nhân gốc rễ (Root Cause Analysis)
1. **WebView Loading & Race Condition:**
   - Sau khi nhập email và bấm `TIẾP TỤC` / `Enter`, Outlook app trên Android không luôn nhảy thẳng vào form password của Microsoft mà có thể rơi vào:
     - Màn hình trắng / Loading spinner (mạng proxy chậm hoặc WebView khởi tạo).
     - Màn hình *"Chọn loại tài khoản"* (`ChooseAccountActivity` - Microsoft/Khác/Nâng cao).
   - Nếu script không xử lý màn hình *"Chọn loại tài khoản"* (bấm vào entry Outlook) hoặc timeout khi chờ form password, runner sẽ fail `OUTLOOK_APP_PASSWORD_FIELD_NOT_FOUND` hoặc dừng dở dang.
2. **AdbKeyboard Broadcast bị nuốt trên WebView Microsoft:**
   - Lệnh broadcast `ADB_KEYBOARD_INPUT_TEXT` có thể không ăn vào ô password của WebView nếu chưa có con trỏ nhấp nháy hoặc bàn phím hệ thống đang active.
   - Khi đó, ô password bị trống -> bấm submit không có tác dụng hoặc script hiểu nhầm là lỗi đăng nhập.
3. **Quy tắc phân loại lỗi sai mật khẩu bị lỏng lẻo:**
   - Bất kỳ trạng thái dừng nào trước khi vào được Inbox đều bị gán nhầm là "sai pass" nếu không kiểm tra chặt chẽ UI proof.

## Giải pháp & Quy trình chuẩn hóa
1. **Điều kiện duy nhất để kết luận sai mật khẩu (Báo Shop):**
   - **BẮT BUỘC:** Chụp screencap và dùng OCR/Vision hoặc XML matcher xác nhận dòng chữ màu đỏ cảnh báo từ Microsoft:
     `! Mật khẩu đó không đúng với tài khoản Microsoft của bạn.` (hoặc `That password is incorrect`).
   - Nếu màn hình là trắng, loading, dừng ở nút *Tiếp theo* mà chưa submit, hoặc đang ở màn hình chọn loại tài khoản -> **TUYỆT ĐỐI KHÔNG BÁO SAI PASS**.
2. **Kỹ thuật gõ Password WebView đáng tin cậy:**
   - Tap đúng tâm ô password `(540, 690)`.
   - Nếu AdbKeyboard không điền được (kiểm tra ô vẫn trống): dùng direct text input:
     `adb shell input text '<password>'` sau đó gửi `adb shell input keyevent 66` (Enter) để submit.
3. **Chuỗi vượt màn hình sau submit password:**
   - *"Bạn muốn thêm một khoản khác không?"* -> Tap `(300, 1770)` ("CÓ LẼ ĐỂ SAU").
   - *"Dữ liệu của bạn, theo cách của bạn"* -> Tap `(875, 1835)` ("TIẾP THEO").
   - *"Cùng nhau cải thiện"* -> Tap `(540, 1760)` ("TỪ CHỐI").
   - *"Nâng tầm trải nghiệm"* -> Tap `(825, 1830)` ("TIẾP TỤC VỚI OUTLOOK").
   - Xác nhận vào Inbox Zero: *"Đã xong công việc hôm nay / Tận hưởng hộp thư đến trống"*.
   - Mở Drawer `(60, 150)`: Kiểm tra dòng đầu tiên dưới chữ Outlook = đúng email target.
