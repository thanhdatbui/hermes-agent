# TikTok Feed Session Management

References:
- `references/tiktok-feed-and-upload-hook-pitfalls.md` — Cạm bẫy argparse conflicting option string, in-memory raw_xml drop, và bóc tách skip reason trên watchdog.

## Kiến trúc & Quy tắc vận hành Feed Session
1. **Comment Peek Logic:**
   - Chỉ kích hoạt trên các video xem sâu (`is_deep_inspect`).
   - Bắt buộc kiểm tra fallback nạp `raw_xml` từ `xml_path` trước khi gọi `_maybe_peek_comments`.
   - Tránh silent bypass khi in-memory payload chỉ lưu file path.

2. **Upload Hook Invocation:**
   - Đảm bảo CLI parser không chứa duplicate argument gây crash toàn bộ batch.
   - Nhận diện đúng các trạng thái skip do ledger phân tán ghi nhận (`already_uploaded_in_shift`).

3. **Watchdog Reporting Discipline:**
   - Không gom các lý do bỏ qua vào chữ "Khác". Bóc tách cụ thể: Cooldown, Tuổi tài khoản, Đã upload trong ca, Dưỡng sinh, Thiếu video.
