# Quy Trình Xóa Dữ Liệu Chọn Lọc Từng Domain (ChatGPT/OpenAI) Trên Profile GPMLogin & Bảo Toàn 100% Session Google/Gmail

## 1. Bối cảnh & Yêu cầu nghiệp vụ (2026-09-05)
- Khi dàn tài khoản ChatGPT / Codex trên các profile GPMLogin bị vô hiệu hóa (`account_deactivated`), cần dọn dẹp sạch sẽ để đăng ký lại tài khoản free mới.
- **Yêu cầu sống còn**: TUYỆT ĐỐI KHÔNG làm mất session Google / Gmail / YouTube đang đăng nhập trên cùng profile.
- **Câu hỏi kỹ thuật cốt lõi**: *"Xóa dữ liệu nhưng fingerprint của GPMLogin vẫn giữ nguyên như cũ thì có đăng ký lại tài khoản ChatGPT được không?"*

---

## 2. Bản Chất Cơ Chế Nhận Diện Của OpenAI / Cloudflare & Fingerprint GPMLogin

1. **OpenAI không ban Hardware Fingerprint (Canvas/WebGL/Audio)**:
   - OpenAI chủ yếu gán danh tính người dùng và phát hiện tài khoản cũ qua:
     + **Storage / Tokens trong trình duyệt**: Cookies định danh thiết bị (`oai-did`, `oaicom-stable-id`), auth session cookies, LocalStorage, IndexedDB.
     + **Địa chỉ IP / Mạng**: Dùng proxy dân cư / 4G xoay IP hoặc proxy di động thật (`test.taadaa.click:5101..5138`).
     + **Thông tin đăng ký**: Email mới hoặc tài khoản Google mới, số điện thoại nhận OTP SMS.
2. **Vai trò của Fingerprint GPMLogin**:
   - Canvas, WebGL, Audio noise, User-Agent của profile GPMLogin đóng vai trò giúp trình duyệt vượt qua rào cản chống bot của **Cloudflare Turnstile** (chứng minh đây là người dùng Chromium thật trên Windows, không phải bot headless tự động).
   - **Quy tắc chuẩn**: **GIỮ NGUYÊN Fingerprint của profile** và **CHỈ XÓA SẠCH Dữ liệu Storage của OpenAI/ChatGPT**. Cách này vừa bảo toàn độ trust cao của profile với Cloudflare, vừa đưa trạng thái OpenAI về như một máy tính mới hoàn toàn truy cập lần đầu, đồng thời giữ nguyên 100% session Gmail.

---

## 3. Quy Trình Xóa Dữ Liệu Chọn Lọc Qua SQLite & Filesystem (Offline)

### Quy Tắc An Toàn Tiền Trạm:
- BẮT BUỘC quét và tắt mọi tiến trình `chrome.exe` / `gpm_browser` đang chạy trên thư mục profile mục tiêu để tránh lỗi khóa file `[WinError 32] The process cannot access the file because it is being used by another process`.
- BẮT BUỘC sao lưu các file `.db` trước khi thực thi:
  + `Default/Network/Cookies` -> `Default/Network/Cookies.bak_chatgpt`
  + `Default/Login Data` -> `Default/Login Data.bak_chatgpt`

### 3 Bước Dọn Dẹp Chi Tiết:

#### Bước 1: Xóa Cookies OpenAI / ChatGPT trong `Default/Network/Cookies`
Chromium lưu cookies trong bảng `cookies` SQLite:
```sql
-- Kiểm tra số lượng cookie trước khi xóa
SELECT count(*) FROM cookies WHERE host_key LIKE '%openai%' OR host_key LIKE '%chatgpt%';

-- Xóa triệt để các cookies của openai và chatgpt
DELETE FROM cookies WHERE host_key LIKE '%openai%' OR host_key LIKE '%chatgpt%';

-- Giải phóng dung lượng và tối ưu lại database
VACUUM;
```
*Lưu ý*: Các cookies của Google (`host_key LIKE '%google%'`), YouTube, Facebook, v.v. hoàn toàn không bị ảnh hưởng.

