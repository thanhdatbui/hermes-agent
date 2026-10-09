# Quy chuẩn Re-auth OAuth độc lập từng tài khoản qua GPM Profile & Samsung S7

## Bối cảnh & Hiện tượng
- Tài khoản Antigravity trên OmniRoute (`:20129`) hiển thị `testStatus: "expired"`, `errorCode: "unrecoverable_refresh_error"`, `lastError: "Refresh token rejected (unrecoverable_refresh_error). Please re-authenticate this account."`.
- Operator yêu cầu Re-auth độc lập cho 1 tài khoản cụ thể (ví dụ `trieutruc05051997@gmail.com` - Connection ID `4cb880db`, Profile GPM `46 - 5108`, máy S7 M46).

## Quy trình kiểm tra & Thực thi chuẩn (5 bước)

### 1. Đối soát Connection ID, Proxy và Profile GPM
- **Tra cứu OmniRoute Connection**:
  Gọi `GET http://127.0.0.1:20129/api/providers` tìm tài khoản theo email hoặc CID prefix.
  Ghi nhận: Connection ID đầy đủ (`4cb880db-...`), priority, trạng thái `isActive: false`.
- **Bảo toàn Proxy Assignment 1:1**:
  Gọi `GET http://127.0.0.1:20129/api/settings/proxies/assignments` đối soát proxy assignment hiện hành (`scope: account`, `scopeId: <conn_id>`).
  Sau khi exchange token mới, OmniRoute giữ nguyên `scopeId` này, đảm bảo không bị mất cấu hình proxy farm 1:1 (`5101..5138`).
- **Tra cứu thư mục profile GPM thực tế O(1) & Bẫy Multi-Account Profile Reuse**:
  - **Bất biến**: Toàn bộ tài khoản đã có connection OAuth trong OmniRoute 100% đều là tài khoản đã login và tạo profile qua GPM. **TUYỆT ĐỐI CẤM vội kết luận "thiếu profile" hoặc "ai đó tự xóa profile" chỉ vì query `WHERE Name LIKE '%<email>%'` trong SQLite không ra.**
  - **Cơ chế dùng chung profile**: Một máy Samsung S7 và một cổng proxy (ví dụ Máy 61 / Port 5127) thường chỉ duy trì 1 profile GPM đại diện (mang tên tài khoản reg đầu tiên, ví dụ `M61 - 5127 - khahoan240161@gmail.com` với `ProfilePath: SUNVqFew4a-05092026`). Profile này được tái sử dụng để login, bật 2FA và nạp OAuth cho các Gmail khác trên cùng máy đó (như `vukhoa04122002@gmail.com`).
  - **Quy trình truy vết chuẩn khi không thấy email trong tên profile**:
    1. Tra cứu `master_gmail_manager.xlsx` (hoặc `gmail_clean_v2.xlsx`) lấy số máy (`mid`), cổng proxy (`port`) và serial S7.
    2. Query SQLite `profile_data.db`: `SELECT Id, Name, ProfilePath FROM Profiles WHERE Name LIKE 'M<mid>%' OR Name LIKE '<mid> - %'` hoặc tìm theo cổng proxy `LIKE '%<port>%'`.
    3. Kiểm tra log cũ (`run_batch_*.log`, `oauth_pipeline_status.json`) để xác định đúng `ProfilePath` hoặc script batch đã nạp connection đó trước đây.
    4. Kiểm tra thư mục vật lý `C:\Users\Kibe\AppData\Local\Programs\GPMLogin\profile\<ProfilePath>` trên đĩa (folder và session cookie thường vẫn còn dù bị đổi tên trên cloud).

### 2. Kiểm tra Credentials & Quy tắc An toàn Farm
- **Nạp credentials**:
  Tra cứu `master_gmail_manager.xlsx` (sheet `Kibe_Farm_S7`) để lấy password, 2FA secret, và recovery email.
- **Safety Rule**:
  Nếu recovery email chứa `khoale` / `khoalee` -> Loại trừ 100% (bỏ qua không đụng vào).
  Tuyệt đối không vào `myaccount.google.com/device-activity` bấm đăng xuất Samsung S7 (nguyên nhân gây cooldown 7 ngày `rrk=77`).

