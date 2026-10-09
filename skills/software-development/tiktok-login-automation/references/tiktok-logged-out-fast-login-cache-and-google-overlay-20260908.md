# TikTok Logged-Out Profile, Google Sign-in Overlay & Fast-Login Cache Verification (2026-09-08)

## 1. Google Sign-in Overlay (`com.google.android.gms`) Trap
Khi khởi chạy TikTok hoặc mở lại sau khi đăng xuất tài khoản, dịch vụ Google Play có thể bung overlay toàn màn hình/dialog:
- Package: `com.google.android.gms`
- Tiêu đề: "Đăng nhập bằng Google" / "Tài khoản Google" (`com.google.android.gms:id/title`, `com.google.android.gms:id/header_text`)
- Nút đóng/thoát: `com.google.android.gms:id/cancel` (`desc="Thoát"`, bounds `[915, 390][1059, 534]`, tâm `987, 462`).
- **Hệ quả:** Nếu không dismiss dialog này, mọi tap điều hướng bên dưới (như tab Hồ sơ `(972, 1857)` hoặc header switcher `(350, 150)`) sẽ bị nuốt hoặc chạm trúng nội dung Google.
- **Xử lý:** Kiểm tra XML, nếu phát hiện `com.google.android.gms:id/cancel` thì tap `(987, 462)` hoặc gửi `keyevent 4` (Back) để giải phóng màn hình trước khi thao tác tiếp trên TikTok.

## 2. Phân Biệt Profile Active vs Màn Hình Profile Logged-Out
Khi kiểm tra Account Switcher trên thiết bị Android:
- Nếu app còn tài khoản đang active: Profile root hiển thị `@username`, follower/following, và tap header `(350, 150)` / `(540, 522)` sẽ bung bottom sheet "Chuyển đổi tài khoản" liệt kê các nick đang online.
- Nếu app đã đăng xuất khỏi tài khoản đang chọn (hoặc không còn tài khoản nào active):
  - `com.ss.android.ugc.trill:id/tv_title`: "Hồ sơ"
  - `com.ss.android.ugc.trill:id/k1m`: "Đăng nhập vào tài khoản hiện có"
  - `com.ss.android.ugc.trill:id/czm`: "Đăng nhập"
  - Không có mũi tên hay anchor Account Switcher trên header để mở sheet chuyển đổi.

## 3. Fast-Login Cache ("Chào mừng bạn trở lại" / One-tap Login)
- Khi tap nút "Đăng nhập" (`bounds=[165, 1016][915, 1172]`, tâm `540, 1094`) từ Profile logged-out, TikTok sẽ mở sheet Fast Login nếu thiết bị còn lưu credential:
  - `com.ss.android.ugc.trill:id/ym3`: "Chào mừng bạn trở lại"
  - `com.ss.android.ugc.trill:id/ym7`: `@username` (Ví dụ: `miumiu67971`)
  - `com.ss.android.ugc.trill:id/ym4`: "Đăng nhập"
  - `com.ss.android.ugc.trill:id/ym6`: "Thêm tài khoản khác"
  - Nút đóng: `com.ss.android.ugc.trill:id/z84` (`desc="Đóng"`, bounds `[936, 168][1068, 300]`)
- **Ý nghĩa nghiệm thu:** Nếu một tài khoản vừa được đăng xuất nhưng vẫn xuất hiện trong màn hình "Chào mừng bạn trở lại", điều này chứng minh tài khoản đó chưa bị xóa hoàn toàn khỏi bộ nhớ cache/saved logins của TikTok trên thiết bị. Muốn xóa triệt để, cần xóa tài khoản khỏi danh sách đăng nhập đã lưu hoặc xóa session tương ứng.

## 4. Chuỗi Đăng Nhập Tài Khoản Mới Từ Màn "Chào Mừng Bạn Trở Lại" (Bypass Fast-Login)
Khi trên màn hình xuất hiện modal "Chào mừng bạn trở lại" nhưng mục tiêu là đăng nhập nick mới:
1. **Thêm tài khoản khác**:
   - Tap nút `id/ym6` ("Thêm tài khoản khác", bounds `[180, 1480][900, 1624]`, tâm `540, 1552`).
   - CẤM bấm nút `id/ym4` ("Đăng nhập") vì sẽ tự động đăng nhập lại nick cũ đã cached.
2. **Chọn phương thức đăng nhập**:
   - Màn hình "Đăng nhập vào TikTok": Tap "Sử dụng số điện thoại/email/tên người dùng" (bounds `[84, 807][996, 951]`, tâm `540, 879`).
3. **Chuyển tab Email**:
   - Màn hình mặc định mở tab "Số điện thoại". Bắt buộc tap tab "Email / TikTok ID" (bounds `[540, 240][960, 360]`, tâm `750, 300`).
   - Nhập email mục tiêu vào ô EditText (`id/user_name` hoặc node EditText đầu tiên).
   - Tap nút "Tiếp tục" (`id/oen` hoặc `bounds=[120, 540][960, 660]`).
4. **Nhập Mật Khẩu**:
   - Màn hình "Nhập mật khẩu" (có ô `password` và biểu tượng con mắt).
   - Dùng `adb shell input text "<password>"` (chú ý ký tự đặc biệt như `@` cần escape hoặc bọc nháy kép).
   - Tap nút "Đăng nhập" màu đỏ.
5. **Xử lý 2FA (Ứng dụng xác thực / Authenticator)**:
   - Nếu xuất hiện màn hình xác thực 2 bước:
     ```python
     import pyotp
     totp = pyotp.TOTP(secret_2fa)
     code = totp.now()
     ```
   - Nhập 6 chữ số vào ô OTP hoặc dùng `input text <code>`. Chờ 5s cho TikTok xác thực và load màn hình chính.
6. **Xử lý Popups Hậu Đăng Nhập (Post-auth Popups)**:
   - "Lưu thông tin đăng nhập?": Tap "Lưu" (Save).
   - "Đồng bộ danh bạ / bạn bè": Tap "Từ chối" hoặc "Để sau".
7. **Nghiệm Thu Tài Khoản Tại Account Switcher**:
   - Vào tab "Hồ sơ" (`972, 1857` hoặc `id/ok0`).
   - Tap header tài khoản (`x=350, y=150` hoặc sticky header giữa đỉnh) để bung bottom sheet "Chuyển đổi tài khoản".
   - Dump ATX XML để xác thực username nick mới có trong danh sách.
   - Chụp ảnh màn hình nghiệm thu trực tiếp tại Account Switcher.

## 5. Kỷ Luật Thực Thi Giới Hạn Lượt Gọi Tool Cho Subagent (Budget-Conscious Subagent)
Khi được giao task delegated có ngân sách tool call nghiêm ngặt (ví dụ: budget <= 18 calls):
- **Cấm thăm dò lan man**: Không gọi `search_files`, `ls` các thư mục tổng của hệ thống (`/d/Taadaa/`, `/d/Taadaa/reports/`, v.v.) hay đọc script cũ không liên quan.
- **Quy trình tinh gọn (3-Phase Execution)**:
  1. *Phase 1 (Turn 1)*: Verify kết nối adb thiết bị + forward port ATX (`adb forward --list`).
  2. *Phase 2 (Turn 2)*: Dump 1 lần ATX XML qua JSON-RPC để xác định trạng thái màn hình hiện thời.
  3. *Phase 3 (Turn 3)*: Tạo script tự động trọn gói trong `D:/Taadaa/tmp/` chứa logic xử lý các bước từ login đến 2FA và chụp proof, sau đó chạy trực tiếp qua python runner và thu thập ảnh nghiệm thu.
