# Tri-layer Hardening: Chống Zombie Process Kẹt Luồng & Tắc Nghẽn Báo Cáo Feed Watchdog

## 1. Bản Chất Sự Cố (Root Cause)
- **Vấn đề non-daemon thread:** Trong Python, `concurrent.futures.ThreadPoolExecutor` mặc định khởi tạo worker thread với `daemon=False`.
- **Hành vi shutdown của Python:** Khi tiến trình runner chạy xong và ghi đầy đủ `run_manifest.json`, lệnh `raise SystemExit(main())` kích hoạt cơ chế `threading._shutdown()`. Python bắt buộc chờ tất cả non-daemon thread kết thúc trước khi thực sự trả tiến trình về cho OS.
- **Kẹt I/O thiết bị ngoại vi:** Khi 1–2 máy con bị kẹt socket ADB/USB (hoặc thiết bị rớt mạng bất thường), worker thread bị treo vĩnh viễn ở tầng socket socket recv. Tiến trình Python và shell bọc ngoài (PowerShell `run-feed-session.ps1`) trở thành tiến trình zombie (0% CPU, không giải phóng PID).
- **Hậu quả dây chuyền trên Farm:** Cronjob `feed_session_watchdog.py` dùng `psutil` kiểm tra `is_feed_runner_active()`. Khi thấy tiến trình runner từ sáng vẫn tồn tại PID, watchdog lầm tưởng ca nuôi vẫn đang diễn ra (`runner_busy = True`), dẫn tới việc **kìm hãm toàn bộ báo cáo hoàn thành của tất cả các ca trong ngày**, không gửi lên Telegram.

---

## 2. Kiến Trúc 3 Tầng Bảo Vệ (Tri-layer Hardening)

### Tầng 1: Worker Thread mang thuộc tính `daemon=True` trong ThreadPool
Trong `multi_machine_feed_session.py`, lớp `_FailClosedThreadPoolExecutor` ghi đè `_adjust_thread_count` để chỉ định `daemon=True` cho tất cả worker thread.
Bọc khối try/except an toàn với fallback `super()._adjust_thread_count()` để phòng ngừa thay đổi private API ở các bản nâng cấp Python:
```python
class _FailClosedThreadPoolExecutor(ThreadPoolExecutor):
    """Do not make the outer watchdog wait for already-running child threads."""

    def _adjust_thread_count(self) -> None:
        try:
            if self._idle_semaphore.acquire(timeout=0):
                return
            def weakref_cb(_, q=self._work_queue):
                q.put(None)
            import weakref
            from concurrent.futures.thread import _worker, _threads_queues
            num_threads = len(self._threads)
            if num_threads < self._max_workers:
                thread_name = '%s_%d' % (self._thread_name_prefix or self, num_threads)
                t = threading.Thread(
                    name=thread_name,
                    target=_worker,
                    args=(weakref.ref(self, weakref_cb), self._work_queue, self._initializer, self._initargs),
                    daemon=True,
                )
                t.start()
                self._threads.add(t)
                _threads_queues[t] = self._work_queue
        except Exception as exc:
            logging.getLogger("multi_machine_feed_session").warning("_adjust_thread_count daemon fallback: %s", exc)
            super()._adjust_thread_count()

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self.shutdown(wait=False, cancel_futures=True)
        return None
```

### Tầng 2: Hard OS-Exit Guard tại CLI Entrypoint
Tại `run_tiktok.py`, sau khi hoàn tất mọi tác vụ ghi artifact, summary, flush I/O buffer và giải phóng device lock, tiến trình thoát dứt khoát bằng `os._exit(_code)` ở cấp độ OS kernel.
Bắt buộc có guard kiểm tra pytest để không phá vỡ test runner khi chạy test suite:
```python
if __name__ == "__main__":
    try:
        _code = main()
    finally:
        sys.stdout.flush()
        sys.stderr.flush()
    if "pytest" in sys.modules or os.environ.get("PYTEST_CURRENT_TEST"):
        raise SystemExit(_code)
    import os
    os._exit(_code if isinstance(_code, int) else 0)
```

### Tầng 3: Watchdog Zombie Circuit Breaker (Bộ lọc thời gian 2.5h)
Trong `feed_session_watchdog.py`, hàm `is_feed_runner_active()` kiểm tra `create_time` của tiến trình qua `psutil`.
Nếu một tiến trình runner tồn tại quá 2.5 giờ (9000 giây) trong khi thời lượng tối đa của một ca là 50–80 phút:
- Tự động bỏ qua tiến trình stale này và ghi cảnh báo `logger.warning`.
- Đánh dấu `runner_busy = False` cho ca đã hoàn thành để giải phóng báo cáo gửi lên Telegram ngay lập tức.
```python
now_ts = time.time()
for p in psutil.process_iter(['name', 'cmdline', 'create_time']):
    try:
        ...
        if any(pat in cmd for pat in runner_patterns):
            try:
                ctime = p.info.get('create_time') or p.create_time()
                if ctime and (now_ts - ctime) > 9000:
                    logger.warning("Bỏ qua runner zombie PID %s chạy quá 2.5h (%.1fh)", p.pid, (now_ts - ctime)/3600)
                    continue
            except Exception:
                pass
            return True
    except Exception:
        pass
```

---

## 3. Teardown Power & Screen Management
Khi kết thúc phiên (`_force_stop_tiktok_and_home`), tránh để màn hình sáng liên tục làm nóng máy và chai pin:
- `am force-stop <package>`
- `input keyevent 3` (HOME)
- `svc power stayon false`
- `settings put global stay_on_while_plugged_in 0`
- `settings put system screen_off_timeout 600000` (10 phút)
- Hỗ trợ routing remote ADB server cho cụm máy Admin (serial >= 200) qua `-H 192.168.110.119 -P 5037`.

---

## 4. Kỷ Luật Dispatch Subagent Cho Repos Nặng (PyTorch / Ultralytics)
- Khi dispatch worker subagent sửa code trên `tiktok-luot nuoi acc`:
  - CẤM chạy `pytest` diện rộng hoặc pytest nạp cả module heavy ML (`feed_swipe_smoke.py` -> `image_navigation.py` -> `ultralytics/torch`) vì import mất >100s, dễ làm subagent cạn 600s budget dẫn tới timeout.
  - Luôn yêu cầu subagent viết focused unit test độc lập dùng `unittest` hoặc mock test chạy trong < 1s.
