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

## 3. Quy Tắc Điều Phối Bắt Buộc
1. **Phân Định Cluster Theo Máy:**
   - Máy `<= 80`: Cluster Kibe (local socket `127.0.0.1:5037`).
   - Máy `>= 200`: Cluster Admin (remote socket `192.168.110.119:5037`, nạp `admin.yaml` và workbook Admin).
2. **Kỷ Luật Tách Batch Khi Chạy Live:**
   - Khi runner chạy trên Kibe: CHỈ nhận target máy `<= 80` (hoặc bọc socket adapter định tuyến `192.168.110.119:5037` riêng cho worker của máy Admin).
   - Để chạy cụm Admin: BẮT BUỘC dispatch sang host Admin qua `D:/Taadaa/tools/admin_ssh.py` hoặc chỉ định remote ADB server trong lệnh worker.
3. **Canary & Tái Hiện:**
   - Khi canary hoặc troubleshoot máy Admin: BẮT BUỘC chỉ định `--machine <N>` kèm socket `192.168.110.119:5037`, cấm test bằng ADB local của Kibe.
