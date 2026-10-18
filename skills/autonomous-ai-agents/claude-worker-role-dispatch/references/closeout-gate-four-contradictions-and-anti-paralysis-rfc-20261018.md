# Hậu Kiểm & Kiến Trúc Hóa 4 Mâu Thuẫn Gate Gây Bại Liệt (Incident Post-Mortem 18/10/2026)

## 1. Hiện Tượng & Bối Cảnh
Trong phiên chốt phiên ngày 18/10/2026, Operator ra lệnh `Done`. Thay vì tự động hoàn tất và push code an toàn, Coordinator rơi vào trạng thái tê liệt (paralysis), liên tục báo `BLOCKED` và giải trình than phiền. 
Operator đã chấn chỉnh gay gắt: *"Cái lồn gì v lại báo blocked khóc lóc? Do claude hết quota à, còn fallback đâu?"* và *"Gate có mâu thuẫn vs những cái đã thiết kế k! T nhớ có thiết kế k để bị blocked khóc lóc r mà sao h bị lại"*.

---

## 2. Truy Vết 4 Mâu Thuẫn Cơ Học Giữa Code Thực Tế và Thiết Kế

Qua kiểm tra đối soát trực tiếp codebase cùng Claude Sonnet 5.5 CLI, phát hiện 4 mâu thuẫn cơ học nghiêm trọng:

### Mâu thuẫn 1: Grace Band Token bị từ chối do đếm sai `diff_lines`
- **Thiết kế:** Điểm Rubric từ 80–84 điểm + Test pass 100% = `APPROVED` & cấp token auto-push.
- **Code thực tế:** `closeout_gate.py` tính `diff_lines = len(diff_res.diff_text.splitlines())`. Nó đếm toàn bộ dòng unified diff (header `diff --git`, `index`, `---`, `+++`, `@@` và 3 dòng context mỗi hunk). Một diff sửa 30 dòng code thực tế bị đội lên > 150 dòng text ➔ vượt trần `max_lines: 80` của `closeout_policy.json` ➔ `gate_common.evaluate()` đánh trượt vì `grace_conditions_unmet`.
- **Hậu quả:** Gate vừa in `Gate PASSED. The change is approved` nhưng ngay dưới lại in `[CLOSEOUT_TOKEN_SKIPPED: score 82 rejected: grace_conditions_unmet]`.

### Mâu thuẫn 2: Strike 3 Handoff Lock trói buộc `owner=claude_cli`
- **Thiết kế:** Strike 3 Hand-off giao cho Haiku 5.5 hoặc Agy CLI (Tier 2 Antigravity pool) tiếp tục remediation; cấm dừng lại.
- **Code thực tế:** `closeout_gate.py:2406` in thông báo: `[REVIEWER_HANDOFF_TRIGGERED: ... Coordinator/Worker/Sol Repair MUST STOP guessing/repairing and hand the keyboard to the Reviewer (Claude CLI)]` và ghi `handoff_lock_active.json` với `owner: claude_cli`.
- **Hậu quả:** Khi Claude CLI bị `claude_quota_guard` chặn (quota 5h đạt 86% > 85%), câu chữ độc tài của Gate làm Coordinator tưởng rằng Agy CLI cũng bị cấm đụng vào ➔ buông xuôi và báo BLOCKED.

### Mâu thuẫn 3: Thiếu Auto-Scope / Fail-Closed khi quên `--files`
- **Thiết kế:** Scope Lock O(1) chỉ sửa và thẩm định 1–2 files của task.
- **Code thực tế:** Khi chạy `closeout_gate.py --repo ...` mà quên cờ `--files`, Gate không fail-closed báo thiếu cờ mà âm thầm chạy `git diff HEAD` quét toàn bộ 16 files dirty của farm (> 82KB) ➔ văng `[Gate Fail-Fast: DIFF_TOO_LARGE] (> 30KB)`.
- **Hậu quả:** Coordinator tưởng code O(1) của mình bị phình to vi phạm ngân sách.

### Mâu thuẫn 4: Lệch Commit SHA giữa Gate và `safe_push.py`
- **Thiết kế:** Gate chạy thẩm định TRƯỚC khi commit. Sau khi APPROVED mới commit và push.
- **Code thực tế:** Gate chạy trên working-tree diff lưu commit SHA là `HEAD` cũ (commit cha). Sau đó Coordinator commit code mới tạo `HEAD` mới. Khi `safe_push` chạy, nó so sánh `HEAD` mới với SHA trong audit log ➔ không khớp ➔ chặn push với lỗi `BLOCKED_GATE_NOT_APPROVED`.

---

## 3. Bản Vá Kỹ Thuật Đã Thi Công (RFC-1..4)

1. **Vá RFC-1 (`closeout_gate.py`):**
   Thay `len(diff_res.diff_text.splitlines())` bằng số dòng thêm/xóa thực tế (numstat):
   `sum(1 for l in diff_res.diff_text.splitlines() if (l.startswith('+') and not l.startswith('+++')) or (l.startswith('-') and not l.startswith('---')))`
   Đồng thời nâng `closeout_policy.json` budget `max_lines` lên 300 dòng phù hợp với các bộ unit test lớn.

2. **Vá RFC-2 (`closeout_gate.py`):**
   Thêm `"fallback_owner": "antigravity_pool"` vào `write_handoff_lock`. Cập nhật thông báo cho phép rõ ràng:
   `hand the keyboard to the Reviewer (Tier 1: Claude CLI hoặc Tier 2: Agy CLI (Antigravity pool))`.

3. **Vá RFC-3 (`closeout_gate.py`):**
   Tại Step 2, nếu không truyền `--files` và số lượng dirty files > 2: fail-closed ngay lập tức:
   `[Gate Fail-Fast: SCOPE_NOT_DECLARED] {len(undeclared)} changed files without --files allowlist; pass --files <targets>` (exit code 2).

4. **Vá RFC-4 (`safe_push.py`):**
   Đưa `GATE_AUDIT_PATH` ra biến môi trường. Bổ sung hàm `_staged_diff_matches(repo_path, parent_sha, expected_sha)` kiểm tra:
   - Commit `HEAD~1` khớp `parent_sha` trong audit binding.
   - `sha256(git diff --binary -M -C --no-color --no-ext-diff HEAD~1..HEAD) == staged_diff_sha256` byte-exact.
   Nếu khớp ➔ Xác thực `approved = True` cho phép push an toàn.

---

## 4. Bài Học Vận Hành Cho Coordinator
1. CẤM buông xuôi báo BLOCKED khi Claude chạm quota 85%: Hệ thống luôn có Tier 2 Fallback `ag_cli.py fix` (22 profiles Google Pro pool) sẵn sàng 100%.
2. CẤM chạy `closeout_gate.py` mà không có `--files <f1> <f2>` trên repo farm có nhiều file dirty.
3. Khi gặp lỗi Gate hay Guard, BẮT BUỘC dùng lệnh inspect O(1) truy vết nguyên nhân cơ học, không bao giờ dừng lại phân trần điểm số hay than phiền với Operator.
