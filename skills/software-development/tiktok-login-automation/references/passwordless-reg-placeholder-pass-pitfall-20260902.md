# Bẫy Mật khẩu Placeholder do Reg qua OTP Hotmail (Passwordless Flow) & Hướng xử lý (2026-09-02)

## 1. Hiện tượng & Triệu chứng
- Khi đăng nhập lại tài khoản TikTok (qua script `reconcile_tiktok_accounts.py` hoặc manual ADB flow) trên thiết bị, nhập mật khẩu từ workbook `taikhoan_dat_v2_updated .xlsx` bị báo lỗi đỏ:
  `text='Mật khẩu sai' rid='com.ss.android.ugc.trill:id/i7f'`
- Thử lại mật khẩu nhiều lần vẫn thất bại dù workbook ghi đầy đủ cột `PASS`.

## 2. Nguyên nhân Gốc (Root Cause)
- Các tài khoản đăng ký theo đợt batch Hotmail (`Tiktok_Reg` / `social-batch-all`) thường đi qua luồng **OTP Graph API / Outlook App**:
  - Nhập email -> TikTok phát hiện và mở màn hình OTP/verify -> Script đọc OTP từ Graph API/Outlook -> Điền DOB/Profile -> Đăng nhập thành công.
  - Trong luồng này, TikTok **không mở màn hình tạo mật khẩu** (`[pw] Không có màn nhập password → KHÔNG lưu pass (để trống)`).
  - Chuỗi mật khẩu lưu trong `tracking_result_stt<N>_<mail>.json` và cột `PASS` của `taikhoan_dat_v2_updated .xlsx` chỉ là chuỗi random placeholder được sinh ra từ đầu kịch bản, nhưng **chưa bao giờ được submit lên TikTok**.

## 3. Quy trình Truy vết & Xác thực (Verification)
1. Tra cứu log trong file `D:\Taadaa\Tiktok_Reg\social_reg_log.txt` hoặc file tracking JSON:
   `D:\Taadaa\runtime\kibe\artifacts\runs\social-batch-all\<run_id>\batch_1\stt_<N>\tracking_result_stt<N>_<mail>.json`
2. Tìm dòng log liên quan đến password:
   Nếu thấy `[pw] Không có màn nhập password → KHÔNG lưu pass (để trống)` => Tài khoản 100% là tài khoản Passwordless (chưa có mật khẩu).

## 4. Hai Phương thức Nạp & Đăng nhập Chuẩn

### Cách 1: Đặt lại mật khẩu TikTok (Khuyên dùng để đồng bộ Workbook)
1. Tại màn hình "Nhập mật khẩu", bấm **"Bạn cần trợ giúp đăng nhập?"** (`id/l77`) -> chọn **"Đặt lại mật khẩu bằng email"** (`(540, 1500)`).
2. Điền địa chỉ Hotmail tương ứng (vd `djricharalfr@hotmail.com`) -> bấm **"Tiếp tục"** (`(540, 1681)`).
3. Đọc mã OTP 6 số gửi về Hotmail qua Graph API:
   - Dùng script token exchange Microsoft Graph API đọc email mới nhất (`subject` chứa `là mã gồm 6 chữ số của bạn` hoặc `là mã TikTok của bạn`).
4. Nhập mã OTP vào màn hình xác minh email trên TikTok.
5. Tại màn hình "Đặt lại mật khẩu": Nhập chuỗi mật khẩu chính xác từ cột `PASS` trong workbook (`VD!jfqr5iukQ*`) -> bấm **"Tiếp tục"**. Mật khẩu TikTok giờ đã chính thức được kích hoạt và khớp 100% với workbook.

### Cách 2: Đăng nhập trực tiếp bằng Email OTP (Bypass khi dính Rate Limit đổi pass)
- Nếu TikTok báo lỗi `Bạn truy cập dịch vụ của chúng tôi quá thường xuyên.` khi đổi mật khẩu:
1. Quay lại màn hình chọn phương thức đăng nhập -> Chọn **"Sử dụng số điện thoại / email / tên người dùng"** -> Chọn tab **"Email / Tên người dùng"**.
2. **Nhập ĐẦY ĐỦ ĐỊA CHỈ EMAIL HOTMAIL** (vd `LyndiaSchlesinger2198@hotmail.com`) thay vì nhập username `@lyndiaschles21`.
3. TikTok sẽ bypass hoàn toàn màn hình hỏi mật khẩu và chuyển thẳng sang màn hình **"Xác minh email"** (Email OTP login mode).
4. Mở app Outlook trên máy (hoặc query Graph API), kéo xuống refresh để nhận mã OTP mới nhất -> Nhập mã 6 số vào TikTok để vào thẳng tài khoản mà không cần mật khẩu.

## 5. Giới hạn Switcher Đồng thời (TikTok Concurrency Limit)
- Trên ứng dụng TikTok Android 46.x, menu trượt Profile Switcher ("Chuyển đổi tài khoản") hiển thị tối đa **5 tài khoản đăng nhập đồng thời**.
- Khi máy đã nạp đủ 5 tài khoản và tiếp tục nạp tài khoản thứ 6, TikTok sẽ lưu tài khoản vào danh sách Fast-Login ("Chào mừng bạn trở lại") và cho phép chuyển đổi slot khi cần.
