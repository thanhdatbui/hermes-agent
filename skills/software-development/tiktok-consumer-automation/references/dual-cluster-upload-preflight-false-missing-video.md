# Dual-Cluster Upload Preflight: False "video_not_rendered" & Anti-SMB Sharing Pattern

## 1. Bối cảnh kiến trúc Dual-Cluster (Taadaa Phone Farm)
- **Cụm Kibe (Máy 1–80)**: Controller chính, điều khiển thiết bị qua ADB local (`127.0.0.1:5037`). Kho video render nằm tại `D:\TIKTOK-videonuoinick`.
- **Cụm Admin (Máy 201–280)**: Máy trạm phụ trợ, kết nối qua mạng LAN với alias SSH `admin-farm` (`192.168.110.119`). Kibe điều khiển thiết bị Android của Admin qua `ADB_SERVER_SOCKET=tcp:192.168.110.119:5037`.
- **Kho video render của Admin**: Nằm trực tiếp trên ổ cứng máy Admin tại `D:\TIKTOK-videonuoinick-admin` (chứa hơn 27.000 clip render cho 80 máy).

## 2. Hiện tượng lỗi: Báo động giả "Hết video / Cần cào"
- Watchdog phiên nuôi feed (`feed_session_watchdog.py`) gửi báo cáo:
  ```text
  • Đăng Video (1/2 - 0 video đã đăng):
    + Hết video/Cần cào (41): 201, 203, 204, 205, 206, 208, 210, 212...
    + Bỏ qua (18): Đang dưỡng sinh (18)
  ```
- Nhưng khi kiểm tra trực tiếp trên máy Admin bằng SSH PowerShell:
  ```powershell
  ssh admin-farm "powershell -Command \"Test-Path 'D:/TIKTOK-videonuoinick-admin/1/3.mp4'\"" # -> True!
  ```
  Tất cả 41 file video mục tiêu đều tồn tại 100% trên máy Admin.

## 3. Nguyên nhân cốt lõi (Root Cause)
1. **Lệch Host kiểm tra Preflight (Gate 5)**:
   - Cron feed session (`tiktok_runner.py`) chạy trên CPU máy **Kibe**.
   - Khi kích hoạt `_run_upload_hook()` trong `multi_machine_feed_session.py`, hàm lấy đường dẫn `media_source_root` từ cấu hình Admin (`D:\TIKTOK-videonuoinick-admin`).
   - Nhưng lệnh kiểm tra `video_file.is_file()` lại thực thi trên filesystem cục bộ của **Kibe**.
   - Trên máy Kibe hoàn toàn không có thư mục này -> Python kết luận `video_not_rendered` -> Watchdog xếp vào nhóm "Hết video / Cần cào".
2. **Lệch Host thực thi Subprocess Upload**:
   - Nếu preflight bị bypass, tiến trình con upload video `scripts.tiktok_workflow` cũng sẽ bị spawn trên máy Kibe, cố gắng tìm file video Admin trên Kibe và truyền ADB socket sai lệch sang device.

## 4. Phản xạ sai lầm chết người (Critical Anti-Pattern)
- **Đề xuất share thư mục qua mạng (SMB / Network Drive / Symlink)**:
  - Agent thiếu kinh nghiệm thường nảy ra ý nghĩ: *"Share thư mục `D:\TIKTOK-videonuoinick-admin` của Admin sang Kibe để Kibe nhìn thấy file"*.
  - **Hậu quả**:
    * Vi phạm nguyên tắc Single Controller / Zero Complexity.
    * Gây nghẽn băng thông mạng LAN khi hàng chục luồng cùng stream video qua SMB.
    * Dễ đứt gãy kết nối khi SMB authentication bị reset hoặc IP đổi.
    * Bị User phản ứng gay gắt vì biến giải pháp đơn giản thành over-engineering lố bịch.

## 5. Giải pháp chuẩn tắc (Architectural Rule)
1. **Phân lập theo Target Host / Machine Range**:
   - `machine < 200` (Kibe): Chạy preflight kiểm tra file và spawn subprocess cục bộ trên Kibe như bình thường.
   - `machine >= 200` hoặc `host_id == "admin"` (Admin):
     - **CẤM** gọi `Path.is_file()` hay glob cục bộ trên máy Kibe đối với đường dẫn video của Admin.
     - Kiểm tra preflight và thực thi upload trên **chính host Admin** qua SSH alias `admin-farm`.
     - Sử dụng đúng môi trường Python của Admin: `D:/Taadaa/python-envs/automation/Scripts/python.exe`.
     - Sử dụng đúng cấu hình Admin: repo `D:/Taadaa/Tiktok-video`, config `config-admin.yaml`, workbook `D:/OneDrive/TaadaaData/admin/TikN.xlsx`.
2. **Loại trừ biến môi trường rò rỉ**:
   - Khi kích hoạt tiến trình upload trên Admin qua SSH, **TUYỆT ĐỐI KHÔNG** truyền biến `ADB_SERVER_SOCKET` của Kibe sang Admin, vì trên máy Admin ADB daemon là `127.0.0.1:5037` nội bộ.
