# Antigravity Pool Routing & Closeout Review Pitfalls (2026-10-22)

## 1. Conflating Coordinator Model with Background Worker CLI Pool
- **Bẫy nhầm lẫn**: Khi gặp `AGY_ERROR: 429 RESOURCE_EXHAUSTED` hoặc profile cooldown trong Antigravity CLI pool (`D:/Taadaa/agy_profiles`), Coordinator KHÔNG ĐƯỢC suy diễn là "mất kết nối LLM" hay "lỗi Gemini không chat được" rồi than vãn với Operator.
- **Thực tế**: Session Coordinator chat trực tiếp qua OmniRoute/Gemini (`ag-gemini-pool-3`), hoàn toàn độc lập với dàn headless profile sandbox của `ag_cli.py`. Phải phân định rạch ròi giữa transport Coordinator và background worker pool để tránh báo cáo nhảm nhí / hoảng loạn gây ức chế cho User.

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

## 4. Diff Budget Truncation Manifest Deadlock (31.9KB vs 28.8KB Ceiling)
- **Cơ chế bẫy**:
  * `sol_payload_guard.py` mặc định `SOL_TARGET_BYTES = 36_000` với `diff_budget = 80% = 28_800 bytes`.
  * Khi gộp cả production code (`ag_cli.py` ~18.5KB) và test file (`tests/test_ag_cli.py` ~13.4KB), tổng diff đạt ~31.9KB, vượt trần 28.8KB.
  * `digest_diff()` tự động cắt bớt phần diff của `ag_cli.py` và chèn `[TRUNCATION_MANIFEST] ... NOTE: Phần bị lược KHÔNG được coi là đã review`.
  * Reviewer Sol High đọc được marker này sẽ từ chối review trọn vẹn, lập tức hạ điểm xuống 76/100 và ghi rõ trong phán quyết: *"Diff bị lược bỏ một phần đáng kể... không thể xem đây là chứng nhận an toàn phát hành"*.
- **Cách phá vỡ Deadlock (Anti-Loop Discipline)**:
  * Không cố chấp append thêm test hay retry prompt cũ khi diff đã chạm trần payload.
  * Tách commit O(1) độc lập: Đưa các tính năng phụ hoặc test bổ sung sang commit kế tiếp, giữ commit hiện tại dưới 25KB để Sol Reviewer nhận trọn vẹn 100% diff và chấm điểm khách quan.
