# Closeout Gate Truncation Manifest, Staged SHA Binding & Fallback Governance (2026-10-18)

## 1. Hiện Tượng & Nguyên Nhân Gốc Rễ Khiến Coordinator Tê Liệt (Paralysis)
Trong các phiên closeout phức tạp tại `D:/Taadaa/tools`, Coordinator dễ rơi vào trạng thái hoảng loạn, dừng lại than vãn và báo `BLOCKED` sai quy định do 4 mâu thuẫn cơ học giữa code và chính sách:

1. **Lỗi đếm dòng unified diff (`RFC-1`):**
   - `closeout_gate.py` từng tính `diff_lines = len(diff_res.diff_text.splitlines())`. Phép tính này đếm cả metadata `diff --git`, `index`, `---`, `+++`, `@@` và 3 dòng context quanh mỗi hunk.
   - Hậu quả: Một patch sửa 30 dòng code thực tế bị đội lên thành 120–250 dòng diff text, vượt ngân sách `budget.max_lines` (80 dòng) của Grace Band ➔ `gate_common.py` đánh trượt oan (`[CLOSEOUT_TOKEN_SKIPPED: score 82 rejected: grace_conditions_unmet]`), khiến Gate vừa in PASSED vừa không cấp token.
   - **Giải pháp:** Bắt buộc tính `diff_lines` theo số dòng thêm/xóa thực tế (numstat):
     `sum(1 for l in diff_res.diff_text.splitlines() if (l.startswith('+') and not l.startswith('+++')) or (l.startswith('-') and not l.startswith('---')))`

2. **Khóa độc quyền Strike 3 Handoff (`RFC-2`):**
   - Gate từng ghi cứng `"owner": "claude_cli"` và in thông báo bắt buộc giao bàn phím cho Claude.
   - Khi Claude CLI bị `claude_quota_guard.py` chặn (quota 5h >= 85%), câu chữ độc tài này làm Coordinator tưởng rằng mọi kênh khác đều bị cấm, dẫn đến đóng băng phiên thay vì gọi Antigravity CLI.
   - **Giải pháp:** Bổ sung `"fallback_owner": "antigravity_pool"` và sửa thông báo rõ ràng cho cả Tier 1 (Claude CLI) lẫn Tier 2 (Agy pool).

3. **Quét nhầm toàn bộ repo khi quên `--files` (`RFC-3`):**
   - Trong repo farm có nhiều file dirty từ các tiến trình khác, nếu chạy gate mà quên `--files`, script âm thầm quét toàn bộ working tree (`git diff HEAD`). Diff phình to >30KB và văng `DIFF_TOO_LARGE`.
   - **Giải pháp:** Fail-closed ngay Step 2 nếu không có `--files` và số file dirty > 2 (`[Gate Fail-Fast: SCOPE_NOT_DECLARED]`).

4. **Lệch Commit SHA giữa Pre-Commit Review và `safe_push.py` (`RFC-4`):**
   - Gate thẩm định khi code còn ở working tree/staged, ghi audit với `commit_sha` là commit cha (HEAD cũ). Khi commit xong, HEAD đổi sang SHA mới ➔ `safe_push` và hook `pre-push` chặn push vì commit SHA mới chưa có bản ghi APPROVED.
   - **Giải pháp:** Hỗ trợ đối soát pre-commit `_staged_diff_matches`: nếu audit record có `parent_sha` và `staged_diff_sha256`, `safe_push` tính hash nhị phân của `git diff HEAD~1..HEAD` đối chiếu byte-exact với `staged_diff_sha256`.

---

## 2. Bẫy Cắt Tỉa Diff của Sol Payload Guard (20KB Diff Ceiling)
- `sol_payload_guard.py` phân bổ ngân sách: Diff (65%), Log (25%), Reserve/Prompt (10%) trên tổng trần an toàn `SOL_TARGET_BYTES` (~32.768 Bytes).
- Ngân sách diff tối đa: `int(32768 * 0.65) = 21.299 Bytes (~20.8KB)`.
- **Cơ chế bẫy:** Nếu commit gộp nhiều file (ví dụ logic + test suites dày) có diff text vượt quá 21KB, `sol_payload_guard` tự động cắt tỉa diff sang cấp độ L1 và chèn khối `TRUNCATION_MANIFEST`.
- **Phản ứng của Sol High (:20129):** Khi nhìn thấy `TRUNCATION_MANIFEST`, Sol High lập tức đánh giá là thiếu bằng chứng ngữ cảnh và từ chối chấm điểm với lý do:
  `NEED_CONTEXT: <file> — không thể chấm điểm toàn diện một cách có căn cứ khi diff bị lược bỏ một phần quan trọng.`
- **Kỷ luật Closeout:**
  - Tuyệt đối KHÔNG gộp nhiều file lớn vượt quá 18KB diff vào 1 commit duy nhất.
  - Bắt buộc phân rã thành các commit tuần tự O(1) (mỗi commit 1–2 files, diff text <= 18KB), chạy gate duyệt và push từng commit một.

---

## 3. Các Bất Biến Của Nhánh Pre-Closeout Short-Circuit
Khi sử dụng tính năng short-circuit (bỏ qua review khi file đã khớp remote), bắt buộc phải thỏa mãn 4 điều kiện:
1. **Target không được rỗng:** `if not targets: return False, "short-circuit requires explicit non-empty targets"`. Cấm cấp điểm 100 cho scope rỗng.
2. **HEAD đồng bộ với Upstream:** Bắt buộc `head_sha == upstream_sha` để đảm bảo không có commit local nào chưa được push.
3. **Không drift so với `base_ref`:** Target files phải không có khác biệt nào so với `base_ref` được chỉ định.
4. **Bắt buộc có test thực thi thành công:** Short-circuit bị cấm khi bật `--skip-test`, và kết quả test focused phải có `passed > 0`.
