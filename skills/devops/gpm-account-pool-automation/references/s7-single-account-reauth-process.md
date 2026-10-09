# Hướng dẫn Re-auth Đơn lẻ Tài khoản S7 vào OmniRoute qua process_account

## 1. Vấn đề thường gặp
Khi chạy re-auth cho một tài khoản cụ thể (ví dụ: `mockieuplus13@gmail.com` trên M57):
- Dòng trong `master_gmail_manager.xlsx` có thể chứa cùng lúc 2 port:
  - OmniRoute proxy port (HTTP proxy: `test.taadaa.click:5123` -> port `5123`).
  - S7 Singbox tunnel port (`http://192.168.110.2:20057` -> port `20057`).
- Hàm `get_account_for_email` trong `run_oauth_s7_pipeline.py` dùng regex parse tự động có thể bốc nhầm `singbox_port` (`20057`) làm `port` của OmniRoute hoặc ngược lại, dẫn đến lỗi gán proxy hoặc lỗi kết nối Playwright.

## 2. Cách thực hiện chuẩn xác (Deterministic Invocation)
Truyền tường minh cấu trúc dict `acc` cho `process_account(acc)`:

```python
import os
import sys

sys.path.append(r"D:\Taadaa\GPM auto\scripts")
from run_oauth_s7_pipeline import process_account

acc = {
    "mid": 57,
    "email": "mockieuplus13@gmail.com",
    "serial": "ce11160b54ee2f3403",
    "profile": "aq6NHRUdWQ-06092026",  # Hoặc tên profile trong D:\GPM_BASE
    "port": 5123,  # OmniRoute proxy port (dùng để gán proxy 1:1)
    "singbox_port": 20057,  # Singbox egress port trên 192.168.110.2
    "password": "MocKieu$Top02",
    "recovery": "",
    "totp_secret": "",
}

res = process_account(acc)
print("RESULT:", res)
```

## 3. Các điểm mấu chốt trong luồng xử lý
1. **Profile Path Resolution**:
   - `prof_dir = os.path.join(GPM_BASE, acc["profile"])`. Nếu đường dẫn không tồn tại trực tiếp, `process_account` tự tra cứu trong `profile_data.db` bằng tên email để tìm đúng folder profile.
2. **Playwright Persistent Context**:
   - Khởi chạy Chromium với proxy `http://192.168.110.2:{singbox_port}` để đảm bảo IP đồng bộ với S7.
3. **Bắt Authorization Code**:
   - Hook `page.on("request", on_request)` bắt URL redirect `/callback?code=...`.
4. **Exchange & Proxy Assignment**:
   - Gửi code lên OmniRoute (`http://127.0.0.1:20128/api/oauth/antigravity/exchange` hoặc `:20129`).
   - Tìm Proxy ID có port trùng với `acc["port"]` (5123) và gọi `PUT /api/settings/proxies/assignments` gán scope `account`.
   - Gọi `POST /api/providers/{conn_id}/sync-models`.
   - Cập nhật an toàn với file lock vào `config/oauth_pipeline_status.json`.
