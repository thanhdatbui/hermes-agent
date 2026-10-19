# Auto-Sync Cron Race & Committed Scope Refusal Triage (2026-10-19)

## Bối Cảnh Sự Cố
Trên kho mã nguồn `D:/Taadaa/Hermes`, cronjob `sync-hermes-skills-and-brain-to-git` (job_id: `7e576815788f`) tự động quét và commit các thay đổi trong `skills/` và `deploy/hermes-home/memories/` định kỳ mỗi 5 phút với thông điệp:
`chore: sync skills and brain memories`.

Khi một phiên làm việc phát triển mã nguồn (ví dụ: sửa `post_evening_gpm_login_watchdog.py` và `cron_chatgpt_web_pool_watchdog.py`), commit tính năng được tạo trên nhánh local. Tuy nhiên, nếu cron sync chạy ngay sau đó, một hoặc nhiều commit `chore: sync...` sẽ nằm đè lên đỉnh nhánh (`HEAD`).

Khi thực hiện thủ tục chốt phiên:
```bash
python D:/Taadaa/tools/closeout_gate.py --repo "D:/Taadaa/Hermes" --base HEAD~1 --files deploy/hermes-home/scripts/post_evening_gpm_login_watchdog.py deploy/hermes-home/scripts/cron_chatgpt_web_pool_watchdog.py tests/test_post_evening_gpm_login_watchdog.py --json-output
```

Hàm `_committed_scope(repo, base_ref)` trong `closeout_gate.py` phân giải phạm vi commit bằng lệnh:
`git diff --name-only base_ref..HEAD`

Do `HEAD` đã bị các commit chore đè lên, phạm vi commit bao gồm cả các file markdown/memories. Hệ thống kiểm soát phạm vi phát hiện:
`committed <range> scope [...] != --files targets [...]; refusing partial committed scope`
và lập tức thoát với `exit code 1`.

---

## Quy Trình Xử Lý Chuẩn (Remediation Protocol)

### Bước 1: Tạm Dừng Cronjob Đồng Bộ
Tránh việc cronjob tiếp tục commit đè trong khi đang sắp xếp lại lịch sử git:
```python
cronjob(action="pause", job_id="7e576815788f")
```

### Bước 2: Sắp Xếp Lại Lịch Sử Commit (Mixed Reset & Replay)
1. Xác định commit cơ sở trước khi có các thay đổi tính năng và chore (ví dụ: `a723e43a3`):
   ```bash
   git -C "D:/Taadaa/Hermes" reset <base_commit>
   ```
   *Lưu ý:* Mixed reset đưa HEAD và Index về commit cũ nhưng giữ nguyên 100% nội dung các file trong working tree dưới dạng unstaged.

2. Stage và commit toàn bộ các file skills và memories vào một commit chore độc lập trước:
   ```bash
   git -C "D:/Taadaa/Hermes" add deploy/hermes-home/memories skills
   git -C "D:/Taadaa/Hermes" commit -m "chore: sync skills and brain memories"
   ```

3. Stage và commit chính xác danh sách các file tính năng vào đỉnh `HEAD`:
   ```bash
   git -C "D:/Taadaa/Hermes" add <target_impl_files...> <target_test_files...>
   git -C "D:/Taadaa/Hermes" commit -m "feat(...): ... [gate-approved]"
   ```

4. Kiểm tra đối soát:
   ```bash
   git -C "D:/Taadaa/Hermes" --no-pager diff --name-only HEAD~1..HEAD
   ```
   Xác nhận kết quả trả về khớp 100% từng file với danh sách `--files`.

### Bước 3: Kích Hoạt Lại Closeout Gate
Chạy lệnh gate với `--base HEAD~1` và `--files`:
```bash
python D:/Taadaa/tools/closeout_gate.py --repo "D:/Taadaa/Hermes" --base HEAD~1 --files <target_files...> --json-output
```
Lúc này `set(targets) == committed_scope` trả về `True`, gate chuyển sang bước chạy test focused và gửi diff cho Reviewer Sol High thẩm định mà không bị chặn phạm vi.

### Bước 4: Mở Lại Cronjob Đồng Bộ
Sau khi Closeout Gate hoàn tất (hoặc commit được push/merge):
```python
cronjob(action="resume", job_id="7e576815788f")
```
