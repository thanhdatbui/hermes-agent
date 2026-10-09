# Single Master (Kibe) - Thin Worker (Admin) Architecture & Operational Patterns

## 1. Nguyên Tắc Cốt Lõi
- **Đầu não duy nhất:** Toàn bộ cron, bot Hermes, logic nuôi nick, phân bổ slot và Git development chỉ diễn ra trên Kibe Master.
- **Admin trạm chấp hành (Thin Worker):** Admin chỉ duy trì daemon ADB lắng nghe cổng mạng LAN (`192.168.110.119:5037`) và OpenSSH Server (`Port 22`). Không chạy bot Hermes, không chạy cron feed chính để tránh đè slot.
- **Cold Standby (Dự phòng thảm họa):** Thư mục Git và môi trường trên Admin được giữ nguyên vẹn 100%, không xóa, để làm nút dự phòng khi Kibe bảo trì.

## 2. Kết Nối & Điều Khiển Qua Mạng LAN
- **Remote ADB điều khiển 80 máy S7 Admin (201–280):**
  - Cú pháp lệnh adb: `adb -H 192.168.110.119 -P 5037 -s <serial> <command>`
  - Trong Python: `AdbClient(host="192.168.110.119", port=5037, serial=...)`
  - Tự động định tuyến: Máy `N < 200` chạy local USB (`host=None, port=None`), máy `N >= 200` chạy remote LAN.
- **SSH điều khiển Windows OS Admin:**
  - Alias: `ssh admin-farm`
  - Direct: `ssh Admin@192.168.110.119` (sử dụng private key `~/.ssh/id_ed25519_kibe_admin`)
  - Thao tác: Bật/tắt cron, kiểm tra process, quản lý service trên Admin do Kibe SSH sang gõ lệnh từ xa.

## 3. Quản Lý Dữ Liệu Excel Đa Cụm (Dual-Cluster Data Isolation)
- **Không bao giờ gộp file Excel:**
  - Cụm Kibe: `D:/OneDrive/TaadaaData/kibe/` (`taikhoan_run_safe.xlsx`, `PROXYgandienthoai.xlsx`)
  - Cụm Admin: `D:/OneDrive/TaadaaData/admin/` (`taikhoan_run_safe.xlsx`, `PROXYgandienthoai.xlsx`)
- Tránh tranh chấp khóa file (`file lock contention`) và lỗi tràn bộ nhớ của thư viện `openpyxl`.

## 4. Chuẩn Hóa Báo Cáo Phân Tách Theo Farm (Report Grouping Standard)
Mọi báo cáo cron nuôi nick, watchdog hay thông báo Telegram của toàn farm BẮT BUỘC phân tách rõ theo từng cụm, tuyệt đối không gộp chung:
```text
📊 [TIKTOK NUÔI ACC] Ca X hoàn tất

🏢 【FARM KIBE - MÁY 1-80】
• Tổng máy xử lý: ...
• Lướt Feed: Success / Fail / Trống slot
• Follow chéo: ...
• Đăng Video: ...

🏢 【FARM ADMIN - MÁY 201-280】
• Tổng máy xử lý: ...
• Lướt Feed: Success / Fail / Trống slot
• Follow chéo: ...
• Đăng Video: ...
```
