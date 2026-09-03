# ATX session primary capture — implementation detail (automation-core 0.4.46, commit e57436b, 2026-08-17)

Session log đầy đủ của việc implement tầng ATX session dump trong `automation-core`
(worktree sạch trên master, KHÔNG dùng branch riêng — commit thẳng vì repo này cho phép).

## Kiến trúc 3 tầng mới trong `ui.py::try_persistent`

1. **ATX session** (`persistent_ui.capture_atx_session_ui`, `CaptureBackend.ATX_SESSION="atx_session"`)
   — PRIMARY. Timeout cap 15s (`min(float(timeout), 15.0)`), `restart_attempts=0` (không restart lần 1;
   primary fail nhanh để rơi xuống persistent).
2. **Persistent cũ** (`capture_persistent_ui` → `/jsonrpc/0`, backend `"persistent"`) — fallback, không đổi.
3. Shell uiautomator + file fallback — nguyên vẹn phía sau.

Cả 2 tầng đều dùng chung `DEFAULT_CIRCUIT_BREAKER` nhưng KEY RIÊNG (PERSISTENT vs ATX_SESSION) — một
backend open circuit không chặn backend kia. Transport failure ở BẤT KỲ tầng nào → `final_block_transport`
ngay (không xuống shell). Provisioning policy (`REQUIRE_PROVISIONED`) áp cho cả 2.

`_dump_current_ui_lightweight` (lightweight path) CHƯA được chuyển — chỉ `_dump_current_ui_unlocked`
(full machinery) dùng session tier. Lightweight giữ persistent-first cũ (không gây lệch — consumer
heavy dùng full path).

## Các hàm mới trong `persistent_ui.py`

- `capture_atx_session_ui(adb, *, timeout=60, restart_attempts=0) -> PersistentCaptureResult` — public API.
- `_session_dump_attempt(...)` — loop attempt: `_ensure_atx_server_running` → `_ensure_forward` →
  `_discover_session_pid` → POST `/session/<pid>:com.github.uiautomator/jsonrpc/0`
  `{"jsonrpc": "2.0", "id": "automation-core-ui-dump", "method": "dumpWindowHierarchy", "params": [true]}`.
  `restart_attempts=N` → chạy N+1 attempt; attempt >1 `service_restart=True` (stop/start agent).
- `_ensure_atx_server_running` — chỉ chạy `atx-agent server -d` khi `_capability` báo agent process
  chưa chạy (`agent_running=False`). Agent chạy sẵn → skip (no-op). KHÔNG pkill (primary path).
- `_ensure_forward` — `forward --list` rồi: đã có `tcp:7912→tcp:7912` → reuse (entry `forward="existing"`);
  chưa có → `forward tcp:7912 tcp:7912` (entry `forward="created"`). Trả `7912`. KHÔNG remove forward.
- `_discover_session_pid` — `ps -A`: exact ` com.github.uiautomator ` (space-wrap) ưu tiên; `.test` chỉ khi
  KHÔNG có exact; đúng 1 candidate → pid; 0 hoặc nhiều → `ATX_SESSION_STUB_NOT_RUNNING` fallback.
- `_pid_of(marker, ps_stdout)` — split line, trả parts[1].
- `_dump_session_ui(...)` — compat string adapter `(xml, attempts)`.
- `_capability` — MỚI thêm probe `ps -A` cho `agent_process.agent_running`; `available` giờ = binary OK +
  packages OK (không cần process chạy — trên-demand start). Log entry `agent_started_on_demand=True` khi
  binary+package có mà process chưa chạy.

## Session path chính xác

`/session/20242:com.github.uiautomator/jsonrpc/0` — format: `/session/<pid>:<package>/jsonrpc/0`.
Dấu hai chấm giữa pid và package là BẮT BUỘC. PID lấy từ `ps -A` của `com.github.uiautomator`.

## Constants mới

```python
ATX_SESSION_JSONRPC_PATH = "/jsonrpc/0"
ATX_SESSION_DUMP_METHOD = "dumpWindowHierarchy"
ATX_UI_AUTOMATOR_PACKAGE = "com.github.uiautomator"
ATX_AGENT_MARKER = "atx-agent"
DEFAULT_ATX_SESSION_PORT = 7912
```

`ui_capture.py`: `CaptureBackend.ATX_SESSION = "atx_session"` (StrEnum, thêm sau REBOOT — test
`test_device_lock_preserves_legacy_positional_parameter_order` không liên quan vì không phải DeviceLock).

## Catalog test

- `tests/test_persistent_ui.py` +5 test mới: session primary đoán đúng session path + request payload
  (params [true], port 7912); reuse forward (không `forward --remove`); stub missing → UNHEALTHY +
  `ATX_SESSION_STUB_NOT_RUNNING`; retry (`service_restart` [False, True] + `atx-agent server -d` gọi 1 lần);
  transport (device offline) → UNAVAILABLE.
- `tests/test_ui_capture_state_machine.py::test_replay_...serial_disappears...` — PHẢI patch thêm mock
  `capture_atx_session_ui` → `PersistentCaptureResult(None, UNAVAILABLE, ...)` vì session tier chạy ADB thật
  trước mock persistent → `len(shell_calls)` tăng → assert `== adb_calls_before_transport_loss` fail.
- Full suite: baseline 572 pass / 3 fail (pre-existing: `test_startup` + 2 `test_tiktok_popup`) →
  sau patch 579 pass / 1 fail (chỉ còn `test_startup` pre-existing; 2 tiktok_popup fail tự hết vì không liên
  quan? KHÔNG — chúng vẫn pre-existing nhưng count thay đổi do +5 tests mới: 572+5=577... thực tế 579 = 572 +
  5 tests mới + 2 tiktok_popup pass?). Ghi chú: count cuối 579 pass + 1 fail `test_startup`; chứng minh
  pre-existing bằng `git stash` lúc baseline.

## Pitfalls CRLF (lặp lại mỗi lần sửa core)

- `file <path>` báo "CRLF, CR line terminators" = file HỎNG (double CRLF) — `git checkout -- <file>` rồi
  làm lại với normalize 1 lần CUỐI CÙNG (`text.replace("\n","\r\n")` sau khi đã edit LF).
- `patch` tool fuzzy matcher re-indent CRLF block → dùng python script edit với `assert old in text` từng
  hunk + `ast.parse()` + 1 normalize cuối. KHÔNG normalize 2 lần (double blank lines).
- Ghi file UTF-8 (tiếng Việt trong 1 file) — `path.write_bytes(text.encode("utf-8"))`; ASCII-only file thì
  giữ ASCII.

## PYTHONPATH pitfall tái khẳng định

`PYTHONPATH=.` từ repo root KHÔNG import `src/` (package nằm trong `src/automation_core/`) — import từ
site-packages STATIC COPY (`D:\Taadaa\python-envs\automation\Lib\site-packages\automation_core`). Vì task
bắt buộc chạy `PYTHONPATH=.`, phải SYNC src → site-packages:
`shutil.copytree(src, dst, dirs_exist_ok=True)` trước khi chạy suite. Bằng chứng: probe
`python -c "import automation_core; print(automation_core.__file__)"`.