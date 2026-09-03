# CDP adb forward lifecycle (magic-link anchor probe)

Bug thật live STT30 2026-08-11 (serial `ce0217126cd4bc640c`), consumer
`D:\Taadaa\Tiktok_Reg\social_reg_v1.py`.

## Triệu chứng

```
[otp-magiclink] CDP tìm thấy tab Outlook
[otp-magiclink] CDP probe exception: ConnectionRefusedError
```
→ fail closed `OUTLOOK_MAGIC_LINK_ACTION_NOT_VERIFIED`, không tap được link
magic-link dù tab Outlook vẫn mở và CDP anchor rect flow hoàn toàn đúng.

## Root cause

`_outlook_magic_link_cdp_websocket_url(device_id)`:
1. mở `adb forward tcp:9224 -> localabstract:chrome_devtools_remote`,
2. query `http://127.0.0.1:9224/json`, tìm tab `outlook.live.com/mail`,
   trả `webSocketDebuggerUrl` (đã rewrite `localhost:9222`/`127.0.0.1:9222`
   → `127.0.0.1:9224`),
3. **`finally:` remove forward ngay trong chính hàm** (`adb forward --remove
   tcp:9224`).

Hàm gọi (`_outlook_magic_link_cdp_tap_target`) nhận được ws URL đã "chết":
probe kế tiếp `socket.create_connection(127.0.0.1:9224)` bị từ chối vì không
còn forward nào đứng sau port đó.

## Fix (đã merge, consumer-only)

Tách lifecycle thành 2 phần:

**(a) Mở forward + lấy websocket_url — KHÔNG remove:**
`_outlook_magic_link_cdp_websocket_url` giữ nguyên mở forward + `/json` +
rewrite port, nhưng BỎ block `finally` remove. Forward sống sau khi return.

**(b) Flow tự quản lifecycle:**
`_outlook_magic_link_cdp_tap_target` bọc toàn bộ body trong `try/finally`:

```python
local_port = _OUTLOOK_MAGIC_LINK_CDP_LOCAL_PORT
try:
    websocket_url = _outlook_magic_link_cdp_websocket_url(device_id)
    if not websocket_url:
        return None  # fail closed, vẫn qua finally
    # probe/scroll loop ... dùng websocket_url nhiều lần
    return {...}     # mọi return path đều qua finally
finally:
    try:
        AdbClient(adb_path=ADB_EXE, serial=device_id, default_timeout=10).run(
            ["forward", "--remove", f"tcp:{local_port}"], timeout=10)
    except Exception:
        pass
```

Nguyên tắc: **forward phải sống suốt toàn bộ CDP session (probe + scroll +
tap); remove đúng MỘT lần, ở hàm điều phối cao nhất, trong `finally`** — không
bao giờ ở helper tạo forward. Numeric path `_try_get_otp_outlook_cdp` giữ
nguyên (forward + remove trong cùng hàm là đúng vì nó dùng xong ngay trong
hàm); Gmail magic-link không đụng.

## Test pattern (quan trọng — bẫy GREEN giả)

Test đầu tiên viết với mock per-seam (mock `_cdp_evaluate` trả probe dict,
đếm call) **PASS cả trên code bug** — vì mock che mất `ConnectionRefusedError`
và đếm call không bắt được thứ tự. Phải assert THỨ TỰ trên một shared event
timeline:

```python
events = []  # timeline chung

def _fake_adb(log):
    class _FakeAdbClient:
        def __init__(self, *a, **k): pass
        def run(self, args, **k):
            log.append(("adb", list(args)))
            return _FakeAdbResult()  # ok=True
    return _FakeAdbClient

def _fake_cdp(ws, expr):
    events.append(("cdp", expr))
    return probe_dict

# assertions:
assert events[0] == ("adb", FORWARD_ARGS)            # mở forward trước
assert events[-1] == ("adb", REMOVE_ARGS)            # remove là bước cuối
assert events.count(("adb", REMOVE_ARGS)) == 1       # đúng 1 lần
cdp_idx = [i for i, e in enumerate(events) if e[0] == "cdp"]
assert cdp_idx == list(range(1, len(events) - 1))    # probe liên tục giữa
```

Mock `urllib.request.urlopen` trả context-manager có `.read()` (json.load đọc
từ đó); mock `AdbClient` (class, không phải instance) vì code gọi
`AdbClient(adb_path=..., serial=..., default_timeout=...).run(...)`.

## Verification

```bash
env -u PYTHONPATH /d/Taadaa/python-envs/automation/Scripts/python -m py_compile social_reg_v1.py
env -u PYTHONPATH /d/Taadaa/python-envs/automation/Scripts/python -m pytest \
  tests/test_login_outlook_magiclink_branch.py tests/test_login_magiclink_classify.py -q
git diff --check
```

Kết quả thật sau fix: py_compile exit 0, 34 passed (30 cũ + 4 test lifecycle
mới), git diff --check exit 0. KHÔNG live ADB/device trong task này.

## Files đụng (scope đúng)

- `social_reg_v1.py` — 2 hàm trên (bỏ finally-remove ở helper; thêm
  try/finally ở tap_target).
- `tests/test_login_outlook_magiclink_branch.py` — thêm `import json`, mock
  `AdbClient` vào `_mock_link_io` (vì tap_target giờ gọi AdbClient trong
  finally kể cả khi ws None), + 4 test lifecycle: `..._opens_forward_without_removing_it`,
  `..._probes_with_same_ws_and_removes_forward_once`,
  `..._forward_alive_through_scroll_loop`, `..._removes_forward_once_when_no_outlook_tab`.
- `docs/ui-compatibility.md` — entry `outlook-magiclink-branch-20260811` bổ
  sung mô tả forward lifecycle fix.
