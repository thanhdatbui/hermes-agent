# Anti-Zombie Process & Runner Teardown (Tri-layer Hardening)

## 1. Triệu chứng & Nguyên nhân gốc rễ (Root Cause)
- **Triệu chứng:** Runner chạy ca (`run-feed-session.ps1` / `run_tiktok.py --mode multi-machine-feed-session`) đã hoàn tất, ghi đầy đủ `run_manifest.json` và `summary.txt`, nhưng tiến trình Python và PowerShell vẫn tồn tại trong OS (CPU = 0%).
- **Hệ quả dây chuyền:** `feed_session_watchdog.py` kiểm tra `is_feed_runner_active()`, thấy tiến trình runner cũ vẫn còn PID nên hiểu lầm farm vẫn bận (`runner_busy = True`), tự động kìm hãm (suppress) toàn bộ báo cáo của các ca tiếp theo trong ngày.
- **Bản chất kỹ thuật:**
  1. Trong Python `concurrent.futures.ThreadPoolExecutor`, các luồng worker sinh ra mặc định mang cờ `daemon = False`.
  2. Dù hàm chính kết thúc và gọi `sys.exit()` / `raise SystemExit()`, trình thông dịch Python chạy `threading._shutdown()` và bắt buộc đợi tất cả non-daemon thread kết thúc.
  3. Khi 1–2 máy gặp lỗi ADB/USB socket hoặc network hang, luồng con không thoát -> tiến trình mẹ bị kẹt vô hạn thành **zombie process**.

---

## 2. Kiến trúc 3 tầng bảo vệ (Tri-layer Hardening)

### Tầng 1: Worker Daemon Threads (`flows/multi_machine_feed_session.py`)
Ghi đè `_adjust_thread_count` trong `_FailClosedThreadPoolExecutor` để toàn bộ worker thread sinh ra đều mang thuộc tính `daemon = True`:
```python
class _FailClosedThreadPoolExecutor(ThreadPoolExecutor):
    """Do not make the outer watchdog wait for already-running child threads."""

    def _adjust_thread_count(self) -> None:
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

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self.shutdown(wait=False, cancel_futures=True)
        return None
```

### Tầng 2: Hard OS-Exit Guard (`python_runner/run_tiktok.py`)
Tại CLI entrypoint, sau khi finalize artifacts và release device locks, thoát thẳng ở cấp độ Kernel qua `os._exit(code)`:
```python
if __name__ == "__main__":
    try:
        _code = main()
    finally:
        sys.stdout.flush()
        sys.stderr.flush()
    if "pytest" in sys.modules:
        raise SystemExit(_code)
    import os
    os._exit(_code if isinstance(_code, int) else 0)
```
*Lưu ý:* Bắt buộc giữ guard `if "pytest" in sys.modules` để test suite khi chạy unit test không bị ngắt ngang.

### Tầng 3: Watchdog Circuit Breaker (`feed_session_watchdog.py`)
Trong hàm `is_feed_runner_active()`, bổ sung kiểm tra tuổi thọ tiến trình qua `create_time`:
```python
now_ts = time.time()
for p in psutil.process_iter(['name', 'cmdline', 'create_time']):
    try:
        if p.pid == my_pid:
            continue
        name = (p.info.get('name') or '').lower()
        if not name.startswith(('python', 'powershell', 'pwsh')):
            continue
        cmd = " ".join(p.info.get('cmdline') or []).lower()
        if any(pat in cmd for pat in runner_patterns):
            # Bỏ qua zombie runner đã chạy quá 2.5h (9000s)
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

## 3. Quy tắc kiểm thử focused (< 1s, né bẫy 100s import)
- **Bẫy:** Không được import `multi_machine_feed_session.py` trong unit test độc lập vì file này kéo theo `torch`, `cv2`, `ultralytics` (YOLO) làm test mất 70-130s dẫn đến worker subagent timeout 600s.
- **Giải pháp:** Viết test kiểm tra AST/string marker trên file đích, đồng thời kiểm tra hành vi `daemon=True` trên class executor mô phỏng độc lập. Chạy bằng `python <test_file>.py` trực tiếp trong < 0.1s.
