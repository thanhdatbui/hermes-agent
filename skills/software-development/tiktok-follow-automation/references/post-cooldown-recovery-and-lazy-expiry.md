# Hướng Dẫn Vận Hành: Cơ Chế Thả Xích & Lớp Warmup Hậu Cooldown (Post-Cooldown Recovery)

## 1. Cơ Chế Thả Xích (Lazy-Expiry)
- **Cơ chế hoạt động**:
  - Khi một máy bị dính nhả follow, runner ghi nhận `follow_failed = True` và timestamp mãn hạn `cooldown_until_at` vào `follow_state_{machine}_row_{account_row_index}.json`.
  - Trong thời gian chờ, file state trên đĩa vẫn giữ nguyên `follow_failed: true` vì không có background daemon chạy quét dọn rác.
  - **Đến cữ chạy tiếp theo sau khi mãn hạn**: Khi runner khởi động, hàm `_check_and_sync_cooldown_expiry()` được gọi. Nó so sánh `now_utc >= cooldown_until_at`. Nếu đã quá hạn, code tự động:
    1. Gán `follow_failed = False` (tháo xích thành công).
    2. Xóa sạch `cooldown_until_at`, `cooldown_until_date`, `follow_failed_date`.
    3. Lưu file JSON mới xuống đĩa và cấp lại `budget_remaining` để chạy.

## 2. Tử Huyệt Vừa Hết Cooldown Đã Bị Nhả Lại
- **Hiện tượng**: Nick được thả xích đúng ngày đúng giờ, nhưng vừa vào chạy phiên đầu tiên là bị nhả lại ngay lập tức ở nick #1 (Canary) và bị phạt cooldown tiếp 7 ngày (`fail_streak = 3`).
- **Nguyên nhân**: Cooldown thời gian chỉ là thời gian chờ tĩnh. Thuật toán TikTok lưu điểm Trust Score của tài khoản ở mức 0. Khi vừa hết hạn, nếu nick đột ngột thực hiện hành vi follow dồn dập với full budget (15-18 follow/phiên) và tốc độ cao, hệ thống chống spam của TikTok sẽ kích hoạt shadow-drop lại ngay lập tức.

## 3. Quy Trình Warmup Hậu Cooldown Bắt Buộc
- **Phiên 1-2 sau khi hết Cooldown**:
  - **Hạ budget thăm dò**: Chỉ follow 3 - 5 nick / phiên (thay vì 15 - 18).
  - **Giãn khoảng cách (Inter-follow delay)**: Delay 8 - 15 giây giữa các lượt follow (thay vì 1.5 - 3.5s).
  - **Tương tác trước khi follow**: Lướt feed 35-40 phút, xem video anchor 8-15s, thả tim 50-70% trên video player trước khi bấm follow.
  - **Bảo lưu Path B**: Không bao giờ bỏ `_path_b_verify` trong danh sách Following. Lượt #1 luôn chạy Path B để kiểm tra server state. Nếu pass thì mới follow tiếp 2-3 nick nữa rồi dừng phiên warmup.
  - **Phục hồi**: Sau 2-3 phiên warmup 3-5 nick thành công không bị nhả, Trust Score được khôi phục, lúc này mới tăng dần budget về mức 15-18 nick bình thường.
