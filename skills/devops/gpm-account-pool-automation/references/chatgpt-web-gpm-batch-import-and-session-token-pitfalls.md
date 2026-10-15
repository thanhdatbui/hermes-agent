# ChatGPT Web: GPM Batch Import & Session-Token Detection Pitfalls

## Tình huống
Nạp danh sách tài khoản Gmail/Hotmail từ GPM vào OmniRoute pool `chatgpt-web-pool`:
- GPM profile khởi động → Playwright CDP → `https://chatgpt.com/` → trích xuất session-token → ghi vào `storage.sqlite`.

---

## Pitfall 1: Phát hiện token sai (eyJhbG cheat-check)

### Vấn đề
Hàm `extract_session_token()` cũ kiểm tra bất kỳ cookie nào có value bắt đầu `eyJhbG` là đủ. Nhưng `https://auth.openai.com` cũng set cookie JWT (`oai-did`, `__cf_bm`, `auth0`) dù chưa login, khiến script báo "LẤY TOKEN THÀNH CÔNG" sai.

### Fix chuẩn
```python
def extract_session_token(context):
    try:
        all_c = context.cookies(['https://chatgpt.com', 'https://auth.openai.com'])
    except Exception:
        return None
    # BẮT BUỘC: phải có tên cookie chứa 'session-token'
    has_token = any('session-token' in (c.get('name') or '') for c in all_c)
    if has_token:
        return '; '.join(f'{c["name"]}={c["value"]}' for c in all_c)
    return None
```

Cookie session-token thật của ChatGPT web:
- Name: `__Secure-next-auth.session-token` (hoặc `.0`/`.1` nếu chunked).
- Độ dài: 3.000–12.000 ký tự.
- Phân biệt với JWT rác: **bắt buộc check `'session-token' in cookie_name`**.

---

## Pitfall 2: age-input fill block khi đang navigate

### Vấn đề
Trang `chatgpt.com/about-you` (onboarding age) trả về page redirect (`api/auth/callback`) khi đang fill `age_inp`. Playwright ném `Locator.fill: Timeout 30000ms exceeded` vì element bị detach trước khi enabled.

### Fix
Wrap trong try/except với `timeout=2000`. Sau bất kỳ hành động nào trong login loop, kiểm tra `extract_session_token(context)` ngay, nếu có thì `break` ngay lập tức:

```python
for step in range(35):
    token = extract_session_token(context)
    if token:
        logger.info(f"Token lấy thành công ở step {step}")
        break
    cur_url = page.url
    if 'about-you' in cur_url:
        try:
            age_inp = page.locator('input[name="age"]').first
            age_inp.fill("24", timeout=2000)
        except Exception:
            pass
        ...
    time.sleep(1)
```

---

## Pitfall 3: Proxy username không khớp với port

### Vấn đề
OmniRoute `proxy_registry` chứa sai username (ví dụ `mobi28` cho tất cả các port). Khi gọi `test.taadaa.click:5104` với user `mobi28` → HTTP 407 → `[Proxy Fast-Fail] Proxy unreachable`.

### Quy tắc port → username
```
Port 5101 → username mobi1
Port 5104 → username mobi4
Port 5108 → username mobi8
Port 5128 → username mobi28
General: username = 'mobi' + str(port - 5100)
```

Kiểm tra trong `proxy_registry`:
```sql
SELECT host, port, username FROM proxy_registry WHERE host='test.taadaa.click';
```

SQL fix hàng loạt nếu bị sai:
```python
for row in cur.fetchall():
    port = row['port']
    if 5101 <= port <= 5138:
        correct_user = f"mobi{port - 5100}"
        cur.execute("UPDATE proxy_registry SET username=? WHERE host='test.taadaa.click' AND port=?",
                    (correct_user, port))
```

---

## Pitfall 4: OmniRoute cache in-memory combo sau khi sửa SQLite

### Vấn đề
OmniRoute (Next.js) cache cấu hình combo trong RAM. Thay đổi `storage.sqlite` trực tiếp không có hiệu lực ngay, combo vẫn dùng danh sách cũ → "Maximum combo retry limit reached" / 503.

### Fix
Sau khi sửa SQLite (add/remove accounts, sửa model, sửa proxy) → BẮT BUỘC restart OmniRoute để xóa cache:

```python
import psutil
for p in psutil.process_iter(['pid', 'name', 'cmdline']):
    cmd = ' '.join(p.info.get('cmdline') or [])
    if 'run-next.mjs' in cmd:
        p.kill()
        break
# Watchdog sẽ tự restart sau 20–60s
```

Probe health sau restart:
```
GET http://127.0.0.1:20129/api/health → {"status":"ok"}
```

---

## Pitfall 5: Hotmail profile đã có session-token sẵn trong GPM

### Phát hiện
Nhiều profile Hotmail trong kho GPM đã từng đăng nhập ChatGPT trước đó và cookie `__Secure-next-auth.session-token` vẫn còn hạn dài (đến 2027). Chỉ cần mở GPM profile → `https://chatgpt.com/` → check cookie ngay mà không cần re-login.

### Script Check nhanh
```python
async def check_hotmail_logged_in(pid, profile_pid):
    cdp_addr = start_gpm(profile_pid)
    ...
    await page.goto("https://chatgpt.com/", timeout=30000, wait_until="domcontentloaded")
    await asyncio.sleep(5)
    cookies = await context.cookies(["https://chatgpt.com", "https://auth.openai.com"])
    st = next((c for c in cookies if "session-token" in c.get("name", "")), None)
    if st:
        print(f"ALREADY_LOGGED_IN: token len={len('; '.join(f'{c[\"name\"]}={c[\"value\"]}' for c in cookies))}")
        return True
    return False
```

---

## Pattern nạp batch vào OmniRoute storage.sqlite (Fail-Closed)

1. `proxy_assignments` (`scope='account'`, `scope_id=connection_id`) INSERT trước `is_active=1`.
2. Username proxy = `mobi{port - 5100}`, password = `TaadaaMobi#2026!`.
3. Model trong combo = `chatgpt-web/auto` (vì tài khoản Free chỉ nhận slug `auto`).
4. Khi có session-token → chụp ảnh Gate 6 → lưu `debug_screenshots/chatgpt_proof_{email_prefix}.png`.
5. Sau khi sửa DB → restart OmniRoute.
6. Probe cuối cùng trực tiếp vào connection ID và cả combo trước khi báo xong.

---

## Account types trong GPM có ChatGPT session

- **Gmail (Free):** `@gmail.com` — models: `auto` (GPT-5.6 Luna). Script `batch_rescue_chatgpt_web_16accs.py`.
- **Hotmail:** `@hotmail.com` — cần check xem cookie còn sống không (nhiều profile đã login sẵn). Script `batch_import_hotmail_chatgpt.py`.
- Cả hai đều dùng `chatgpt-web/auto` làm model trong combo (Free tier).

---

## Lệnh kiểm tra pool nhanh

```python
# Probe combo chatgpt-web-pool
import urllib.request, json, time
start = time.time()
req = urllib.request.Request(
    'http://127.0.0.1:20129/v1/chat/completions',
    headers={'Content-Type': 'application/json'},
    data=json.dumps({'model': 'chatgpt-web-pool', 'messages': [{'role': 'user', 'content': 'PING'}]}).encode(),
    method='POST'
)
with urllib.request.urlopen(req, timeout=40) as r:
    resp = json.loads(r.read().decode())
    print(f"HTTP {r.status} in {time.time()-start:.1f}s | {resp['choices'][0]['message']['content']}")
```

Expected: HTTP 200 trong ~15–35s, model field = `auto`.
