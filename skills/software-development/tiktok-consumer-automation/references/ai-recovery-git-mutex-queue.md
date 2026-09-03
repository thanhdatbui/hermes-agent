# AI Auto-Recovery Git Mutex Queue & Safe Concurrency Pattern

## 1. Vấn đề thực tế
Khi farm chạy nhiều máy song song (batch nuôi/reg/follow), nhiều máy có thể gặp màn hình kẹt bất thường cùng lúc (ví dụ Máy 3, Máy 46, Máy 47):
1. **Lỗi `❌ git_lock_busy`**: Cơ chế mutex cũ chỉ check 1 lần không chờ (non-blocking). Máy đến sau thấy file lock lập tức trả về `git_lock_busy` và bỏ qua bước commit code vào repo.
2. **Lỗi `cannot pull with rebase: You have unstaged changes`**: Nếu thực hiện `git pull --rebase` khi code patch vừa được ghi vào file trên disk (nhưng chưa `git add` & `git commit`), Git sẽ từ chối rebase.

## 2. Giải pháp chuẩn hóa (`code_patcher.py`)

### A. Spin Lock với Queue / Retry Loop (Chờ tối đa 60s)
Cho phép tiến trình chờ (spin lock với sleep polling 1.0s) tối đa 60 giây thay vì fail ngay:

```python
def _acquire_git_lock(timeout: float = 60.0, retry_interval: float = 1.0) -> bool:
    GIT_PATCH_LOCK.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.time() + timeout
    while True:
        if GIT_PATCH_LOCK.exists():
            try:
                age = time.time() - GIT_PATCH_LOCK.stat().st_mtime
                if age >= GIT_LOCK_TTL_SECONDS:
                    # Lock stale (>10m), safely overwrite
                    break
            except Exception:
                pass
            if time.time() >= deadline:
                return False
            time.sleep(retry_interval)
        else:
            break
    try:
        GIT_PATCH_LOCK.write_text(str(time.time()), encoding="utf-8")
        return True
    except Exception:
        return False
```

### B. Thứ tự Git Commit & Rebase chuẩn
Sau khi máy lấy được lock, patch code và chạy Pytest thành công:
1. `_git(["add", str(target_path)])`
2. `_git(["commit", "-m", msg])` (Bắt buộc commit trước để working tree sạch sẽ)
3. `_git(["fetch", "origin"])` && `_git(["pull", "--rebase", "origin", "master"])` (Rebase an toàn sau commit, tránh lỗi unstaged changes)
4. `_git(["push", "origin", "master"])`
5. Giải phóng lock trong khối `finally: _release_git_lock()`
