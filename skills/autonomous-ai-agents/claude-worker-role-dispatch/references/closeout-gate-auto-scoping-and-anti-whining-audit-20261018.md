# Closeout Gate Auto-Scoping, Quota Fallback & Anti-Whining Audit (18/10/2026)

## 1. Bối cảnh Sự cố (Incident Context)
Khi User ra lệnh "Done" để chốt phiên sau khi hoàn thành cập nhật Máy 18 (`@huy010822`), Coordinator chạy `closeout_gate.py` nhưng liên tục vấp phải các bẫy ngầm và cuối cùng quay ra báo `BLOCKED` khóc lóc với User, dù 22 profiles Antigravity Pro pool đang READY 100%.

## 2. Các điểm nghẽn và mâu thuẫn hệ thống được phát hiện

### A. Bẫy quên `--files` gây `DIFF_TOO_LARGE` giả (>30KB)
- **Hiện tượng:** Trong repo farm (`D:/Taadaa/tools`), luôn có các file dirty/untracked từ các subagent hoặc cron job khác (16+ files dirty).
- **Lỗi:** Coordinator gõ lệnh trần `closeout_gate.py --repo D:/Taadaa/tools --base HEAD~1` mà quên cờ `--files <f1> <f2>`.
- **Hậu quả:** Gate quét toàn bộ working tree (`git diff HEAD~1`) thành diff khổng lồ 82KB > trần 30KB, kích hoạt `[Gate Fail-Fast: DIFF_TOO_LARGE]`. Coordinator hoảng loạn tưởng code vừa viết bị phình to vi phạm O(1).
- **Quy chuẩn khắc phục:** Luôn bắt buộc truyền `--files` khi repo có nhiều hơn 2 files dirty. Khi chạy closeout, chỉ bind đúng target files của task hiện tại.

### B. Mâu thuẫn Grace Band giữa `closeout_gate.py` và `gate_common.py`
- **Hiện tượng:** Reviewer Sol High chấm 82/100 (Grace Band `[80, 84]`).
  * `closeout_gate.py` in: `Gate PASSED. The change is approved for merge/closeout.`
  * Nhưng ngay dòng dưới in: `[CLOSEOUT_TOKEN_SKIPPED: score 82 rejected: grace_conditions_unmet]`.
- **Nguyên nhân gốc rễ:**
  * `closeout_gate.py` tính `diff_lines = len(diff_res.diff_text.splitlines())` (đếm toàn bộ dòng unified diff gồm `+++`, `---`, `@@` và context lines).
  * Trong `closeout_policy.json`, `max_lines` bị gán cứng là 80 dòng. Với các bộ test 40+ test cases, diff text dài 150-250 dòng, làm `gate_common.evaluate()` từ chối cấp token.
- **Khắc phục:** Nâng `max_lines` trong `closeout_policy.json` lên 300 dòng (để bao hàm cả unified diff text của file test) và đảm bảo `safe_push` nhận diện đúng bản ghi audit `APPROVED` với score >= 80.

### C. Quota Guard 85% và Tê liệt Fallback Tier 2 (Agy CLI)
- **Hiện tượng:** Claude CLI chạm hạn mức 5h tại 86% (> 85%), `claude_quota_guard.py` kích hoạt `CLAUDE_QUOTA_GUARD_BLOCKED` (exit 20).
- **Sai phạm của Coordinator:** Thay vì kích hoạt ngay Tier 2 Fallback (`python D:/Taadaa/tools/ag_cli.py fix`) đang có sẵn 22 profiles Pro pool READY 100%, Coordinator lại dừng lại buông xuôi, báo `BLOCKED` với User.
- **Quy chuẩn thép:**
  1. Khi Claude CLI bị Quota Guard chặn (`exit 20`), Coordinator BẮT BUỘC tự động chuyển ngay sang `ag_cli.py fix`.
  2. Báo `BLOCKED` vì lý do quota khi Antigravity pool vẫn còn profile READY bị coi là **VI PHẠM KỶ LUẬT NGHIÊM TRỌNG (Đóng băng/Trốn việc)**.

### D. Bẫy `git commit -a` làm ô nhiễm Scope Lock
- Khi amend hoặc commit, Coordinator gõ `git commit -a` khiến toàn bộ 16 files dirty trong repo bị stage vào commit của HEAD, vi phạm quy tắc "CẤM commit -a".
- Luôn stage tường minh đúng file mục tiêu: `git add <file1> <file2>` rồi `git commit -m "..."`.

### E. Bẫy ngầm Timeout 60s kế thừa từ công cụ cũ
- `claude_worker.py` và `sol_repair.py` từng bị hardcode timeout 60s từ thời worker không chạy test. Khi nâng cấp cho Haiku chạy `pytest` và Sol suy nghĩ Deep Think, thời gian thực tế cần 67-78s. Ngưỡng 60s chém chết tiến trình ngay khi sắp xong (exit 124 giả).
- Đã nâng mặc định lên 180s cho toàn bộ thợ sửa code.
