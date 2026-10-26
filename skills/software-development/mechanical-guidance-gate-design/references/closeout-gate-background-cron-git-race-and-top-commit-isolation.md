# Closeout Gate: Xử Lý Xung Đột Race Condition Commit Ngầm Từ Cronjob Git-Sync

## 1. Hiện Tượng Thực Tế
- Hệ thống có cronjob chạy ngầm định kỳ tự động commit vào git (ví dụ `sync-hermes-skills-and-brain-to-git`, chạy `sync_hermes_skills_silent.py` mỗi 5 phút, commit `chore: sync skills and brain memories` vào nhánh `main`).
- Agent thực hiện nhiệm vụ, sửa file nghiệp vụ và commit với tiền tố `[L2-surgery]` hoặc feature commit.
- Khi User ra lệnh `Done` / `chốt phiên`: Cronjob ngầm đã kịp commit 1 hoặc nhiều commit `chore: sync...` đè lên trên commit của Agent.
- Khi Agent chạy Closeout Gate:
  `python D:/Taadaa/tools/closeout_gate.py --repo "D:/Taadaa/Hermes" --base HEAD~1 --files <target_file> --json-output`
- Thẩm định thất bại ngay tại Bước 2 (Extract Candidate Diff) với 2 dạng lỗi:
  * **Dạng 1 (dùng `--base HEAD~1`):** `Failed to extract diff: no staged, working-tree, or HEAD-commit changes for targets ['<target_file>']` (do `HEAD` hiện tại là commit của cronjob, không chứa target file).
  * **Dạng 2 (dùng `--base <agent_commit>~1`):** `ValueError: committed <range> scope [...] != --files targets ['<target_file>']; refusing partial committed scope` (do trong range có lẫn 10+ file skills/memories của cronjob, vi phạm luật cô lập 100% scope).

## 2. Bản Chất Cơ Học Của Closeout Gate
- `closeout_gate.py` yêu cầu: Commit được review bắt buộc phải là commit ở đỉnh `HEAD` khi đối soát `--base HEAD~1`, HOẶC toàn bộ committed scope giữa `base` và `HEAD` phải khớp chính xác 100% với danh sách `--files`.
- Gate kiên quyết từ chối partial committed scope để ngăn chặn rủi ro push các thay đổi chưa được kiểm chứng.

## 3. Quy Trình 4 Bước Cô Lập Đỉnh HEAD (Top-Commit Isolation)

Khi gặp lỗi này, Agent thực hiện chính xác quy trình sau:

### Bước 1: Tạm dừng Cronjob Git-Sync
```python
cronjob(action='pause', job_id='7e576815788f') # sync-hermes-skills-and-brain-to-git
```
*Mục đích: Ngăn chặn cronjob chèn thêm commit mới trong lúc đang thao tác git.*

### Bước 2: Đưa Target Commit lên Đỉnh HEAD
1. Soft reset về ngay trước commit của Agent:
   ```bash
   git -C <repo> reset --soft <agent_commit>~1
   ```
2. Unstage file target để giữ lại trong working tree:
   ```bash
   git -C <repo> restore --staged <target_file>
   ```
3. Commit toàn bộ các file skills/memories của cron trước:
   ```bash
   git -C <repo> commit -m "chore: sync skills and brain memories"
   ```
4. Stage và commit lại file target ở đỉnh `HEAD`:
   ```bash
   git -C <repo> add <target_file>
   git -C <repo> commit -m "[L2-surgery] <thông điệp commit>"
   ```
5. Kiểm tra bảo đảm:
   ```bash
   git -C <repo> diff HEAD~1..HEAD --name-only
   # Bắt buộc chỉ xuất hiện đúng DUY NHẤT file <target_file>
   ```

### Bước 3: Chạy Lại Closeout Gate
```bash
python D:/Taadaa/tools/closeout_gate.py --repo "<repo>" --base HEAD~1 --files <target_file> --json-output
```
*Gate sẽ nhận diện đúng `committed_targeted` cho 1 file duy nhất và tiến hành chấm điểm review bình thường.*

### Bước 4: Khôi phục Cronjob Git-Sync
```python
cronjob(action='resume', job_id='7e576815788f')
```
