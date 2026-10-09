# Xử lý Divergence Commit Trùng Tree & Stash Concurrent Edits Khi Chốt Phiên

## 1. Hiện tượng
Khi chốt phiên trong môi trường farm có nhiều tiến trình/subagent chạy song song:
1. **Unstaged changes chặn `git pull --rebase`:** Trong lúc Coordinator đang chạy các bước review, background worker có thể ghi thêm code/test vào working tree. Lệnh `git pull --rebase` sẽ văng lỗi `cannot pull with rebase: You have unstaged changes`.
2. **Diverged commit cùng tree hash:** Khi local commit được tạo và push lên remote, một process/subagent khác có thể đã commit một commit tương đương tại local trước đó hoặc git fetch ghi nhận phân nhánh (`Your branch and 'origin/main' have diverged, and have 1 and 1 different commits each`). Khi kiểm tra bằng `git rev-parse HEAD^{tree} origin/main^{tree}`, hai tree hash hoàn toàn giống nhau (`d5e16fb^{tree} == 1ae2f95^{tree}`).

## 2. Quy trình xử lý chuẩn (Non-Destructive)
1. **Cô lập unstaged changes:**
   ```bash
   git stash push -m "stash_concurrent_worker_edits"
   ```
2. **Pull rebase & Push:**
   ```bash
   TOKEN=$(gh auth token)
   git pull --rebase "https://${TOKEN}@github.com/<owner>/<repo>.git" <branch>
   git push "https://${TOKEN}@github.com/<owner>/<repo>.git" HEAD:<branch>
   ```
3. **Đồng bộ hóa Diverged Commit cùng Tree:**
   Nếu local commit và remote commit có cùng tree hash:
   ```bash
   git reset --mixed <pushed_sha>
   ```
   Lệnh này kéo `HEAD` local về khớp 100% với `origin/<branch>` mà không làm mất bất kỳ thay đổi nào trong working directory (không dùng `--hard`).
4. **Phục hồi working tree:**
   ```bash
   git stash pop
   ```
   Đảm bảo `git status` hiển thị `Your branch is up to date with 'origin/<branch>'`.
