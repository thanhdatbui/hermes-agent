# Kiến Trúc Quản Lý Vòng Đời Hotmail -> GPM Dual-Farm (Kibe & Admin)

## 1. Phân Định Kiến Trúc Host (Kibe vs Admin)
- **GPMLogin:** Cài đặt và vận hành tập trung DUY NHẤT trên host **Kibe**. Host Admin không chạy GPM.
- **Dữ liệu Hotmail Admin:** Nằm tại `D:\OneDrive\TaadaaData\admin\taikhoan_dat_v2_updated .xlsx` là kho tài khoản Hotmail đang đăng nhập trên phone farm Admin (M201-280).
- **Cơ chế bốc nick:** Máy Kibe đọc dữ liệu Admin và bốc cuốn chiếu từng tài khoản để đăng nhập lên các profile GPMLogin tương ứng trên Kibe, đi qua đúng dải proxy port của Admin (`10008`–`10035`).

## 2. Kỷ Luật Điều Phối Cronjob (Chống Rác Cron & Chống Cướp Focus)
- Trên máy Kibe chỉ duy trì DUY NHẤT 1 cronjob điều phối GPM: `gpm-5profiles-lifecycle-supervisor` (`341f42ae292c`).
- **CẤM TUYỆT ĐỐI** tạo thêm cronjob riêng lẻ cho Admin (như `gpm-5profiles-supervisor-admin`). Việc chạy 2 cronjob độc lập sẽ gây:
  - Tranh chấp tài nguyên GPM API (`http://127.0.0.1:19995`).
  - Xung đột file lock.
  - Nháy cửa sổ CMD / trình duyệt cướp focus của người dùng khi đang thao tác hoặc chơi game.
- **Quy trình Wrapper Chuẩn (`gpm_5profiles_supervisor_wrapper.py`):**
  1. Quét và xử lý batch 5 profile cho Farm Kibe (M1-80, proxy 5101-5180).
  2. Quét tuần tự tiếp theo batch 5 profile cho Farm Admin (M201-280, proxy 10008-10035).

## 3. Invariant Vòng Đời: CẤM Bỏ Qua Bước HOTMAIL_LOGIN Khi Có OAuth Token
- **Sai lầm thường gặp:** Thấy tài khoản có OAuth Refresh Token (Graph API) trong file dữ liệu thì tự ý gán `initial_stage = "CHATGPT_REG"` hoặc tự động convert `HOTMAIL_LOGIN` -> `CHATGPT_REG`.
- **Hậu quả:** Toàn bộ tài khoản bị nhảy cóc sang reg ChatGPT mà chưa từng được đăng nhập Hotmail trên trình duyệt GPMLogin, dẫn đến không có cookie/session `login.live.com` để nuôi profile và đổi pass sau này.
- **Quy tắc bắt buộc:**
  - OAuth Token chỉ là công cụ phụ trợ để bóc OTP qua API.
  - 100% tài khoản Hotmail (kể cả có OAuth token) BẮT BUỘC phải bắt đầu từ `stage: "HOTMAIL_LOGIN"`.
  - Chuỗi trạng thái chuẩn: `HOTMAIL_LOGIN` -> `CHATGPT_REG` -> `WAIT_7D` -> `CHANGE_INFO` -> `DONE`.
  - 84 tài khoản Admin đã hoàn tất đăng ký ChatGPT trước đó được bảo lưu nguyên vẹn tại `WAIT_7D`.
