# Quy Trình Đăng Xuất Một Tài Khoản TikTok 46.x & Bẫy Popup "Thêm số điện thoại" (2026-09-08)

## 1. Bối cảnh & Quy tắc bất biến
- **Quy tắc bất biến**: TUYỆT ĐỐI CẤM dùng `pm clear com.ss.android.ugc.trill` để đăng xuất một tài khoản, vì lệnh này sẽ xóa sạch toàn bộ các tài khoản khác đang đăng nhập trên thiết bị.
- Khi cần loại bỏ/đăng xuất một tài khoản cụ thể (tài khoản hỏng, trùng, hoặc theo chỉ định của user để dọn slot): BẮT BUỘC thực hiện tuần tự qua giao diện UI của TikTok.

## 2. Chi tiết luồng Đăng xuất chuẩn trên TikTok 46.x (Samsung Galaxy S7 1080x1920)

1. **Chuyển sang tài khoản đích cần đăng xuất**:
   - Nếu tài khoản hiện tại trên màn hình chưa phải là tài khoản cần đăng xuất, mở Account Switcher bằng cách tap vào display name ở header Profile (tâm `(540, 552)`) hoặc sticky header (tâm `(540, 150)`).
   - Trong bảng trượt Account Switcher, tìm node tương ứng với username cần đăng xuất và tap để chuyển sang.
   - Chờ 3-4s cho Profile của tài khoản đó tải xong.

2. **Mở Menu hồ sơ**:
   - Từ màn hình Profile chính của tài khoản cần đăng xuất, tap nút Menu 3 gạch ở góc trên cùng bên phải:
     - Resource ID / Desc: `content-desc="Menu hồ sơ"`
     - Bounds: `[948,96][1056,204]` -> Tâm: `(1002, 150)`.
   - Chờ 1.5s cho bottom-sheet menu xuất hiện.

3. **Chọn Cài đặt và quyền riêng tư**:
   - Trong bottom-sheet menu, tap vào mục "Cài đặt và quyền riêng tư" (Settings and privacy):
     - Resource ID: `com.ss.android.ugc.trill:id/dqo` (Button) hoặc `com.ss.android.ugc.trill:id/yxo` (TextView).
     - Bounds: `[204,1176][1038,1320]` -> Tâm: `(621, 1248)`.
   - Chờ 2-3s để trang Cài đặt mở ra hoàn toàn.

4. **Cuộn xuống đáy trang Cài đặt**:
   - Thực hiện vuốt cuộn màn hình từ dưới lên:
     - Lệnh: `adb shell input swipe 540 1600 540 400 250`
     - Thực hiện lặp lại 3-4 lần (mỗi lần nghỉ 0.5s - 1.0s) để cuộn xuống tận cùng danh sách cài đặt.

5. **Bấm nút Đăng xuất**:
   - Quét tìm node có text hoặc content-desc là `"Đăng xuất"` / `"Log out"`:
     - Bounds: `[24,1901][1056,1920]` -> Tâm: `(540, 1910)`.
   - Tap vào nút Đăng xuất.

6. **Xác nhận popup đăng xuất**:
   - TikTok hiển thị popup dialog xác nhận: *"Bạn có chắc chắn muốn đăng xuất?"*.
   - Tìm nút xác nhận đăng xuất màu đỏ:
     - Resource ID: `com.ss.android.ugc.trill:id/a64` (TextView) trong Button `[0,1584][1080,1740]`.
     - Tâm: `(540, 1662)`.
   - Tap vào nút xác nhận.

7. **Xử lý hậu đăng xuất**:
   - Chờ 4-5s để TikTok xử lý đăng xuất. Ứng dụng sẽ tự động chuyển sang một trong các tài khoản còn lại trên máy.
   - Nếu app quay về Home feed, tap tab Hồ sơ (`(972, 1857)` hoặc `(972, 1883)`) để về trang cá nhân.
   - Mở lại Account Switcher để kiểm tra danh sách: xác nhận tài khoản vừa đăng xuất đã biến mất hoàn toàn và số lượng tài khoản còn lại đúng như kế hoạch.

---

## 3. Bẫy Popup "Thêm số điện thoại" (Phone Number Prompt Trap)

- **Hiện tượng**: Sau khi mở TikTok hoặc sau khi chuyển đổi/đăng xuất tài khoản, TikTok có thể bung popup trượt *"Thêm số điện thoại"* kèm mô tả *"Thêm số điện thoại của bạn để tăng cường bảo mật, khôi phục tài khoản dễ hơn..."* và bàn phím ảo tự động bật lên.
- **Tác hại**: Bàn phím ảo và modal che khuất toàn bộ giao diện phía sau (các tab điều hướng đáy, Profile, v.v.), khiến flow đọc UI XML bị nhầm sang các node bàn phím (`com.sec.android.inputmethod` hoặc phím emoji/sticker).
- **Cách xử lý**:
  - Không nhấn BACK mù quáng khi chưa xác định trạng thái (tránh văng ra Launcher).
  - Tap trực tiếp vào nút Đóng ("X") ở góc trên bên phải popup:
    - Resource ID / Desc: `content-desc="Đóng"`
    - Bounds: `[936,84][1056,216]` -> Tâm: `(996, 150)`.
  - Sleep 1.5s để bàn phím và popup biến mất trước khi tiếp tục flow.
