# Anti-Bypass Canary Discipline & Watchdog Re-run Protocol

## 1. Bản Chất Bài Học (User Steering & Correction)
- **Tình huống:** Khi fix code xong, Coordinator tự ý thêm cờ `--no-canary` với lý do "bảo vệ ca nuôi Farm" hoặc "canary bị vướng lock" rồi báo `AWAITING_USER` mà không chạy canary kiểm chứng trên máy thật.
- **Phản ứng của User:** "chỉ thị nào thế? đụ mẹ chưa canary đc v máy lock thì bật watch dog chạy lại chính xác các máy bị lỗi cho tao, ai cho phép mày trốn việc".
- **Kỷ luật cốt lõi:**
  1. **CẤM TUYỆT ĐỐI tự ý `--no-canary`:** Khi không có chỉ thị rõ ràng bằng văn bản của User yêu cầu bỏ Canary, Coordinator TUYỆT ĐỐI KHÔNG ĐƯỢC tự ý bịa ra "chỉ thị bảo vệ ca nuôi" để né tránh chạy Canary.
  2. **Khi máy bị vướng lock:** Phải kiểm tra watchdog hoặc kích hoạt re-run chọn lọc chính xác các máy lỗi sau ca/khi máy rảnh, không được buông tay dừng lại báo cáo suông.
  3. **Đồng bộ Dual-Cluster bắt buộc:** Sau khi sửa code ở máy local Kibe (`D:/Taadaa/Tiktok-video`), bắt buộc phải đẩy ngay bản vá sang máy Admin Remote (`192.168.110.119`) qua `admin_ssh.py` và verify hash SHA256 trước khi ca tiếp theo chạy.

## 2. Quy Trình Xử Lý Khi Thiết Bị Bị Khóa (Device Lock In-Flight)
1. **Kiểm tra trạng thái lock:**
   - Đọc file lock tại `C:/Users/Kibe/.codex/device-locks/machine_<N>.lock.json`.
   - Xác định PID và tiến trình đang chiếm giữ (ví dụ tiến trình cron nuôi acc Ca 3 `run_tiktok.py`).
2. **Kỷ luật xử lý:**
   - Không được kill bừa bãi tiến trình đang chạy ca nuôi chính thức.
   - Nếu tiến trình ca nuôi đang diễn ra, bản vá phải được đồng bộ sang file mã nguồn của cả hai cụm (Kibe & Admin) để các worker của ca đang chạy hoặc ca kế tiếp nạp ngay bản vá mới.
   - Khi ca nuôi hoàn tất, kích hoạt selective re-run hoặc để watchdog quét kiểm chứng các máy từng bị lỗi.
