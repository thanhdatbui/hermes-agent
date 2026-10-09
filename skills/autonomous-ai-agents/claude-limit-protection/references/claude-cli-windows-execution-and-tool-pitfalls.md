# Claude CLI Execution on Windows (MSYS/Bash) — Pitfalls & Best Practices (03/10/2026)

## 1. Lỗi Treo Pipe (Hang) khi Pipe Input từ MSYS / Git-Bash
- **Triệu chứng**: Chạy `cat prompt.txt | claude -p ...` trên Windows terminal (MSYS/git-bash) bị treo kịch trần timeout (`[Command timed out after 60s]`).
- **Nguyên nhân**: Quá trình Node.js trên Windows đôi khi không nhận diện được tín hiệu EOF sạch từ MSYS pipe, khiến tiến trình ngâm chờ mãi mãi.
- **Giải pháp**: Truyền nội dung prompt trực tiếp qua argument hoặc dùng command substitution:
  `claude -p "$(< /c/Users/Kibe/.../prompt.txt)"`
  hoặc ghi prompt ra file rồi chạy background process.

## 2. Bẫy "Error: Reached max turns" khi chạy One-Shot Text Review
- **Triệu chứng**: Chạy `claude -p "..." --max-turns 1` (hoặc 5) văng lỗi ngay:
  `Error: Reached max turns (1)`
- **Nguyên nhân**: Khi không chỉ định `--tools ""`, Claude CLI mặc định bật các công cụ tích hợp (`Read`, `Bash`, `Edit`). Khi nhận prompt yêu cầu review/audit code, model cố gọi tool `Read` ở turn đầu tiên. Khi số lượt bị giới hạn `--max-turns 1` (hoặc 5), lượt gọi tool nuốt hết số turns trước khi model kịp xuất ra câu trả lời text cuối cùng.
- **Giải pháp**: Với tác vụ thuần đánh giá/thẩm định text/diff (one-shot LLM review mà đã cung cấp đủ code/diff trong prompt), BẮT BUỘC tắt toàn bộ công cụ bằng cờ:
  `--tools ""`
  Lệnh chuẩn:
  `claude -p "$(< /path/to/prompt.txt)" --tools ""`

## 3. Khắc phục Timeout Foreground (>60s) bằng Background Process
- **Vấn đề**: Các bài toán review kiến trúc chuyên sâu với model Opus/Sonnet thường mất 60s – 120s để suy luận và xuất kết quả. Trong khi đó, Foreground Terminal Guard giới hạn cứng `timeout <= 60s`.
- **Giải pháp**: BẮT BUỘC khởi chạy tiến trình ngầm kèm cờ thông báo tự động:
  ```bash
  claude -p "$(< prompt.txt)" --tools "" > review_output.txt 2>&1
  ```
  Gọi qua tool Hermes: `terminal(command="...", background=True, notify_on_complete=True, timeout=240)`.

## 4. Dọn dẹp Tiến trình Mồ côi (Orphaned Processes)
- Khi các lệnh `claude` bị ngắt giữa chừng do timeout, tiến trình `claude.exe` có thể tiếp tục chạy ngầm trong Windows, tích tụ hàng chục process chiếm nhiều GB RAM.
- **Lệnh dọn dẹp sạch bằng PowerShell**:
  ```powershell
  Get-Process -Name 'claude' -ErrorAction SilentlyContinue | Stop-Process -Force
  ```
