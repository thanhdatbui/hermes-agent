# TikTok 46.x: Quick-Login "Tiếp tục với tên @username" on Add Account Surface

## 1. Hiện tượng & Bối cảnh
Khi thiết bị mở **Chuyển đổi tài khoản** -> bấm **Thêm tài khoản**, thay vì vào form nhập Số điện thoại / Email thông thường, TikTok 46.x có thể hiển thị màn hình gợi ý đăng nhập nhanh tài khoản đã từng lưu credential/session trên thiết bị:
- Header: `Đóng` (`[12,78][144,210]`), `Khác`, `Báo cáo vấn đề`
- Nút bấm chính: `Tiếp tục với tên` (`[198,1193][882,1238]`) kèm `@<username>` (`[198,1238][882,1298]`) nằm trong khung clickable `[132,1160][948,1340]`
- Nút phụ: `Sử dụng tài khoản khác` (`[72,1764][1008,1908]`)

## 2. Quy trình xử lý tự động (Fast-path 1-tap Login)
1. **Khớp Username:**
   - Đọc text node con trong view clickable hoặc text `@<username>`.
   - Nếu username trùng khớp với `expected_account`/`expected_username` cần đăng nhập (ví dụ `@mautuoi08` khớp `mautuoi08`):
2. **Tap Đăng Nhập Nhanh:**
   - Tap trực tiếp vào vùng `[132,1160][948,1340]` (hoặc center `(540, 1250)`).
   - TikTok sẽ đăng nhập ngay lập tức không cần gõ lại email/password/OTP.
3. **Xử lý Popup Hậu Đăng Nhập:**
   - Màn hình có thể xuất hiện popup **"Hãy cùng kiểm tra bảo mật nhanh nhé"** (`com.ss.android.ugc.trill:id/ywu`).
   - Bấm nút **Đóng** (`[936,857][1056,989]` / center `(996, 923)`) để đóng popup, tuyệt đối không bấm "Tiếp tục" vì sẽ vào flow liên kết SĐT/bảo mật.
4. **Xác thực kết quả:**
   - Tap tab Hồ sơ (`[864,1794][1080,1920]`), kiểm tra node `@<username>`.
   - Mở switcher sheet kiểm tra danh sách tài khoản đã đủ các slot hay chưa trước khi đưa máy về Home và release lock.
