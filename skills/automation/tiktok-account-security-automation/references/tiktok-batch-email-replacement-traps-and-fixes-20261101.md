# TikTok Batch Email Replacement: Traps, Concurrency & Resolution (2026-11-01)

## 1. Popup Xác Nhận Hai Lớp Khi Bấm "Thay Đổi Email"
- **Bẫy:** Sau khi tap vào dòng "Thay đổi email" trong modal ban đầu, TikTok không mở ngay ô nhập text mà bật thêm popup xác nhận 2 lớp:
  `Thay đổi email? Email mới của bạn cũng sẽ được dùng cho xác minh 2 bước. [Quay lại] [Tiếp tục]`
- **Hiện tượng:** Nếu worker bỏ qua popup này và cắm đầu gõ email / rút OTP, tọa độ gõ rơi vào màn hình cũ hoặc trượt sang "Chọn quốc gia" (`Chqn qu6c gia hoäc khu vVc`), làm nghẽn toàn bộ luồng đổi email.
- **Giải pháp chuẩn hóa:**
  Sau khi tap `Thay đổi email`, chụp ảnh kiểm tra `cafter.png`. Nếu thấy text chứa `('thay' in text and 'email' in text)` cùng nút `('tiếp tục' or 'tiép tvc')`, bắt buộc tap vào tâm nút `Tiếp tục` (tọa độ ~`[651, 1286, 849, 1339]`, trung tâm `(750, 1285)`) và đợi 3-4s cho app chuyển hẳn sang form input mới.

## 2. Bẫy Grant Hết Hạn (AADSTS70000) & Tranh Chấp Mail Trong Batch Đa Luồng
- **Bẫy 1 - Token Expired:** Một số refresh token của Hotmail bị hết hạn grant (`AADSTS70000: The grant is expired`). Nếu worker không bắt ngoại lệ HTTP 400 mà crash hoặc tiếp tục polling, nick sẽ bị kẹt hoặc worker chết im lặng.
  - **Khắc phục:** Pre-validate hoặc bắt `urllib.error.HTTPError`: nếu dính 400/invalid_grant, xóa mail khỏi pool sạch hoặc gán `oauth_status = 'EXPIRED'`, bốc ngay mail khác.
- **Bẫy 2 - Concurrency Race Condition:** Khi chạy song song `max_workers = 10`, nhiều worker cùng query SQLite `LIMIT 1` sẽ bốc trùng một email nếu chưa có cờ khóa tạm.
  - **Khắc phục:** Ngay khi bốc mail ra khỏi pool, worker phải atomic UPDATE `oauth_status = 'HOLD_CHANGE'`. Chỉ gán `ASSIGNED_TIKTOK` khi đổi thành công, hoặc giải phóng về `READY` nếu thất bại.
- **Bẫy 3 - SQLite NULL Trap Khi Lọc Trạng Thái (`oauth_status != 'ASSIGNED_TIKTOK'`):**
  - Trong SQL chuẩn của SQLite, mệnh đề `col != 'VAL'` hoặc `col NOT IN ('A', 'B')` sẽ **LOẠI BỎ TOÀN BỘ CÁC DÒNG CÓ `col IS NULL`** (vì NULL so sánh với bất kỳ giá trị nào đều ra NULL/False).
  - Nếu kho tài nguyên Hotmail mới nạp có `oauth_status` là NULL, câu lệnh query `WHERE oauth_status != 'ASSIGNED_TIKTOK'` sẽ trả về 0 dòng, khiến worker báo nhầm `"Het hotmail sach!"`.
  - **Khắc phục:** Bắt buộc viết rõ: `WHERE (mb.oauth_status IS NULL OR mb.oauth_status NOT IN ('ASSIGNED_TIKTOK', 'HOLD_CHANGE', 'EXPIRED'))`, hoặc chuẩn hóa giá trị mặc định của bảng thành `READY`.