#### Bước 2: Xóa Thông Tin Đăng Nhập Đã Lưu trong `Default/Login Data`
Tránh việc Chrome tự động autofill email/mật khẩu của tài khoản OpenAI cũ đã chết:
```sql
DELETE FROM logins WHERE origin_url LIKE '%openai%' OR origin_url LIKE '%chatgpt%';
VACUUM;
```

#### Bước 3: Xóa Dữ Liệu Lưu Trữ Cục Bộ (IndexedDB & Cache)
Xóa các thư mục lưu cache của ChatGPT trong profile:
- `Default/IndexedDB/https_chatgpt.com_0.indexeddb.leveldb`
- `Default/IndexedDB/https_chatgpt.com_0.indexeddb.blob`
- `Default/Service Worker/CacheStorage/` (nếu có cache của `chatgpt.com` hoặc `openai.com`).

---

## 4. Script Tự Động Hóa Hàng Loạt (Batch Automation Script)

Script sản xuất lưu tại: `C:\Users\Kibe\scripts\batch_clear_chatgpt_all_profiles.py`

### Mẫu Code Core:
```python
import os, shutil, sqlite3

def clean_chatgpt_data_for_profile(profile_dir: str):
    cookies_path = os.path.join(profile_dir, "Default", "Network", "Cookies")
    login_data_path = os.path.join(profile_dir, "Default", "Login Data")
    indexeddb_dir = os.path.join(profile_dir, "Default", "IndexedDB")
    
    # 1. Cookies
    if os.path.exists(cookies_path):
        bak = cookies_path + ".bak_chatgpt"
        if not os.path.exists(bak): shutil.copy2(cookies_path, bak)
        conn = sqlite3.connect(cookies_path)
        cur = conn.cursor()
        cur.execute("DELETE FROM cookies WHERE host_key LIKE '%openai%' OR host_key LIKE '%chatgpt%'")
        conn.commit()
        cur.execute("VACUUM")
        conn.close()
        
    # 2. Login Data
    if os.path.exists(login_data_path):
        bak = login_data_path + ".bak_chatgpt"
        if not os.path.exists(bak): shutil.copy2(login_data_path, bak)
        conn = sqlite3.connect(login_data_path)
        cur = conn.cursor()
        cur.execute("DELETE FROM logins WHERE origin_url LIKE '%openai%' OR origin_url LIKE '%chatgpt%'")
        conn.commit()
        cur.execute("VACUUM")
        conn.close()
        
    # 3. IndexedDB
    if os.path.exists(indexeddb_dir):
        for item in os.listdir(indexeddb_dir):
            if "chatgpt" in item.lower() or "openai" in item.lower():
                shutil.rmtree(os.path.join(indexeddb_dir, item), ignore_errors=True)
```

---

## 5. Bằng Chứng Xác Thực (Post-Verification Evidence)
- **Thử nghiệm trên Profile 02 (`2_r7clp`)**:
  + Xóa sạch 40 cookies OpenAI/ChatGPT, 1 login, 1 thư mục IndexedDB.
  + Số cookie Google trước: **75**, sau: **75** (giữ nguyên 100%).
  + Mở `https://myaccount.google.com/`: Session Gmail `luuhuong28022000@gmail.com` live 100%, không bị văng ra trang đăng nhập.
  + Mở `https://chatgpt.com/`: Trang hiển thị giao diện trắng ban đầu với các nút Đăng nhập / Đăng ký, không còn dấu hiệu lỗi `account_deactivated`.
- **Chạy hàng loạt 457 profile**:
  + Quét và xử lý thành công 17 profiles có chứa cookie/login OpenAI (xóa tổng cộng 267 cookies, 11 logins, 15 thư mục IndexedDB trong 4.14 giây).
