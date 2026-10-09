# Dual-Cluster Feed Runner & Watchdog Batch Ops (160 Máy)

## 1. Cơ Chế Dual-Cluster Runner (`tiktok_runner.py`)
- Kibe Master đóng vai trò đầu não duy nhất kích hoạt ca chạy:
  - **Cụm Kibe (1–80)**: Chạy với `D:/OneDrive/TaadaaData/kibe/taikhoan_run_safe.xlsx`, artifact tại `D:/Taadaa/runtime/kibe/live`.
  - **Cụm Admin (201–280)**: Chạy với `D:/OneDrive/TaadaaData/admin/taikhoan_run_safe.xlsx`, artifact tại `D:/Taadaa/runtime/admin/live`.
  - Worker subprocess nuôi acc tự động nhận diện `account.machine >= 200` để gắn Remote ADB `-H 192.168.110.119 -P 5037`.

## 2. Quy Chuẩn Báo Cáo Phân Tách Theo Farm (`feed_session_watchdog.py`)
- Mọi báo cáo ca nuôi acc BẮT BUỘC phân tách rõ thành 2 khối riêng biệt trên Telegram:
  ```text
  📊 [TIKTOK NUÔI ACC] Ca X - Phiên Y/2 hoàn tất (Row Z)

  🏢 【FARM KIBE - MÁY 1-80】
  • Tổng máy xử lý: 80 máy
  • Lướt Feed: ...
  • Follow chéo: ...
  • Đăng Video: ...

  🏢 【FARM ADMIN - MÁY 201-280】
  • Tổng máy xử lý: 80 máy
  • Lướt Feed: ...
  • Follow chéo: ...
  • Đăng Video: ...
  ```
- CẤM gộp chung số liệu giữa 2 cụm để đảm bảo khả năng phát hiện lỗi cụm tức thì.

## 3. Quy Trình Điều Tra Hiện Trường Khi Báo Cáo Báo Lỗi Máy Admin (>=200)
1. Tra cứu O(1) trạng thái thiết bị:
   `python D:/Taadaa/tools/inspect_machine.py <N>`
2. Đọc log chi tiết và ảnh chụp màn hình ngay trên máy Kibe:
   `D:/Taadaa/runtime/admin/live/<Date>/row-<Row>-<Time>/...`
3. Nếu cần can thiệp hệ thống Windows Admin:
   `ssh admin-farm "<powershell_command>"`
