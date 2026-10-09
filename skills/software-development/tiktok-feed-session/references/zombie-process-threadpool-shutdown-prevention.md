# Chống Kẹt Zombie Process ThreadPoolExecutor & Nghẽn Watchdog Báo Cáo

## 1. Triệu chứng & Hiện tượng (Incident Symptoms)
- **Mất báo cáo ca nuôi acc:** Không thấy bot gửi báo cáo các phiên nuôi acc (Ca 1 Sáng, Ca 2 Chiều...) về Telegram dù các máy đã hoàn tất chạy từ lâu và thư mục artifact `D:/Taadaa/runtime/<cluster>/live/<date>/row-X-...` đã có đầy đủ `run_manifest.json` và `summary.txt`.
- **Tiến trình zombie treo ngầm:** Kiểm tra `ps -W | grep -i python` hoặc `Get-CimInstance Win32_Process` thấy các tiến trình `powershell.exe (run-feed-session.ps1)` và `python.exe (run_tiktok.py)` từ nhiều giờ trước (ví dụ 6h sáng) vẫn tồn tại trong Windows Task Manager nhưng CPU = 0%, không có kết nối mạng (`Get-NetTCPConnection`), và không giữ file lock.
- **Watchdog bị block:** Script `feed_session_watchdog.py` chạy mỗi 5 phút gọi `is_feed_runner_active()`. Vì thấy PID cũ vẫn tồn tại nên cờ `runner_busy = True` liên tục bật, khiến watchdog kìm hãm (suppress) toàn bộ báo cáo trong ngày vì tưởng ca chạy chưa kết thúc.

## 2. Nguyên nhân gốc rễ (Root Cause)
1. **Non-daemon worker threads trong Python `ThreadPoolExecutor`:**
   - Mặc định trong Python `concurrent.futures.thread.ThreadPoolExecutor`, các worker thread sinh ra là **non-daemon thread** (`daemon=False`).
   - Khi chạy batch 40–80 máy con qua ADB, nếu có máy bị kẹt socket USB/ADB không phản hồi khi watchdog huỷ (timeout/cancel), luồng worker đó vẫn bị kẹt trong lệnh gọi socket hệ điều hành.
2. **Interpreter shutdown hang:**
   - Khi hàm `main()` của `run_tiktok.py` chạy xong (đã ghi log, release locks, ghi summary) và kết thúc bằng `raise SystemExit(main())` hoặc `sys.exit(...)`, Python runtime thực hiện dọn dẹp nội bộ qua `threading._shutdown()`.
   - `threading._shutdown()` lặp qua toàn bộ non-daemon threads và gọi `.join()`. Do luồng ADB kẹt socket không bao giờ thoát, Python runtime bị treo vĩnh viễn tại bước shutdown.
   - Hậu quả: Tiến trình Python chính không bao giờ return mã exit cho PowerShell bọc ngoài (`run-feed-session.ps1`), biến cả 2 thành zombie process.

## 3. Kiến trúc 3 Tầng Khắc Phục Triệt Để (Tri-layer Hardening)

### Tầng 1: Luồng Worker Daemon (`_FailClosedThreadPoolExecutor`)
Ghi đè `_adjust_thread_count` trong class executor con để mọi worker thread sinh ra đều mang thuộc tính `daemon=True`:
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
Khi `daemon=True`, hàm `threading._shutdown()` của Python bỏ qua hoàn toàn các luồng worker này khi thoát.

### Tầng 2: Hard OS-Exit tại CLI Entrypoint (`run_tiktok.py`)
Tại entrypoint CLI, sau khi `main()` hoàn tất và flush stdout/stderr, gọi thẳng `os._exit(code)` ở cấp độ OS kernel để ngắt tiến trình tức thì, kèm guard an toàn cho pytest:
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

### Tầng 3: Watchdog Stale Process Filter (`feed_session_watchdog.py`)
Trong hàm `is_feed_runner_active()`, kiểm tra tuổi thọ tiến trình qua `p.create_time()`. Nếu tiến trình runner đã chạy quá 2.5 giờ (9000s - vượt xa ngưỡng 50-80 phút của 1 phiên nuôi bình thường), watchdog tự động đánh dấu là zombie, bỏ qua và giải phóng báo cáo cho các phiên tiếp theo:
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

## 4. Quy trình Cứu Hộ Hiện Trường Nhanh (Field Recovery Runbook)
1. **Phát hiện:** Khi user báo không thấy tin nhắn báo cáo phiên, kiểm tra runner process:
   ```powershell
   Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*run_tiktok*' -or $_.CommandLine -like '*run-feed-session*' } | Select-Object ProcessId, CreationDate, CommandLine
   ```
2. **Xác nhận zombie:** Xem folder artifact mới nhất trong `D:/Taadaa/runtime/<cluster>/live/<date>/`. Nếu file `run_manifest.json` đã có `end_time` và CPU tiến trình = 0% suốt nhiều giờ -> chính xác là zombie.
3. **Kill an toàn:**
   ```powershell
   Stop-Process -Id <PID1>, <PID2> -Force
   ```
4. **Kích hoạt gửi báo cáo bù ngay lập tức:**
   ```powershell
   python C:/Users/Kibe/AppData/Local/hermes/scripts/feed_session_watchdog.py
   ```
   Báo cáo tồn đọng sẽ ngay lập tức được đẩy về nhóm Telegram Farm.
