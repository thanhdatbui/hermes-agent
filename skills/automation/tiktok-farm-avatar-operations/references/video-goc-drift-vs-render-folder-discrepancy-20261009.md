# Video Goc Drift vs Render Folder Discrepancy in Single-Nick Avatar Triage (2026-10-09)

## Context & Incident
Khi nhận screenshot đổi avatar cho tài khoản đơn lẻ (như `@vothitram9184` - Máy 16 / Tik 7):
- Excel `Tik7.xlsx` ghi nhận:
  - `Folder Video`: 127
  - `video gốc`: 496
  - `Keyword Video`: "Câu chuyện"
- Trong thực tế:
  - Thư mục `D:\video goc\496` chứa 52 video sự cố giao thông (dashcam tai nạn, đèo núi, banner vàng "Chịu thua!", "Vãi linh hồn", "thôi"). Nếu lấy video gốc `496` để cắt avatar, sẽ bị cắt trúng biển chữ vàng hoặc hiện trường tai nạn.
  - Thư mục `D:\TIKTOK-videonuoinick\127` và `D:\video goc\127` chứa 45 video chân dung thời trang / gái xinh (trùng khớp với các video thực tế đã đăng trên kênh TikTok của tài khoản).
  - File `avatar.jpg` cũ trong folder 127 bị cắt quá sát (chỉ thấy phần miệng, cằm và cổ, mất hoàn toàn mắt và trán).

## Nguyên Tắc Đối Soát Media Trực Quan Trước Khi Cắt Avatar
1. **Kiểm tra song song cả 2 nguồn video:**
   - Trích xuất frame mẫu (1.mp4, 2.mp4, 8.mp4) từ cả `D:\video goc\<video_goc>` và `D:\TIKTOK-videonuoinick\<folder_video>`.
   - Dùng Vision API đối chiếu nội dung frame với các thumbnail bài đăng trên ảnh screenshot profile của tài khoản để xác định chính xác folder nào là nội dung thực tế đang đăng trên kênh.
2. **Cắt chân dung cân đối chuẩn Headroom:**
   - Không lấy frame t=0s. Quét các video đầu (1, 2, 4...) tại timestamp 1.5s - 4.5s.
   - Dùng Haar Cascade phát hiện khuôn mặt và mở rộng vùng crop với headroom (giữ đỉnh đầu và trán, `box_size = int(fh * 2.4)`).
   - Đánh giá bằng Vision API để chấm điểm (chọn candidate >= 8.5/10).
3. **Đồng bộ kho lưu trữ & Reset Queue:**
   - Khi folder render chứa video chuẩn, copy avatar mới vào cả:
     - `D:\video goc\<folder_video>\avatar.jpg`
     - `D:\TIKTOK-videonuoinick\<folder_video>\avatar.jpg`
   - Cập nhật SQLite `avatar_replace_queue`:
     `UPDATE avatar_replace_queue SET status='PENDING', last_error=NULL, updated_at=datetime('now','localtime') WHERE username='<username>';`
4. **Cấu hình thiết bị trước khi chạy runner:**
   - Thiết lập `settings put global stay_on_while_plugged_in 3` và wake screen (`keyevent 224, 82`) trên thiết bị thật trước khi dispatch runner để tránh timeout đen màn hình.
