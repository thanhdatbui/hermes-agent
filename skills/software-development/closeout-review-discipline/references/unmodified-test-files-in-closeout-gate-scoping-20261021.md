# Pitfall: Unmodified Files in `closeout_gate.py --files` Argument (21/10/2026)

## 1. Triệu chứng sự cố (The "Targets without working-tree changes" Trap)
Khi gọi `closeout_gate.py` có cờ `--files` để khóa phạm vi diff (tránh lan sang các file dirty khác trên repo farm), nếu Coordinator truyền cả file test sạch (không sửa đổi) vào `--files`:
```bash
python D:/Taadaa/tools/closeout_gate.py --repo "D:/Taadaa/tools" --base HEAD --files claude_quota_guard.py tests/test_claude_quota_guard.py --json-output
```
Gate lập tức thất bại ngay tại **Bước 2 (STEP 2: EXTRACT CANDIDATE DIFF)** với mã thoát `exit 1`:
```text
✘ Failed to extract diff: targets without working-tree changes: ['tests/test_claude_quota_guard.py']
```

## 2. Gốc rễ thiết kế trong `closeout_gate.py`
Trong `closeout_gate.py` hàm `targeted_candidate(repo, targets, base_ref)`:
```python
if changed:
    if sorted(changed) != targets:
        raise ValueError(f"targets without working-tree changes: {sorted(set(targets) - changed)}")
    return "worktree_targeted", targets, diff
```
* Bộ trích xuất diff yêu cầu: MỌI file được liệt kê trong `--files` **BẮT BUỘC PHẢI CÓ THAY ĐỔI** (staged, unstaged diff hoặc untracked file).
* Nếu một file trong danh sách không có diff so với HEAD, gate coi đó là lỗi sai lệch khai báo phạm vi (`targets without working-tree changes`) và fail-closed lập tức.

## 3. Cơ chế tự động tìm test của `closeout_gate.py`
Coordinator KHÔNG CẦN và KHÔNG ĐƯỢC truyền file test không sửa đổi vào `--files` vì:
1. `closeout_gate.py` có sẵn bộ suy diễn focused test (`_detect_test_command` / `direct_tests`):
   - Khi truyền `--files claude_quota_guard.py`, gate tự động bóc tách stem và tìm `tests/test_claude_quota_guard.py` để chạy focused test.
2. Quy tắc chuẩn:
   - Nếu file test **CÓ ĐƯỢC SỬA / TẠO MỚI**: Truyền cả `<source_file>` và `<test_file>` vào `--files`.
   - Nếu file test **GIỮ NGUYÊN (CHỈ CHẠY TEST KHÔNG SỬA TEST)**: CHỈ truyền đúng `<source_file>` có diff vào `--files`.
