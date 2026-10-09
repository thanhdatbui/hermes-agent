# Quy Chuẩn & Workflow Tạo Hàng Loạt Profile Farm GPM (Farm S7 Online ADB)

Tài liệu hướng dẫn quy trình, bộ lọc và các pitfall khi tạo hàng loạt profile GPMLogin cho các tài khoản Gmail sạch trên dàn Samsung S7 Farm qua Local API v3 (port 19995).

---

## 1. File Thực Thi Chuẩn
- **Script**: `D:\Taadaa\GPM auto\scripts\batch_create_farm_gpm_profiles.py`
- **Module Client**: `D:\Taadaa\GPM auto\src\gpm_client.py` (`GPMClient`)
- **Excel Nguồn**:
  - Master Gmail: `D:\OneDrive\TaadaaData\kibe\master_gmail_manager.xlsx` (Sheet: `Kibe_Farm_S7`)
  - Proxy Mapping: `D:\OneDrive\TaadaaData\kibe\PROXYgandienthoai.xlsx` (Sheet: `Proxy`)
- **Pipeline Status**: `D:\Taadaa\GPM auto\config\oauth_pipeline_status.json`
- **GPMLogin DB**: `%LOCALAPPDATA%\Programs\GPMLogin\profile\profile_data.db` (Bảng `Profiles`)
- **ADB Path**: `C:\Program Files (x86)\xiaowei\tools\adb.exe`

---

## 2. Bộ Lọc 7 Bước Bắt Buộc Trước Khi Tạo Profile

1. **Trạng thái LIVE**:
   - Chỉ lấy tài khoản có cột `Trạng Thái` == `'LIVE'` từ sheet `Kibe_Farm_S7`.
   - Bỏ qua toàn bộ `DIE`, `BAN`, `SUSPENDED`.

2. **Bỏ qua Khoa Lee**:
   - Kiểm tra `'khoale' in email.lower() or 'khoale' in recovery.lower()`.
   - Loại trừ triệt để cả các biến thể như `khoaleemagic`, `khoalemagic`.

3. **Loại trừ theo Pipeline Status (`oauth_pipeline_status.json`)**:
   - Bỏ qua tài khoản đã thuộc `omniroute_success`, `excluded_khoalee`, `wrong_password_or_checkpoint`.
   - **Pitfall Dữ Liệu**: Các key trong `oauth_pipeline_status.json` có cấu trúc hỗn hợp:
     - `omniroute_success`: `dict` (keys là email).
     - `wrong_password_or_checkpoint`: `dict` (keys là email).
     - `excluded_khoalee`: `list` (items là email).
     - **Giải pháp**: Phải viết hàm extract hỗ trợ cả `dict` và `list`, nếu gọi `.keys()` trực tiếp trên list sẽ dính lỗi `AttributeError: 'list' object has no attribute 'keys'`.
     ```python
     def extract_emails(val):
         if isinstance(val, dict):
             return [str(k).strip().lower() for k in val.keys()]
         elif isinstance(val, list):
             return [str(item).strip().lower() for item in val]
         return []
     ```

4. **Đối soát chống trùng trong GPMLogin DB**:
   - Mở SQLite DB tại `%LOCALAPPDATA%\Programs\GPMLogin\profile\profile_data.db`.
   - Quét regex email `[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+` trong cả hai cột `Name` và `JsonData` của bảng `Profiles`.
   - Nếu email đã tồn tại, bỏ qua không tạo trùng.

5. **Kiểm tra trạng thái ADB Online của thiết bị S7**:
   - Chạy `adb devices` và lọc các serial có trạng thái `device`.
   - Đọc mapping máy từ `PROXYgandienthoai.xlsx` (cột `Máy` -> `device ID` & `proXy`).
   - S7 tương ứng với `mid` BẮT BUỘC phải đang online ADB. Nếu offline, bỏ qua.

6. **Chuẩn hóa Tên Profile & Nhóm**:
   - Format: `name = f"{mid:02d} - {email} - {port}"`
   - Trong đó `port` được trích xuất từ proxy string (`test.taadaa.click:PORT:...` hoặc `mirotik1.taadaa.click:PORT:...`).
   - `group_id = 1`.

7. **Rate Limit khi gọi Local API**:
   - Gọi `GPMClient.create_profile(...)`.
   - Chèn `time.sleep(1.5)` giữa mỗi lần tạo profile để chống tràn buffer và nghẽn tiến trình Local API của GPMLogin.
