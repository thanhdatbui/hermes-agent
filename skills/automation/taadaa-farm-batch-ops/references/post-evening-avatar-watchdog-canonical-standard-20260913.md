# Chuẩn Hóa Script Canonical post_evening_avatar_watchdog.py & Đồng Bộ HTML Farm Report (2026-09-13)

## 1. Vị Trí Canonical & Đồng Bộ Runtime
- **Vị trí nguồn chuẩn (Canonical):** `D:\Taadaa\Tiktok-video\scripts\post_evening_avatar_watchdog.py`
- **Các vị trí runtime đồng bộ (Distribution Targets):**
  1. `C:\Users\<user>\AppData\Local\hermes\scripts\post_evening_avatar_watchdog.py`
  2. `D:\Taadaa\Hermes\deploy\hermes-home\scripts\post_evening_avatar_watchdog.py`
  3. `D:\OneDrive\Taadaa_Sync_Shared\hermes-cron\scripts\post_evening_avatar_watchdog.py`

## 2. Host Context Tự Động (Kibe vs Admin)
Script dùng chung cho cả 2 máy Kibe và Admin, tự động phân giải context:
- **Biến môi trường ưu tiên:** `TAADAA_HOST_CONFIG`
- **Fallback theo máy:**
  - Nếu `admin.yaml` hoặc user `admin`:
    - `host_id`: `admin`
    - `target_tiks`: `[2, 1, 3, 4, 5, 6, 7, 8]`
    - `workbook_dir`: `D:\OneDrive\TaadaaData\admin`
  - Nếu `kibe.yaml` hoặc user `kibe`:
    - `host_id`: `kibe`
    - `target_tiks`: `[5, 6, 7, 8, 3, 4]`
    - `workbook_dir`: `D:\OneDrive\TaadaaData\kibe`

## 3. Quy Chuẩn Silent Guard & Khung Giờ
- Khung kích hoạt batch: `21:00` -> `23:30`
- Khung kết thúc / chốt ca: sau `23:30` -> `04:00` sáng hôm sau.
- **Silent Guard (Thoát 0 im lặng, không spam):**
  - Ngoài khung giờ cho phép (`04:00` -> `21:00`).
  - Có feed runner / follow / reg đang hoạt động (`run-feed-session.ps1`, `multi_machine_feed_session`, `run_tiktok.py`).
  - Device locks đang active > 5.
  - Tiến trình PowerShell batch upload avatar đang thực thi (`run_tiktok_upload_avatar.ps1` hoặc `run_tiktok_upload_batch.ps1`).
  - Không có máy nào cần up.

## 4. Chuẩn Hóa HTML Farm Report Telegram
Gửi về Farm Alert Telegram (`chat_id = -5373649734`), CHỈ phát đúng 1 lần duy nhất:
- **Trường hợp Hoàn tất 100%:**
  ```html
  🎉 <b>[FARM REPORT][{HOST_ID.upper()}] BÁO CÁO TỔNG KẾT UP AVATAR: HOÀN TẤT 100%</b>
  • <b>Thời gian:</b> HH:MM:SS DD/MM/YYYY
  • <b>Trạng thái:</b> Tất cả các Tik đã hoàn tất 100% (0 máy tồn)
  • <b>Chi tiết từng Tik:</b>
  • <b>Tik X:</b> hoàn tất 100%
  ```
- **Trường hợp Hết khung giờ ca tối (sau 23:30):**
  ```html
  ⏰ <b>[FARM REPORT][{HOST_ID.upper()}] BÁO CÁO TỔNG KẾT UP AVATAR: HẾT KHUNG GIỜ</b>
  • <b>Thời gian:</b> HH:MM:SS DD/MM/YYYY
  • <b>Trạng thái:</b> Hết khung giờ ca tối (sau 23:30), còn {total_unuploaded} máy chưa up
  • <b>Chi tiết từng Tik:</b>
  • <b>Tik X:</b> còn {N} máy ({danh_sách_máy}...)
  ```
