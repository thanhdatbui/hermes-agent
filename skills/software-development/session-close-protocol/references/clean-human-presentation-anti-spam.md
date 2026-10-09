# Clean Human Presentation & Anti-Spam in Closeout

## 1. Vấn đề thực tế
Khi chạy `terminal(background=True, notify_on_complete=True)` cho closeout gate hoặc các tác vụ chạy nền, nếu cấu hình `display.background_process_notifications` là `result` hay `all`, hệ thống sẽ xả toàn bộ stdout/stderr thô (bash error, raw JSON rubric, telemetry, tracebacks) lên Telegram.
Điều này khiến User bực mình ("thông báo đọc khó hiểu, trình bày ngu quá") và làm loãng ngữ cảnh làm việc.

## 2. Quy tắc cấu hình bắt buộc
1. `display.background_process_notifications` trong `config.yaml` phải luôn là `"off"`:
   ```bash
   hermes config set display.background_process_notifications "off"
   ```
2. Không dùng `notify_on_complete=True` cho các script sinh ra output rác lớn nếu không cần thiết; ưu tiên điều phối ngầm và đọc log qua file hoặc `process(action='log')`.

## 3. Quy chuẩn trình bày với User
1. **Chế độ im lặng trong hậu trường:** Mọi lần reviewer từ chối (<85 điểm), lỗi test, hay lỗi binding mismatch phải được Coordinator và Worker âm thầm giải quyết.
2. **Chỉ giao tiếp kết quả đã qua chắt lọc (Human Language):**
   - Chỉ xuất 1 tin nhắn ngắn gọn, mạch lạc khi có tiến triển quan trọng.
   - Nêu rõ: Lý do Reviewer từ chối (ngắn gọn 1-2 dòng) -> Hành động đang làm -> Kết quả cuối cùng (`APPROVED X/100`, mã commit, trạng thái push).
3. **Tuyệt đối cấm:** Copy paste raw JSON, raw bash dump, hoặc để lộ các thông báo hệ thống thô vào kênh chat của User.
