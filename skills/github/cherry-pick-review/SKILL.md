---
name: cherry-pick-review
description: Review cherry-picked/backport commits for dropped context — missing constant/import definitions, stale pre-rule patterns, partial migrations, silent fail-open gates. Trigger on commits labeled "cherry-pick <sha>" or backport diffs.
---
# Cherry-Pick Review (backport diffs)

Commits named `(cherry-pick <sha>)` reappear across Taadaa repos (`Tiktok_Reg`, consumer repos). A cherry-pick re-applies a diff onto a DIFFERENT base tree — new context often breaks incomplete copies. Review these differently from normal commits: **the upstream commit is the ground truth, and the new base is the danger zone.**

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
