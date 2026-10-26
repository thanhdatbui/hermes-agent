# Điều Phối Batch 2FA TikTok Cụm Farm Admin (Máy 201-280) Qua Remote ADB Socket (26/10/2026)

## 1. Hiện Tượng Thực Tế
- Báo cáo 2FA ban đêm toàn farm:
  - Farm Kibe (Máy 1-80): Hoàn tất 21 | Bỏ qua 18 | Lỗi 34
  - Farm Admin (Máy 201-280): Hoàn tất 0 | Bỏ qua 22 | Lỗi 69
- Cụm Admin liệt toàn bộ 69 máy mục tiêu (0 máy thành công).

## 2. Nguyên Nhân Kỹ Thuật (Root Cause)
1. **Lệch ADB Host Socket:**
   - Máy 1-80 kết nối trực tiếp vào máy chủ Kibe qua cổng USB / XiaoWei local (`localhost:5037`).
   - Máy 201-280 nằm vật lý trên máy chủ Admin, kết nối qua ADB server của Admin tại `192.168.110.119:5037`.
2. **Batch Runner Chạy Ngầm Mặc Định Local ADB:**
   - `python_runner/run_batch_live_2fa.py` quét workbook và đóng băng toàn bộ target (cả Kibe và Admin).
   - Khi fork worker `run_capture_phase_b.py`, tham số `--adb-path` mặc định trỏ về `C:\Program Files (x86)\xiaowei\tools\adb.exe` mà không có biến môi trường `ADB_SERVER_SOCKET=tcp:192.168.110.119:5037` cho các máy `>= 200`.
   - Kết quả: Tất cả worker gán cho máy 201-280 đều tìm thiết bị trên ADB server local của Kibe -> Gặp `DEVICE_NOT_CONNECTED` hoặc crash worker hàng loạt.

## 3. Quy Tắc Điều Phối Bắt Buộc & Giải Pháp Đã Áp Dụng (26/10/2026)
1. **Cơ Chế Auto-Routing Trong Code (`resolve_cluster_adb_endpoint`):**
   - Trong `run_capture_phase_b.py`, hàm `resolve_cluster_adb_endpoint(machine)` kiểm tra `int(machine) >= 200`:
     * Máy Admin (≥ 200): trả về `("192.168.110.119", 5037, r"D:\Taadaa\machine-config\admin.yaml")`.
     * Khởi tạo `AdbClient(..., host=host, port=port)` và set `os.environ.setdefault("TAADAA_HOST_CONFIG", host_cfg)`.
     * Giúp VPN gate `require_android_vpn` đọc đúng workbook mapping Admin (`D:\OneDrive\TaadaaData\admin\PROXYgandienthoai.xlsx`).
   - Trong `run_batch_live_2fa.py`, `run_target()` chủ động gán `worker_env["TAADAA_HOST_CONFIG"]` cho worker dựa trên số máy.
2. **Fallback `automation_core` Cho Standalone Chạy Trên Host Admin:**
   - Trên máy chủ Admin, tiến trình python mặc định không có `automation_core` trong global site-packages.
   - Đầu file `run_batch_live_2fa.py` và `run_capture_phase_b.py` bắt buộc tự chèn fallback `AUTO_CORE_SRC = Path(r"D:\Taadaa\automation-core\src")` vào `sys.path` trước khi import để chống văng `ModuleNotFoundError`.
3. **Kỷ Luật Tự Động Tiếp Tục Khi Auto-Resume Session (User Steering Invariant):**
   - Khi phiên làm việc chạm trần iteration limit (ví dụ turn 92/100) và hệ thống auto-resume, CẤM TUYỆT ĐỐI gửi tin nhắn chào hỏi đóng vai khách sáo ("Phiên làm việc đã khôi phục... bạn muốn làm gì tiếp theo?").
   - Coordinator BẮT BUỘC chủ động `git status`, kiểm tra tiến trình nền/kết quả đang chạy dở và làm tiếp tục ngay lập tức đến khi hoàn tất nghiệm thu (DONE).
4. **Canary & Tái Hiện:**
   - Khi canary hoặc troubleshoot máy Admin: BẮT BUỘC chỉ định `--machine <N>` kèm socket `192.168.110.119:5037`, cấm test bằng ADB local của Kibe.
