# Kỷ Luật Di Chuyển Nick Giải Phóng Trần 8 Slot: Bật 2FA Trước -> Out Sau -> Nạp Mới (2026-10-12)

## 1. NGUYÊN TẮC BẤT DI BẤT DỊCH (USER CORRECTION DIRECTIVE)
Khi một thiết bị Android farm đã kịch trần 8 tài khoản (hoặc có nick dư cần chuyển sang máy khác để nạp nick mới):
- **CẤM TUYỆT ĐỐI**:
  1. Đăng xuất nick cũ khi CHƯA bật 2FA TOTP và chưa lưu mật khẩu an toàn (nguy cơ mất phiên hoặc mất quyền truy cập tài sản farm).
  2. Cố gắng đăng nhập nick mới khi máy vẫn đang đủ 8 nick (TikTok sẽ ẩn hoàn toàn nút `Thêm tài khoản` / `Add account` và văng lỗi `04_add_account`).
- **THỨ TỰ THỰC THI 4 BƯỚC BẮT BUỘC**:
  1. **Bước 1 — Bật 2FA & Mật khẩu trên máy nguồn**:
     - Trong khi tài khoản vẫn đang đăng nhập trên thiết bị hiện tại, chạy runner kích hoạt Xác minh 2 bước (Authenticator App).
     - Trích xuất 2FA Secret Key (32 ký tự) và khởi tạo Mật khẩu TikTok đạt chuẩn (18 ký tự).
  2. **Bước 2 — Lưu trữ hồ sơ sang máy đích**:
     - Ghi nhận đầy đủ thông tin: ID, Password, 2FA Secret Key, Email, Pass mail vào Master DAT (`taikhoan_dat_v2_updated .xlsx`) và các bảng ca (`TikN.xlsx`, `taikhoan_run_safe.xlsx`) của máy đích.
     - TUYỆT ĐỐI KHÔNG đăng nhập vội lên máy đích nếu chưa có chỉ đạo (tuân thủ thời gian ngâm nguội).
  3. **Bước 3 — Đăng xuất nick trên máy nguồn để giải phóng slot**:
     - Thực hiện quy trình logout chuẩn: Profile -> Menu 3 gạch -> Cài đặt và quyền riêng tư -> Cuộn đáy -> Bấm Đăng xuất -> Xác nhận.
     - BẮT BUỘC chụp ảnh nghiệm thu Switcher kiểm chứng danh sách đã giảm xuống còn 7 nick.
  4. **Bước 4 — Đăng nhập nick thay thế vào máy nguồn**:
     - Khi máy đã còn 7 nick, nút `Thêm tài khoản` sẽ hiển thị trở lại.
     - Thực hiện đăng nhập nick mới vào máy nguồn để khôi phục cấu trúc 8 nick.

---

## 2. CẠM BẪY KỸ THUẬT & BẢN VÁ (TECHNICAL PITFALLS)

### A. Cạm bẫy Swipe Overshoot làm văng Bottom Sheet Switcher trên S7 (1080x1920)
- **Hiện tượng**: Khi Switcher chứa 7 tài khoản, nút `Thêm tài khoản` nằm ở đáy dưới fold. Script chạy lệnh cuộn `swipe(540, 1500, 540, 800)` nhưng ngay sau đó văng lỗi không tìm thấy nút và màn hình bị rơi về Trang chủ (Feed).
- **Nguyên nhân**: Mép trên của bottom sheet TikTok nằm ở khoảng `y=1050 - 1100`. Thao tác vuốt từ `y=1500` lên `y=800` đã kéo ngón tay ra ngoài vùng bottom sheet (vào vùng dimmed trong suốt phía trên). Android coi đây là sự kiện `TOUCH_OUTSIDE` và lập tức dismiss bottom sheet, trả UI về Feed.
- **Giải pháp**:
  - Giới hạn tọa độ vuốt nằm trọn trong lòng bottom sheet: `swipe(540, 1500, 540, 1100, 400)`.
  - Bổ sung fallback an toàn: Nếu bottom sheet không thấy nút, điều hướng qua *Menu hồ sơ -> Cài đặt và quyền riêng tư -> cuộn đáy Settings -> tap 'Thêm tài khoản'*. Trong màn hình Settings toàn màn hình, thao tác cuộn không bao giờ bị văng dialog.

### B. Cạm bẫy phím Back (Keyevent 4) sau khi Switch tài khoản
- **Hiện tượng**: Script switch sang nick cần logout, sau đó gửi liên tiếp `keyevent 4` để tắt popup nhưng làm TikTok thoát ra Launcher. Các bước tap Menu sau đó bấm vào khoảng trống ngoài màn hình chính.
- **Giải pháp**: Tuyệt đối không dùng `keyevent 4` mù quáng. Sử dụng `find_text_tap` có kiểm tra XML và OCR:
  `find_text_tap("Hồ sơ")` -> `find_text_tap("Menu hồ sơ")` -> `find_text_tap("Cài đặt và quyền riêng tư")`.

### C. Cạm bẫy thiếu phương thức `swipe()` trong `_CanonicalAdapter`
- **Hiện tượng**: Runner 2FA báo lỗi `ACCOUNT_NOT_IN_SWITCHER` dù nick rõ ràng có trong máy.
- **Nguyên nhân**: Nick tạo sau cùng nằm ở vị trí thứ 7 hoặc 8 (ngoài viewport). `account_switcher.select_exact_account` gọi `adapter.swipe()` để cuộn tìm nick, nhưng adapter không cài đặt hàm này nên không thể cuộn và văng lỗi thiếu nick.
- **Giải pháp**: Bắt buộc cài đặt `swipe(self, x1, y1, x2, y2, duration_ms=300)` trong adapter ủy quyền gọi `adb.shell(["input", "swipe", ...])`.
