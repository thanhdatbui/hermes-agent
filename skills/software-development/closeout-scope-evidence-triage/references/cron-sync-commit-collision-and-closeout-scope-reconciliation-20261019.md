# Background Cron Commit Collision & Closeout Scope Reconciliation Incident (2026-10-19)

## 1. Hiện Tượng & Triệu Chứng
Khi chạy Closeout Gate trên repo `D:/Taadaa/Hermes`:
```bash
python D:/Taadaa/tools/closeout_gate.py --repo "D:/Taadaa/Hermes" --base a723e43a3 --files deploy/hermes-home/scripts/post_evening_gpm_login_watchdog.py deploy/hermes-home/scripts/cron_chatgpt_web_pool_watchdog.py tests/test_post_evening_gpm_login_watchdog.py --json-output
```
Gate lập tức exit code 1 và ném lỗi:
```text
✘ Failed to extract diff: committed a723e43a3d18b0a4b724c6755714d82677510a00..HEAD scope ['deploy/hermes-home/memories/MEMORY.md', 'deploy/hermes-home/memories/USER.md', 'deploy/hermes-home/scripts/cron_chatgpt_web_pool_watchdog.py', 'deploy/hermes-home/scripts/post_evening_gpm_login_watchdog.py', 'skills/autonomous-ai-agents/claude-worker-role-dispatch/SKILL.md', ...] != --files targets ['deploy/hermes-home/scripts/cron_chatgpt_web_pool_watchdog.py', 'deploy/hermes-home/scripts/post_evening_gpm_login_watchdog.py', 'tests/test_post_evening_gpm_login_watchdog.py']; refusing partial committed scope
```

## 2. Nguyên Nhân Gốc Rễ (Root Cause)
1. **Background Cron Chạy Ngầm:** Trong hệ sinh thái Hermes có cronjob `sync-hermes-skills-and-brain-to-git` (`7e576815788f`) với lịch chạy `*/5 * * * *` (mỗi 5 phút một lần).
2. **Race Condition Đè Commit:** Mỗi khi có sự thay đổi trong `skills/` hoặc `memories/`, cronjob này tự động tạo commit `chore: sync skills and brain memories` đè lên đỉnh của `HEAD`.
3. **Mất Dấu Committed Scope:** Trong quá trình agent phát triển hoặc chờ reviewer, commit thực tế của task (`feat(gpm): ...`) bị 4-5 commit chore đè lên trên.
4. **Logic Kiểm Tra Của Gate:** Hàm `_extract_diff_targeted()` trong `closeout_gate.py` gọi `_committed_scope(repo, base_ref)`, vốn tính toán `git diff --name-only base_ref..HEAD`. Vì khoảng diff chứa cả các file của commit task lẫn các file của commit chore (`MEMORY.md`, `USER.md`, `skills/**`), `set(targets) == committed_scope` trả về `False`, khiến gate từ chối trích xuất diff vì nghi ngờ "partial committed scope".

## 3. Quy Trình Khắc Phục Chuẩn (Standard Resolution Protocol)
1. **Bước 1: Tạm dừng Cronjob Auto-Sync:**
   ```python
   cronjob(action="pause", job_id="7e576815788f")
   ```
2. **Bước 2: Phân Tách Lịch Sử Git (Git Re-alignment):**
   - Reset mixed về commit gốc trước khi task bắt đầu:
     ```bash
     git -C "D:/Taadaa/Hermes" reset <pre_task_commit>
     ```
   - Gom toàn bộ thay đổi của skills và memories vào một commit chore nằm phía dưới:
     ```bash
     git -C "D:/Taadaa/Hermes" add deploy/hermes-home/memories skills
     git -C "D:/Taadaa/Hermes" commit -m "chore: sync skills and brain memories"
     ```
   - Gom đúng các file mục tiêu của task (`targets`) vào commit trên cùng (HEAD):
     ```bash
     git -C "D:/Taadaa/Hermes" add <target_files>
     git -C "D:/Taadaa/Hermes" commit -m "feat(...): ... [gate-approved]"
     ```
3. **Bước 3: Xác Minh Committed Scope:**
   - Chạy lệnh kiểm tra:
     ```bash
     git -C "D:/Taadaa/Hermes" diff --name-only HEAD~1..HEAD
     ```
   - Kết quả bắt buộc phải trùng khớp tuyệt đối 1:1 với danh sách `--files targets`.
4. **Bước 4: Thực Thi Closeout Gate:**
   - Chạy lệnh gate với `--base HEAD~1`:
     ```bash
     python D:/Taadaa/tools/closeout_gate.py --repo "D:/Taadaa/Hermes" --base HEAD~1 --files <target_files> --json-output
     ```
5. **Bước 5: Khôi Phục Cronjob:**
   - Sau khi gate chấm điểm xong và commit được push/chốt, mở lại cronjob auto-sync:
     ```python
     cronjob(action="resume", job_id="7e576815788f")
     ```
