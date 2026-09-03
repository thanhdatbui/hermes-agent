# Gmail Reg & Night Chain Pipeline: Device Serial Date-String Corruption & Startup Diagnosis (2026-08-26)

## 1. Hiện tượng lỗi 1: Device Serial bị ghi nhầm chuỗi ngày tháng
- Khi chạy batch Gmail qua `run_all.ps1` hoặc `run_parallel.ps1`, một số máy báo lỗi:
  ```text
  [DEVICE_STATE][STARTUP] adb.exe: device '23/08/2026' not found
  [DEVICE_STATE][STARTUP] adb.exe: device '2026-08-24' not found
  ```
- **Nguyên nhân:**
  - File workbook `taikhoan_run_safe.xlsx` (sheet `Accounts`) có cấu trúc nhiều dòng/máy. Khi người dùng nhập liệu, một số dòng bị paste nhầm chuỗi ngày tạo (`23/08/2026` hoặc `2026-08-24`) vào cột `Device ID` (cột 2).
  - Hàm `load_device_map_from_excel()` trong `gmail_reg_v10.py` đọc tuần tự từ trên xuống dưới và gán `device_map[stt] = phone_id`.
  - Dòng chứa ngày tháng nằm ở cuối danh sách các dòng của máy đó đã ghi đè lên serial thật của máy $\rightarrow$ ADB nhận serial là ngày tháng và báo device not found.

- **Giải pháp chuẩn:**
  1. Thêm hàm kiểm tra `_normalize_device_serial_cell(value)` để lọc bỏ tất cả các giá trị mang định dạng ngày tháng (`%d/%m/%Y`, `%Y-%m-%d`, chứa `/` hoặc `\`).
  2. Dùng cấu trúc `serials_by_machine.setdefault(stt, set()).add(phone_id)` gom các serial hợp lệ.
  3. Nếu 1 máy có >1 serial hợp lệ khác nhau $\rightarrow$ raise fail-closed `conflicts`.
  4. Nếu 1 máy có 1 serial hợp lệ kèm các dòng ngày tháng rác $\rightarrow$ lấy đúng serial hợp lệ duy nhất đó.

---

## 2. Hiện tượng lỗi 2: 10/15 máy fail `[BLOCKED][PRE_GMAIL][APP_STARTUP]`
- Khi chạy batch ban đêm (đêm 26/08), hàng loạt máy (1, 5, 12, 19, 23, 24, 30, 31, 42, 44) dừng ngay tại preflight:
  ```text
  ❌ STOPPED: [BLOCKED][PRE_GMAIL][APP_STARTUP] repeated after one recovery; artifacts saved
  ```
- **Nguyên nhân:**
  - `run_machine_preflight()` gọi `prepare_app_for_automation()` của `automation-core`.
  - Core thực hiện lệnh `monkey` để mở Gmail, sau đó gọi `focus_reader` đọc qua `dumpsys window windows` tìm `mCurrentFocus`.
  - Trên Samsung S7 / Android 7 & 8, app Gmail khởi động nặng có độ trễ lớn hoặc `mCurrentFocus` không khớp regex trong 10 attempts (15 giây) $\rightarrow$ core đánh giá khởi động thất bại $\rightarrow$ script dừng trước khi vào flow chính.

- **Hướng xử lý chuẩn:**
  - Không dựa đơn thuần vào `monkey` + `mCurrentFocus` strict. Cần kết hợp `am start -n com.google.android.gm/.ConversationListActivityGmail` tường minh và kiểm tra `get_ui_xml()` / UI hierarchy thực tế để xác nhận Gmail đã lên giao diện hay chưa.
