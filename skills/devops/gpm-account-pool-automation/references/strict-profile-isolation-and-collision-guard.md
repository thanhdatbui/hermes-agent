# Strict Profile Isolation & Collision Guard (1 Profile : 1 Gmail)

## 1. Bản chất sự cố dùng chung profile
Khi tự động hóa nhiều tài khoản Gmail qua GPMLogin (ví dụ trong OAuth pipeline `run_oauth_s7_pipeline.py`), nếu code kiểm tra:
```python
prof_dir = os.path.join(GPM_BASE, acc["profile"])
if not os.path.exists(prof_dir):
    # query DB...
```
Nếu `acc["profile"]` bị truyền nhầm là một thư mục profile của máy khác (ví dụ máy M61 truyền sang M57) mà thư mục đó vốn có thật trên ổ đĩa, script sẽ không bao giờ truy vấn DB theo email mà nhảy thẳng vào dùng luôn profile của Gmail khác. Hậu quả: cookies/session của 2 Gmail bị đè lên nhau, gây checkpoint hàng loạt (Hard SMS Checkpoint).

## 2. Quy tắc phân giải Strict Profile Isolation (3 Bước bắt buộc)

### Bước 1: Ưu tiên tuyệt đối tra cứu DB theo Email
Luôn tra cứu `profile_data.db` theo email của `acc["email"]` trước tiên:
```python
cur.execute("SELECT ProfilePath, Name FROM Profiles WHERE lower(Name) LIKE ?", (f"%{email.lower()}%",))
```
Nếu tìm thấy ProfilePath và thư mục `os.path.join(GPM_BASE, ProfilePath)` tồn tại, dùng ngay đường dẫn này và bỏ qua giá trị `acc["profile"]` truyền vào từ bên ngoài.

### Bước 2: Cross-account Collision Guard
Nếu DB chưa có profile theo email mà `acc.get("profile")` được cung cấp:
- **Guard 1 (Email trong tên profile):** Nếu `acc["profile"]` có chứa ký tự `@` nhưng không chứa `email.lower()` -> Chặn ngay lập tức (`PROFILE_COLLISION_BLOCKED: Profile directory contains another email`).
- **Guard 2 (Chủ sở hữu trong DB):** Truy vấn `SELECT Name FROM Profiles WHERE ProfilePath = ?`. Nếu `Name` của profile đó có chứa `@` và khác `email.lower()` -> Chặn ngay lập tức (`PROFILE_COLLISION_BLOCKED: ProfilePath is owned by another email`).

### Bước 3: Tuyệt đối không fallback bừa bãi
Nếu không tìm thấy profile hợp lệ hoặc phát hiện profile bị chiếm dụng bởi tài khoản khác:
Log cảnh báo `🚫 LỖI CÁCH LY PROFILE: Tài khoản {email} không có profile riêng hoặc profile chỉ định thuộc về tài khoản khác!` và trả về status `PROFILE_COLLISION_BLOCKED` hoặc `PROFILE_NOT_FOUND`. Tuyệt đối CẤM fallback mở bừa profile của acc khác.

## 3. Xử lý khi bị Hard SMS Checkpoint
- Nếu tài khoản gặp màn hình đòi nhập SMS thay vì Google Prompt S7 / TOTP:
  1. Dừng ngay lập tức, tuyệt đối KHÔNG cố thử lại liên tục trên cùng proxy/IP.
  2. Ngâm nghỉ IP/proxy tối thiểu 24-48h để Google hạ mức cờ bất thường.
  3. Kiểm tra xem profile trình duyệt có bị đè cookies của tài khoản khác hay không trước khi chạy lại.
