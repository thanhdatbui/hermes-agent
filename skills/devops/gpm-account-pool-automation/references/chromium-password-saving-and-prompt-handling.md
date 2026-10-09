# Chromium / Playwright Password Saving & Auto-Save Prompt Handling

Khi chạy profile Chromium tự động (đặc biệt là qua Playwright `launch_persistent_context` hoặc CDP automation cho Google login), Playwright mặc định bật cờ tắt bubble lưu mật khẩu (`--disable-save-password-bubble`), đồng thời trong Preferences profile có thể chưa bật `credentials_enable_service` và `profile.password_manager_enabled`.

## 1. Cơ chế bật lưu mật khẩu trong Chromium Profile (Preferences)
Trước khi khởi động browser context, cập nhật file `Preferences` của profile:
```python
import json
import os

def enable_password_saving_in_profile(prof_dir: str):
    """Bật cờ quản lý và lưu mật khẩu trong Preferences của Chromium profile."""
    pref_path = os.path.join(prof_dir, "Default", "Preferences")
    if not os.path.exists(pref_path):
        return
    try:
        with open(pref_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["credentials_enable_service"] = True
        if "profile" not in data or not isinstance(data["profile"], dict):
            data["profile"] = {}
        data["profile"]["password_manager_enabled"] = True
        with open(pref_path, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception:
        pass
```

## 2. Loại bỏ cờ vô hiệu hóa bubble lưu mật khẩu trong Playwright
Playwright `launch_persistent_context` mặc định tiêm `--disable-save-password-bubble`. Cần loại bỏ cờ này bằng `ignore_default_args`:
```python
context = p.chromium.launch_persistent_context(
    user_data_dir=prof_dir,
    locale="vi-VN",
    headless=False,
    ignore_default_args=["--disable-save-password-bubble"],
    args=[
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-blink-features=AutomationControlled",
        "--lang=vi-VN,vi",
    ]
)
```

## 3. Xử lý Prompt "Lưu mật khẩu" (Web UI / Dialog)
Trong quy trình login hoặc dismiss popups, cần ưu tiên click **Lưu / Save** trước khi rơi vào các logic dismiss ("Để sau", "Hủy", "Not now", "Skip"):
```python
try:
    save_pw = page.locator(
        'button:has-text("Lưu"), button:has-text("Save"), button:has-text("Lưu mật khẩu"), button:has-text("Save password")'
    ).first
    if save_pw.count() > 0 and save_pw.is_visible():
        s_txt = save_pw.inner_text().strip().lower()
        if any(k in s_txt for k in ["lưu", "save"]) and not any(k in s_txt for k in ["để sau", "hủy", "not now", "không"]):
            logger.info(f"Phát hiện prompt lưu mật khẩu/tài khoản, click '{s_txt}'...")
            save_pw.click()
            time.sleep(3)
except Exception:
    pass
```
*Lưu ý:* Kiểm tra phủ định (`not any(...)`) để tránh click nhầm vào các nút "Không bao giờ lưu" hoặc "Để sau".
