# Tách Biệt Telemetry JSON & Báo Cáo Người Dùng Trong Cronjob `no_agent: true` (2026-10-14)

## 1. Bối Cảnh Lỗi & Hiện Trường (User Steering)
- **Hiện tượng:** Người dùng nhận báo cáo định kỳ 6h (`hotmail-gpm-lifecycle-6h-report`) trên Telegram nhưng ở đầu tin nhắn bị đính kèm 5 dòng sự kiện JSON thô:
  ```json
  {"event": "state_loaded", "timestamp": "...", "correlation_id": "...", "level": "info", ...}
  {"event": "state_loaded", "timestamp": "...", "correlation_id": "...", "level": "info", ...}
  {"event": "db_query_ok", "timestamp": "...", "correlation_id": "...", "level": "info", ...}
  {"event": "db_query_ok", "timestamp": "...", "correlation_id": "...", "level": "info", ...}
  {"event": "lifecycle_report_snapshot", "timestamp": "...", "correlation_id": "...", "level": "info", ...}
  📊 [BÁO CÁO 6H: VÒNG ĐỜI HOTMAIL -> GPM -> CHATGPT TOÀN FARM]
  ...
  ```
- **Phản ứng của User:** Gửi ảnh chụp màn hình kèm chỉ trích: *"Chứ spam 1 đống gì đây"*.

## 2. Nguyên Nhân Gốc Rễ (Root Cause)
- Trong kiến trúc scheduler của Hermes Agent:
  * Khi job cron được cấu hình `no_agent: true`, scheduler thực thi script con và lấy **toàn bộ dữ liệu in ra `sys.stdout`** gửi nguyên văn (verbatim) làm tin nhắn tới channel/chat đích (Telegram).
  * Trong script `cron_hotmail_gpm_lifecycle_6h_report.py`, lớp `Telemetry.emit()` dùng lệnh:
    ```python
    print(json.dumps(record, ensure_ascii=False, default=str))
    ```
    Lệnh này mặc định ghi vào `sys.stdout`.
  * Hậu quả: Dù telemetry JSON rất hữu ích cho log nội bộ và unit test, việc xuất ra `stdout` đã vô tình biến toàn bộ luồng telemetry thành rác màn hình chat Telegram của người dùng.

## 3. Quy Chuẩn Kỹ Thuật Bắt Buộc (Invariant)

1. **Stdout dành riêng cho Human Report:**
   - Trong mọi script watchdog / report chạy dưới `no_agent: true`, `sys.stdout` CHỈ ĐƯỢC PHÉP chứa nội dung báo cáo hoàn chỉnh, định dạng Markdown sạch sẽ, không có bất kỳ dòng JSON thô `{...}` nào.
2. **Telemetry & Logs bắt buộc trỏ sang Stderr:**
   - Lớp `Telemetry` hoặc logger bắt buộc cấu hình xuất ra `sys.stderr` (hoặc ghi vào file log chuyên biệt):
     ```python
     class Telemetry:
         def __init__(self, correlation_id: str | None = None, stream: Any = None) -> None:
             self.correlation_id = correlation_id or uuid.uuid4().hex[:12]
             self.events: list[dict[str, Any]] = []
             self.stream = stream if stream is not None else sys.stderr

         def emit(self, event: str, *, level: str = "info", error_class: str | None = None, **fields: Any) -> dict[str, Any]:
             record = {...}
             self.events.append(record)
             print(json.dumps(record, ensure_ascii=False, default=str), file=self.stream)
             return record
     ```
   - Scheduler chỉ ghi nhận `sys.stderr` khi tiến trình crash (exit code != 0) để phục vụ debug, hoàn toàn không làm bẩn tin nhắn thành công trên Telegram.
3. **Kỷ luật Unit Test:**
   - Test suite cho reporting script phải kiểm tra tách biệt:
     * `redirect_stdout(out)`: kiểm tra nội dung bảng báo cáo và khẳng định `self.assertNotIn("{", text)` để chống rò rỉ JSON.
     * `redirect_stderr(err)`: parse các event JSON từ `err.getvalue()` để xác minh đầy đủ `correlation_id`, `state_loaded`, `lifecycle_report_snapshot`.
