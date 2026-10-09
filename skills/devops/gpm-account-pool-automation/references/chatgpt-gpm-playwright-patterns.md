# Pitfalls & Patterns: ChatGPT Automation qua GPM & Playwright CDP

## 1. False-Positive `check_logged_in` trên ChatGPT
### Triệu chứng:
ChatGPT trang chủ (`https://chatgpt.com`) khi chưa đăng nhập (Guest Mode) vẫn hiển thị ô nhập liệu prompt (`#prompt-textarea`, textarea, `[data-placeholder]`), khiến hàm check chỉ nhìn vào textarea sẽ ngộ nhận là đã đăng nhập thành công.

### Giải pháp chuẩn:
Luôn kiểm tra 2 chiều:
1. **Phủ định nút auth**: Bắt buộc KHÔNG CÒN các nút đăng nhập / đăng ký:
   ```python
   login_selectors = [
       'button:has-text("Đăng nhập")', 'a:has-text("Đăng nhập")',
       'button:has-text("Log in")', 'a:has-text("Log in")',
       'button:has-text("Sign up")', 'a:has-text("Sign up")',
       '[data-testid="login-button"]', '[data-testid="signup-button"]'
   ]
   for sel in login_selectors:
       if page.locator(sel).first.is_visible(timeout=500):
           return False
   ```
2. **Khẳng định Profile / User Menu**:
   ```python
   profile_selectors = [
       'button[data-testid="profile-button"]',
       '[aria-label*="User menu"]',
       '[aria-label*="Menu người dùng"]',
       'button[aria-label*="profile"]',
       'button[aria-haspopup="menu"] img[alt]'
   ]
   for sel in profile_selectors:
       if page.locator(sel).first.is_visible(timeout=1000):
           return True
   ```

---

## 2. Xử lý Cookie Banner che khuất UI
ChatGPT và Google thường hiển thị OneTrust hoặc cookie banner toàn màn hình/thanh bar dưới đáy (`#onetrust-accept-btn-handler`, "Chấp nhận tất cả", "Accept all cookies"), che khuất nút click OAuth hoặc điều hướng:
```python
def dismiss_cookie_banner(page):
    cookie_btns = [
        'button:has-text("Chấp nhận tất cả")',
        'button:has-text("Accept all cookies")',
        'button:has-text("Accept all")',
        '#onetrust-accept-btn-handler'
    ]
    for sel in cookie_btns:
        loc = page.locator(sel).first
        if loc.is_visible(timeout=1000):
            loc.click()
            time.sleep(1)
            break
```

---

## 3. Xung đột PYTHONPATH giữa Host / Hermes Agent và venv Target
### Triệu chứng:
Khi chạy script Python trong venv riêng (ví dụ `D:/Taadaa/python-envs/automation`) từ terminal hoặc subagent của Hermes, biến môi trường `PYTHONPATH` có thể kế thừa path của Hermes (`.../AppData/Local/hermes/hermes-agent/venv/Lib/site-packages`). Điều này gây lỗi C-extension nhị phân không tương thích (ví dụ: `ModuleNotFoundError: No module named 'greenlet._greenlet'`).

### Khắc phục:
1. Khi gọi command qua shell:
   ```bash
   PYTHONPATH="" /path/to/venv/Scripts/python.exe script.py
   ```
2. Trong code Python tự vệ sinh `sys.path`:
   ```python
   import sys
   sys.path = [p for p in sys.path if "hermes-agent" not in p]
   ```
