# Báo Cáo Up Avatar: Kiến Trúc Dashboard SQLite & Crawler Re-scan Tức Thời

## 1. Bản Chất Vận Hành Của Báo Cáo Avatar
- **Source of Truth Duy Nhất**: Trạng thái avatar (`has_avatar`) của toàn bộ nick farm BẮT BUỘC lấy từ cơ sở dữ liệu SQLite `D:/Taadaa/data/tiktok_tracker.db` (dữ liệu hiển thị trực tiếp trên Web Dashboard `http://kibe:1905`).
- **Tuyệt Đối Không Dùng Cột Excel "Avatar" Để Báo Cáo**: File Excel chỉ ghi nhận kết quả upload cục bộ của máy; TikTok có thể nhả avatar hoặc nick lỗi khiến cột Excel ghi "OK" nhưng trên TikTok thực tế vẫn là avatar xám mặc định. Do đó, Dashboard SQLite là thẩm định độc lập từ bên ngoài.

## 2. Vấn Đề Lệch Pha Dữ Liệu & Giải Pháp
- **Triệu chứng**: Cron quét toàn farm (`daily-tiktok-farm-tracker`) chỉ chạy 1 lần/ngày vào lúc 07:00 sáng. Khi ca tối (21:00 - 23:45) chạy upload avatar xong, DB vẫn giữ snapshot cũ từ 7h sáng, khiến báo cáo cuối ca (sau 23:30) báo thiếu avatar ảo và tiếp tục spawn lại các máy đã up.
- **Giải Pháp Bắt Buộc (Crawler Re-scan)**:
  1. Sau khi mỗi batch upload avatar hoàn tất trong `check_batch_status`, tự động gọi crawler `tiktok_account_tracker.py` quét lại đúng danh sách máy vừa up (`--machines <list> --workers 10`).
  2. Trước khi tổng hợp báo cáo tổng kết cuối ca (`report_final_summary`), kiểm tra và gọi `rescan_completed_machines` để DB có snapshot mới nhất trước khi tính phần trăm và số máy còn thiếu.
  3. Ghi telemetry structured metrics JSON (`duration_sec`, `exit_code`, `machines_count`, `stdout/stderr`) phục vụ audit và reviewer.

## 3. Khóa Phạm Vi Host (Host Context & Machine Range Filter)
- **Vấn Đề**: Bảng `farm_account_info` lưu tập trung toàn bộ máy của Farm (cả Kibe và Admin). Nếu truy vấn `WHERE m.tik = ?` mà không có điều kiện `host_id`, dữ liệu sẽ bị trộn lẫn (ví dụ Tik 7 của Kibe bị cộng 67 máy của Admin thành 132 máy).
- **Quy Tắc Lọc Chuẩn**:
  - **Host Kibe**: Chỉ lấy các máy thuộc Kibe (`may < 200` và `(host_id = ? OR host_id IS NULL OR host_id = ?)` với params `('kibe', '')`).
  - **Host Admin**: Chỉ lấy các máy thuộc Admin (`(host_id = ? OR may >= ?)` với params `('admin', 200)`).
  - **Parameterization**: BẮT BUỘC dùng parameterized query trong SQLite, tuyệt đối không dùng format string ghép câu lệnh WHERE để tránh lỗi reviewer và SQL injection.
