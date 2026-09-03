# Quy tắc Điều chuyển Slot Tài khoản & Phục hồi Password TikTok gốc từ Backup (2026-09-01)

## 1. Quy tắc Điều chuyển Slot thay vì Logout/Login vòng vo (User Directive 2026-09-01)
- **Bối cảnh**: Khi máy báo dừng phiên do thiếu nick trong ca nuôi (ví dụ: ca 3 chạy Slot 5 nhưng không tìm thấy nick `janayerton71` trong Account Switcher) và trên máy thực tế đã đăng nhập đủ 6 tài khoản (có chứa 1 tài khoản thật ở Slot 7/8 như `buithudung2011`).
- **Nguyên tắc**:
  - **TUYỆT ĐỐI KHÔNG** đăng xuất tài khoản đang có trên máy để đăng nhập lại nick thiếu nếu không bắt buộc. Việc đăng xuất / đăng nhập lặp lại nhiều vòng làm tăng nguy cơ checkpoint, rớt session, hoặc bị TikTok gắn cờ thiết bị bất thường.
  - **Phương án tối ưu**: Tận dụng tài khoản đã có sẵn trên máy:
    1. Gán tài khoản có sẵn (Slot 7/8) vào Slot ca nuôi đang chạy (Slot 5) trên cả 3 file: `taikhoan_dat_v2_updated .xlsx`, `taikhoan_run_safe.xlsx`, và `Tik5.xlsx`.
    2. Dọn sạch slot phụ (Slot 7/8) về trống.
    3. Chuyển tài khoản bị thiếu sang gán vào một máy khác trong farm đang còn slot trống (ví dụ: Máy 61 đang có 4/6 nick) và đăng nhập bù sau.

## 2. CẤM Gán Pass Mail vào Cột PASS TikTok (User Scold 2026-09-01)
- **Hiện tượng**: Nick `janayerton71` khi đăng nhập sang máy mới bị báo "Mật khẩu sai" do cột PASS TikTok trong Excel lưu giá trị `qaxvon909063` (trùng 100% với pass Hotmail dạng chữ thường + số).
- **Quy tắc bất biến**:
  - Mật khẩu TikTok do script reg (`social_reg_v1.py::make_tiktok_password`) sinh ra luôn ngẫu nhiên, có độ dài 10-16 ký tự, gồm chữ hoa, chữ thường, số và ký tự đặc biệt (ví dụ: `d50Xi*Uzk7`).
  - **CẤM TUYỆT ĐỐI** bot AI khi khôi phục dữ liệu lấy mật khẩu mail (Gmail/Hotmail) điền vào cột PASS TikTok.
  - **Quy trình truy vết mật khẩu gốc khi nghi ngờ sai pass**:
    1. Quét thư mục backup lịch sử: `C:\Users\Kibe\AppData\Local\Taadaa\Tiktok_Reg\workbook-backups\*.xlsx`.
    2. Lọc các file backup được tạo tại thời điểm/ngày tạo nick (`taikhoan_dat_v2_updated_before_account_success_*` hoặc `taikhoan_dat_v2_updated_before_mail_die_*`).
    3. Đọc dữ liệu cột PASS TikTok từ file backup gốc để lấy lại mật khẩu thật và cập nhật vào `taikhoan_dat_v2_updated .xlsx`.

## 3. Luồng Đăng nhập Thiết bị mới & Xác minh Danh tính qua Graph API
1. Nhập TikTok ID + Mật khẩu thật (`d50Xi*Uzk7`) tại form login.
2. TikTok chuyển sang màn hình WebView **"Xác minh danh tính"** (*Xác minh đó là bạn bằng cách nhập mã được gửi đến j***2@hotmail.com*).
3. Đảm bảo mailbox có token trong `gmail_clean_v2.xlsx` (cột token và client_id).
4. Gọi `read_tiktok_otp_from_graph_token(device_id, email, stt)` để lấy OTP 6 số qua Graph API trên PC (không mở Outlook app trên điện thoại).
5. Nhập mã OTP vào ô nhập trên WebView -> TikTok xác thực thành công và đưa vào tài khoản.
6. Verify trên Account Switcher và chụp bằng chứng.
