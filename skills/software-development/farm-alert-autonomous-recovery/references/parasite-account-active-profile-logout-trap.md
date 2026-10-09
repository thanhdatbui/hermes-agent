# Bẫy Tử Huyệt Khi Dọn Nick Kí Sinh: Tài Khoản Kí Sinh Đang Là Active Profile (Active Profile Parasite Trap)

## 1. Hiện tượng & Bản chất lỗi
Khi chạy script dọn dẹp / logout nick kí sinh (`watchdog_idle_parasite_reconcile.py` hoặc runner tự động):
- Script mở Switcher bottom-sheet để tìm `@<username_kí_sinh>` rồi click chuyển sang nick đó trước khi vào Settings logout.
- **BẪY TỬ HUYỆT (FATAL TRAP)**: Nếu tài khoản kí sinh đang là **tài khoản active trên màn hình chính Profile** (được hiển thị ở Header `[36, 280][556, 364]`), TikTok v46.x **chỉ liệt kê các tài khoản phụ khác** trong danh sách switcher bottom sheet bên dưới!
- Script duyệt cây XML danh sách switcher không thấy `@<username_kí_sinh>`, dẫn đến ngộ nhận sai lầm:
  `"Nick @<username> da khong con trong Switcher!" -> return True`
  và lưu trạng thái `DONE` vào `parasite_reconcile_state.json`.
- Thực tế nick **chưa hề bị logout**, vẫn chiếm giữ vị trí active profile và chiếm 1 trong 8 slot của thiết bị suốt nhiều tuần mà không ai hay biết.

## 2. Hậu quả vận hành trên Farm
- Thiết bị bị đầy 8 tài khoản (hoặc 7 tài khoản + 1 nick kí sinh chiếm slot).
- Khi runner chạy ca nuôi có target account rơi vào các slot sau (đặc biệt Row 1 hoặc Row 8):
  - Target account bị đẩy ra khỏi viewport đầu tiên của switcher hoặc bị chiếm mất slot chưa được login, runner văng lỗi:
    `UploadHook: [ACCOUNT_SWITCHER_FAILED] select account failed: ACCOUNT_MISSING: expected account was not found.`
  - Watchdog batch aggregator tự động gộp exception này thành cảnh báo đỏ nguy hiểm: `⚠️ [P0 CẢNH BÁO MẤT PHIÊN / VĂNG ACCOUNT]`.

## 3. Quy trình chuẩn hóa Triage & Logout chuẩn xác (O1 Procedure)
1. **Kiểm tra Active Profile trước khi mở Switcher**:
   - Dump XML hoặc WinRT OCR trên màn hình Profile cá nhân.
   - So sánh username hiển thị tại header (`@<handle>`) với target parasite username cần logout.
   - **Nếu trùng khớp**: Tài khoản kí sinh chính là active profile! **TUYỆT ĐỐI KHÔNG mở Switcher bottom-sheet** để tìm nó nữa.
2. **Quy trình Logout trực tiếp từ Active Profile**:
   - Tại Profile: Tap Menu 3 gạch góc trên bên phải (`[954, 96][1056, 204]`, tâm `(1005, 150)`).
   - Tap `Cài đặt và quyền riêng tư` (Settings) (tọa độ `(548, 1276)`).
   - Cuộn xuống đáy Settings: Thực hiện 6-8 lượt `input swipe 540 1400 540 400 300` (safe swipe bounds tránh dính Samsung Pay và dock).
   - Tìm mục `Đăng xuất` (Logout) ở đáy trang (tâm khoảng `(282, 1662)`).
   - Xác nhận hộp thoại: `Bạn có chắc chắn muốn đăng xuất?` -> Tap `Đăng xuất` (nút đỏ/đậm, tâm `(540, 1664)`).
   - Tránh tap nhầm nút `Chuyển đổi tài khoản` ở trên nút Đăng xuất.
3. **Nghiệm thu sau Logout (Capture-Before-Cleanup & OCR Readback)**:
   - Sau khi logout, TikTok tự động chuyển về 1 trong các tài khoản phụ còn lại.
   - Điều hướng về tab Profile (`input tap 972 1857`).
   - Mở switcher (`input tap 296 322`), cuộn xuống đáy (`input swipe 540 1400 540 600 400`).
   - Chụp screencap và chạy WinRT OCR xác nhận:
     a) Danh sách accounts không còn chứa nick kí sinh.
     b) Đã xuất hiện lại nút `+ Thêm tài khoản` (Add account) ở đáy switcher.
   - Gửi ảnh nghiệm thu `MEDIA:<path>` kèm highlight OCR.
