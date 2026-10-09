# Cross-Host Media Preflight & Remote Execution Contract

## Context & Incident (2026-10-05)
Trong kiến trúc Central Controller (Kibe) điều khiển cụm phone farm từ xa (Admin: M201-280):
- Kibe chạy `tiktok_runner.py` và spawn `run-feed-session.ps1` cục bộ trên Kibe, kết nối tới dàn điện thoại Admin qua remote ADB (`ADB_SERVER_SOCKET=tcp:192.168.110.119:5037`).
- Kho video render của Admin (`D:\TIKTOK-videonuoinick-admin`) nằm trên ổ đĩa vật lý của máy Admin (`admin-farm`). Máy Kibe KHÔNG có thư mục này.
- Khi luồng nuôi feed hoàn tất và kích hoạt `_run_upload_hook()`, Gate 5 kiểm tra `video_file.is_file()` trên filesystem cục bộ của Kibe. Do không tìm thấy file trên Kibe, script đánh dấu nhầm 41 máy thành `video_not_rendered` (`Hết video/Cần cào`), gây báo động giả nghiêm trọng lên Farm Alert.

## Invariant Bất Biến
1. **Tuyệt đối cấm Network Share / SMB / sao chép kho video sang Controller:**
   - Không được đề xuất hay tạo SMB share (`\\admin-farm\...`), mount ổ đĩa mạng, hoặc sao chép hàng trăm GB video từ Admin sang Kibe chỉ để vượt qua lệnh `Path.exists()` cục bộ.
   - Kho video render thuộc quyền sở hữu của máy gắn thiết bị (Admin PC).
2. **Kiểm tra và Thực thi Upload đúng Host sở hữu (Owner-Host Execution):**
   - Với các máy thuộc cụm Admin (`host_id == 'admin'` hoặc `machine >= 200`), việc kiểm tra preflight video và lệnh upload hook `scripts.tiktok_workflow` BẮT BUỘC phải thực thi trên chính host Admin (qua SSH `admin-farm` hoặc executor từ xa).
   - Trên host Admin, đường dẫn `D:\TIKTOK-videonuoinick-admin` là local, workbook là local, và ADB là local (`127.0.0.1:5037`).
3. **Cấm rò rỉ Remote ADB Socket sang Host sở hữu:**
   - Khi gọi tiến trình upload trên host Admin, CẤM truyền biến môi trường `ADB_SERVER_SOCKET=tcp:192.168.110.119:5037` của Kibe. Host Admin phải giao tiếp với các thiết bị qua ADB server cục bộ của nó.
4. **Mocked Unit Test Boundary:**
   - Mọi test case cho luồng cross-host preflight/upload BẮT BUỘC phải chạy offline với mocked SSH / subprocess, cấm kết nối live thiết bị hay mạng thật trong test suite.
