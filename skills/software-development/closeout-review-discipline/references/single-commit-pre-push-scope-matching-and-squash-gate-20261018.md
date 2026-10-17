# Single-Commit Pre-Push Scope Matching & Squash Gate Protocol (2026-10-18)

## Bối Cảnh Lỗi
Trong quá trình phát triển và remediation closeout gate, một tác vụ thường trải qua nhiều commit nhỏ liên tiếp:
1. Commit 1: Sửa file logic chính (`cron_night_tiktok_2fa_watchdog.py`)
2. Commit 2: Sửa file unit test tương ứng (`test_cron_night_tiktok_2fa_watchdog.py`)
3. Commit 3: Cập nhật mock hoặc thêm edge cases vào file test integration (`tests/test_cron_night_tiktok_2fa_watchdog.py`)

Khi chạy `closeout_gate.py --base <root_commit> --target-file ...`:
- Reviewer thẩm định toàn bộ dải diff giữa `root_commit` và `HEAD`.
- Kết quả `APPROVED` được ghi vào `gate_audit.jsonl` với:
  - `commit_sha`: `<HEAD_SHA>` (hash của Commit 3).
  - `scope`: `[cron_night_tiktok_2fa_watchdog.py, test_cron_night_tiktok_2fa_watchdog.py, tests/test_cron_night_tiktok_2fa_watchdog.py]`.
  - `scope_hash`: hash của danh sách 3 files trên.

## Triệu Chứng Sập Tại Pre-Push Hook (`safe_push.py`)
Khi tiến hành `safe_push.py`, hook `.git/hooks/pre-push` thực hiện kiểm tra an toàn nghiêm ngặt:
```python
current_commit = git_output('rev-parse', 'HEAD')
raw_scope = git_output('diff-tree', '--no-commit-id', '--name-only', '-r', current_commit)
current_scope = sorted(set(p.replace('\\\\', '/').lstrip('./') for p in raw_scope.splitlines() if p.strip()))

if binding.get('commit_sha') == current_commit:
    if sorted(binding.get('scope', [])) == current_scope and binding.get('scope_hash') == scope_hash(current_scope):
        # PASS
```
Vì Commit 3 (HEAD) chỉ sửa đổi file test của commit đó (1 file), `git diff-tree -r HEAD` chỉ trả về 1 file, trong khi `binding.get('scope')` trong log chứa cả 3 files. Hook báo lỗi:
```text
❌ [BLOCKED - PRE-PUSH HOOK]: Gate check FAILED — Không tìm thấy bản ghi Closeout Gate APPROVED >= 80 cho commit hiện tại!
```

Nếu chạy lại `closeout_gate.py --base HEAD~1`:
- Gate sẽ từ chối hoặc đánh tụt điểm nghiêm trọng (57-78 điểm) vì commit HEAD~1..HEAD là **test-only commit** (thiếu bằng chứng implementation tương ứng).

## Quy Trình Xử Lý Chuẩn (Squash-to-Single-Commit Workflow)
Trước khi đưa code vào thẩm định closeout gate cuối cùng hoặc khi gặp lỗi lệch scope tại pre-push:

1. **Soft reset về commit gốc chưa sửa:**
   ```bash
   git reset --soft <base_commit>
   ```
   *(Toàn bộ các thay đổi ở cả file logic và file test sẽ chuyển về trạng thái staged, giữ nguyên working tree)*.

2. **Commit gom nguyên tử thành 1 commit duy nhất:**
   ```bash
   git commit -m "fix(domain): implement complete feature with unit and integration tests"
   ```

3. **Chạy Closeout Gate với `--base HEAD~1`:**
   ```bash
   python D:/Taadaa/tools/closeout_gate.py --repo <repo_path> --base HEAD~1 \
     --target-file <path/to/impl.py> \
     --target-file <path/to/test.py> \
     --model review --json-output
   ```

4. **Kết quả:**
   - Reviewer chấm điểm trên gói thay đổi hoàn chỉnh (cả code và test).
   - `commit_sha` trong `gate_audit.jsonl` trùng `HEAD`.
   - `audit_binding.scope` khớp 100% với `git diff-tree -r HEAD`.
   - `safe_push.py` kiểm tra pre-push thành công ngay lập tức không bị cản trở.
