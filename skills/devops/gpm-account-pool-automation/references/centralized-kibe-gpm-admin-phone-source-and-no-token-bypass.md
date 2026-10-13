# Quy Chuẩn Vận Hành GPM Tập Trung Tại Kibe & Cơ Chế Hotmail Admin Farm

## 1. Nguyên Tắc Kiến Trúc: GPM Duy Nhất Trên Kibe
- **Chỉ chạy GPM trên Kibe:** Toàn bộ tiến trình GPMLogin v3 (API port 19995) chỉ được cài đặt và vận hành tập trung trên máy Kibe. Tuyệt đối không cài đặt hay mở profile GPM trên máy Admin.
- **Admin chỉ là nguồn Hotmail:** Farm Admin (M201–280) là cụm phone farm lưu các tài khoản Hotmail đang đăng nhập trên ứng dụng Outlook của điện thoại Admin.
- **Bốc cuốn chiếu từ Kibe:** Máy Kibe đọc dữ liệu tài khoản Admin tại `D:\OneDrive\TaadaaData\admin\taikhoan_dat_v2_updated .xlsx` và proxy mapping `PROXYgandienthoai.xlsx` (dải port `10008`–`10035`), sau đó bốc cuốn chiếu từng tài khoản để tạo và đăng nhập profile GPM ngay trên Kibe.

## 2. Cấm Tuyệt Đối Bypass Qua OAuth Refresh Token
- **Vai trò của OAuth Token:** Refresh token từ Microsoft Graph API chỉ được sử dụng cho tác vụ bóc mã xác thực OTP qua API một cách tự động khi đăng ký dịch vụ bên thứ ba (ChatGPT, TikTok...).
- **Không thay thế Session Browser:** OAuth token KHÔNG thay thế cookie trình duyệt. Mọi tài khoản Hotmail (kể cả đã có sẵn OAuth token) BẮT BUỘC phải trải qua stage khởi đầu `HOTMAIL_LOGIN` trên GPMLogin để nuôi profile, vượt cookie consent và lưu session disk (`login.live.com`).
- **State Machine Chuẩn Hóa:**
  `HOTMAIL_LOGIN` -> `CHATGPT_REG` -> `WAIT_7D` (ngâm an toàn) -> `CHANGE_INFO` -> `DONE`.
  Cấm mọi logic tự ý convert hay nâng cấp nick có token từ `HOTMAIL_LOGIN` nhảy cóc sang `CHATGPT_REG`.

## 3. Kỷ Luật Điều Phối Cronjob Đơn Nhất
- **Duy nhất 1 Cronjob:** Duy trì DUY NHẤT một cronjob `gpm-5profiles-lifecycle-supervisor` trên Hermes Kibe (chu kỳ 5 phút).
- **Tuần tự Kibe -> Admin:** Script wrapper chạy tuần tự:
  1. Quét xử lý 5 candidates của Farm Kibe (M1–80, port `5101`–`5180`).
  2. Quét xử lý 5 candidates của Farm Admin (M201–280, port `10008`–`10035`).
- **Chống Phân Mảnh:** Tuyệt đối không tạo thêm cronjob phụ chạy chéo (như `gpm-5profiles-supervisor-admin`), nhằm chống cướp focus chuột/phím và ngăn ngừa nghẽn RAM/GPM API.
