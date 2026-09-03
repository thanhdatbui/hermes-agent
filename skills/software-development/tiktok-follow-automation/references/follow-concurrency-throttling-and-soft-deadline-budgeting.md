# Follow Concurrency Throttling & Soft Deadline Budgeting

## Bối cảnh & Vấn đề

Khi 40-80 máy đồng loạt hoàn thành feed session và kích hoạt `_run_follow_hook`, việc chạy subprocess `follow_runner` đồng thời gây quá tải nghiêm trọng cho ADB server (`localhost:5037`) và USB host controller. Hệ quả:
- Các lệnh `dump_ui` / `tap_center` / `type_text` bị timeout hoặc delay kéo dài.
- Follow runner bị quá hạn hard timeout (1200s), kích hoạt watchdog kill cứng, gửi cảnh báo đỏ `GIỮ HIỆN TRƯỜNG FOLLOW TIMEOUT` giả mạo.

---

## Giải pháp 2 tầng

### 1. Concurrency Throttling ở Parent Runner (`tiktok-luot nuoi acc`)

- **Khai báo giới hạn**: `DEFAULT_FOLLOW_MAX_CONCURRENCY = 15`.
- **Lock root**: `~/.codex/follow-concurrency-locks` (hỗ trợ ghi đè qua `TAADAA_TIKTOK_FOLLOW_LOCK_ROOT` hoặc config).
- **Lease Mechanism (`_FollowConcurrencyLease`)**:
  - In-process: `_FOLLOW_CONCURRENCY = threading.BoundedSemaphore(15)`.
  - Cross-process (giữa các tiến trình cron độc lập): 15 file slot OS lock `slot-0.lock` .. `slot-14.lock` sử dụng `msvcrt.locking(LK_NBLCK)` (Windows) hoặc `fcntl.flock(LOCK_EX | LOCK_NB)` (Linux).
- **Subprocess Execution Wrapping trong `_run_follow_hook`**:
  - Bọc `subprocess.run` trong lease context `with _follow_concurrency_lease(timeout=follow_timeout_budget, config=ctx.config) as wait_seconds:`.
  - Tính toán lại timeout thực tế của subprocess: `effective_subprocess_timeout = follow_timeout_budget - wait_seconds`.
  - Nếu `effective_subprocess_timeout <= 0`: fail closed với payload `follow-hard-deadline-after-lease`.
  - Nếu lease acquisition timeout (`TimeoutError`): trả về `follow-queue-timeout`.

---

### 2. Soft Deadline Budgeting ở Child Runner (`tiktok-follow`)

- **Deadline tracking trong `FollowEngine`**:
  - `self.start_time = time.monotonic()` (Lưu ý: KHÔNG gọi `self.now()` trong `__init__` nếu `self.now` là mock generator để tránh cướp tick của unit test loop).
  - `self.feed_timeout_seconds = float(getattr(cfg, 'feed_timeout_seconds', 1200.0) or 1200.0)`.
  - Helper method:
    ```python
    def has_time_for_next_action(self, reserve_seconds: float = 60.0) -> bool:
        elapsed = time.monotonic() - self.start_time
        remaining = self.feed_timeout_seconds - elapsed
        return remaining > float(reserve_seconds)
    ```
- **Graceful loop break ở `run_mode1` & `run_mode2`**:
  - Tại đầu vòng lặp duyệt UID:
    ```python
    if not engine.has_time_for_next_action(reserve_seconds=60.0):
        logger.info("Session deadline approaching, completing gracefully with %d followed accounts", len(res.followed))
        break
    ```
  - Khi còn < 60s, runner tự động dừng vòng lặp và trả về kết quả bình thường (`status: "OK"`, `failed: False`) cùng số nick đã follow thành công, thay vì cố chạy tiếp rồi bị watchdog kill giữa chừng.

---

### 3. Safe Selector Contract cho Top-Left Back Button

Trong `_back_to_feed` (`mode2_follow_followers.py`), khi lọc nút Back trong `_is_search_history_screen`, luôn dùng:
```python
and (is_tiktok_package(n.get("package")) or not n.get("package"))
```
để bảo đảm an toàn khi node XML thiếu thuộc tính package kế thừa, đồng bộ với `_find_top_left_back_button`.
