# Antigravity Pool Routing & Closeout Review Pitfalls (2026-10-22)

## 1. Conflating Coordinator Model with Background Worker CLI Pool
- **Bẫy nhầm lẫn**: Khi gặp `AGY_ERROR: 429 RESOURCE_EXHAUSTED` hoặc profile cooldown trong Antigravity CLI pool (`D:/Taadaa/agy_profiles`), Coordinator KHÔNG ĐƯỢC suy diễn là "mất kết nối LLM" hay "lỗi Gemini không chat được".
- **Thực tế**: Session Coordinator chat trực tiếp qua OmniRoute/Gemini (`ag-gemini-pool-3`), hoàn toàn độc lập với dàn headless profile sandbox của `ag_cli.py`. Phải phân định rạch ròi giữa transport Coordinator và background worker pool để tránh báo cáo nhảm nhí / hoảng loạn.

## 2. Model Alias Mismatch trong Headless CLI (`agy`)
- CLI binary `agy` khi khởi chạy với cờ `--model gemini-3.8-flash-high` có thể bị từ chối với lỗi:
  `error: invalid model selection (--model "gemini-3.8-flash-high" --effort ""): model gemini-3.8-flash-high is not recognized as a known model or custom model in settings`
- **Nguyên nhân**: Cấu hình sandbox trong `D:/Taadaa/agy_profiles/<profile>/.gemini/settings.json` chưa map alias hoặc binary mong đợi model khác (ví dụ: `gemini-3.8-flash-medium` hoặc `claude-sonnet-4-6`).
- **Khắc phục**: Chạy `python ag_cli.py models` để inspect danh sách model thực tế được hỗ trợ bởi profile hiện hành trước khi dispatch lệnh fix/ask.

## 3. Stale-Lock Recovery TOCTOU & Reviewer Rejection
- Khi implement lock lease file trên Windows:
  * Quy trình kiểm tra nội dung stale rồi `os.replace` / `os.remove` bị Sol High Reviewer trừ nặng điểm (giới hạn ở 78-79/100) vì có race window (TOCTOU) giữa các syscall.
  * Việc tạo thêm mutex phụ bằng thư mục (`.oplock`) nếu xử lý cồng kềnh sẽ làm phình diff vượt 26KB-30KB, kích hoạt `NEED_CONTEXT` hoặc `DIFF_TOO_LARGE`.
- **Nguyên tắc**: Giữ diff súc tích (< 26KB), tránh đưa các thay đổi timeout/model không liên quan vào cùng diff để không bị Reviewer bắt bẻ scope creep và thiếu ngữ cảnh.
