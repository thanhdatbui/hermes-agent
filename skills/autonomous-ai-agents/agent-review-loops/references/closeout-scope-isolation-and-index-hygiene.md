# Closeout Scope Isolation & Index Hygiene

## Context & Problem
Trong các phiên làm việc kéo dài trên phone farm repo, repo thường tích tụ các thay đổi staged hoặc unstaged từ các task trước (watchdog scripts, background jobs, test modules). Khi Coordinator chạy Closeout Gate:
1. **Lệch Target Scope (Step 2 Fail-Closed):**
   Nếu dùng `closeout_gate.py --files <targets>`, script kiểm tra nghiêm ngặt:
   `staged files != --files targets; unstage extras or adjust --files`
   Nếu staged index chứa dù chỉ 1 file thừa từ phiên trước, Closeout Gate sẽ lập tức crash/exit code 1 ngay tại Step 2 mà không thể sang bước chấm điểm.
2. **Diff Bloat & Reviewer Penalty:**
   Nếu chạy `closeout_gate.py` toàn diện (không filter `--files`), toàn bộ diff tồn đọng (+200.000 ký tự) sẽ bị nạp vào prompt của Sol Auditor. Reviewer sẽ trừ điểm nặng vì:
   - Thiếu test evidence tương xứng cho toàn bộ các file watchdog/lifecycle tồn đọng.
   - Diff bị cắt ngắn (truncation) do vượt context window.
   - Điểm số bị kẹt ở mức 76 - 82 / 100 và không thể vượt ngưỡng 85.

## Quy Trình Cách Ly Index Chuẩn Bị Cho Closeout Gate
Trước khi phát lệnh chạy Closeout Gate:
1. **Reset Index về trạng thái sạch:**
   Chạy `git reset HEAD` để unstage toàn bộ các file tồn đọng trong staging area.
2. **Stage duy nhất các file thuộc Scope của phiên hiện tại:**
   Chỉ `git add` đúng:
   - Các file nghiệp vụ / script vừa sửa trong task.
   - Các file unit test và integration test trực tiếp đi kèm.
3. **Đối soát khớp 100% trước khi kích hoạt Gate:**
   Chạy `git diff --cached --name-only` và kiểm tra danh sách này phải trùng khớp tuyệt đối với tham số `--files` truyền vào `closeout_gate.py`.

## Tiêu Chí Đạt Điểm >= 85 Khi Review Policy/Junction
Khi task liên quan đến setup script hoặc policy guard:
- **Contract Inspection:** Có unit test đọc source kiểm tra cú pháp và cấu trúc lệnh (ví dụ `mklink /J` thay cho `robocopy`).
- **Runtime Execution Proof:** Có test chứng minh hành vi runtime thực tế trên Windows (tạo junction tạm trong tempfile, kiểm tra 2 chiều, xóa junction không làm mất file gốc).
- **Telemetry & Audit Schema:** Có test kiểm chứng cấu trúc JSON/JSONL của event audit log để tránh bị trừ điểm phần Observability.
