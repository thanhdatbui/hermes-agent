# Chuẩn hóa Watchdog Tự Động Up Avatar Sau Ca Tối (post_evening_avatar_watchdog.py)

## 1. Mục tiêu & Vị trí Canonical
- Script nguồn chuẩn (canonical): `D:\Taadaa\Tiktok-video\scripts\post_evening_avatar_watchdog.py`.
- Đồng bộ tự động sang các vị trí phân phối runtime:
  - `C:\Users\<user>\AppData\Local\hermes\scripts\post_evening_avatar_watchdog.py`
  - `D:\Taadaa\Hermes\deploy\hermes-home\scripts\post_evening_avatar_watchdog.py`
  - `D:\OneDrive\Taadaa_Sync_Shared\hermes-cron\scripts\post_evening_avatar_watchdog.py`

## 2. Quy tắc Host Context & Mục tiêu Quét
Tự động nhận diện host (Kibe hoặc Admin) qua biến môi trường hoặc cấu hình:
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

## 3. Silent Guard & Kỷ luật Báo cáo Telegram (Farm Alert)
- **Silent Guard:**
  - Khung giờ chạy: `21:00` -> `23:30` (khung kích hoạt batch). Sau `23:30` đến `04:00` là khung kết thúc báo cáo tồn.
  - Im lặng hoàn toàn nếu:
    - Ngoài khung giờ cho phép (`04:00` -> `21:00`).
    - Có feed runner / follow / reg đang chạy (`run-feed-session.ps1`, `multi_machine_feed_session`, `run_tiktok.py`).
    - Số lượng device lock đang active > 5.
    - Đang có batch powershell upload avatar đang chạy ngầm (`run_tiktok_upload_avatar.ps1`).
    - Không có máy nào cần up.
- **Duy nhất 1 báo cáo tổng kết HTML:**
  - Chỉ gửi tin nhắn vào nhóm Farm Alert Telegram (`chat_id = -5373649734`) khi:
    1. Tất cả các Tik đã hoàn tất 100% (0 máy tồn).
    2. HOẶC đã hết khung giờ ca tối (sau `23:30`) và tổng kết các máy còn tồn lại.
  - Format HTML template chuẩn cho cả 2 máy:
    ```html
    🎉 <b>[FARM REPORT][{HOST}] BÁO CÁO TỔNG KẾT UP AVATAR: HOÀN TẤT 100%</b>
    • <b>Thời gian:</b> HH:MM:SS DD/MM/YYYY
    • <b>Trạng thái:</b> Tất cả các Tik đã hoàn tất 100% (0 máy tồn)
    • <b>Chi tiết từng Tik:</b>
    • <b>Tik X:</b> hoàn tất 100%
    ```
    Hoặc khi hết khung giờ:
    ```html
    ⏰ <b>[FARM REPORT][{HOST}] BÁO CÁO TỔNG KẾT UP AVATAR: HẾT KHUNG GIỜ</b>
    • <b>Thời gian:</b> HH:MM:SS DD/MM/YYYY
    • <b>Trạng thái:</b> Hết khung giờ ca tối (sau 23:30), còn N máy chưa up
    • <b>Chi tiết từng Tik:</b>
    • <b>Tik X:</b> còn M máy (1,2,3...)
    ```
