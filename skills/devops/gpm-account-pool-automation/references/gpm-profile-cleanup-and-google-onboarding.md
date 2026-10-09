# GPM Profile Cleanup, API Quirks & Google Onboarding Bypass

## 1. GPMLogin Local API (v3 port 19995) Profile Deletion
### Pitfall: `INVALID_MODE` Error
Khi gọi API xóa profile trên GPMLogin:
- **Sai (gây lỗi)**: `GET /api/v3/profiles/delete/{id}` hoặc `DELETE /api/v3/profiles/delete/{id}` không có param -> API trả về:
  ```json
  {"success": false, "data": null, "message": "INVALID_MODE"}
  ```
  Profile sẽ không bị xóa và vẫn tồn tại trong SQLite database.
- **Đúng**: Bắt buộc phải truyền query parameter `mode=1`:
  ```python
  import requests

  profile_id = "f3b0e76c-8560-45fb-8b55-b726d5da34ec"
  res = requests.get(f"http://127.0.0.1:19995/api/v3/profiles/delete/{profile_id}?mode=1", timeout=5)
  data = res.json()
  if not data.get("success"):
      raise RuntimeError(f"Failed to delete profile {profile_id}: {data}")
  ```

---

## 2. Google Account Landing / Onboarding Bypass (`about/?hl=vi`)
### Vấn đề
Khi tự động hóa đăng nhập Google trong profile GPM, sau khi nhập mật khẩu hoặc xử lý xong xác minh danh tính, Google thường redirect sang trang giới thiệu sản phẩm:
- URL: `https://www.google.com/account/about/?hl=vi` (hoặc `https://www.google.com/account/about/`)
- Page title: `Chào mừng` / `Welcome`
Nếu kịch bản automation chờ selector của trang quản lý tài khoản hoặc `two-step-verification`, script sẽ bị treo timeout.

### Giải pháp
Sau khi đăng nhập hoặc hoàn thành pass/otp/recovery, chủ động kiểm tra URL/Title:
```python
current_url = page.url.lower()
page_title = page.title().lower()

if "account/about" in current_url or any(k in page_title for k in ["chào mừng", "welcome"]):
    logger.info("Phát hiện landing page 'about/chào mừng', điều hướng trực tiếp vào myaccount...")
    page.goto("https://myaccount.google.com/?authuser=0", wait_until="domcontentloaded", timeout=15000)
```
Sau đó mới tiến hành truy cập các trang cài đặt bảo mật như:
`https://myaccount.google.com/two-step-verification/authenticator`

---

## 3. OmniRoute Exchange Debugging
Khi gửi authorization code lên OmniRoute API (`POST /api/oauth/antigravity/exchange`):
- Luôn log `res.text` nếu `not res.ok` trước khi gọi `res.raise_for_status()`, tránh việc HTTPError giấu mất thông tin chi tiết (ví dụ lỗi redirect_uri mismatch, code_verifier sai, hoặc Google token revoked).
