# Merge branch → main (quy trình user yêu cầu, Tiktok-video)

User dictate 2026-08-05: "commit các thay đổi các nhánh tree xong merge về nhánh main,
kiểm tra conflict trùng logic script, sau đó merge bản hoàn chỉnh r commit main trước"
→ thứ tự: **commit working tree → merge main VÀO branch (test conflict) → resolve →
merge branch VỀ main → push**. Không chạy batch live trước khi git sạch.

## Thứ tự an toàn

1. `git worktree list` + `git branch -a -v` — xác định nhánh/worktree thật sự đang có.
2. Với working tree dirty: `git status --short` phân loại modified/untracked.
   Chạy test suite liên quan TRƯỚC commit (`305 passed` cho workflow+inventory+yolo).
3. Commit working tree trên main trước (bản hoàn chỉnh).
4. `git checkout <branch>` rồi `git merge main --no-commit --no-ff` — test conflict sớm
   ngay trên nhánh, KHÔNG đợi merge về main mới vỡ.
5. Resolve conflict. Rule chung: **giữ bản main** khi branch chỉ đóng góp docs cũ /
   branch mang bản file stale (kiểm tra: `git diff <branch> main --stat` sau resolve
   phải rỗng với file script — "trùng logic script" nghĩa là code 2 bên khớp nhau).
6. Commit merge trên branch, `git checkout main`, `git merge <branch>`, resolve conflict
   lần 2 (có thể phát sinh ở file khác do branch đã chứa bản copy từ merge trước —
   giữ theirs = main), commit.
7. `git fetch origin` → so `rev-list --count HEAD..origin/main`; nếu 0 là remote không
   có commit mới → pull sạch rồi push. User: "pull on remote trước, push sau".

## Pitfall git

- **`git add -A` dính `.codex-work/`**: thư mục chứa node_modules + file bị permission
  denied (`.codex-work/tiktok-upload-launcher-worker-*/lease.json` short read) →
  `fatal: adding files failed` giữa chừng, staging lẫn lộn. Fix: `git reset -q` rồi
  `git add` theo từng đường dẫn cụ thể (scripts/, tests/, tasks/...). `.codex-work/`
  là diagnostic/tmp — KHÔNG commit (không nằm trong .gitignore, phải add tay né).
- **`git pull --rebase` fail giữa chừng**: khi local đã có merge commit + remote
  không có gì mới, rebase branch docs cũ sẽ conflict → `git rebase --abort` để về
  trạng thái trước pull (local vẫn nguyên, push vẫn OK nếu remote không advance).
- **`git patch-id` phát hiện commit trùng**: 2 commit cùng message docs ở 2 nhánh
  (963bb80 main vs 17ef8ff branch) có patch-id khác nhau → không phải cherry-pick
  trùng, là 2 bản docs riêng; branch đó chỉ đóng góp docs, script toàn là main mới.
- **Conflict file tests khi merge branch về main**: branch đã chứa bản copy stale của
  file (từ lần merge trước) → `git checkout --theirs <file>` (theirs = main) là đúng.
- CRLF warnings từ git (LF sẽ bị thay CRLF) là vô hại — đừng coi là lỗi.
- `git log --parents -1 <commit>` để xác nhận merge commit có đúng 2 parent.

## Branch hygiene + closeout push (2026-08-05)

Khi repo có NHIỀU branch remote (vd `origin/main` + `origin/master`) và user hỏi
"nhánh nào mới là chính / đã pull push chưa / dọn xoá luôn", quy trình xác định +
dọn:

1. **Xác định nhánh chính**: `git branch -r` + `git remote show origin | grep HEAD`
   (hoặc `git branch -r | grep origin/HEAD`) — `origin/HEAD -> origin/main` =
   GitHub default branch = **main là chính**, master chỉ là branch cũ từ trước khi
   đổi tên default. Xác nhận thêm: `git merge-base origin/main origin/master` rồi
   `git merge-base --is-ancestor <merge-base> origin/main` (main chứa toàn bộ lịch
   sử cũ) + `git rev-list --count origin/main..origin/master` (master chỉ hơn main
   vài commit).
2. **Đánh giá master cũ có đáng merge không**: xem `git show <commit> --stat` —
   nếu chỉ pin core CŨ (vd 0.4.0 trong khi main đã 0.4.35) + file docs main đã
   xóa/đổi → KHÔNG merge (conflict rác, zero giá trị). `git diff main origin/master
   --stat` để thấy mức độ lệch.
3. **Xóa branch cũ sạch**: `git push origin --delete master` (+ `git branch -D
   master` nếu có local). Không cần hỏi lại khi user nói "dọn xoá luôn".
4. **Commit nốt working tree** (nếu còn modified hợp lệ — vd bump core pin +
   test sync): commit + push từng cụm, mỗi commit 1 chủ đề.
5. **Closeout chuẩn**: `git status -sb` phải `## main...origin/main` (không ahead/
   behind); `git rev-list --left-right --count origin/main...HEAD` → `behind: 0 |
   ahead: 0`; untracked còn lại chỉ nên là `.codex-work/` (runtime, không commit).
   Trả lời user bằng con số: "ahead 0, behind 0, N commits đã push".

## Test trước/sau

- Chạy `env -i` sạch + `PYTHONPATH=scripts`: suite workflow/inventory/yolo
  (305 passed). Test `test_vietnamese_pipeline.py` đòi yt-dlp — fail SystemExit
  không liên quan thay đổi, bỏ qua.
