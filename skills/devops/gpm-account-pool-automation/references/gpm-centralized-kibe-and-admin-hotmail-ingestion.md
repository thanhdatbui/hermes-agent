# Kiến Trúc GPM Tập Trung Trên Kibe & Tiếp Nhận Hotmail Farm Admin

## 1. Nguyên Tắc Cốt Lõi Về Hạ Tầng GPM & Dữ Liệu Farm
- **GPMLogin Duy Nhất Trên Kibe:** Ứng dụng GPM v3 (`http://127.0.0.1:19995`) CHỈ cài đặt và vận hành tập trung trên máy **Kibe**. Máy Admin KHÔNG chạy GPM.
- **Admin Là Nguồn Lưu Trữ (Hotmail Inventory):** Dữ liệu `D:\OneDrive\TaadaaData\admin\` là nơi lưu trữ danh sách các tài khoản Hotmail đang đăng nhập trên phone farm Admin (M201–280).
- **Luồng Ingestion & Quy Hoạch Cronjob:**
  - Máy Kibe chịu trách nhiệm đọc dữ liệu từ Admin (`taikhoan_dat_v2_updated .xlsx` & `PROXYgandienthoai.xlsx`), sau đó bốc cuốn chiếu từng nick để đăng nhập lên GPMLogin trên Kibe (sử dụng đúng dải proxy port `10008`–`10035` của Admin).
  - **CẤM tạo nhiều cronjob riêng lẻ phân mảnh:** KHÔNG tạo cronjob riêng `gpm-5profiles-supervisor-admin`. Toàn bộ luồng supervisor được tích hợp vào duy nhất một cronjob `gpm-5profiles-lifecycle-supervisor` trên Kibe.
  - Wrapper `gpm_5profiles_supervisor_wrapper.py` chạy tuần tự:
    1. Quét Farm Kibe (M1–80, proxy 5101–5180).
    2. Quét Farm Admin (M201–280, proxy 10008–10035).
  - Việc chạy tuần tự giúp kiểm soát tải (tối đa 5 profile song song/tick), chống nghẽn RAM/CPU và triệt tiêu xung đột profile lock.

## 2. Kỷ Luật Về Stage Machine & OAuth Token
- **Bắt buộc trải qua `HOTMAIL_LOGIN`:** Mọi tài khoản Hotmail (dù đã có OAuth refresh token Microsoft Graph API hay chưa) đều BẮT BUỘC phải trải qua stage `HOTMAIL_LOGIN` trên GPM để lưu session/cookie và nuôi browser profile.
- **CẤM TỰ TIỆN BYPASS SANG `CHATGPT_REG`:** Tuyệt đối không được viết code kiểm tra `has_token` rồi tự động gán hoặc migrate `initial_stage = "CHATGPT_REG"`.
- Token Microsoft Graph API chỉ dùng cho tác vụ lấy OTP tự động qua API khi cần, không thay thế cho session trình duyệt GPM.
- Khi cần migrate state cũ bị kẹt, giữ nguyên các tài khoản đã reg ChatGPT (`chatgpt_registered_at`) ở `WAIT_7D`, chuyển toàn bộ tài khoản chưa reg ChatGPT về `HOTMAIL_LOGIN` (`PENDING`).
