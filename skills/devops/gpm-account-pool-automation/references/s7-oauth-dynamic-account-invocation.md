# S7 OAuth Pipeline: Dynamic Account & GPM Profile Invocation

## Pitfall: Email không có trong `master_gmail_manager.xlsx` (Sheet `Kibe_Farm_S7`)

Khi chạy re-auth hoặc lấy OAuth connection ID bằng `run_oauth_s7_pipeline.py`:
- `get_account_for_email(email)` và `get_account_for_mid(mid)` mặc định chỉ tìm kiếm trong sheet `Kibe_Farm_S7` của file `D:\OneDrive\TaadaaData\kibe\master_gmail_manager.xlsx`.
- Nếu email thuộc danh sách bổ sung hoặc mới tạo, chỉ tồn tại trong GPM SQLite DB (`profile_data.db`) hoặc các sheet khác (`Gmail_Dat`, `Master_All`), lệnh CLI:
  ```bash
  python "D:/Taadaa/GPM auto/scripts/run_oauth_s7_pipeline.py" <email>
  ```
  sẽ trả về `None` và kết thúc ngay mà không thực hiện re-auth.

## Giải pháp: Gọi trực tiếp `process_account(acc)`

Khởi tạo cấu trúc dictionary `acc` với đầy đủ thông số được truy vấn từ `profile_data.db` và OmniRoute `/api/settings/proxies`:

```python
import sys
sys.path.insert(0, r"D:\Taadaa\GPM auto\scripts")
from run_oauth_s7_pipeline import process_account

acc = {
    "mid": 4,                                # Machine ID
    "email": "yenduypham2002997@gmail.com",
    "serial": "9885e6484432423046",         # ADB serial của thiết bị S7
    "port": 5104,                            # Proxy port (tương ứng proxy trên OmniRoute)
    "profile": "Sy0xpMIS71-06092026",        # ProfilePath trong profile_data.db
    "singbox_port": 20004,                   # Quy tắc: 20000 + (port - 5100)
    "password": "Password_Cua_Account"
}

res = process_account(acc)
print("Result:", res)
```

## Các điểm kiểm tra trước khi chạy
1. **Kiểm tra trạng thái cooldown / IP cooling**: Kiểm tra `D:\Taadaa\GPM auto\config\oauth_pipeline_status.json` để đảm bảo account không nằm trong diện cooldown 7 ngày (`cooldown_7days`) hoặc dính checkpoint khoale (`excluded_khoalee`).
2. **Kiểm tra Proxy trên OmniRoute (`:20129`)**: Đảm bảo port proxy (ví dụ `5104`) đã được khai báo trên OmniRoute (`/api/settings/proxies`) để pipeline tự động gán proxy mapping sau khi exchange OAuth token thành công.
