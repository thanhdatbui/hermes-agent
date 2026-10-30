# Google Sign-in Personal Menu Overlay & Family Link Trap (2026-10-30)

## Hiện tượng & Nguyên nhân gốc rễ
1. **WebView UI Drop Node**:
   - Khi tap nút *"Tạo tài khoản"* (`center=(202, 1462)`), Google Sign-in trên WebView Android 7 sẽ mở một popup menu gồm 2 lựa chọn:
     - Mục 1 (ở trên, X=[150, 400], Y=[1250, 1380]): *"Dành cho mục đích cá nhân của tôi"*
     - Mục 2 (ở dưới hoặc cao hơn tùy layout): *"Dành cho trẻ em"* (Family Link)
   - Cả 2 node text này đều không xuất hiện trong cây ATX Accessibility XML dump (`fail_05_personal.xml`).

2. **Trap 1: False Bounce-Back Detection**:
   - Popup menu là lớp phủ (overlay) đè lên WebView, bên dưới vẫn còn node `identifierId`.
   - Hàm `_poll_personal` nếu kiểm tra `if "identifierId" in xml` quá 4 giây sẽ hiểu nhầm là bị "bật ngược trở lại (bounce-back)" màn hình đăng nhập, tự động văng `GOOGLE_CREATE_ACCOUNT_BOUNCE_BACK`.

3. **Trap 2: Family Link / Child Account Coordinate Collision**:
   - Tọa độ trước đây dùng thử `(350, 1180)` nằm quá cao và lệch sang phải, tap trúng mục *"Dành cho trẻ em"*.
   - Màn hình chuyển sang: *"Tạo Tài khoản Google cho trẻ - Cuộc phiêu lưu bắt đầu từ đây - Bắt đầu bằng một Tài khoản Google (Google Family Link)"*.
   - Hậu quả: Script bị kẹt ở bước nhập Họ Tên vì không tìm thấy 2 trường `firstName` / `lastName` của tài khoản cá nhân thông thường.

4. **Trap 3: must_tap_text khi màn hình đã chuyển**:
   - Khi tap tọa độ chuẩn `(250, 1320)`, popup menu biến mất và màn hình lập tức chuyển sang form điền Họ Tên.
   - Nếu script vẫn gọi `must_tap_text("Dành cho mục đích cá nhân")`, lệnh sẽ văng lỗi vì text menu không còn trên màn hình.

---

## Giải pháp kỹ thuật chuẩn hóa O(1)
1. **Calibrated Coordinates**:
   - Nút *"Tạo tài khoản"*: `(202, 1462)`.
   - Popup *"Dành cho mục đích cá nhân"*: `(250, 1320)` (ngay phía trên nút Tạo tài khoản, căn chuẩn bên trái).
2. **Grace Transition Check**:
   - Trong `_poll_personal`, khi thấy `identifierId` ổn định 4s, tap `(250, 1320)`.
   - Nếu XML sau tap có `firstName` hoặc `BẮT ĐẦU!` hoặc `Cuộc phiêu lưu`, return ngay trạng thái thành công và BỎ QUA lệnh `must_tap_text`.
3. **Thẩm định bằng Vision**:
   - Chụp screenshot `05_personal.png` và dùng `browser_vision` xác nhận màn hình đích là *"Tạo Tài khoản Google - Nhập tên của bạn"* (chứa ô Họ `Dao`, Tên `Ngoc Thuy Trang` và nút Tiếp theo màu xanh).
