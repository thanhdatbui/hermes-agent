# OmniRoute Browser Hook Hardening (ChatGPT-Web / Codex)

Patterns rút ra từ fix triệt để 3 điểm trong `codex_omniroute_hook.py` và `chatgpt_omniroute_hook.py`.

## 1. profile_started guard cho finally
- Vấn đề: `finally: stop profile` luôn chạy kể cả khi `start` fail → stop profile đang chạy của người khác / lỗi phụ.
- Fix:
```python
profile_started = False
try:
    start_res = requests.get(f'{GPM_API_BASE}/profiles/start/{profile_id}?...')
    if start_res.status_code != 200: return {...}
    addr = start_res.json().get('data', {}).get('remote_debugging_address')
    if not addr: return {...}
    profile_started = True
    ...
finally:
    if profile_started:
        try: requests.get(f'{GPM_API_BASE}/profiles/stop/{profile_id}', timeout=15)
        except Exception as e: logger.warning(...)
```
- Rule: chỉ set `True` sau khi có `remote_debugging_address`. Mọi `return` sớm trước đó sẽ skip stop.

## 2. Token format validation (fail-fast trước khi gọi OmniRoute)
- Codex access_token (JWT): `if not tok or len(tok) < 50 or not tok.startswith('ey'): return Invalid...`
- ChatGPT session cookie: `if not tok or len(tok) < 20: return Invalid...`
- Lợi ích: tránh import rác vào OmniRoute, tránh log token rác, lỗi rõ ràng thay vì 500 từ downstream.
- Luôn dùng message generic `Invalid or malformed ... format`, KHÔNG echo token vào error (dùng `redact_sensitive`).

## 3. Strict identity matching cho existing connection
- Cũ (sai): `email in c.get('name','')` → `test@example.com` match nhầm `othertest@example.com`.
- Mới:
```python
target = email.strip().lower()
for c in connections:
    if c.get('provider') != 'chatgpt-web': continue
    c_name = (c.get('name') or '').strip()
    c_email = (c.get('email') or '').strip().lower()
    if c_email == target or c_name == label or c_name.startswith(f"{email} ("):
        existing_conn = c; break
```
- Match theo thứ tự: email exact → name exact (`label = email (display)`) → prefix `email (`.

## 4. Verification ad-hoc (không có suite chính thức)
- Dùng `tempfile.NamedTemporaryFile(prefix='hermes-verify-', suffix='.py')` dưới `C:\Users\Kibe\AppData\Local\Temp`, mock `requests.get/put/post` + extractor, assert:
  - start fail → `get.call_count == 1`, không gọi stop.
  - token invalid → error message đúng + stop được gọi (`call_count == 2`).
  - strict match → `conn-target` được chọn, không nhầm `conn-other`.
- Chạy `python <tmp>`, xóa file sau khi xong, report là ad-hoc chứ không phải suite green.
