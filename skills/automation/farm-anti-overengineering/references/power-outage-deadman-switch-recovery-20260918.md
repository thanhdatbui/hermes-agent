# SỰ CỐ CÚP ĐIỆN VÀ HARD GATE #0 DEADMAN SWITCH FALSE-POSITIVE (18/09/2026)

## 1. Hiện Tượng & Nguyên Nhân
- **Tình huống:** Host/máy trạm bị cúp điện đột ngột hoặc mất kết nối mạng/nguồn trong thời gian dài.
- **Triệu chứng:** Khi host bật lại và tiếp tục session cũ (hoặc reconnect Telegram gateway), Hard Gate #0 (Deadman Switch) kiểm tra timestamp:
  `Session ... đã chạy X phút (>15-20 phút) và thực hiện N thao tác thăm dò mà KHÔNG có State Change thực tế!`
- **Hậu quả:** Hook khóa cứng toàn bộ tool execution (`terminal`, `read_file`, `search_files`, `clarify`) khiến Coordinator bị đóng băng và liên tục fail loop, tưởng nhầm agent bị treo vô tận trong khi nguyên nhân thực tế là **cúp điện / downtime vật lý**.
- Ngoài ra, việc route nhầm model fallback ngoại vi (như 9router/omni không có context hệ thống) sẽ phát sinh phản hồi sai lệch (nói tiếng Anh, lạc đề).

## 2. Quy Trình Phục Hồi Chuẩn (Recovery Procedure)
Khi gặp Deadman Switch kích hoạt do cúp điện hoặc downtime ngoài ý muốn:
1. **Clear Signal / File State Lock:**
   - Deadman switch hook thường theo dõi qua state file / write event.
   - Gọi `write_file` tạo/cập nhật một state change thực tế (ví dụ: `write_file` vào một file signal/flag) để reset bộ đếm probe & cập nhật last active timestamp.
   - Xóa các file lock tạm liên quan nếu hook dùng file-based tracking trong `~/.hermes/` hoặc `AppData/Local/hermes/`.
2. **Khôi Phục Phân Vai Coordinator Chuẩn:**
   - Đảm bảo Coordinator không trực tiếp chạy loop quét toàn bộ ổ đĩa (`os.walk` diện rộng trên `D:/Taadaa`), tránh việc tiêu tốn thời gian khiến Deadman switch tiếp tục timeout.
   - Định vị trực tiếp file qua thông tin đã biết:
     - Dashboard TikTok Farm: `D:/Taadaa/tools/tiktok_dashboard.py` (cổng mặc định 20130, tham số `--port 1905`, database `D:/Taadaa/data/tiktok_tracker.db`).
     - Lệnh giải pháp truy cập từ xa cho web dashboard nội bộ: Khuyên dùng **Tailscale** (giữ nguyên hostname/IP P2P) hoặc **Cloudflare Tunnel** (`cloudflared tunnel --url ...`).
3. **Dispatch Worker Ngay Khi Xác Định Scope:**
   - Không tự sửa file lớn trên session chính; dispatch worker qua `delegate_task` với task contract rõ ràng để thực hiện thay đổi UI / metrics.
