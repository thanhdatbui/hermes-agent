# Phân tích Cooldown 48h Khi Dính Nhả Follow & Xử Lý Lệch Số Liệu Video Đã Đăng (2026-08-27)

## 1. Cơ Chế Cooldown 48h Khi Dính Nhả Follow (Pull-to-Refresh Released)
- **Chu kỳ xoay tua 48h (Ngày chẵn Row 2 / Ngày lẻ Row 1):**
  - Khi một tài khoản bị TikTok gắn cờ rate-limit (`FOLLOW_FAILED` do nhả nút follow sau pull-to-refresh), tài khoản đó cần tối thiểu 24h–48h để hệ thống giảm mức giám sát tự động.
  - Sau 48h nghỉ follow (vẫn duy trì lướt feed làm ấm tài khoản và đăng video), tài khoản có thể chạy lại follow.
- **Chiến lược Budget Thăm Dò Sau Sự Cố:**
  - Ở cữ chạy đầu tiên sau khi hết 48h cooldown, **CẤM dồn full budget (8–10 follow)** ngay từ đầu.
  - Khuyến nghị: Chạy **budget thăm dò 3–5 follow/phiên**, chia đều 2 cữ sáng/tối cách nhau $\ge 8$ tiếng để kiểm tra độ hồi phục Trust Score.

## 2. Pitfall Lệch Số Liệu Cột "Video Đã Đăng" Giữa Workbook và Thực Tế App
- **Nguyên nhân lệch:**
  - Khi tiến trình upload video ở Phiên 3 bị `upload-timeout` hoặc gặp sự cố mạng, video có thể đã được đẩy lên app TikTok thành công nhưng script chưa kịp cập nhật tăng chỉ số tại cột `Video Đã Đăng` trong file `Tik2.xlsx` / `taikhoan_run_safe.xlsx`.
  - Hậu quả: Cột `Video Đã Đăng` trên sheet vẫn lưu giá trị `0`, dẫn đến:
    1. Khi audit bằng script/tool sẽ kết luận sai là tài khoản chưa có video.
    2. Nếu follow gate đọc trực tiếp cột `Video Đã Đăng` từ workbook, tài khoản có video thật trên app vẫn bị ép về budget = 0 hoặc bị xếp nhầm nhóm clone.
- **Quy tắc Vận Hành & Khắc Phục:**
  - Định kỳ audit đối soát giữa Profile Grid thật trên app (hoặc kiểm tra live profile) với cột `Video Đã Đăng` trong `TikN.xlsx`.
  - Đồng bộ cập nhật thủ công hoặc chạy script sync để đưa giá trị số video thật vào `TikN.xlsx` và `taikhoan_run_safe.xlsx` trước khi áp gate follow.
