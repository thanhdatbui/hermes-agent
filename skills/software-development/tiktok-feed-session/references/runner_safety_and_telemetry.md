# Runner Safety, Daemon Thread Pools & Watchdog Telemetry (Feed Session)

## 1. Fail-Closed Daemon Thread Pool & Private API Fallback
Khi tùy biến `ThreadPoolExecutor` để tạo daemon thread (nhằm tránh process bị treo bởi running child worker threads khi main exit/shutdown):
- `_adjust_thread_count` can thiệp vào internal private API của standard library (`_worker`, `_threads_queues`, `_idle_semaphore`).
- **Bắt buộc:** Bọc toàn bộ phần logic tạo daemon thread trong khối `try...except Exception as exc`.
- Nếu có lỗi phát sinh (ví dụ thay đổi internal signature giữa các bản Python hoặc test mock môi trường), ghi log `logger.warning(...)` và gọi fallback:
  ```python
  except Exception as exc:
      logging.getLogger("multi_machine_feed_session").warning(
          "_adjust_thread_count daemon customization fallback: %s", exc
      )
      super()._adjust_thread_count()
  ```
- Định nghĩa `__exit__` đảm bảo fail-closed: `self.shutdown(wait=False, cancel_futures=True)`.

## 2. Test Guard cho Process Termination (`os._exit` vs `SystemExit`)
- Trong các production runner (như `run_tiktok.py`), `os._exit(_code)` thường được gọi ở `__main__` để dọn dẹp triệt để các background thread treo hoặc blocking socket.
- Tuy nhiên, trong test suite (pytest/unittest), `os._exit` sẽ lập tức terminate toàn bộ test runner process, làm crash runner và mất báo cáo test.
- **Quy tắc Guard chuẩn:** Kiểm tra cả `sys.modules` lẫn environment variable của pytest:
  ```python
  if "pytest" in sys.modules or os.environ.get("PYTEST_CURRENT_TEST"):
      raise SystemExit(_code)
  import os
  os._exit(_code if isinstance(_code, int) else 0)
  ```

## 3. Telemetry & Error Visibility trong Watchdog (`feed_session_watchdog.py`)
- **Đo thời gian thực thi (Telemetry):** Các hàm kiểm tra tiến trình định kỳ (`is_feed_runner_active`) và duyệt file kết quả đệ quy (`parse_run_all`) phải được đo bằng `time.perf_counter()`.
  - Ghi log ở mức `DEBUG`: ví dụ `logger.debug("parse_run_all completed in %.4fs for %s (found %d machines)", elapsed, run_dir, count)`.
- **Cấm Silent `pass` trong vòng lặp parse:**
  - Thay vì `except Exception: pass`, hãy dùng `except Exception as err: logger.debug("parse_run_all detail error: %s", err)`.
  - Giữ cho terminal sạch nhưng vẫn cho phép chẩn đoán nguyên nhân khi parse JSON/text bị lỗi.
