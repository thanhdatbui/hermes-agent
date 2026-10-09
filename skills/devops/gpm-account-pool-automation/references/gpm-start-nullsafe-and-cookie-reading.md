# GPM Local API Start & SQLite Cookie Reading Pitfalls

### 1. Null-safe GPM Start API Response
Khi gọi `/api/v3/profiles/start/{id}`, nếu profile gặp lỗi (ví dụ proxy lỗi, profile đang mở, hoặc port xung đột), API của GPM trả về:
```json
{
  "success": false,
  "message": "...",
  "data": null
}
```
**Pitfall:** Nếu code truy cập trực tiếp `res.get("data", {}).get("remote_debugging_address")` thì trong Python:
- `res.get("data", {})` sẽ trả về `None` (vì key `"data"` tồn tại với value `None`, default dictionary không được kích hoạt).
- `None.get(...)` ném ra `AttributeError: 'NoneType' object has no attribute 'get'`.

**Safe Pattern:**
```python
res = requests.get(f"{GPM_API_BASE}/profiles/start/{profile_id}?win_scale=0.8", timeout=30).json()
data = res.get("data") or {}
addr = data.get("remote_debugging_address")
if not addr:
    logger.error(f"GPM Start failed: {res.get('message')}")
    # handle error cleanly
```

---

### 2. Cookie SQLite Lock khi check Session (`copyfile` trước khi đọc)
File cookie Chrome của GPM nằm tại:
`C:\Users\Kibe\AppData\Local\Programs\GPMLogin\profile\<profile_path>\Default\Network\Cookies`

Nếu profile đang mở hoặc tiến trình Chromium nền chưa thoát hoàn toàn, SQLite sẽ bị lock file (`busy` hoặc `PermissionError`).
Đặc biệt trên Windows, mở trực tiếp `sqlite3.connect(f"file:{cookie_db}?mode=ro", uri=True)` vẫn có thể bị fail nếu tiến trình khác đang ghi WAL mode.

**Giải pháp chuẩn (Copy ra Temp DB):**
```python
import shutil
import tempfile
import sqlite3
import os

temp_db = os.path.join(tempfile.gettempdir(), f"gpm_cookie_check_{idx}.db")
try:
    shutil.copyfile(cookie_db, temp_db)
    conn = sqlite3.connect(f"file:{temp_db}?mode=ro", uri=True)
    cur = conn.cursor()
    cur.execute('SELECT COUNT(*) FROM cookies WHERE host_key LIKE "%google%" AND name = "SID"')
    has_sid = cur.fetchone()[0] > 0
    conn.close()
except Exception:
    has_sid = False
finally:
    if os.path.exists(temp_db):
        try:
            os.remove(temp_db)
        except Exception:
            pass
```

---

### 3. Playwright Automation trong Codex OAuth Flow
- Sau khi bấm "Continue with Google" từ màn hình đăng nhập OpenAI, cần đợi load state:
  ```python
  page.wait_for_load_state("load", timeout=15000)
  ```
- Kết hợp click locator và DOM fallback bằng `page.evaluate()` khi selector động không bắt được Account Chooser hoặc Authorize / Allow button.
- Luôn chụp ảnh debug trước khi thoát Playwright để có evidence chẩn đoán (lưu vào thư mục `debug_screenshots/`).
