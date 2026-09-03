# SparkActivity Identity Verification & Zero Spare-Account Assumption (2026-09-01)

## 1. Cấm tự chế "Nick dự phòng" khi thiếu Inventory trên thiết bị
- **Nguyên tắc bất di bất dịch:** Mọi row có ID TikTok trong `taikhoan_run_safe.xlsx` và `taikhoan_dat_v2_updated .xlsx` (Row 1..6) đều là tài khoản thật theo ca chạy hoặc lộ trình warmup (Row 5 & 6 là ca 3 ngày lẻ/chẵn).
- **Tuyệt đối KHÔNG:** Tự ý kết luận hoặc giải thích "máy chỉ cần 3 nick, các row còn lại là dự phòng" khi inventory trên máy thiếu so với file Excel.
- Khi đối chiếu inventory (`reconcile_tiktok_accounts.py` hoặc kiểm tra thủ công) thấy thiếu bất kỳ ID nào có trong Excel $\rightarrow$ BẮT BUỘC tiến hành đăng nhập bù ngay lập tức cho đến khi đủ toàn bộ tài khoản.

## 2. Quy trình xử lý SparkActivity "Xác minh đó là bạn" (Identity Verification qua Gmail)
- **Hiện tượng:** Sau khi submit mật khẩu TikTok, TikTok không vào thẳng profile mà chuyển sang WebView `com.bytedance.hybrid.spark.page.SparkActivity` với tiêu đề *"Xác minh đó là bạn"* / *"Chọn một phương thức để xác minh danh tính..."*.
- **Các bước xử lý chuẩn:**
  1. **Kích hoạt gửi OTP:** Tap vào hàng email `n***8@gmail.com` (tâm `(540, 774)`). Màn hình chuyển sang *"Xác minh danh tính bằng cách nhập mã được gửi đến..."*.
  2. **Đọc OTP từ Gmail app trên máy:**
     - Gọi `_try_get_otp_gmail_app(device_id, email)`.
     - Script tự động mở Gmail app, switch sang account Gmail tương ứng, pull-to-refresh hòm thư và đọc mã OTP 6 số mới nhất theo timestamp hiện tại.
  3. **Khôi phục TikTok & Nhập OTP:**
     - Đưa TikTok về foreground bằng `monkey -p com.ss.android.ugc.trill 1` (KHÔNG force-stop, KHÔNG clear data).
     - Tap vào vùng nhập OTP (y ≈ 800) và gõ 6 số qua ADB.
     - Sau khi nhập OTP, TikTok tự động xác thực và chuyển vào Profile của tài khoản mới.
  4. **Xác thực hoàn tất:** Mở Account Switcher kiểm tra đủ số lượng nick trên máy trước khi release lock.

## 3. Bẫy Case-Insensitive Duplicate Username trong Master Workbook
- TikTok ID không phân biệt chữ hoa/chữ thường (`Samnga2403` $\equiv$ `samnga2403`).
- Khi lọc trùng trong `taikhoan_dat_v2_updated .xlsx` bằng Excel thông thường, so sánh case-sensitive sẽ bỏ sót dòng trùng giữa chữ hoa và chữ thường.
- Khi audit hoặc viết script sync/clean, luôn normalize: `id.strip().lower()` hoặc `normalize_account(id)`.
