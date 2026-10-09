# Khởi Chạy Profile GPMLogin Trực Tiếp Bằng Playwright Persistent Context

Kỹ thuật bỏ qua Local API GPM (`/profiles/start/{id}` + CDP port) để chạy trực tiếp Playwright persistent context với lõi Chromium của GPMLogin.

---

## 1. Ưu Điểm So Với GPM Local API CDP
- **Không phụ thuộc port/API GPM**: Không lo API port 19995 bị nghẽn, trả về timeout hoặc remote debugging port bị xung đột.
- **Tốc độ khởi tạo nhanh**: `launch_persistent_context` gắn trực tiếp vào thư mục profile, không qua bước trung gian scale cửa sổ/spawn tiến trình của GPM app.
- **Tự động quản lý vòng đời**: Đóng browser context sạch sẽ khi xong hoặc gặp lỗi qua `browser.close()`, không cần `stop_and_kill_gpm_profile` phức tạp.

---

## 2. Đường Dẫn Chuẩn Trên Hệ Thống
- **Profile base directory**:
  `C:\Users\Kibe\AppData\Local\Programs\GPMLogin\profile`
  (Mỗi profile nằm ở thư mục con tương ứng với `profile_path` trong metadata GPM).
- **Lõi Chromium GPM (Core 142)**:
  `C:\Users\Kibe\AppData\Local\Programs\GPMLogin\gpm_browser\gpm_browser_chromium_core_142\chrome.exe`

---

## 3. Cấu Hình Proxy Trong Playwright
Playwright hỗ trợ proxy dạng dict:
```python
def parse_playwright_proxy(raw_proxy):
    if not raw_proxy:
        return None
    parts = raw_proxy.strip().split(":")
    if len(parts) == 4:
        host, port, user, pwd = parts
        return {
            "server": f"http://{host}:{port}",
            "username": user,
            "password": pwd
        }
    elif len(parts) == 2:
        host, port = parts
        return {"server": f"http://{host}:{port}"}
    return None
```

---

## 4. Mẫu Khởi Chạy Chuẩn (Playwright Sync API)
```python
from playwright.sync_api import sync_playwright
import os

BASE_PROFILE_DIR = r"C:\Users\Kibe\AppData\Local\Programs\GPMLogin\profile"
CHROME_EXE = r"C:\Users\Kibe\AppData\Local\Programs\GPMLogin\gpm_browser\gpm_browser_chromium_core_142\chrome.exe"

full_path = os.path.join(BASE_PROFILE_DIR, profile["profile_path"])
proxy_cfg = parse_playwright_proxy(profile.get("raw_proxy", ""))

with sync_playwright() as pw:
    launch_kwargs = {
        "user_data_dir": full_path,
        "executable_path": CHROME_EXE,
        "headless": True,
        "args": ["--no-first-run", "--no-default-browser-check"]
    }
    if proxy_cfg:
        launch_kwargs["proxy"] = proxy_cfg

    context = pw.chromium.launch_persistent_context(**launch_kwargs)
    pages = [pg for pg in context.pages if not pg.url.startswith("chrome-extension://")]
    page = pages[0] if pages else context.new_page()

    # Thực hiện tác vụ (OAuth / Cookie / Web session)...

    context.close()
```

---

## 5. Lưu Ý Về Khử Xung Đột & sys.path
- **Độc quyền lock file Profile**: Một profile Chrome chỉ được mở bởi 1 tiến trình tại một thời điểm. Đảm bảo GPM UI hoặc tiến trình khác không đang giữ profile trước khi `launch_persistent_context`.
- **Loại bỏ hermes-agent khỏi sys.path**: Luôn đặt ở đầu script:
  ```python
  import sys
  sys.path = [p for p in sys.path if "hermes-agent" not in p]
  ```
- **Kiểm tra cú pháp**: Chạy `env -u PYTHONPATH ... -m py_compile ...` để đảm bảo code sạch lỗi trước khi phân phối.
