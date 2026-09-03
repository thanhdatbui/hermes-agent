# Gmail Preflight Startup & Device Map Date Pitfalls (2026-08-26)

## 1. Lỗi Mapping Serial do Cell Ngày Tháng trong Workbook (`Device ID`)
### Hiện tượng
- ADB báo lỗi không tìm thấy thiết bị: `[DEVICE_STATE][STARTUP] adb.exe: device '23/08/2026' not found` hoặc `device '2026-08-24' not found`.
- Batch Gmail thất bại ngay tại bước preflight cho các máy bị ảnh hưởng.

### Nguyên nhân
- Trong `taikhoan_run_safe.xlsx` hoặc `taikhoan_dat_v2_updated .xlsx`, cột `Device ID` / `device ID` có một số dòng bị nhập nhầm chuỗi ngày tháng (ví dụ: ngày tạo/ghi chú bị paste lệch cột).
- Hàm load device map (`load_device_map_from_excel`) đọc tuần tự từng dòng theo STT máy:
  ```python
  device_map[stt] = phone_id
  ```
  Nếu dòng cuối cùng của máy đó là dòng bị lỗi ngày tháng, giá trị ngày tháng sẽ ghi đè lên serial hợp lệ ở các dòng trước.

### Giải pháp kỹ thuật chuẩn (Đã được Approved bởi Reviewer)
- Bắt buộc chuẩn hóa và kiểm tra cell serial qua `_normalize_device_serial_cell(cell_value, cell_number_format=None)`:
  - Loại bỏ các kiểu dữ liệu `datetime`, `date`.
  - Kiểm tra `number_format` của openpyxl cell để phát hiện định dạng ngày (`yy`, `mm`, `dd`).
  - Chặn các unformatted Excel date serials dạng số trong dải `35000..60000`.
  - Kiểm tra và bỏ qua các format ngày tháng thông dụng (`%d/%m/%Y`, `%Y-%m-%d`, `%d-%m-%Y`, `%d.%m.%Y`, `%Y.%m.%d`, kể cả format có `T` và giờ phút giây).
  - Chuẩn hóa chuỗi dấu chấm trước khi gọi `fromisoformat(text.replace(".", "-"))`.
  - Loại bỏ các chuỗi có ký tự phân cách ngày như `/`, `\`, khoảng trắng, nhưng **bảo toàn các serial TCP/IP hợp lệ (`192.168.1.10:5555`) và serial số thuần túy (8+ chữ số)**.
- Gom nhóm serial hợp lệ theo từng máy (`serials_by_machine.setdefault(stt, set()).add(phone_id)`).
- Fail-closed (`RuntimeError`) nếu phát hiện 1 máy có từ 2 serial hợp lệ khác nhau trở lên.

---

## 2. Lỗi `[BLOCKED][PRE_GMAIL][APP_STARTUP]` trên Samsung S7 (Android 7/8)
### Hiện tượng
- Hàng loạt máy (10/15 máy) dừng tại preflight với lỗi:
  `[BLOCKED][PRE_GMAIL][APP_STARTUP] repeated after one recovery; artifacts saved`
- UI dump lưu lại rỗng (0 bytes).

### Nguyên nhân
- Trong `run_machine_preflight`, hàm `prepare_app_for_automation` mở app bằng lệnh `monkey` và gọi `focus_reader` lặp 10 lần (15s) kiểm tra foreground qua `dumpsys window windows`.
- Cú pháp `dumpsys window` trên Samsung Galaxy S7 (Android 7.0/8.0) thường có định dạng:
  - `mCurrentFocus=Window{... com.google.android.gm/...}`
  - `mFocusedApp=AppWindowToken{... ActivityRecord{... com.google.android.gm/...}}`
- Regex cũ `mCurrentFocus=.*?\s([a-zA-Z0-9_.]+)/` không bắt được các token này $\rightarrow$ `focus_reader` trả về rỗng $\rightarrow$ core đánh giá chưa focus vào Gmail và raise lỗi.

### Giải pháp kỹ thuật chuẩn
1. **Mở rộng Regex nhận diện focus cho Samsung S7**:
   ```python
   match = re.search(r"mCurrentFocus=.*?\s([a-zA-Z0-9_.]+)/", out)
   if not match:
       match = re.search(r"mFocusedApp=.*?\s([a-zA-Z0-9_.]+)/", out)
   if not match:
       match = re.search(r"mCurrentFocus=Window\{[a-f0-9]+ [^}]+ ([a-zA-Z0-9_.]+)/", out)
   if not match:
       match = re.search(r"mFocusedApp=AppWindowToken\{[a-f0-9]+ token=Token\{[a-f0-9]+ ActivityRecord\{[a-f0-9]+ [^}]+ ([a-zA-Z0-9_.]+)/", out)
   ```
2. **Fallback qua `launch_gmail_home`**:
   Nếu `prepare_app_for_automation` thất bại do kiểm tra focus strict (`verify_app_focus`), whitelist lỗi và cho phép `launch_gmail_home` thử xác thực qua UI XML thực tế trước khi kết luận lỗi.
