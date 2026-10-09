# Lưu Mật Khẩu & Tài Khoản vào Chromium Browser trong GPMLogin

Tài liệu hướng dẫn cấu hình và tự động hóa tính năng lưu tài khoản/mật khẩu vào trình quản lý mật khẩu của Chromium khi đăng nhập Google qua GPMLogin + Playwright.

---

## 1. Bản chất & Nguyên nhân Mặc định Không Lưu
1. **Playwright chặn bong bóng lưu mật khẩu (Default Arg)**:
   - Playwright mặc định thêm cờ `--disable-save-password-bubble` vào mọi Chromium instance khởi chạy (`launch_persistent_context` hoặc `launch`).
   - Cờ này triệt tiêu hoàn toàn native pop-up "Lưu mật khẩu? / Save password?" của trình duyệt.
2. **Cấu hình Preferences Profile chưa kích hoạt Password Manager**:
   - Trong thư mục profile GPM (`Default/Preferences`), các thuộc tính `credentials_enable_service` và `profile.password_manager_enabled` có thể mặc định là `false` hoặc chưa khởi tạo.
3. **Logic dismiss tự động bấm "Để sau"**:
   - Khi Google Web UI hiển thị prompt hỏi về lưu mật khẩu / passkey / duy trì đăng nhập, các script tự động hóa thường gom chung vào bộ lọc bỏ qua (`Not now`, `Để sau`, `Skip`, `Hủy`), dẫn đến việc từ chối lưu mật khẩu.

---

## 2. Quy Chuẩn Kỹ Thuật Để Bật Lưu Mật Khẩu

### A. Gỡ Cờ Chặn của Playwright
Trong lệnh `p.chromium.launch_persistent_context`, bắt buộc truyền:
```python
ignore_default_args=["--disable-save-password-bubble"]
```

### B. Kích Hoạt Cờ Preferences Trước Khi Launch
Trước khi mở trình duyệt, ghi đè cấu hình vào `Default/Preferences` của profile:
```python
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

### C. Ưu Tiên Click "Lưu / Save" Thay Vì Dismiss
Trong vòng lặp xử lý các màn hình đăng nhập Google:
```python
# Save Password / Lưu mật khẩu / Duy trì đăng nhập (nếu Google web UI hoặc prompt hỏi)
try:
    save_pw = page.locator('button:has-text("Lưu"), button:has-text("Save"), button:has-text("Lưu mật khẩu"), button:has-text("Save password")').first
    if save_pw.count() > 0 and save_pw.is_visible():
        s_txt = save_pw.inner_text().strip().lower()
        if any(k in s_txt for k in ["lưu", "save"]) and not any(k in s_txt for k in ["để sau", "hủy", "not now", "không"]):
            logger.info(f"Phát hiện prompt lưu mật khẩu/tài khoản, click '{s_txt}'...")
            save_pw.click()
            time.sleep(3)
            continue
except Exception:
    pass
```

---

## 3. Kiểm Tra Nghiệm Thu (Verification)
1. **Preferences**: Kiểm tra file `Default/Preferences` trong thư mục profile có `credentials_enable_service: True` và `profile.password_manager_enabled: True`.
2. **SQLite Database `Login Data`**:
   - Nằm tại: `<profile_path>/Default/Login Data`.
   - Bảng `logins`: Có bản ghi với `origin_url` chứa `https://accounts.google.com` và `username_value` chứa email vừa đăng nhập.
