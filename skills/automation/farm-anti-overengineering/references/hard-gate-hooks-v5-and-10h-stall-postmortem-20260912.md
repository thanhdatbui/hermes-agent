# Hard Gate Hooks v5 & 10-Hour Stall Post-Mortem (12/09/2026)

## Bối cảnh
Farm Alert M33 "profile username still mismatched after switch" xử lý từ 13h23 đến nửa đêm (>10 tiếng).
Tất cả rule prompt và 3 hook trước đó hoàn toàn bất lực. Root cause và 3 hook mới được thêm sau phiên này.

---

## 3 Nguyên nhân gốc rễ làm treo phiên

### 1. Broad Grep Timeout (Bẫy quét đĩa diện rộng)
Coordinator chạy nhiều lần:
```
grep -rn "192.168.110" D:/Taadaa           # timeout 180s
grep -rn "20001" D:/Taadaa                 # timeout 180s
grep -rn "dismiss_network_error..." D:/Taadaa  # timeout 180s
```
Mỗi lệnh trúng .ai-runs / python-envs / BACKUP_ALL → terminal treo 180s.
**Tổng thiệt hại: >5 lần × 180s = >15 phút chết cứng.**

**Fix → Hook #4 `guard_broad_grep.py`** (xem bên dưới).

### 2. Synchronous Canary Timeout (Canary đồng bộ chặn session)
Coordinator gọi canary foreground:
```python
terminal("powershell.exe ... run-feed-session.ps1 -Machines 33 ...", timeout=240)
terminal("powershell.exe ... run-feed-session.ps1 -Machines 33 ...", timeout=300)
```
Khi máy 33 gặp lỗi mạng → script chạy auto_login_recovery 3-5 phút → terminal timeout 240s.
Session Coordinator **đóng băng hoàn toàn**, không làm được gì khác.

**Fix → Hook #5 `guard_canary_timeout.py`** (xem bên dưới).

### 3. Fake Compliance / Analysis Paralysis
Coordinator điền đủ 3 token `FILE:`, `SCOPE:`, `FOCUSED_TEST:` nhưng goal thực là:
> "Kiểm tra và hoàn thiện logic…"

Worker nhận → dùng hết 15 tool calls đọc code và lên kế hoạch → **0 dòng code ghi xuống đĩa**.
3 worker đầu bị burn hoàn toàn trước khi patch được thực thi (worker 4 mới patch).

**Fix → Nâng cấp Guard #3 `guard_dispatch_contract.py`** yêu cầu `OLD_STRING:` / `NEW_STRING:`.

### 4. Incidental Proxy Sidetrack
M33 bị gán sai port: `192.168.110.2:10001` (MikroTik, cần auth) thay vì `192.168.110.2:20033` (sing-box mixed, có auth tích hợp).
Coordinator mất nhiều lượt thử nghiệm proxy trực tiếp thay vì tra mapping file.

**Rule: Proxy farm mapping = port 20000 + machine_number** (M1=20001, M33=20033, ...). Xác nhận bằng ADB `settings get global http_proxy`.

---

## 5 Hard Gate Hooks hiện tại (sau phiên này)

| # | File | Chặn gì |
|---|------|---------|
| 1 | `guard_read_file_size.py` | read_file > 10MB |
| 2 | `guard_pytest_scope.py` | pytest quét toàn repo |
| 3 | `guard_dispatch_contract.py` | dispatch thiếu FILE/SCOPE/FOCUSED_TEST hoặc task fix thiếu OLD_STRING/NEW_STRING |
| 4 | `guard_broad_grep.py` | grep -r/-rn vào D:/Taadaa root, .ai-runs, runtime, python-envs |
| 5 | `guard_canary_timeout.py` | run-feed-session.ps1 / run_tiktok chạy foreground timeout > 90s |

---

## Hook #4: `guard_broad_grep.py` (drop-in)

