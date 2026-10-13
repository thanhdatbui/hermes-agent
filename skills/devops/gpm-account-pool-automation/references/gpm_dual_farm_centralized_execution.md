# Quy Tắc Điều Phối GPM Hotmail Dual-Farm (Kibe vs Admin)

## 1. Bản Chất & Phân Bổ Kiến Trúc
- **GPMLogin chỉ chạy duy nhất trên máy Kibe:** Không cài đặt hay chạy GPMLogin trên máy Admin.
- **Dữ liệu Farm Admin:** File `D:\OneDrive\TaadaaData\admin\taikhoan_dat_v2_updated .xlsx` là nơi lưu trữ thông tin các nick Hotmail đang đăng nhập trên farm điện thoại Admin (M201–280).
- **Cơ chế bốc nick:** Máy Kibe sẽ đọc dữ liệu từ data Admin và bốc cuốn chiếu từng tài khoản để đăng nhập lên các profile GPMLogin tương ứng trên Kibe (chạy qua đúng dải proxy port 10008–10035 của Admin).

## 2. Kỷ Luật Cronjob Duy Nhất (Chống Phân Mảnh)
- **CẤM TUYỆT ĐỐI đẻ thêm cronjob riêng lẻ** như `gpm-5profiles-supervisor-admin`.
- Mọi điều phối GPM Hotmail cho cả 2 farm (Kibe M1–80 và Admin M201–280) được gộp vào chạy tuần tự trong **DUY NHẤT một cronjob** `gpm-5profiles-lifecycle-supervisor` (`341f42ae292c`) trên Kibe.
- Wrapper `gpm_5profiles_supervisor_wrapper.py` chạy tuần tự:
  1. Quét Farm Kibe (M1–80, proxy 5101–5180).
  2. Quét Farm Admin (M201–280, proxy 10008–10035).
- Chạy tuần tự giúp quản lý tải profile GPM (tối đa 5 profile/lần), bảo vệ RAM/CPU và triệt tiêu xung đột lock profile hoặc cướp focus.

## 3. Kỷ Luật State Machine — Cấm Nhảy Cóc `HOTMAIL_LOGIN`
- **Quy trình chuẩn bắt buộc:**
  `HOTMAIL_LOGIN` -> `CHATGPT_REG` -> `WAIT_7D` -> `CHANGE_INFO` -> `DONE`
- **Vai trò của OAuth Refresh Token (Graph API):**
  Token ở cột 9 chỉ dùng cho tác vụ bóc OTP tự động qua API khi đăng ký dịch vụ (ChatGPT/TikTok), TUYỆT ĐỐI KHÔNG được dùng để bỏ qua bước đăng nhập Hotmail trên GPM.
- Mọi tài khoản mới hoặc chuyển đổi bắt buộc phải khởi đầu ở `stage: "HOTMAIL_LOGIN"` (`status: "PENDING"`) để mở trình duyệt, đăng nhập `login.live.com` và lưu giữ cookie/session sống.
- CẤM TUYỆT ĐỐI tự ý code logic tự nâng `HOTMAIL_LOGIN` thành `CHATGPT_REG` khi thấy có token.
