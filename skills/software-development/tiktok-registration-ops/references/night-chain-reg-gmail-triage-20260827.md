# Triage & Khắc phục chuỗi lỗi Night-chain Reg Gmail (2026-08-27)

## 1. Bối cảnh & Hiện tượng
- Cronjob `night-chain-reg-gmail-only` (Job ID: `38ea60c09825`) chạy đêm liên tục exit code 1.
- Log báo lỗi hàng loạt `[BLOCKED][PRE_GMAIL][APP_STARTUP]` trên 15/15 máy farm.

## 2. Các nguyên nhân gốc (Root Causes) & Giải pháp

### 2.1. Lỗi Mapping Thiết bị đọc nhầm Date Cell (Samsung S7 / Multi-row Account Workbooks)
- **Triệu chứng:** Máy 1 và Máy 30 bị ADB báo `device '23/08/2026' not found` hoặc `device '2026-08-24' not found`.
- **Nguyên nhân:** File `taikhoan_run_safe.xlsx` có ô `Device ID` bị người dùng/tool ghi nhầm định dạng ngày tháng. Hàm nạp mapping duyệt tuần tự và lấy giá trị cuối cùng đè lên serial thật.
- **Khắc phục:** 
  - Thêm `_normalize_device_serial_cell(value, number_format)` lọc bỏ toàn bộ datetime/date object, chuỗi ngày regex, và định dạng Excel date serial số (35000..60000).
  - Vẫn giữ nguyên các serial hợp lệ dạng số (16 số) và serial TCP/IP (`192.168.1.10:5555`).
  - Gom các serial hợp lệ theo máy; fail-closed nếu phát hiện conflict serial thật.

### 2.2. Lỗi Cooldown 5 ngày tính nhầm tài khoản Hotmail
- **Triệu chứng:** Đêm 27/08 batch chỉ chọn được 6 máy, 74 máy bị từ chối với lý do `COOLDOWN_NOT_READY`.
- **Nguyên nhân:** Khi nạp Hotmail vào `gmail_clean_v2.xlsx`, hàm `_load_last_run_dates()` duyệt tất cả các dòng mà không kiểm tra đuôi mail, làm máy vừa nạp Hotmail bị tính là vừa tạo Gmail.
- **Khắc phục:** Lọc nghiêm ngặt `email_val.endswith("@gmail.com")` khi duyệt cột ngày tạo (Cột 7) để tính cooldown cho máy.

### 2.3. Lỗi ATX Session UI Dump do Mock AdbClient thiếu `.run()`
- **Triệu chứng:** 15/15 máy bị lỗi `[BLOCKED][PRE_GMAIL][APP_STARTUP] repeated after one recovery; artifacts saved`. File UI dump rỗng (0 bytes).
- **Nguyên nhân:** Consumer khởi tạo `_CoreUiAdb` chỉ hỗ trợ `.shell()` và `.exec_out()`. Khi `capture_atx_session_ui()` thực hiện cấp port forward động (`forward tcp:0 tcp:7912`), nó gọi `adb_client.run(...)` $\rightarrow$ quăng ngoại lệ `AttributeError: '_CoreUiAdb' object has no attribute 'run'` trong silent block $\rightarrow$ trả về XML rỗng.
- **Khắc phục:** Dùng trực tiếp `automation_core.adb.AdbClient` chuẩn trong `get_ui_xml()`.