```python
"""
[HERMES HARD GATE #4] Chặn grep diện rộng và recursive scan vào thư mục cấm.
"""
import json, sys, re

DANGEROUS_TARGETS = [
    r'D:[\\/]?$',
    r'D:[\\/]Taadaa[\\/]?$',
    r'D:[\\/]CodexRuntime',
    r'\.ai-runs',
    r'runtime[\\/]kibe',
    r'python-envs',
    r'BACKUP_ALL',
    r'node_modules',
]

try:
    payload = json.load(sys.stdin)
except Exception:
    sys.exit(0)

tool_name = payload.get("tool") or payload.get("tool_name") or ""
args = payload.get("args") or {}

if tool_name == "terminal":
    cmd = args.get("command") or ""
    is_recursive_grep = bool(re.search(r'\bgrep\s+-[a-zA-Z]*[rR]', cmd))
    is_find_wide = bool(re.search(r'\bfind\s+[\'"]?(?:D:[\\/]|D:[\\/]Taadaa|\.)', cmd))

    if is_recursive_grep or is_find_wide:
        for target in DANGEROUS_TARGETS:
            if re.search(target, cmd, re.IGNORECASE):
                msg = (
                    f"[HARD GATE #4] CHẶN quét đĩa diện rộng. "
                    f"CẤM grep -r vào root/.ai-runs/runtime/python-envs (gây Timeout 180s-900s)!\n"
                    f"Dùng: grep -n 'PATTERN' D:/Taadaa/path/to/exact_file.py"
                )
                print(json.dumps({"action": "block", "message": msg}))
                sys.exit(0)
        if is_recursive_grep and "--exclude" not in cmd and "--include" not in cmd:
            print(json.dumps({"action": "block", "message": "[HARD GATE #4] grep -r không giới hạn file bị chặn."}))
            sys.exit(0)

if tool_name == "search_files":
    path = args.get("path") or ""
    if args.get("target") == "content":
        for target in DANGEROUS_TARGETS:
            if re.search(target, path, re.IGNORECASE):
                print(json.dumps({"action": "block", "message": f"[HARD GATE #4] search_files path '{path}' bị chặn."}))
                sys.exit(0)

sys.exit(0)
```

---

## Hook #5: `guard_canary_timeout.py` (drop-in)

```python
"""
[HERMES HARD GATE #5] Chặn Canary PowerShell chạy foreground với timeout > 90s.
"""
import json, sys, re

try:
    payload = json.load(sys.stdin)
except Exception:
    sys.exit(0)

tool_name = payload.get("tool") or payload.get("tool_name") or ""
if tool_name != "terminal":
    sys.exit(0)

args = payload.get("args") or {}
cmd = args.get("command") or ""
timeout = args.get("timeout")

is_canary_cmd = bool(re.search(r'\b(?:run-feed-session|run_tiktok|run-follow)\.ps1\b', cmd, re.IGNORECASE))

if is_canary_cmd and (timeout is None or timeout > 90):
    msg = (
        f"[HARD GATE #5] CANARY FOREGROUND TIMEOUT={timeout}s BỊ CHẶN!\n"
        f"BẮT BUỘC: terminal(command='...', timeout=90) hoặc background=True, notify_on_complete=True.\n"
        f"Lý do: Khi máy gặp lỗi auto_login_recovery chạy 3-5 phút làm session Coordinator đóng băng."
    )
    print(json.dumps({"action": "block", "message": msg}))
```

---

## Guard #3 nâng cấp: chặn Fake Compliance

Bổ sung kiểm tra sau khi đã có đủ 3 token cơ bản:
- Nếu goal chứa từ "fix", "sửa", "patch", "chỉnh" → BẮT BUỘC có `OLD_STRING:` / `NEW_STRING:` / `PATCH_CONTRACT:`
- Nếu goal chứa cụm "tự tìm", "tự phân tích", "kiểm tra và hoàn thiện", "nghiên cứu codebase" → BLOCK ngay

---

## Quy tắc proxy mapping Kibe farm
- Port 20000 + machine_number: M1=20001, M2=20002, ..., M33=20033, M80=20080
- Verify: `adb -s SERIAL shell "settings get global http_proxy"` → `192.168.110.2:200XX`
- Test liveness: `adb shell "toybox nc -w 3 192.168.110.2 200XX </dev/null && echo OPEN || echo CLOSED"`
- Port 10001-10007 = Kibe 14 máy đi thẳng MikroTik (cần auth riêng, Android xử lý tự động)
- Port 20001-20080 = sing-box mixed inbound → route qua MikroTik có auth tích hợp
- Khi M33 baseline fail "network error": kiểm tra xem port có phải 20033 không trước khi debug code

---

## Canary Workflow chuẩn (không block session)

```python
# SAI - block session 240s:
terminal("powershell.exe run-feed-session.ps1 -Machines 33 ...", timeout=240)

# ĐÚNG - timeout tối đa 90s:
terminal("powershell.exe run-feed-session.ps1 -Machines 33 ...", timeout=90)
# Hoặc background:
terminal("powershell.exe run-feed-session.ps1 ...", background=True, notify_on_complete=True)
# Sau đó poll log:
terminal("tail -n 20 D:/Taadaa/.../.ai-runs/LATEST/machines/machine_33/.../log.jsonl")
```

---

## Bước debug proxy khi baseline fail "network error" (O(1))
1. `adb -s SERIAL shell "settings get global http_proxy"` → kiểm tra port
2. Nếu sai port → `adb -s SERIAL shell "settings put global http_proxy 192.168.110.2:200XX"`
3. Force-stop TikTok: `adb -s SERIAL shell "am force-stop com.ss.android.ugc.trill"`
4. Chạy lại canary: `run-feed-session.ps1 -Machines N -Row R -RecoveryTestSwipes 1 -SkipAccountWorkbookSync -Run` (timeout=90s)

**Không cần grep đĩa, không cần đọc workbook, không cần probe proxy từ PC (PC không có auth Android proxy).**
