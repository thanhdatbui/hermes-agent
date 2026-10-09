# Test Suite Side-Effect Isolation & Stale Telemetry Prevention (2026-09-24)

## Bối cảnh sự cố (Farm Telegram Spam)
- Khi chạy unit test `pytest tests/test_ensure_row_accounts.py`, hàm `run_tiktok_reg_for_machines([201], row=5)` được kích hoạt.
- Test case quên mock `send_telegram_summary`, dẫn tới việc Python bắn HTTP request POST thật tới nhóm Telegram `-5373649734`.
- Script nhặt trúng folder run cũ rích `20260924-060255` (Máy 76 lỗi lúc 6h sáng) ghép với tham số máy test `201`, gây ra tin nhắn rác bất thường.

## 3 Chốt chặn bất biến (Invariants)
1. **Hard Guard chặn HTTP notification trong môi trường Test:**
   ```python
   def send_telegram_summary(row: int, missing: list[int], rc: int, batch_start_time: datetime | None = None, disable_telegram: bool = False) -> bool:
       if disable_telegram or "pytest" in sys.modules or os.environ.get("PYTEST_CURRENT_TEST"):
           print("[telemetry] [TEST ENV] Skipped send_telegram_summary during test execution.")
           return False
   ```
2. **Mock triệt để notification trong Test Cases:**
   ```python
   def test_admin_adb_socket_telemetry(monkeypatch, capsys):
       monkeypatch.setattr(era, "send_telegram_summary", lambda *a, **kw: None)
       ...
   ```
3. **Time-gated Run Artifact Selection (Chống Zombie Summary):**
   - Tuyệt đối cấm bốc `dirs[0]` trần trụi khi không có run folder mới.
   ```python
   if batch_start_time is not None:
       min_ts = batch_start_time.timestamp() - 10
       dirs = [d for d in dirs if d.stat().st_mtime >= min_ts]
       if not dirs:
           print("[telemetry] No new run folder found since batch start. Skipping summary.")
           return False
   ```
