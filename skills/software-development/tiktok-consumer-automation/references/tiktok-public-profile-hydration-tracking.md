# TikTok Public Profile Hydration Tracking

Phương pháp theo dõi chỉ số tài khoản TikTok (follower, heart, video count, status) hàng loạt cho farm mà KHÔNG cần cắm máy / chạy ADB / login.

## 1. Web Rehydration Scraping Pattern

TikTok render dữ liệu trang cá nhân qua JSON state nhúng trong HTML tag `<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__" ...>`.

### Request Configuration
- **URL**: `https://www.tiktok.com/@{username}`
- **Headers**:
  ```python
  headers = {
      'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
      'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
      'Accept-Language': 'vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7',
  }
  ```

### Parsing Logic
```python
import re
import json

match = re.search(r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>({.*?})</script>', html_text)
if match:
    data = json.loads(match.group(1))
    scope = data.get('__DEFAULT_SCOPE__', {})
    user_detail = scope.get('webapp.user-detail', {})
```

### Account Status Detection
- **Die / Banned / 404**:
  - `user_detail.get('statusCode') == 10221` hoặc `statusMsg == 'user banned'`
  - `user_info is None`
  - Đánh dấu nick Die/Banned mà không cần test trên app.
- **Live / Active**:
  - `user = user_detail['userInfo']['user']`
    - `id`: TikTok UID
    - `uniqueId`: Username
    - `nickname`: Tên hiển thị
    - `secUid`: Secondary UID
  - `stats = user_detail['userInfo']['stats']`
    - `followerCount`: Số follower
    - `followingCount`: Đang follow
    - `heartCount`: Tổng tim
    - `videoCount`: Tổng video public
    - `friendCount`: Bạn bè

## 2. Python Environment Pitfall on Windows Farm
Trên môi trường Windows chạy Hermes Agent:
- Hermes venv (`C:\Users\<user>\AppData\Local\hermes\hermes-agent\venv`) dùng Python 3.11 với C-extensions compiled riêng.
- Venv farm (`D:\Taadaa\python-envs\automation`) dùng Python 3.12.
- Nếu chạy lệnh terminal hoặc subprocess mà không un-export `PYTHONPATH`, Python 3.12 sẽ load nhầm thư viện C của Python 3.11 gây crash `ImportError: ModuleNotFoundError: No module named 'numpy._core._multiarray_umath'`.
- **Khắc phục**: Luôn chạy script bằng `env -u PYTHONPATH <python_path> ...` hoặc `python -s`.

## 3. Thống kê & Báo cáo
- Lưu snapshot vào SQLite: `snapshots (timestamp, username, uid, nickname, follower, following, heart, video, status, may, device_id)`.
- Tính delta so với snapshot trước đó để phát hiện tài khoản cắn đề xuất (viral spike: delta follower >= 100).
- Xuất báo cáo hàng ngày ra Excel (`tiktok_stats_daily.xlsx`).
