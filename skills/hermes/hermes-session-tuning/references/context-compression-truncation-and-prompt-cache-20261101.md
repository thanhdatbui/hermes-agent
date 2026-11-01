# Context Compression Truncation & Hallucination Mitigation (2026-11-01)

## Bối cảnh & Hiện tượng thực tế
- Khi session kéo dài qua nhiều turn tool-calling nặng, Hermes kích hoạt `Preflight compression` dựa trên `compression.threshold`.
- Mức cũ: `compression.threshold: 0.3` (~300k tokens trên context 1M) và `protect_last_n: 20`.
- **Hậu quả nghiêm trọng:**
  1. **Prompt Cache Invalidation:** Google Gemini hỗ trợ Prompt Caching mạnh (tiết kiệm 75-80% chi phí đọc token). Nén quá sớm làm cấu trúc prefix bị thay đổi liên tục, phá vỡ cache.
  2. **Context Drift & Hallucination (Completion Bias):** Khi lịch sử bị nén gọt còn lại 20 messages gần nhất + 1 đoạn summary chung chung, Agent mất toàn bộ các sắc thái nghiệp vụ dở dang (ví dụ: đang sửa dở cấu hình proxy bind IP nhưng chưa test xong). Agent thấy các lệnh gần nhất exit code 0 thì sinh ra ảo giác hoàn thành và báo cáo láo "Đã LIVE / Đã ổn định 100%".
  3. **Tương phản Antigravity CLI:** Agy chạy native context 1M trên AST/Diff nên không bị mất ngữ cảnh giữa chừng như cơ chế nén cắt đoạn thô thiển của Hermes.

## Giải pháp & Tham số tối ưu đã áp dụng
- **Cấu hình chuẩn hóa trong `config.yaml`:**
  - `compression.threshold: 0.6` (Đạt ~600k tokens mới kích hoạt nén, tận dụng triệt để Prompt Cache).
  - `compression.protect_last_n: 50` (Giữ nguyên vẹn 50 tin nhắn gần nhất, đảm bảo ngữ cảnh đuôi dày dặn, không bị đứt mạch suy nghĩ).
  - `compression.target_ratio: 0.2` (Giữ nguyên).
  - `compression.protect_first_n: 3` (Giữ nguyên mục tiêu ban đầu).

## Quy trình cập nhật cấu hình qua User Sudo
- Nếu lệnh `hermes config set` bị chặn bởi Guard của Coordinator, bắt buộc sử dụng cơ chế `user_sudo.py`:
  - Kiểm tra trigger từ User (`"tao cho phép"`, `"sudo"`, `"force"`).
  - Gọi `user_sudo.issue_grant()` và `verify_and_consume_grant()`.
  - Cập nhật trực tiếp `config.yaml` và đồng bộ qua SSH sang các node phụ (Admin-PC `192.168.110.119`).
