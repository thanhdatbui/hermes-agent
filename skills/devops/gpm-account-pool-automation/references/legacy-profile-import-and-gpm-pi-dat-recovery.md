# Khôi phục & Nhập Profile Cũ Từ `gpm_pi.dat` & Xác Minh Live Google CDP

## 1. Cơ Chế Lưu Metadata GPM Trong Thư Mục Vật Lý (`gpm_pi.dat`)
Khi các thư mục profile GPM tồn tại trên ổ đĩa (`C:\Users\Kibe\AppData\Local\Programs\GPMLogin\profile\{ProfilePath}`) nhưng bị mất dòng trong SQLite `profile_data.db`:
- GPMLogin lưu trữ toàn bộ cấu hình gốc tại file:
  `{ProfilePath}\Default\GPMSoft\gpm_pi.dat`
- File này là chuỗi mã hóa Base64 của một JSON object chứa:
  - `id`: GUID nguyên bản của profile.
  - `name`: Tên gốc của profile (vd: `"21"`, `"16"`).
  - `json_data`: Chuỗi JSON chứa đầy đủ 124-130 keys phần cứng fingerprint gốc (AudioNoise, Canvas, WebGL, UserAgent...).
  - `created_at`: Thời gian tạo gốc.

### Mẫu Python Đọc & Trích Xuất Cấu Hình Gốc:
```python
import base64, json, os

def extract_gpm_pi(profile_dir):
    pi_path = os.path.join(profile_dir, "Default", "GPMSoft", "gpm_pi.dat")
    if not os.path.exists(pi_path):
        return None
    with open(pi_path, "rb") as f:
        data = json.loads(base64.b64decode(f.read().strip()).decode("utf-8"))
    raw_jd = data.get("json_data")
    jd = json.loads(raw_jd) if isinstance(raw_jd, str) else raw_jd
    return {
        "id": data.get("id"),
        "name": data.get("name"),
        "created_at": data.get("created_at"),
        "json_data": jd
    }
```

---

## 2. Quy Trình Nhập GroupId = 1 & Bổ Sung Proxy Chuẩn
Khi import lại vào `profile_data.db`:
1. Giữ nguyên 100% các giá trị phần cứng trong `json_data` (không randomize).
2. Hoàn thiện 6 trường proxy trong `json_data` từ raw proxy gán cho máy:
   - `Proxy`: `host:port:user:pass`
   - `raw_proxy`: `host:port:user:pass`
   - `proxy_type`: `'http'`
   - `proxy_host`, `proxy_port`, `proxy_user`, `proxy_pass`
   - `ProxyRegion`: `'VN'`
3. Thực hiện câu lệnh SQL `INSERT INTO Profiles` với `GroupId = 1`.

---

## 3. Quy Tắc Xác Minh Live & Đổi Tên An Toàn
1. Khởi động profile qua Local API: `GET /api/v3/profiles/start/{id}`.
2. Kết nối Playwright qua CDP vào `remote_debugging_address`.
3. Điều hướng tới `https://myaccount.google.com/`.
4. **Phân loại kết quả:**
   - **Đang có session sống:** URL là `myaccount.google.com` và không redirect về `signin` $\rightarrow$ Trích xuất email từ DOM (`[data-email]` hoặc `a[aria-label*="@gmail.com"]`) $\rightarrow$ Đổi tên profile thành `{Machine} - {Verified_Email}` trong cả SQLite DB (`Profiles.Name` + `JsonData['Name']`) và `master_gmail_manager.xlsx`.
   - **Phiên hết hạn / Cần Login:** Tự động điền mật khẩu + 2FA TOTP (`pyotp`) + giải reCAPTCHA âm thanh (`pydub` + `speech_recognition`).
   - **Gặp Google Phone Checkpoint (`challenge/iap`):** "Nhập số điện thoại để nhận tin nhắn..." $\rightarrow$ Fail-closed, đóng profile ngay lập tức, giữ nguyên tên pending (CẤM đổi tên thành verified email), ghi chú `DIE / Phone Checkpoint` vào Excel.
5. Đóng browser và gọi `GET /api/v3/profiles/stop/{id}`.
