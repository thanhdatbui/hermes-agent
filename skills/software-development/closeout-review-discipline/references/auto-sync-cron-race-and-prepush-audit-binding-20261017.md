# Auto-Sync Cron Race Condition during Closeout Gate & Pre-Push Audit Binding (2026-10-17)

## 1. Hiện tượng & Vấn đề thực tế
Khi chốt phiên (`closeout-review-discipline` / `closeout_gate.py`):
1. **Cronjob `sync-hermes-skills-and-brain-to-git` chạy ngầm mỗi 5 phút**:
   - Nếu trong lúc Coordinator/Worker đang chạy Closeout Gate hoặc vừa commit xong code task, cron job này chạy `sync-hermes-skills.py` và auto-commit đè lên git HEAD:
     ```text
     e098b8b7d chore: sync skills and brain memories
     5af47a19d fix(cron): normalize chatgpt_ok calculation ...
     ```
   - Hậu quả: HEAD bị trôi sang commit mới (`e098b8b7d`), trong khi bản ghi Closeout Gate trong `gate_audit.jsonl` được ký cho commit trước đó hoặc worktree.
2. **Pre-Push Hook chặn đứng vật lý (`INC-HERMES-2026-001`)**:
   - Hook kiểm tra `current_commit = git_output('rev-parse', 'HEAD')`.
   - Nếu commit ở HEAD không khớp với `audit_binding.commit_sha` và `audit_binding.scope_hash` trong `gate_audit.jsonl`, pre-push hook sẽ từ chối:
     ```text
     ❌ [BLOCKED - PRE-PUSH HOOK]: Gate check FAILED — Không tìm thấy bản ghi Closeout Gate APPROVED >= 85 cho commit hiện tại!
     ```
3. **Closeout Gate `HEAD~1` từ chối khi commit không nằm ở đỉnh HEAD**:
   - Khi chạy `closeout_gate.py --base HEAD~1 --files ...`:
   - Nếu commit task bị chìm xuống dưới 1-2 commit sync khác, `closeout_gate.py` báo:
     ```text
     ✘ Failed to extract diff: no staged, working-tree, or HEAD-commit changes for targets [...]
     ```

---

## 2. Quy trình Xử lý Chuẩn Mực (Standard Operating Procedure)

### Bước 1: Tạm dừng Cron Sync trước khi chốt phiên
Trước khi commit và chạy Closeout Gate hoặc khi phát hiện commit sync chen ngang, tạm dừng cronjob:
```python
cronjob(action="pause", job_id="7e576815788f")  # sync-hermes-skills-and-brain-to-git
```

### Bước 2: Đưa commit của task lên đỉnh HEAD (nếu bị chen ngang)
Dùng `git reset --soft <task_commit_sha>` để loại bỏ các commit sync rác ở đỉnh HEAD, giữ nguyên toàn bộ thay đổi uncommitted/staged trong working directory:
```bash
git reset --soft <task_commit_sha>
git restore --staged .  # đưa về unstaged để tránh lệch candidate diff
```

### Bước 3: Chạy `closeout_gate.py` với base ref chính xác
Chạy Closeout Gate với base là commit ngay trước task commit:
```bash
python D:/Taadaa/tools/closeout_gate.py --repo D:/Taadaa/Hermes --base HEAD~1 --files <files...> --json-output
```
- Khi thẩm định thành công (`APPROVED >= 85` hoặc `GRACE BAND APPROVED 80-84`), Closeout Gate sẽ ghi bản ghi audit với `commit_sha: <current_commit>` và `scope_hash` tương ứng vào `gate_audit.jsonl`.

### Bước 4: Push an toàn qua `safe_push.py`
```bash
python D:/Taadaa/tools/safe_push.py D:/Taadaa/Hermes fork main
```
- Pre-push hook sẽ duyệt ngược `gate_audit.jsonl`, xác nhận `binding.commit_sha == current_commit` và cho phép push.

### Bước 5: Kích hoạt lại Cron Sync
Sau khi push thành công, bật lại cronjob đồng bộ:
```python
cronjob(action="resume", job_id="7e576815788f")
```
