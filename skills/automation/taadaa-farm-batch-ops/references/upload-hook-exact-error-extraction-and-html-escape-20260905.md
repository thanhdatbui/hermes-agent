# Trích Xuất Chính Xác Nguyên Nhân Lỗi Upload & Bảo Vệ Ký Tự HTML Farm Alert (2026-09-05)

## 1. Bối cảnh & Sự cố
- **Triệu chứng:** Khi quy trình upload TikTok thất bại trong `_run_upload_hook`, tin nhắn Telegram Farm Alert liên tục báo:
  `• Triệu chứng: upload_subprocess_nonzero`
- **Phản ứng của user:** *"Sao cứ lỗi upload nonprocess zero củ cặc gì v. Lỗi gì thì ghi chính xác ra chứ"* — User không thể biết lỗi cụ thể là gì (timeout ADB, lệch nick, kẹt popup, không tìm thấy nút, lỗi quyền camera, v.v.).
- **Nguyên nhân gốc rễ:**
  1. Trong `multi_machine_feed_session.py` (`_run_upload_hook`), khi `proc.returncode != 0`, code đang hardcode fallback gán:
     `reason = "upload_subprocess_nonzero"`
     Dù tiến trình upload (`run_post.py`) có ghi file `report.json` chứa thông tin chi tiết (`error`, `reason`, `last_state`, `status`) hoặc `stderr` có traceback, hệ thống vẫn bỏ qua và chỉ gán chuỗi chung chung.
  2. Trong `automation_core.alerts`: các chuỗi động như `error_reason`, `account` được nhét trực tiếp vào template Telegram HTML mà không escape, dẫn đến nguy cơ lỗi cú pháp Telegram API khi chuỗi chứa `<redacted>` (từ SecretFilter) hoặc `<module>`.

## 2. Quy chuẩn Trích xuất Lỗi Đa Tầng (Multi-tier Error Extraction)
Khi một subprocess (như `run_post.py`) trả về mã lỗi khác 0, BẮT BUỘC trích xuất nguyên nhân theo thứ tự ưu tiên:
1. **Tier 1 (Structured Report `report.json`):**
   - Đọc `rep_data = json.loads(target_rep_file)`
   - Lấy `err = rep_data.get("error") or rep_data.get("reason")`
   - Lấy `last_state = rep_data.get("last_state")`
   - Nếu có `err`:
     - Nếu `last_state` chưa có trong `err`: gộp `[{last_state}] {err}`
     - Ngược lại dùng trực tiếp `err`
   - Nếu không có `err` nhưng có `last_state`: `failed_at_state_{last_state}`
   - Nếu có `status` khác `SUCCESS`: `upload_status_{status}`
2. **Tier 2 (Stderr Traceback / Exception):**
   - Lấy dòng text cuối cùng không rỗng trong `stderr` (dòng mô tả exception thực tế).
3. **Tier 3 (Stdout Error Log):**
   - Quét tìm dòng log có tag `[ERROR]` hoặc `[CRITICAL]` gần nhất, hoặc dòng trạng thái state cuối cùng `>>> State: <state>`.
4. **Tier 4 (Fallback Exit Code):**
   - Chỉ khi cả 3 tầng trên đều rỗng mới dùng `upload_exit_code_{returncode}`.
   - CẮM TUYỆT ĐỐI dùng chuỗi tĩnh vô nghĩa như `upload_subprocess_nonzero`.
5. **Giới hạn độ dài:** Cắt ngắn chuỗi lỗi ở mức tối đa ~250 ký tự để caption Telegram luôn gọn gàng và không vỡ layout.

## 3. Quy chuẩn Bảo vệ Ký tự HTML Telegram (`html.escape`)
- Trong `automation_core.alerts.py` (`send_farm_machine_alert` và `send_farm_script_alert`):
  BẮT BUỘC bọc `html.escape(str(...))` cho toàn bộ các trường dữ liệu động:
  - `error_reason`
  - `account`
  - `serial`
  - `status_text`
- Tránh tuyệt đối lỗi `can't parse entities: Unsupported start tag "redacted"` khi log chứa chuỗi nhạy cảm bị filter che giấu.