### 3. Preflight phần cứng S7 & Khởi động ATX Daemon
- Kiểm tra serial thiết bị qua `adb devices` (ví dụ M46 `ce0916092531413504`).
- **Bẫy `atx-agent` & stub daemon chưa chạy**:
  Nếu ADB báo device online nhưng daemon ATX (`atx-agent`) hoặc stub `uiautomator` chưa chạy trong `ps -A`, lệnh dump UI `http://127.0.0.1:170xx/dump/hierarchy` sẽ bị lỗi `Remote end closed connection without response`.
  **Khắc phục chuẩn**:
  Trước khi Playwright mở link OAuth, chạy preflight khởi động daemon nền:
  ```bash
  adb -s <serial> shell "/data/local/tmp/atx-agent server -d"
  adb -s <serial> shell "/data/local/tmp/atx-agent curl -X POST http://127.0.0.1:7912/uiautomator"
  ```
  (CẤM dùng `monkey -p com.github.uiautomator 1` làm xoay ngang màn hình và cướp foreground).

### 3.1. Bẫy trích xuất Security Code khi máy S7 đăng nhập nhiều tài khoản Google (Multi-Account Switcher)
- **Hiện tượng**:
  Khi Google kích hoạt `challenge/ootp` (Mã bảo mật trên điện thoại), pipeline mở màn hình `GoogleSettingsLink` -> `Mã bảo mật`.
  Nếu thiết bị S7 chứa nhiều tài khoản Google (`dumpsys account` có >= 2 accounts), màn hình Mã bảo mật mặc định mở tài khoản đang active đầu tiên (ví dụ `phamthimyduyen...`).
  Script in ra log: `Đang ở email ..., cần đổi sang <target_email> trên màn hình Mã bảo mật...`.
- **Cơ chế lỗi**:
  1. Spinner / Dropdown chọn account trên màn hình Google Security Code không phải lúc nào cũng hiển thị toàn bộ tài khoản nếu danh sách dài (> 4-5 accounts), cần scroll hoặc xử lý popup ListView.
  2. Nếu tap vào spinner nhưng picker dialog bị ẩn/không ăn, script lặp lại chu kỳ tap `Tài khoản Google` dẫn đến kẹt loop và timeout callback code trên Playwright browser.
- **Biện pháp xử lý chuẩn**:
  - Kiểm tra danh sách account trước bằng `adb -s <serial> shell dumpsys account`.
  - Nếu cần chọn tài khoản, switch ngay từ màn hình chính của Google Settings (`GoogleSettingsLink`) trước khi tap vào `Bảo mật` / `Mã bảo mật`.
  - Sau khi tap spinner, kiểm tra `dump_ui()` để chắc chắn ListView account picker đã bung ra; nếu tài khoản nằm ngoài viewport, thực hiện swipe nhẹ (`input swipe 500 1200 500 800`) trước khi tìm node text match `<target_email>`.

### 4. Dọn dẹp trạng thái Lock trước khi chạy
- Trong `config/oauth_pipeline_status.json`:
  Nếu email đang nằm trong `omniroute_success`, BẮT BUỘC xóa email khỏi dict này trước khi chạy `run_oauth_s7_pipeline.py <email>`, nếu không script sẽ phát hiện và trả về `ALREADY_SUCCESS` mà không thực sự re-auth.

### 5. Thực thi Re-auth & Verify kết quả
- Chạy pipeline:
  `python "D:/Taadaa/GPM auto/scripts/run_oauth_s7_pipeline.py" <email>`
- Kiểm tra kết quả:
  - Playwright bắt code và gọi `POST /api/oauth/antigravity/exchange`.
  - OmniRoute cập nhật in-place vào Connection ID `4cb880db...`, reset `testStatus: "active"`.
  - Xác nhận bằng canary chat test độc lập:
    Gửi request tới `POST /v1/chat/completions` với header `x-omniroute-connection-id: <cid>` trên model `antigravity/gemini-3.8-flash-tiered` trả về HTTP 200 OK.
