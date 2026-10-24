# Sol Web (:20129) Tool Calling Verification & Gateway Daemon Restart Audit (2026-10-25)

## 1. Sol Web (`gpt-web-sol`) Tool Calling Verification
Kiểm tra thực nghiệm gửi yêu cầu OpenAI function calling tới endpoint OmniRoute `http://127.0.0.1:20129/v1/chat/completions`:

- **Hỗ trợ Native Tool Calling**: `gpt-web-sol` phản hồi hoàn toàn hợp lệ theo JSON function calling schema của OpenAI:
  ```json
  {
    "tool_calls": [
      {
        "id": "cgpt-1792862581266_0",
        "type": "function",
        "function": {
          "name": "terminal",
          "arguments": "{\"command\":\"ls -la\"}"
        }
      }
    ]
  }
  ```
- **Invariant `stream: True`**:
  * `stream: False`: Bị timeout/hang I/O do CDP ngầm không đẩy dữ liệu khi buffer chưa đầy.
  * `stream: True`: Bắt buộc kích hoạt HTTP SSE. Luồng chunk `choices[0].delta` hoạt động trơn tru.
- **Độ trễ & Đánh giá phân vai**:
  * Latency trung bình: ~27.6s cho một turn multi-turn tool completion.
  * Đánh giá: Rất thích hợp làm Worker O(1) chuyên sâu (`sol_worker.py` / `sol_repair.py`). Không khuyến nghị làm Coordinator Telegram chính vì độ trễ 27s/turn gây cảm giác bot bị đơ, cộng thêm rủi ro phụ thuộc cookie web (403 QR camera).

## 2. Gateway Daemon In-Memory Module Staleness
- **Sự cố thực tế**: Người dùng đã commit bản vá `d3d2e55` trong `consult_advisor.py` (23:43 ngày 24/10) để chặn spam Advisor, nhưng trên Telegram bot vẫn tiếp tục tự động append Advisor ở các turn tiếp theo.
- **Nguyên nhân cốt lõi**:
  * Tiến trình Gateway nền (`python -m hermes_cli.main gateway run`) được khởi chạy từ 11:28 ngày 24/10 (12 giờ trước thời điểm commit).
  * Python runtime giữ nguyên module trong RAM (`sys.modules`), không tự reload khi file trên đĩa thay đổi.
- **Quy trình xử lý chuẩn**:
  * Kiểm tra PID: `psutil` / PowerShell tìm `hermes_cli.main gateway run`.
  * Kill và restart Gateway daemon để nạp lại bytecode mới vào RAM.
