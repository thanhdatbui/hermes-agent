# Quy Tắc Dọn Dẹp Về Home Khi Nhả Follow & Ngưỡng Video Đã Đăng (19/08/2026)

## 1. Dọn Dẹp Ứng Dụng Khi Dính Nhả Follow (`FOLLOW_FAILED`)
- **Hành vi bắt buộc**: Khi phát hiện follow bị nhả sau cú vuốt `pull-to-refresh` xác nhận (`FOLLOW_FAILED`):
  1. Ghi nhận `follow_failed = True` và `follow_failed_date = "YYYY-MM-DD"` cô lập cho **RIÊNG nick đó** (theo `account_row_index`).
  2. Dừng toàn bộ các lượt follow còn lại trong phiên.
  3. **Tự động gọi `adapter.close_all_apps()` (đóng TikTok, clear recent apps) và `adapter.home()` (về màn hình chính)** để dọn sạch hiện trường, không để app treo ở màn hình tìm kiếm/profile.

## 2. Ngưỡng Video Đã Đăng (Video Count Gate) & Tỉ Lệ Nhả Follow
- **Thực nghiệm 19/08 trên 64 trạng thái toàn farm**:
  - **Nick đã đăng 8 – 12 video (Row 1)**: Có độ trust từ TikTok, follow thành công được 4 – 8 nick/phiên (tổng 525 lượt thành công trong ngày) trước khi bị rate-limit.
  - **Nick chưa đăng video nào (0 video — Row 2, Row 3, Row 5)**: **100% bị TikTok nhả follow ngay từ lượt đầu tiên (followed = 0)** do bị phân loại là tài khoản rác/bot.
- **Quy tắc điều phối farm**:
  - **TUYỆT ĐỐI KHÔNG bật kịch bản Follow trên các nick 0 video**.
  - Các nick mới chỉ được chạy ca Nuôi Feed và Đăng tối thiểu 1–2 video trước khi cho tham gia follow chéo.
