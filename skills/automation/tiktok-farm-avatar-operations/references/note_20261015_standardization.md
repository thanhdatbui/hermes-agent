# Bổ sung bài học từ sự cố chuẩn hoá kênh @sambich012 (15/10/2026)

## 1. Cấm Up Lại File Avatar Có Sẵn Khi Nhận Lệnh Đổi Avatar
- Khi User yêu cầu "đổi ava" hoặc "chuẩn hoá kênh", file `avatar.jpg` nằm trong `D:/TIKTOK-videonuoinick/<F_out>/` hoặc `D:/video goc/<F_src>/` chính là avatar cũ đang dùng.
- Bắt buộc trích xuất frame mới từ video khác (`10.mp4`, `20.mp4`...) để tạo diện mạo hoàn toàn mới.

## 2. Bẫy Exit Code 0 Khi Bị SKIPPED_LOCKED
- Launcher avatar chạy qua PowerShell/subprocess trả về exit code 0 ngay cả khi 100% target bị bỏ qua do `device lock active`.
- Không được tin exit code 0; bắt buộc parse `summary.csv` để xác nhận `Verified == True` và `Status == THÀNH CÔNG`.
