# Closeout Gate Payload Guard & Monorepo Dirty Diff Isolation

Khi sử dụng công cụ thẩm định độc lập `D:/Taadaa/tools/closeout_gate.py` cho phiên làm việc (Closeout Gate threshold >= 85):

## 1. Cơ Chế Sol Payload Guard (32KB Buffer Ceiling)
- `closeout_gate.py` tích hợp `sol_payload_guard.py` để bảo vệ payload gửi sang Reviewer (OmniRoute / Sol Auditor) không vượt quá trần buffer an toàn (~32KB).
- Hàm `split_budget(total_budget)` phân bổ budget:
  - Diff: ~65%
  - Log: ~25%
  - Reserve: ~10%
- Khi git diff quá lớn (+600/-200 dòng) hoặc repository đang có nhiều file uncommitted từ các nhánh/tác vụ song song khác, `diff_digest` sẽ rơi vào trạng thái `truncated` (`[TRUNCATION_MANIFEST]`).
- Khi manifest truncation xuất hiện, Reviewer có thể từ chối phê duyệt hoàn toàn (`REJECTED` hoặc yêu cầu `NEED_CONTEXT`), làm rớt điểm dưới 85 dù unit tests đạt 100%.

## 2. Giải Pháp Cách Ly Diff Cần Review
1. **Dùng Audit Package Độc Lập / File Diff Tập Trung**:
   - Thay vì chạy `--repo <repo_path>` (sẽ gom toàn bộ dirty diff của cả monorepo vào), hãy trích xuất diff hoặc package tài liệu độc lập:
     ```bash
     git -C "<repo_path>" diff -- <target_script> <test_file> > session_diff.patch
     python "D:/Taadaa/tools/closeout_gate.py" --input session_diff.patch
     ```
   - Hoặc soạn một file markdown audit package tương tự `closeout_audit_package.md` bao gồm:
     - Root cause & Architectural resolution
     - Scoped diff của tính năng đang sửa
     - Fresh verification log & Telemetry evidence
     - Chạy với cờ `--input closeout_audit_package.md`.

2. **Bảo Đảm Test Invariants Cho Cron Nurture & GPM**:
   - SQLite Cookies Preflight: Kiểm tra trực tiếp file SQLite Cookies Chromium trên đĩa trước khi khởi động trình duyệt (`has_google_session`).
   - Float Group ID Boundary: Chỉ nhận integer hoặc float nguyên (`10.0`), từ chối float không nguyên (`10.5`, `10.7`) để tránh ép kiểu sai lệch.
   - Telemetry Invariant: Ghi nhận đầy đủ telemetry structured JSONL cho cả 3 pha: candidate summary, profile completion, và batch summary.
