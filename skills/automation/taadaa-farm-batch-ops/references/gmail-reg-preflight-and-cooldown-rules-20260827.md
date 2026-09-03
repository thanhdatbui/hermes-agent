# Gmail Registration & Night-Chain Pipeline Diagnostics (2026-08-27)

## 1. Cooldown 5 Ngày Chỉ Tính Cho Gmail (@gmail.com)
- **Vấn đề:** File kho `gmail_clean_v2.xlsx` lưu cả Gmail đã reg thành công và Hotmail nạp vào. Khi nạp Hotmail mới (ghi cột `ngày tạo` gần đây), nếu hàm `_load_last_run_dates()` duyệt toàn bộ rows mà không lọc email, các máy vừa nạp Hotmail sẽ bị tính là vừa tạo mail -> ăn cooldown 5 ngày giả tạo (`COOLDOWN_NOT_READY`), làm rơi rụng danh sách máy từ 71 máy xuống còn 6 máy.
- **Quy tắc:** `_load_last_run_dates()` BẮT BUỘC lọc `email_val.endswith("@gmail.com")` trước khi lấy `date_val` ở cột 7.

## 2. Loại Bỏ Ô Ngày Tháng Khi Đọc Serial Thiết Bị Từ `taikhoan_run_safe.xlsx`
- **Vấn đề:** Workbook `taikhoan_run_safe.xlsx` có nhiều row cho mỗi máy. Một số row bị ghi đè ô `Device ID` bằng ngày tháng (`23/08/2026`, `2026-08-24`, hoặc Excel date serial số 35000-60000). Loader cũ đọc tuần tự nên row lỗi ghi đè lên serial thật (`9885b6...`), làm ADB báo lỗi không tìm thấy thiết bị (`device '23/08/2026' not found`).
- **Xử lý chuẩn (`_normalize_device_serial_cell`):**
  - Bỏ qua các giá trị `datetime`, `date`, `bool`.
  - Kiểm tra `cell.number_format`: bỏ qua nếu format chứa `yy`, `mm`, `dd`.
  - Bỏ qua số trong khoảng Excel date serial `35000 <= val <= 60000`.
  - Dùng `strptime` loại bỏ các định dạng ngày phổ biến (`%d/%m/%Y`, `%Y-%m-%d`, `%d.%m.%Y`, `%Y.%m.%d`, kết hợp giờ và `T`).
  - Cho phép giữ lại serial dạng số (như `1234567890123456`), numeric 8 chữ số (`20260824`) và TCP/IP serial (`192.168.1.10:5555`).
  - Gom các serial hợp lệ theo từng máy vào `set()`; nếu 1 máy có > 1 serial hợp lệ khác nhau -> fail-closed (báo conflict), không chọn bừa.

## 3. ATX-Agent Session UI Capture Bắt Buộc Dùng `AdbClient` Chuẩn
- **Vấn đề:** Khi gọi `automation_core.persistent_ui.capture_atx_session_ui()`, đối tượng ADB client truyền vào phải là instance của `automation_core.adb.AdbClient` có phương thức `.run()`. Nếu truyền class mock/wrapper thiếu `.run()`, ATX session dump sẽ văng `AttributeError` ngầm và trả về XML rỗng (`len(xml) == 0`), khiến preflight tưởng UIAutomator chết và dừng máy (`[BLOCKED][PRE_GMAIL][APP_STARTUP]`).
- **Khắc phục:** Khởi tạo `adb_client = _RealAdbClient(adb_path=ADB_EXE, serial=device_id, default_timeout=20)` trong `get_ui_xml()`.

## 4. Nhận Diện Màn Hình "Thiết Lập Email" & Tap Đúng Google Provider (Samsung S7)
- **Vấn đề:** Màn hình "Thiết lập email" trên Gmail Samsung S7 không dùng `id/providers_list` mà dùng danh sách các LinearLayout `id/account_setup_item`. Nếu dùng text tap mù "Google", có thể chạm nhầm vào container cha hoặc bento menu.
- **Xử lý chuẩn:**
  - `is_gmail_provider_setup_xml(xml)`: Kiểm tra tiêu đề ("Thiết lập email" / "Set up email") + có ít nhất 2 items `:id/account_setup_item` (hoặc `:id/providers_list`) + có chữ "Google".
  - `find_google_provider_item_node(xml)`: Duyệt các node khớp chính xác `rid.endswith(":id/account_setup_item")`, tìm node có nhãn con khớp `text == "Google"`, và chỉ trả về tọa độ tâm khi tìm thấy duy nhất 1 item Google hợp lệ.

## 5. Timeout Cron Clear TikTok Cache
- Script `clear-tiktok-cache.py` chạy qua nhiều bước fallback (Deep link 1 -> Deep link 2 -> Dò 5 offsets widget -> Tap confirm -> Verify). Trên máy Samsung S7, thời gian thực thi có thể mất 50-70s.
- Worker timeout trong `cron_clear_tiktok_cache.py` phải set tối thiểu **120s** (không để 45s) để tránh ngắt giữa chừng.
