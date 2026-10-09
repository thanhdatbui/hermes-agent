# Stale proxy_pending marker gây WORKER_CRASH timeout 180s (09/09/2026)

## Triệu chứng
Phase 3 Add 2FA thất bại loạt với:
```
41 | 323 | m************* | failed | WORKER_CRASH: TimeoutError: proxy readiness timed out for ce031823f9b1903c01
```
Alert Telegram chỉ hiện **1 máy** (dòng cuối bảng) dù thực tế **11 máy** cùng lỗi:
- 08, 12, 14, 17, 20, 22, 24, 27, 35, 39, 41

## Giải mã alert log format

| Cột | Giá trị ví dụ | Ý nghĩa |
|-----|-------|---------|
| 1 | `41` | **Số máy** (Machine), KHÔNG phải STT đợt chạy |
| 2 | `323` | **source_row Excel** — row thực sự trong workbook |
| 3 | `m*************` | username bị mask |
| 4 | `failed` | status |
| 5 | `WORKER_CRASH: ...` | lý do |

Parser `parse_summary_line` quét ngược output từ dưới lên → chỉ bốc dòng cuối cùng làm alert Telegram.
Để xem toàn bộ máy lỗi: đọc log cron `C:\Users\Kibe\AppData\Local\hermes\cron\output\<job_id>\<date>.md`.

## Root Cause

File stale trong `.codex/device-readiness/`:
- Path: `C:\Users\Kibe\.codex\device-readiness\859cd1654e5bc969ec29ebca.json`
- Content: `{"serial": "ce031823f9b1903c01", "state": "proxy_pending", "updated_at": "2026-08-30T03:48:29..."}`
- Tồn đọng từ 30/08 (10 ngày cũ) — không có watcher nào cập nhật

`run_capture_phase_b.py` gọi `acquire_device_lock()` thiếu `bypass_proxy_readiness=True`.
→ automation-core kích hoạt `wait_for_proxy_ready(serial, timeout=180)`.
→ Hàm thấy file tồn tại, state=`proxy_pending`, poll 180s không thay đổi → ném `TimeoutError`.
→ Subprocess crash exit code 1, runner gán nhãn `WORKER_CRASH`.

## Hash readiness file từ serial
```python
import hashlib
sha = hashlib.sha256(serial.encode()).hexdigest()[:24]
# ce031823f9b1903c01 → 859cd1654e5bc969ec29ebca
```

## Fix chuẩn (commit d27fc02 + c3d141f)

### Fix 1 — `tiktok-add-bao-mat-f2a/python_runner/run_capture_phase_b.py`
```python
lease = acquire_device_lock(
    machine=cfg.machine, serial=cfg.serial,
    project="tiktok-add-bao-mat-f2a", command="phase-b-live",
    user_authorized=True,
    bypass_proxy_readiness=True,   # ← THÊM DÒNG NÀY
    allow_takeover=True,
    takeover_scope=os.environ.get("TAKEOVER_SCOPE", "OPERATOR_PREEMPT"),
    takeover_authorized=True,
    takeover_reason="operator live execution",
)
```
Lý do: Phase B runner đã có `require_android_vpn()` độc lập fail-closed. Proxy readiness handshake chỉ cần cho flow reboot/reconnect watcher.

### Fix 2 — `automation-core/src/automation_core/readiness.py`
Bổ sung helper + early-exit:
```python
def _is_stale_marker(current: dict | None, max_stale_seconds: float = 600) -> bool:
    if not current or not isinstance(current, dict):
        return False
    raw = current.get("updated_at")
    if not raw:
        return False
    try:
        updated = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        if updated.tzinfo is None:
            updated = updated.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - updated).total_seconds() > max_stale_seconds
    except Exception:
        return False

def wait_for_proxy_ready(serial, boot_id="", *, timeout=180, poll_interval=1,
                          max_stale_seconds=600, root=None, live_vpn_verifier=None):
    current = read_readiness(serial, root=root)
    # Bỏ qua stale proxy_pending marker (không có watcher active)
    if current and current.get("state") == "proxy_pending" and _is_stale_marker(current, max_stale_seconds):
        if live_vpn_verifier is None:
            return None
    ...
```

## Dọn stale markers

```python
import glob, json, os
from datetime import datetime, timezone, timedelta

p = os.path.expanduser("~/.codex/device-readiness")
cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
deleted = []
for f in glob.glob(p + "/*.json"):
    try:
        data = json.load(open(f))
        if data.get("state") == "proxy_pending":
            updated = datetime.fromisoformat(data["updated_at"].replace("Z", "+00:00"))
            if updated < cutoff:
                os.unlink(f)
                deleted.append(f)
    except Exception:
        pass
print(f"Deleted {len(deleted)} stale files")
```

## Kiểm tra nhanh phân phối state hiện tại
```python
import glob, json, os
p = os.path.expanduser("~/.codex/device-readiness")
counts = {k: sum(1 for f in glob.glob(p+"/*.json") if json.load(open(f)).get("state")==k)
          for k in ["proxy_ready", "proxy_pending", "proxy_failed"]}
print(counts)
# Expected: proxy_pending < 5 (chỉ các máy đang thực sự chờ watcher)
```

## Test verification
```bash
# Phase B runner tests
cd D:/Taadaa/tiktok-add-bao-mat-f2a
pytest python_runner/tests/test_run_capture_phase_b.py -o cache_dir=/tmp/.pytest_cache
# → 5/5 passed

# Readiness tests
cd D:/Taadaa/automation-core
pytest tests/test_readiness.py -o cache_dir=/tmp/.pytest_cache
# → 8/8 passed

# Probe lock máy target (không còn 180s delay)
python -c "from core.device_lock import acquire_device_lock; lease = acquire_device_lock(machine=41, serial='ce031823f9b1903c01', project='tiktok-add-bao-mat-f2a', command='test', user_authorized=True, bypass_proxy_readiness=True); print('OK'); lease.finish(succeeded=True)"
```
