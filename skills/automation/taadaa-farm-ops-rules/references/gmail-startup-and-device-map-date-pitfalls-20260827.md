# Gmail Auto-Reg Startup, Device-Map Serial Hardening & Cooldown Invariants (2026-08-27)

Tài liệu ghi lại các nguyên nhân cốt lõi và bài học vận hành sau sự cố chuỗi Cron ban đêm (`register gmail` / `night-chain-reg-gmail-*`).

---

## 1. Lỗi Device-Map Serial Bị Đè Chuỗi Ngày Tháng (`taikhoan_run_safe.xlsx`)

### Triệu chứng
ADB báo lỗi thiết bị không tìm thấy ngay lúc khởi động:
```text
[DEVICE_STATE][STARTUP] adb.exe: device '23/08/2026' not found
[DEVICE_STATE][STARTUP] adb.exe: device '2026-08-24' not found
```

### Nguyên nhân
- `taikhoan_run_safe.xlsx` là file view đa tài khoản (mỗi máy có 2–6 dòng).
- Do thao tác paste/nhập liệu, một số dòng ở cột `Device ID` (cột B) bị paste nhầm ngày giờ (ví dụ `23/08/2026`, `2026-08-24`, `24.08.2026T18:27:39` hoặc số serial ngày unformatted 46200).
- Hàm `load_device_map_from_excel()` trong `gmail_reg_v10.py` đọc tuần tự từ trên xuống dưới và gán `device_map[stt] = phone_id`, khiến dòng ngày tháng cuối cùng ghi đè lên serial hợp lệ của máy.

### Giải pháp kỹ thuật chuẩn (`_normalize_device_serial_cell`)
1. **Loại trừ Date/Datetime objects & cell format:**
   - Bỏ qua nếu là `datetime`, `date`, `bool` hoặc `cell_number_format` chứa token ngày (`yy`, `mm`, `dd`).
   - Bỏ qua số nguyên unformatted trong dải serial ngày của Excel (`35000 <= value <= 60000`).
2. **Loại trừ Date String Formats:**
   - Parse và reject các format ngày chuẩn (`%d/%m/%Y`, `%d-%m-%Y`, `%d.%m.%Y`, `%Y-%m-%d`, `%Y.%m.%d`, kèm giờ phút giây và định dạng ISO kết hợp `T`).
   - Chặn các chuỗi chứa dấu phân cách ngày (`/`, `\`, khoảng trắng).
3. **BẢO TOÀN Serial Hợp Lệ:**
   - **Bắt buộc hỗ trợ** các serial TCP/IP như `192.168.1.10:5555` (chứa dấu `.` và `:`).
   - **Bắt buộc hỗ trợ** các serial thuần số (ví dụ `1234567890123456` hoặc `20260824`).
4. **Fail-Closed khi có Conflict:**
   - Gom toàn bộ serial hợp lệ theo máy `serials_by_machine.setdefault(stt, set()).add(phone_id)`.
   - Nếu 1 máy có `> 1` serial hợp lệ khác nhau $\rightarrow$ ném `RuntimeError` dừng batch, không chọn bừa.

---

## 2. Lỗi `[BLOCKED][PRE_GMAIL][APP_STARTUP]` trên Samsung S7 (Android 7/8)

### Triệu chứng
10/15 worker dừng ở bước preflight với log:
```text
❌ STOPPED: [BLOCKED][PRE_GMAIL][APP_STARTUP] repeated after one recovery; artifacts saved
```

### Nguyên nhân
1. `prepare_app_for_automation` trong `automation-core` mở Gmail qua `monkey`, sau đó lặp 10 lần (15s) gọi `focus_reader` để xác nhận `mCurrentFocus` thuộc `com.google.android.gm`.
2. Trên Samsung S7, output của `dumpsys window windows` có định dạng đặc thù (`Window{... com.google.android.gm/...}` hoặc `AppWindowToken{...}`) khiến regex cũ không match được.
3. Khi hết 10 lần retry, core trả về `stop_reason = "failed to focus target app after launch"`.

### Giải pháp kỹ thuật
1. **Bổ sung Regex Samsung S7 trong `get_current_focus_package`:**
   - Bắt mẫu: `r"mCurrentFocus=Window\{[a-f0-9]+ [^}]+ ([a-zA-Z0-9_.]+)/"`
   - Bắt mẫu: `r"mFocusedApp=AppWindowToken\{[a-f0-9]+ token=Token\{[a-f0-9]+ ActivityRecord\{[a-f0-9]+ [^}]+ ([a-zA-Z0-9_.]+)/"`
2. **Whitelist Focus Fallback sang `launch_gmail_home`:**
   - Nếu `prepare_app_for_automation` fail cụ thể do focus (`verify_app_focus`, `focused package is`, `failed to focus target app after launch`), không ném `RuntimeError` ngay mà gọi `launch_gmail_home` để xác thực qua UI XML thực tế.
   - Nếu `launch_gmail_home` vẫn không lên được Gmail home thì mới raise `[PRE_GMAIL][APP_STARTUP]`.

---

## 3. Quy Tắc Tính Cooldown 5 Ngày trong `register gmail`

- Cooldown 5 ngày **ĐƯỢC TÍNH DỰA TRÊN NGÀY TẠO MAIL THÀNH CÔNG trong file `gmail_clean_v2.xlsx`**, chứ không phải cứ chạy batch là ăn cooldown.
- Công thức: `elapsed = today - max(ngày tạo)` tại Cột 7 của máy đó trong `gmail_clean_v2.xlsx`.
- **Lưu ý:** Khi mua hoặc nạp mail Hotmail mới vào `gmail_clean_v2.xlsx`, nếu ghi ngày nạp là ngày hôm nay/hôm qua, các máy đó sẽ bị tính là vừa có mail mới và rơi vào trạng thái `COOLDOWN_NOT_READY` cho đến khi đủ 5 ngày.

---

## 4. Timeout Worker Cho Cron Dọn Cache TikTok (`cron_clear_tiktok_cache.py`)

- Quy trình dọn cache TikTok qua Deep Link + dò Widget + bấm xác nhận + verify UI XML trên máy Samsung S7 mất khoảng **50 – 70 giây**.
- **Quy tắc:** Bắt buộc cấu hình worker `timeout >= 120s` trong `cron_clear_tiktok_cache.py` để tránh việc launcher ngắt ngang tiến trình (`[TIMEOUT] cache clear timed out after 45s`).
