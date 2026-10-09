# Chẩn Đoán & Điều Phối Render Worker (Kibe vs Admin)

## 1. Tránh Nhầm Lẫn Giữa Kibe Local vs Admin Remote
- **Kibe Local**:
  - Thư mục video gốc: `D:\video goc`
  - Thư mục render: `D:\TIKTOK-videonuoinick`
  - Tiến trình chạy trên host hiện tại (kiểm tra qua `tasklist`).
- **Admin Remote**:
  - Thư mục video gốc: `D:\video goc may 2`
  - Thư mục render: `D:\TIKTOK-videonuoinick-admin`
  - Tiến trình chạy trên máy Admin (`192.168.110.119`). Tuyệt đối không dùng `tasklist` của Kibe để phán đoán tiến trình Admin.

## 2. Kiểm Tra Trạng Thái Render Admin O(1) Qua File Đồng Bộ OneDrive
Do cả Coordinator và Worker Gate đều áp dụng strict allowlist hạn chế lệnh SSH trực tiếp (`ssh admin-farm ...`), cách nhanh và chuẩn nhất để đọc trạng thái Admin là qua file telemetry cache đồng bộ thời gian thực:
- **Đường dẫn**: `D:\OneDrive\TaadaaData\admin\last_render_stats.json`
- **Các trường cốt lõi**:
  - `"is_rd": true` ➔ Render trên Admin đang chạy.
  - `"is_rd": false` ➔ Render trên Admin đang dừng (không có ffmpeg nào chạy).
  - `"is_dl": true / false` ➔ Trạng thái download video gốc.
  - `"tik_stats"`: Chi tiết số folder đạt chuẩn $\ge 45$ clip theo từng Tik1..Tik8.

## 3. Quy Tắc Ứng Xử Khi User Yêu Cầu "Giảm Worker Render Xuống Còn 1"
1. **Cập nhật launcher**:
   - Sửa `D:\Taadaa\Tiktok-video\run_admin_render_chain.bat`: Đảm bảo cờ `--parallel 1` (tránh để `--parallel 2`).
   - Đảm bảo các script PowerShell (`run_tikX_random_render.ps1`) chạy với `-Parallel 1`.
2. **Đối soát trạng thái thực tế trước khi trả lời**:
   - Đọc `D:\OneDrive\TaadaaData\admin\last_render_stats.json`.
   - Nếu `is_rd == false`: Phải giải thích mạch lạc ngay:
     *"Cấu hình launcher đã được chuyển về 1 worker (--parallel 1) cho các đợt chạy tới. Hiện tại đợt render trước đó đã kết thúc / đang dừng, máy Admin đang rảnh hoàn toàn."*
   - Tuyệt đối không báo mâu thuẫn: vừa bảo chuyển về worker 1 lại vừa bảo "0 tiến trình chạy" mà không giải thích rõ là đợt cũ đã hoàn tất từ trước.
