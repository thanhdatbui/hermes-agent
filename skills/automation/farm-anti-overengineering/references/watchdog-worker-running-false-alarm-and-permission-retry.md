# Khắc phục Báo động giả Watchdog ở Phase WORKER_RUNNING, Windows PermissionError Retry & Lock Acquisition Logging

References:
- Audit Claude Opus Vòng 3 (06/09/2026).
- Script: `C:/Users/Kibe/AppData/Local/hermes/scripts/hermes_stale_watchdog.py` và `D:/Taadaa/Hermes/deploy/hermes-home/scripts/hermes_stale_watchdog.py`.
- Plugin: `C:/Users/Kibe/AppData/Local/hermes/plugins/farm-coordinator-guard/__init__.py` và `D:/Taadaa/Hermes/deploy/hermes-home/plugins/farm-coordinator-guard/__init__.py`.

---

## 1. Bối cảnh & Nguyên nhân Báo động giả (Blocker #2)

### Hiện tượng
Khi Coordinator dispatch subagent worker (ví dụ sửa code hoặc chạy canary), trạng thái Coordinator chuyển sang `phase = "WORKER_RUNNING"`.
Coordinator dừng gọi tool và chờ worker hoàn tất (có thể kéo dài 10–15 phút).
Lúc này, trong `watchdog_state.json`:
- Session Coordinator (`sid`) có `last_beat` dừng lại ở thời điểm gọi `delegate_task`.
- Watchdog định kỳ quét `phase_sessions.items()`:
  Trước đây, watchdog lấy `w_state = watchdog_sessions.get(sid)` của chính Coordinator. Sau 10 phút (600s), watchdog thấy Coordinator im lặng nên bắn cảnh báo treo giả (`⚠️ [CẢNH BÁO HERMES TREO]`), dù thực tế worker con vẫn đang làm việc bình thường hoặc Coordinator đang chờ hợp pháp!

### Giải pháp khắc phục triệt để
Khi duyệt session `sid` có `phase == "WORKER_RUNNING"`:
1. **Ưu tiên quét child session trước:**
   ```python
   child_candidates = [
       (csid, cstate) for csid, cstate in watchdog_sessions.items()
       if isinstance(cstate, dict) and cstate.get("parent_session_id") == sid
   ]
   ```
2. **Nếu CÓ child session:**
   - Sắp xếp lấy child session mới nhất:
     ```python
     child_candidates.sort(
         key=lambda pair: pair[1].get("current_tool_start") or pair[1].get("last_beat") or 0,
         reverse=True,
     )
     matched_sid, w_state = child_candidates[0]
     ```
   - Lấy `current_tool_start` hoặc `last_beat` của chính worker để giám sát tiến độ thực tế của worker.
   - Ngưỡng chờ: 1500s (25m) nếu `is_canary=True`, 600s (10m) nếu tool thường.
3. **Nếu CHƯA CÓ child session (worker mới spawn hoặc chưa kịp gọi tool đầu tiên):**
   - Không lấy beat cũ của Coordinator.
   - Tính thời gian trễ từ thời điểm dispatch: `elapsed = max(0.0, now - d_at)`.
   - Ngưỡng chờ mở rộng thành: `threshold = WORKER_TIMEOUT_SECONDS = 1200.0` (20 phút, khớp trần timeout của FSM worker).
   - Đảm bảo tuyệt đối không bao giờ báo động giả trước khi worker dùng hết ngân sách 20 phút.
4. **Khi `phase == "ALERT"`:**
   - Coordinator trực tiếp ở hiện trường, áp dụng ngưỡng 600s theo dõi beat của Coordinator bình thường.

---

## 2. Windows PermissionError Retry khi đọc JSON (Major #3)

### Vấn đề
Trên hệ điều hành Windows, khi plugin ghi file `watchdog_state.json` hoặc `farm_coordinator_phase.json` atomic bằng cơ chế ghi file tạm rồi gọi `os.replace(tmp, path)`:
Nếu tiến trình watchdog `hermes_stale_watchdog.py` đọc đúng khoảnh khắc `os.replace` đang giữ file lock ở cấp OS kernel, Windows ném lỗi `PermissionError: [WinError 5] Access is denied` hoặc `OSError`. Nếu chỉ bắt exception chung chung và trả về `{}` ngay lần đầu, watchdog sẽ bỏ sót chu kỳ kiểm tra hoặc xóa nhầm cache.

### Giải pháp
Bọc vòng lặp retry 3 lần kèm độ trễ ngắn 50ms trong `_load_json`:
```python
def _load_json(path: Path) -> dict:
    for attempt in range(3):
        try:
            if not path.is_file():
                return {}
            with open(path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if not content:
                    return {}
                data = json.loads(content)
                return data if isinstance(data, dict) else {}
        except (PermissionError, OSError):
            if attempt < 2:
                time.sleep(0.05)
                continue
            return {}
        except Exception:
            return {}
    return {}
```

---

## 3. Cảnh báo Timeout Lock thay vì Degrade Im lặng (Major #4)

### Vấn đề
Trong `farm-coordinator-guard/__init__.py`, context manager `_watchdog_lock()` thử tạo lock file độc quyền `WATCHDOG_LOCK_FILE` trong 2.0s deadline.
Nếu hết deadline mà vẫn không lấy được lock (`fd is None`), code cũ bỏ qua và `yield` trực tiếp mà không để lại dấu vết gì, gây khó khăn cho việc debug khi có hiện tượng contention/deadlock.

### Giải pháp
Kiểm tra `if fd is None:` và ghi log cảnh báo rõ ràng trước khi `yield`:
```python
    if fd is None:
        logger.warning("[FARM_GUARD] Timeout acquiring watchdog lock (%s), proceeding without lock", WATCHDOG_LOCK_FILE)
    try:
        yield
    finally:
        ...
```

---

## 4. Float Casting An toàn (Minor #5)

Tránh crash do sai kiểu dữ liệu khi `dispatched_at` hoặc `updated_at` bị lưu dạng string hoặc None trong JSON:
```python
d_at = float(sdata.get("dispatched_at", 0) or sdata.get("updated_at", 0) or 0)
```
