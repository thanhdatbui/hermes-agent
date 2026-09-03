# Khôi Phục Mật Khẩu TikTok Gốc Từ Workbook Backups & Đăng Nhập OTP Graph API

## 1. Bẫy Sync Nhầm Mật Khẩu Hotmail Vào Cột Pass TikTok
- **Triệu chứng**: Đăng nhập tài khoản TikTok báo "Mật khẩu sai" dù copy đúng chuỗi trong cột `PASS` của file `taikhoan_dat_v2_updated .xlsx`.
- **Nguyên nhân**: Quá trình restore/reconcile sau sự cố mất file/sync OneDrive trước đó đã đọc nhầm cột mật khẩu Hotmail (`PASS MAIL`, thường là chuỗi chữ thường + số như `qaxvon909063`, `jmpkaw15539`) ghi đè vào cột `PASS` TikTok. Trong khi TikTok bắt buộc mật khẩu phải chứa chữ hoa, số và ký tự đặc biệt (`d50Xi*Uzk7`, `B0MRdvm2$uI@HL`).
- **Quy trình truy vết mật khẩu gốc từ Backups**:
  1. Quét toàn bộ thư mục `C:\Users\Kibe\AppData\Local\Taadaa\Tiktok_Reg\workbook-backups\`.
  2. Lọc các file backup dạng `taikhoan_dat_v2_updated_before_account_success_<email>_<timestamp>.xlsx` hoặc `taikhoan_dat_v2_updated_before_mail_die_*.xlsx` được tạo ngay trong ca reg của ngày đó.
  3. Đọc dữ liệu dòng tương ứng với TikTok ID cần tìm để trích xuất mật khẩu TikTok gốc do hàm `make_tiktok_password()` tạo ra.
  4. Cập nhật lại mật khẩu chuẩn vào `taikhoan_dat_v2_updated .xlsx`.

## 2. Quy Trình Đăng Nhập Thiết Bị Mới Kèm OTP Graph API (Hotmail Loại 2)
1. **Nhập ID + Mật khẩu gốc**:
   - Sử dụng ADB nhập username và password chuẩn.
   - Khi mật khẩu đúng, TikTok sẽ chuyển tiếp sang màn hình `Xác minh đó là bạn` (Identity Verification / Device Verification).
2. **Chọn phương thức nhận mã OTP**:
   - Tap vào dòng `Email` (`j***2@hotmail.com`) để TikTok gửi mã OTP xác minh 6 số.
3. **Đọc OTP trực tiếp qua Graph API trên PC**:
   - Kiểm tra token trong `gmail_clean_v2.xlsx` (cột 9 Refresh Token, cột 10 Client ID).
   - Gọi hàm `read_tiktok_otp_from_graph_token(serial, email, stt, timeout=60)` từ `social_reg_v1.py`.
   - Lấy mã 6 số từ kết quả Graph API mà KHÔNG mở app Outlook trên điện thoại (tránh làm lệch focus hoặc văng app TikTok).
4. **Nhập mã OTP & Hoàn tất đăng nhập**:
   - Tap vào ô nhập mã OTP (hoặc gửi qua `input text <OTP>` vào ô `code-input`).
   - TikTok tự động xác thực và chuyển vào Home / Profile.
   - Chụp ảnh kiểm tra Account Switcher để xác nhận nick đã hiện diện đầy đủ trên thiết bị.
