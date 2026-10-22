# Sol Review Mặc Định & Kiến Trúc Chống Kẹt Vòng Lặp 3-Strike Remediation (2026-10-23)

## 1. Bối Cảnh & Thực Tế Vận Hành (Problem Statement)
- **Vấn nạn đốt Quota của Sonnet Reviewer**: Khi ép `closeout_gate.py` dùng `--model claude-sonnet`, mỗi vòng review đọc full diff + scorecard chiếm 10k–15k tokens. Trải qua 3 vòng reject + 1 vòng hand-off sửa + 1 vòng re-audit = ~60k tokens Sonnet $\rightarrow$ cạn kiệt 85% hạn mức 5h của Claude CLI (`CLAUDE_QUOTA_GUARD_BLOCKED`).
- **Nghịch lý Moving Goalposts**: Sonnet Reviewer có xu hướng "kính hiển vi", liên tục đổi tiêu chí qua từng vòng:
  * Vòng 1: Chê thiếu telemetry & test âm.
  * Vòng 2: Sửa xong telemetry & test âm $\rightarrow$ lại chê "tại sao dùng substring mà không dùng prefix".
  * Vòng 3: Sửa xong prefix $\rightarrow$ lại chê "prefix chưa đủ hẹp" dù 72/72 tests pass 100%.
- **Điểm yếu của Sol Repair**: Tạo proposal JSON mà không có bước sandbox test nội bộ $\rightarrow$ dễ sinh patch dính lỗi cú pháp (`SyntaxError: unindent`) hoặc chắp vá hời hợt, làm lãng phí Strike.

## 2. Kiến Trúc Khắc Phục Tinh Gọn (Anti-Loop Remediation Architecture)

### A. Mặc Định Closeout Qua Sol Review (:20129)
- `closeout_gate.py` mặc định chạy `--model review` (Sol Auditor qua OmniRoute `:20129`).
- **Chi phí**: Tốn đúng 0% Quota Claude (sử dụng pool ChatGPT Web), không bao giờ gây gián đoạn hay khóa tài khoản Claude Code của Operator.
- **Phân vai**: Chỉ bật `--model claude-sonnet` khi Operator yêu cầu tường minh cho các đợt refactor kiến trúc lớn.
- **Tách biệt code**: Trong `run_gate_pipeline()`, cấm gộp `"review"` vào tuple gọi `run_claude_review_pipe()`. Chỉ khi `model in ("claude", "claude-sonnet", "claude_cli")` mới gọi Claude Sonnet CLI.

### B. Cơ Chế Tự Kiểm Thử Của Sol Repair (Pre-flight Validation & AST Dedent)
- **Dedent & Dummy Function AST Validation**: Trong `sol_repair._validate_python_patch()`, khi `ast.parse` gặp snippet thụt lề, bắt buộc fallback qua `textwrap.dedent()` và wrap trong `def _dummy():\n...` để tránh báo lỗi cú pháp giả mạo (`SyntaxError: unindent`).
- **Dry-run kiểm thử nội bộ**: Trước khi ghi proposal ra đĩa, `sol_repair.py` phải thực hiện dry-run: áp dụng patch vào bản sao tạm và chạy `pytest <test_file>`.
- Nếu syntax error hoặc test fail: Sol Repair tự động loop-back sửa lại ngay trong nội bộ nó, không nộp bài thi hỏng lên Gate để tránh bị mất Strike oan.

### C. Khóa Tiêu Chí Chấm Điểm Bằng Code (Anti-Moving Goalposts)
- **Đóng băng findings vòng 1**: Khi Strike 1 bị REJECTED, `closeout_gate.py` lưu cứng danh sách lỗi `findings_v1` vào runtime state.
- **Kiểm soát bằng code**: Từ Strike 2 trở đi, prompt chỉ hỏi Reviewer: "Các mục trong `findings_v1` đã được khắc phục chưa?". CẤM Reviewer tự ý đẻ thêm các tiêu chí kiến trúc mới ngoài danh sách đã đóng băng.

### D. Phân Tầng Rubric Theo Numstat (O(1) Fast-Path)
- **Diff O(1) nhỏ gọn (<= 30 dòng, 1-2 files)**: Chỉ chấm 2 tiêu chí cốt lõi:
  1. *Logic khắc phục đúng issue.*
  2. *100% focused tests pass.*
- CẤM TUYỆT ĐỐI trừ điểm vì thiếu refactor kiến trúc lớn hay thiếu logging/telemetry rườm rà ngoài scope O(1).
- Nếu logic đúng và test pass: Kích hoạt Grace Band (80đ) để cấp Token APPROVED và push ngay, không ép cày điểm lên >=85đ bằng các test/comment thừa thãi.

### E. Fast-Track Remediation (Khi Dùng Sonnet)
- Nếu bài toán bắt buộc cần Sonnet, bỏ qua hoàn toàn chuỗi Sol Repair 3 vòng:
  * Ném thẳng review feedback cho Sonnet sửa ngay trong 1 phiên mới.
  * Chấm lại 1 phiên độc lập.
  * Tổng cộng tối đa 2 lần gọi Sonnet (tiết kiệm >60% quota so với cách cũ 4-5 lần).

## 3. Các Bẫy Kỹ Thuật Đã Xử Lý Khi Thi Công Gate (Implementation Pitfalls)
- **Bẫy Quote Argument `--tools ""` trong Subprocess (2026-10-23)**: Khi gọi `claude -p` qua `subprocess.run(cmd, ...)` trong Python, danh sách `cmd` không qua shell (`shell=False`). Nếu truyền `"--tools", "\"\""`, Python gửi nguyên chuỗi literal gồm 2 ký tự nháy kép `""` sang binary, khiến Claude CLI cố tìm tool tên `""` và báo lỗi cú pháp CLI. BẮT BUỘC truyền `"--tools", ""` (chuỗi rỗng thực tế) để tắt hoàn toàn tools cho phiên review.
- **Bẫy Cache Quota 2 Giờ & Probe Cưỡng Chế Sau Reset**: `claude_worker.py` cache mẫu quota trong `plan-usage-history.json` với `MAX_QUOTA_STALE_HOURS = 2.0`. Khi qua mốc reset (ví dụ 3:49am), mẫu cũ (100%) vẫn chưa đủ 2 giờ nên guard vẫn chặn. Bắt buộc kích hoạt probe làm mới: `python -c "import sys; sys.path.insert(0, 'D:/Taadaa/tools'); from claude_worker import try_refresh_claude_quota; try_refresh_claude_quota()"` để cập nhật ngay mẫu mới 0% vào JSON.
- **Bẫy Snippet First-Line Strip Indentation trong AST Validation**: Khi LLM sinh patch mà dòng đầu bị strip leading whitespace so với thân hàm (`x = 1\n    y = 2`), `textwrap.dedent()` thông thường sẽ thất bại. Trong `sol_repair._validate_python_patch()`, đo số space thụt lề ở dòng 2 (`len(l) - len(l.lstrip())`), tái tạo khoảng trắng cho dòng 1 rồi mới dedent và bọc vào `def _dummy():\n...`.
- **Fence Nonce & NEED_CONTEXT Trong Claude Review Pipe**: Khi tích hợp Claude Sonnet CLI (`run_claude_review_pipe`), bắt buộc sinh `nonce = secrets.token_hex(6)` cho mọi thẻ fence (`<<<GIT_DIFF nonce=...>>>`), kiểm tra chuỗi `NEED_CONTEXT:` trong phản hồi để set verdict tương ứng, và đếm dòng thay đổi thật từ unified diff (+/-) cho fast-path O(1).
