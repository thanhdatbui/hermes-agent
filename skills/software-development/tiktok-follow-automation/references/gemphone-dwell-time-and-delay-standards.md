# Quy chuẩn Dwell Time & Follow Delays (Chuẩn GemPhone - Ông Khoa)

Tài liệu này ghi lại các thông số dwell time và delay nhịp sinh học người dùng thực tế được áp dụng trong repo `tiktok-follow` nhằm chống nhả follow (anti-release) và tránh TikTok rate-limit/batch detection:

1. **Profile Dwell Time (Mode 1)**:
   - Trước khi bấm Follow trên trang profile mục tiêu: ngâm `random.uniform(6.0, 12.0)` giây.
   - Mô phỏng hành vi người dùng thật đọc bio, xem ảnh đại diện, kiểm tra các video trước khi quyết định ấn Follow.

2. **Post-tap Settling Delay**:
   - Sau khi tap nút Follow trên UI (cả trong header action của Mode 1 lẫn row action của Mode 2):
   - Đợi `random.uniform(2.5, 5.0)` giây thay vì `1.5s` cố định.
   - Giúp UI TikTok cập nhật trạng thái đồng bộ về server và hiển thị đúng trước khi kích hoạt quy trình verify.

3. **Inter-follow Delay giữa các lần follow thành công**:
   - Khoảng nghỉ giữa 2 lần follow kế tiếp: `random.uniform(cfg.delay_min, cfg.delay_max)`.
   - Chuẩn mặc định cập nhật: `delay_min: 8.0`s đến `delay_max: 25.0`s (thay vì 1-5s cũ quá nhanh dẫn tới flag bất thường).
