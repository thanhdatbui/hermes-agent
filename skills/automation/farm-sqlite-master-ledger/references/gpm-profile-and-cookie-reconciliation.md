# Đối Soát Trạng Thái Mailbox & GPM Login Session

## 1. Cấu Trúc Ánh Xạ Farm Slot vs Account
- **Slot Mapping:** Mỗi máy Android có 8 slot (`slot_no` 1 đến 8 tương ứng Row 1 đến 8).
- **Global video_slot:** Chỉ số toàn cục `video_slot` trong `tiktok_accounts` tuân theo công thức `(machine_id - 1) * 8 + slot_no`.
- **Cựu Binh / Nick Già:** Chủ lực là Row 1 (`slot_no = 1`) và Row 2 (`slot_no = 2`).

## 2. Đường Dẫn Cơ Sở Dữ Liệu GPMLogin & Cookie Store
- **GPM Database:** `C:/Users/Kibe/AppData/Local/Programs/GPMLogin/profile/profile_data.db`
  - Bảng `Profiles`: `Id`, `Name`, `ProfilePath`, `GroupId`.
  - Bảng `Groups`: Nhóm 10 (`Google_Live_Ready`), nhóm 11 (`Google_Cooldown_Error`).
- **Thư Mục Cookie Trình Duyệt GPM:**
  - `C:/Users/Kibe/AppData/Local/Programs/GPMLogin/profile/<ProfilePath>/Default/Network/Cookies`
  - File SQLite chứa toàn bộ cookie của profile Chromium.

## 3. Kỹ Thuật Đọc Cookie An Toàn Tránh Lock & File Permission
- **Tuyệt đối không copy file hoặc chạy subprocess:** Sử dụng SQLite URI read-only mode trực tiếp:
  ```python
  import sqlite3
  conn = sqlite3.connect(f"file:{cookie_path}?mode=ro", uri=True)
  cur = conn.cursor()
  ```
- **Chỉ Dấu Session Đăng Nhập (Live Session Indicators):**
  - **Google (Gmail):**
    ```sql
    SELECT count(*) FROM cookies WHERE host_key LIKE '%google%' AND name IN ('SID', 'SAPISID', 'SSID')
    ```
    Nếu count > 0: Profile đang có session Google đăng nhập hợp lệ.
  - **Microsoft (Outlook/Hotmail):**
    ```sql
    SELECT count(*) FROM cookies WHERE (host_key LIKE '%live.com%' OR host_key LIKE '%microsoft%') AND name LIKE '%AUTH%'
    ```
    Nếu count > 0: Profile có session Microsoft đăng nhập qua web.
  - **TikTok Web:**
    ```sql
    SELECT count(*) FROM cookies WHERE host_key LIKE '%tiktok.com%' AND name IN ('sessionid', 'sid_guard')
    ```

## 4. Phân Biệt "Đã Có Profile GPM" vs "Đã Login Sống Session"
- **Đã có profile GPM:** Email có tên tương ứng trong `Profiles` (GPM Local API `http://127.0.0.1:19995/api/v3/profiles`). Đây chỉ là vỏ profile trình duyệt.
- **Đã login thành công:** File `Cookies` tồn tại và chứa session token (`SID`/`AUTH`). Nếu count = 0, profile đang ở trạng thái logged out hoặc chưa từng đăng nhập.
- **Hotmail có OAuth Token:** Hơn 880 Hotmail trong `farm_master.db` có `oauth_refresh_token` để lấy OTP qua Microsoft Graph API; nhóm này KHÔNG bắt buộc phải login web trên GPM (tránh kích hoạt checkpoint bảo vệ của Microsoft).
