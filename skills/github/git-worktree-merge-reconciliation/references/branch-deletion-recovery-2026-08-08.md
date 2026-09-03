# Case 2026-08-08 — xoá nhầm remote branches rồi khôi phục từ dangling commits

## Bối cảnh
User yêu cầu "kiểm tra all nhánh merge về main check conflict trùng rồi xoá". 2 remote branch
cũ (base 0.4.28-era):
- `origin/codex/device-lock-transactional-recovery-20260804` (3 commits, transactional device lock)
- `origin/codex/tiktok-shared-startup-dismiss-20260731` (2 commits: shared typed popup dismissal helpers)

## Sai lầm ban đầu
1. Chạy `merge-tree --write-tree` nhưng script truyền cho audit chỉ `.splitlines()[:3]`
   (3 dòng đầu) → audit kết luận "chỉ conflict CHANGELOG.md" (sai — thật 8 file).
2. Dựa trên grep HEAD (`device_lock.py` có transactional/takeover refs, `startup.py` có 7 defs)
   kết luận "main đã hấp thụ hết" → `git push origin --delete` c<span>ả 2 branch.
3. User phản hồi: **"đáng lẽ phải audit những cái vừa làm và cho audit đọc nhánh cây chứ —
   xoá rồi sao nó đọc mà biết đã merge chính xác"**.

Bình luận: content-refs grep (transactional xuất hiện ở main) KHÔNG chứng minh được toàn bộ
feature — main có thể phát triển theo hướng riêng, branch có hàm/defs chưa có ở main
(verify: startup.py diff 164 dòng, device_lock diff 176 dòng giữa archive và master).

## Khôi phục (dữ liệu không mất — git store giữ)
```bash
git fsck --unreachable 2>/dev/null | grep commit      # thấy 64f0206, a604aa3, b30a0e1...
git branch archive/codex-device-lock-transactional-20260804 64f0206
git branch archive/codex-dismiss-shared-startup-20260731 a604aa3
```
66 unreachable ngoài master: phân loại — "Rescue snapshot"/"WIP on master"/"index on" = stash
cũ/amend rơi; chỉ vài commit feature (dismiss/device-lock) là báo động thật.

## Audit round 2 (đọc cây đã restore)
- branch 1 (device-lock) → verdict **(a) delete — superseded** (master đã có transactional
  implementation + scope + DeviceLockTransactionError — functional no loss).
- branch 2 (dismiss/startup) → verdict **(c) MERGE NGAY — real feature code absent from master**.
  → Đúng user nghi ngờ: xoá mà không merge = mất code.

## Merge thật (không tin merge-tree cắt)
`git merge --no-commit archive/codex-dismiss-shared-startup-20260731` → **8 conflict files /
23 blocks** (không chỉ CHANGELOG): CHANGELOG(1), ui-compatibility-contract(2), pyproject(1),
benign_popup.py(7), test_tiktok_benign_popup(5), startup.py(AA,3), test_tiktok_startup(AA,2),
tasks/*.md(AA,1). Resolve spec: GIỮ CẢ 2 PHÍA — master version 0.4.44/record
coordinate-fallback/add-phone; branch shared dismiss hàm thêm vào. Commit merge sau verify
pytest 4 nhóm (_startup, _benign_popup, _tiktok_popup, _input_jitter) + py_compile + 0 markers.

## Lessons
- Audit cây TRƯỚC DELETION; nếu đã xoá → restore `git branch archive/<name> <dangling>`.
- Truyền merge-tree output ĐẦY ĐỦ (grep `^[0-9]{6}` + awk) cho audit; dùng `git merge
  --no-commit` để lộ conflict thật rồi mới quyết resolve hoặc bỏ.
- Grep content main "CÓ từ khoá" ≠ "CÓ feature" — so diff theo file khi quyết legacy.
- Khuôn mẫu resolve branch cũ × main mới: keep master (version, evidence, form) + thêm
  part feature còn thiếu của branch shadow (startup defs, dismissal terms).