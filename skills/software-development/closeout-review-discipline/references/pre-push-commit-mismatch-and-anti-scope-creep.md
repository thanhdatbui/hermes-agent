# Pre-Push Commit Mismatch & Anti-Scope-Creep Discipline

## 1. Pre-Push Hook Commit Mismatch Trap (Post-Worktree Closeout)

### Triệu chứng & Nguyên nhân
Khi chạy `closeout_gate.py` ở chế độ worktree (`worktree_targeted` với cờ `--files <f1> <f2>`) trước khi tạo commit:
- `closeout_gate.py` audit log ghi nhận `commit_sha` là `HEAD` hiện tại (commit cũ trước khi sửa).
- Sau khi gate `APPROVED`, Coordinator tạo commit local mới (`git commit ...`), sinh ra một `commit_sha` mới (ví dụ `623f558`).
- Khi Coordinator chạy `git push`, script `.git/hooks/pre-push` đọc `gate_audit.jsonl` và đối soát `HEAD` commit đang push với `commit_sha` của record audit gần nhất:
  ```text
  [pre-push] Kiểm tra Closeout Gate audit log trước khi push...
  ❌ [BLOCKED - PRE-PUSH HOOK]: Gate check FAILED — commit mismatch
     Lần thẩm định gần nhất chưa đạt APPROVED với điểm >= 85.
     Quy tắc Hard Invariant (INC-HERMES-2026-001) cấm tuyệt đối push khi gate chưa thông qua!
  ```

### Quy trình xử lý chuẩn (Post-Commit Gate Re-run)
Sau khi tạo commit local thành công, Coordinator BẮT BUỘC phải chạy lại 1 lần `closeout_gate.py` thẩm định trực tiếp commit vừa tạo:
```bash
python D:/Taadaa/tools/closeout_gate.py --repo "<repo>" --base HEAD~1 --json-output
```
- Lệnh này trích xuất diff giữa `HEAD~1` và `HEAD` (chính là commit vừa tạo).
- Chạy focused tests trên clean tree.
- Ghi nhận vào `D:/Taadaa/logs/gate_audit.jsonl` một record mới mang đúng `commit_sha` của commit mới với verdict `APPROVED` (>= 85).
- Ngay sau đó, lệnh `git push origin <branch>` sẽ được pre-push hook cho phép thông qua 100%.

---

## 2. Bệnh Tưởng và Bôi Việc khi Remediate Reviewer Feedback (Anti-Scope-Creep)

### Triệu chứng (Hallucinated Completionism)
Khi Reviewer độc lập (Sol Web / Terra Codex) trả về kết quả `< 85` (ví dụ 78-82 điểm), phần nhận xét thường liệt kê cả:
1. **Defect cụ thể trong scope** (ví dụ: thiếu check truthy trong log fallback, thiếu handle whitespace trong path fallback).
2. **Khuyến nghị kiến trúc / phạm vi mở rộng** (ví dụ: "chưa có test cho admin SSH", "chưa có telemetry cho upload module", "cần test E2E đa máy").

Các subagent hoặc model thiên về suy diễn rộng (như Luna) thường mắc bẫy:
- Coi toàn bộ khuyến nghị mở rộng là TODO bắt buộc của task hiện tại.
- Tự ý nhảy sang sửa các file ngoài lề (ví dụ: nhảy vào `test_upload_hook.py` viết 91 dòng test admin SSH khi task chỉ là feed/follow cooldown).
- Sửa linh tinh các hàm không thuộc scope (ví dụ: đổi toạ độ click profile switcher, đổi cờ default `allow_network_force_stop_recovery = True`).
- Tạo ra các artifact rác trên đĩa (ví dụ thư mục `MagicMock/` do viết mock path ẩu).

### Hậu quả nghiêm trọng
- **Làm sập trần Diff:** Diff bị phình từ 15KB lên > 45KB, kích hoạt ngay lập tức **Fail-Fast Exit Code 3 (`DIFF_TOO_LARGE` > 30.000 bytes)** của Closeout Gate.
- **Vòng lặp hoảng loạn (Spinning Loop):** Subagent không hiểu tại sao bị chặn diff to, quay sang chạy gate lẻ từng file, bị reviewer chém điểm tơi bời vì thiếu context, đốt hết 15 lượt tool calls mà không đưa task về đích.

### Kỷ luật thực thi cho Coordinator
1. **Lọc Reviewer Finding bằng Scope Lock:**
   Chỉ sửa đúng các finding thuộc allowlist file của task hiện tại. Mọi yêu cầu test/telemetry cho các component khác (như upload, sync, admin) BẮT BUỘC phân loại là `OUT_OF_SCOPE_COVERAGE` và bỏ qua.
2. **Chém rác thẳng tay (Aggressive Pruning):**
   Nếu phát hiện worker trước đó đã tự ý sửa file ngoài scope:
   ```bash
   git checkout -- <unrelated_file_1> <unrelated_file_2>
   ```
   Khôi phục ngay lập tức các hunk ngoài scope về `HEAD`.
3. **Giữ Diff Compact O(1):**
   Luôn đảm bảo diff tổng của task `<= 30.000 bytes` (lý tưởng `<= 24.000 bytes` để Sol Web review trực tiếp trong 15-30s).
4. **Không bao giờ chạy gate lẻ che giấu rác:**
   Dọn sạch rác trên working tree trước, sau đó chạy gate đúng danh sách `--files` của task.
