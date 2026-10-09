# Kiến Trúc Single Master (Kibe) — Thin Worker (Admin) & Dual-Cluster Operations

## 1. Nguyên Tắc Cốt Lõi
- **Kibe Master Điều phối Độc quyền**:
  - Quản lý toàn bộ 160 máy: Cụm Kibe (1–80 qua USB Local) và Cụm Admin (201–280 qua Remote ADB LAN `192.168.110.119:5037` và OpenSSH `ssh admin-farm`).
  - Mọi chỉnh sửa mã nguồn, cấu hình cron, fix bug chỉ diễn ra trên Kibe Master, chấm dứt hoàn toàn tình trạng dual-master và phân mảnh git.
  - Máy Admin giữ Git làm trạm Standby dự phòng nguội (Disaster Recovery).

## 2. Quy Tắc Báo Cáo Định Kỳ Theo Farm (Dual-Cluster Reporting)
- **Tách Khối Minh Bạch**:
  - Mọi báo cáo ca nuôi acc / cron BẮT BUỘC phân tách thành 2 khối riêng biệt:
    - `🏢 【FARM KIBE - MÁY 1-80】`
    - `🏢 【FARM ADMIN - MÁY 201-280】`
  - CẤM gộp chung số liệu giữa 2 farm làm mất khả năng truy vết lỗi cục bộ.
- **Tách Thư Mục Dữ Liệu Excel**:
  - `D:/OneDrive/TaadaaData/kibe/taikhoan_run_safe.xlsx` (máy 1–80).
  - `D:/OneDrive/TaadaaData/admin/taikhoan_run_safe.xlsx` (máy 201–280).
  - CẤM gộp file Excel nhằm tránh file lock contention của `openpyxl` và giới hạn bán kính ảnh hưởng khi có lỗi dữ liệu.

## 3. Điều Khiển & Can Thiệp Hiện Trường Admin
- **Inspect O(1) tức thì**:
  - `python D:/Taadaa/tools/inspect_machine.py <N>`
  - N < 200: Tra cứu Kibe local USB.
  - N >= 200: Tra cứu Admin remote LAN `192.168.110.119:5037`.
  - Trích xuất Model, Pin, Screen awake/sleep, Foreground Activity trong <0.3s.
- **Can thiệp hệ điều hành Windows Admin qua OpenSSH**:
  - Alias SSH đã cấu hình: `ssh admin-farm "<command>"`
  - Dùng để kiểm tra cron, pause/resume job, restart daemon ADB, dọn dẹp tiến trình treo trên máy Admin mà không cần Ultraviewer hay bắt user thao tác tay.
