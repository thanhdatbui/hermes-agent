# Multi-Host Cron Synchronization & Dedicated Reporting Discipline (Kibe vs Admin)

## 1. Cơ Chế Tự Động Đồng Bộ Cấu Hình Cron Toàn Farm
Hệ thống sử dụng tiến trình watchdog nền `cron_sync_watchdog.py` (chạy định kỳ 15 phút, Job ID `2b5b608429c7`) để loại bỏ triệt để việc copy tay và drift cấu hình:
- **Nguồn chân lý (Source of Truth):** `%LOCALAPPDATA%\hermes\cron\jobs.json` trên máy Kibe.
- **Điểm đến tự động:**
  1. `D:\Taadaa\Hermes\deploy\hermes-home\cron\jobs.json` (Git deploy repo).
  2. `D:\OneDrive\Taadaa_Sync_Shared\hermes-cron\jobs.json` (Kho chia sẻ qua OneDrive cho máy Admin).
  3. Quét toàn bộ file script (`.py`, `.ps1`) trong `%LOCALAPPDATA%\hermes\scripts\` và tự động mirror sang OneDrive Shared nếu có mtime mới hơn.

## 2. Kịch Bản Đồng Bộ Sang Bot Admin
Khi cần nạp/cập nhật cron trên máy Admin, câu lệnh duy nhất cần kích hoạt trong chat bot Admin là:
```text
Chạy lệnh sync cron từ Kibe:
python D:\OneDrive\Taadaa_Sync_Shared\tools\setup_admin_cron.py
```
Script này tự động:
- Đọc `D:\OneDrive\Taadaa_Sync_Shared\hermes-cron\scripts\` copy đè sang `%LOCALAPPDATA%\hermes\scripts\` của Admin.
- Tự động nạp hoặc cập nhật 12 core cron jobs chuẩn của Admin vào `%LOCALAPPDATA%\hermes\cron\jobs.json`.

## 3. Quy Tắc Tách Biệt Máy & Báo Cáo (Chung vs Riêng)

### A. Tách biệt tập máy & Dữ liệu
- Tự động định danh môi trường qua `TAADAA_HOST_CONFIG` / `kibe.yaml` vs `admin.yaml`:
  * **Kibe:** Làm việc trên `D:\OneDrive\TaadaaData\kibe`, quản lý cụm máy của Kibe (Tik 5, 6, 7, 8, 3, 4).
  * **Admin:** Làm việc trên `D:\OneDrive\TaadaaData\admin`, quản lý cụm máy của Admin (Tik 2, 1, 3, 4, 5, 6, 7, 8).
- Tuyệt đối không xung đột thiết bị nhờ cơ chế **Device Lock vật lý 1:1** (`~/.codex/device-locks/machine_<M>.lock.json`).

### B. Tách biệt kênh báo cáo
- **Báo cáo Vận Hành Farm (Chung):** Gửi về nhóm Farm Alert (`telegram:-5373649734`) cho các tác vụ toàn farm (Up Avatar, Dọn cache ca đêm, Tiến độ Render/Download, Báo cáo phiên Feed). Bắt buộc có prefix phân định máy rõ ràng trong tiêu đề:
  * `[FARM REPORT][KIBE] ...`
  * `[FARM REPORT][ADMIN] ...`
- **Báo cáo Giám Sát Nội Bộ (Riêng):**
  * `hermes-stale-watchdog` và `auto-trim-startup-files` trên Admin gửi về kênh riêng của Admin (`telegram:-5188753741`).
  * Các utility dọn dẹp nền (`reap-dead-owner-locks`, `taikhoan-run-safe-sync`, `cron-sync-watchdog`) chạy chế độ `local` im lặng trên từng máy.
