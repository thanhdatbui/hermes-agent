---
name: git-worktree-merge-reconciliation
description: Rà soát & merge branch/worktree về main an toàn — dùng git cherry để biết commit đã merge hay cherry-pick, phát hiện uncommitted trùng/khác nhau giữa các worktree ("conflict trùng"), nhận diện pin wheel lỗi thời trỏ vào worktree đã xoá, và chạy pytest đúng interpreter (PYTHONPATH=.). Dùng khi user yêu cầu "commit các tree rồi merge về main" / "check conflict trùng" hoặc có nhiều branch codex chờ merge.
---
# Git Worktree Merge Reconciliation

Khi user yêu cầu commit các worktree/branch rồi merge về main (hoặc "check conflict trùng"), KHÔNG merge mù. Làm theo thứ tự dưới đây.

## 1. Inventory

```bash
git status && git branch -a && git worktree list && git log --oneline -10
```

Ghi nhận trạng thái dirty của TỪNG worktree: `git -C <worktree> status` + `git -C <worktree> diff --stat`. Một branch "đã merge hết commit" vẫn có thể còn uncommitted.

**`origin/main` có thể chỉ là ALIAS của `origin/master`** (proven 2026-08-16, repo Hotmail): so 2 chiều `git log --oneline master..origin/main` + `git log --oneline origin/main..master` — cả 2 rỗng = cùng commit, KHÔNG phải branch riêng, không có gì để merge. Đừng tạo merge commit cho "main" khi 2 ref đã trùng. (Ngược lại nếu `git log origin/main..master` ra commit → local ahead, chỉ cần push; nếu `master..origin/main` ra commit → origin có thêm, pull trước.)

## 2. Xác định trạng thái merge của từng branch

```bash
git cherry -v master <branch>        # + = commit CHƯA có trên master; - = đã merge/cherry-pick
git log master..<branch> --oneline   # commit chỉ có trên branch
git log <branch>..master --oneline   # commit master có thêm
git merge-base master <branch>
```

Pitfall: `git cherry` dấu `-` nghĩa là commit đã vào master (merge hoặc cherry-pick) → branch đó hết commit mới, merge sẽ no-op về commit. Dấu `+` = còn commit thật sự chưa merge. Luôn kiểm tra cả `git log master..<branch>` trước khi kết luận.

## 3. So sánh uncommitted giữa các worktree (phát hiện "conflict trùng")

```bash
git diff <branch> --stat                       # working tree master vs commit branch
diff <(cat file) <(cat <worktree>/file)        # so từng file trùng giữa 2 working tree
```

Khi 2 worktree cùng sửa 1 file (thường gặp: AGENTS.md, pyproject.toml, requirements-automation-core.txt, tests/test_ui_capture_contract.py), xác định bản nào canonical trước khi quyết định giữ:

- **Policy file (AGENTS.md)**: so với nguồn canonical `D:\Taadaa\AGENTS.md` (không thuộc git — bản trên đĩa là chuẩn). Có thể tồn tại 2 phiên bản khác hướng (vd prose v3 vs block v3 + Coordinator/Worker Boundary) giữa các worktree → resolve semantic, không "lấy ours" mù, không merge bản cũ/superseded.
- **Pin version**: bản mới hơn thắng. Xác minh commit nào bump: `git show <commit>:pyproject.toml | grep automation-core` và `git log --all -S "0.4.XX" -- pyproject.toml`.
- Branch có thể "đã merge hết commit" nhưng uncommitted của nó là bản CŨ (vd pin 0.4.29 trong khi master đã 0.4.32) → KHÔNG commit+merge bản đó.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