## 4. Xử Lý Phân Cấp Menu Cài Đặt & Switcher Trên Samsung Galaxy S7
- **Phân cấp Menu Cài đặt:**
  - Trên các giao diện TikTok mới, mục *Cài đặt và quyền riêng tư* nằm ở sát đáy menu 3 gạch (`y ~ 1600`), sau đó trong trang Cài đặt mục *Tài khoản* nằm ở `y ~ 1817` và trang con *Thông tin tài khoản* ở `y ~ 326`.
  - Nếu worker tap nhầm vào giữa màn hình Cài đặt, app sẽ trượt vào các mục con như *"Thời gian sử dụng màn hình"* (màn hình có biểu đồ thời gian).
  - **Khắc phục:** Bắt buộc dùng WinRT OCR kiểm tra tiêu đề trang trước khi tiếp tục: nếu không thấy text `"Thông tin tài khoản"`, phải bấm Back thoát ra ngoài menu chính và retry, tuyệt đối không tap mù vào tọa độ form đổi email.
- **OCR Switcher tài khoản lẹm chữ:**
  - OCR trên app TikTok thường đọc nhầm chữ cái đầu tiên hoặc ký tự của username (ví dụ `@l.thanh.ngn311` bị đọc thành `I.thanh.ngn311` với chữ `I` hoa thay cho `l`, `@phungloan0138` đọc thành `phungIoan0138` với chữ `I` hoa thay cho `l`).
  - Worker cần dùng hàm chuẩn hóa chuẩn (Fuzzy Match):
    `norm_name = lambda s: s.lower().replace('l', 'i').replace('1', 'i').replace('.', '').replace('_', '').strip()`
    So sánh cả `username.lower() in text_item.lower()` lẫn `norm_name(username) in norm_name(text_item)` khi so khớp với danh sách Switcher để tránh nhận diện nhầm là "không tìm thấy nick".
- **Bẫy Màn hình "Xác minh danh tính" (Identity Verification Gate):**
  - Một số tài khoản TikTok khi bấm "Thay đổi email" bị TikTok chặn bởi màn hình *"Xác minh danh tính - Xác minh để là bạn"*.
  - Có 2 trường hợp:
    1. Chỉ cho phép gửi mã OTP về Gmail cũ đã DIE (`k***l@gmail.com`). Trường hợp này không thể đổi email được nữa nếu không cứu được Gmail. Worker bắt buộc phải nhận diện text `"xác minh danh tính"` và skip ngay sang nick khác để không làm nghẽn luồng.
    2. Cho phép xác minh bằng *"Mật khẩu"* (`Måt khäU`): Worker có thể tap vào dòng Mật khẩu, lấy password từ file Excel/SQLite điền vào để vượt qua gate xác minh rồi mới tiến hành nhập Hotmail mới.
- **Sự cố ảnh Screencap 12 bytes trên thiết bị rớt frame:**
  - Khi thiết bị Android bị lag hoặc rớt kết nối surface flinger, lệnh `adb exec-out screencap -p` hoặc `adb shell screencap -p` có thể tạo ra file ảnh rác rỗng chỉ có 12 bytes (`b'\x00\x00...'`).
  - Worker phải kiểm tra kích thước file ảnh chụp (`os.path.getsize > 1000` bytes): nếu ảnh < 1KB, bắt buộc sleep 2s và chụp lại qua phương thức thay thế (`adb shell screencap /sdcard/... && pull`) trước khi ném vào WinRT OCR để tránh làm sập luồng nhận diện.

## 3. Quản Lý Trạng Thái Ứng Dụng Chậm Trên Samsung Galaxy S7 (Splash Delay)
- **Đặc thù phần cứng:** Samsung S7 mở TikTok mất 8-12 giây màn hình đen logo splash.
- **Quy tắc:** Bắt buộc có sleep tối thiểu 10-12s kèm vòng lặp kiểm tra WinRT OCR `wait_app_ready()` bắt các từ khóa màn hình chính (`hö sd`, `trang ch`, `live`) trước khi gửi bất kỳ lệnh tap nào vào UI.
- **Popup Nhật ký che Switcher:** Khi mở trang cá nhân, nếu bị popup *"Thêm vào Nhật ký"* che khuất góc trên, bắt buộc tap dấu `x` (`[84, 144]`) để đóng popup trước khi tap mở Switcher tài khoản.
