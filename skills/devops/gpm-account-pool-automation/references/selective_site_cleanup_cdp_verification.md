# Selective Site Data Cleanup & CDP Verification for GPMLogin Profiles

## 1. Khi nào sử dụng
- Cần xóa dữ liệu đăng nhập, cookies, session hoặc indexedDB của một website cụ thể (ví dụ: OpenAI/ChatGPT khi bị `account_deactivated` hoặc lỗi phiên) trên một GPM profile mà **không** làm mất session của các website khác (đặc biệt là Google/Gmail, Facebook, Hotmail...).
- Reset trạng thái web về ban đầu mà không cần tạo lại profile hay xóa toàn bộ cache profile.

---

## 2. Pitfalls quan trọng cần chú ý

### ⚠️ Pitfall 1: Database file locked bởi Chrome (`sqlite3.OperationalError`)
- Khi Chrome đang chạy hoặc chưa đóng hoàn toàn, file `Default/Network/Cookies` và `Default/Login Data` sẽ bị khóa với các file `-journal`.
- **Giải pháp:**
  1. Luôn gọi API Stop Profile qua GPMLogin trước khi thao tác SQLite:
     `GET http://127.0.0.1:19995/api/v3/profiles/stop/{profile_id}`
  2. Dọn dẹp các tiến trình `chrome.exe` mồ côi liên quan đến profile đó nếu GPM chưa tắt hẳn.

### ⚠️ Pitfall 2: `psutil` treo (hang) trên Windows khi lặp qua tất cả process cmdline
- **Hiện tượng:** Chạy `psutil.process_iter(['pid', 'name', 'cmdline'])` trên Windows có thể bị treo vô hạn hoặc dính timeout do đụng phải tiến trình hệ thống / antivirus được bảo vệ.
- **Giải pháp chuẩn:**
  Chỉ lấy `['pid', 'name']` trước, lọc `name` chứa `'chrome'`, sau đó mới truy cập `p.cmdline()` trong khối `try...except (psutil.AccessDenied, psutil.NoSuchProcess)`:
  ```python
  for p in psutil.process_iter(['pid', 'name']):
      if p.info['name'] and 'chrome' in p.info['name'].lower():
          try:
              cmd = ' '.join(p.cmdline() or [])
              if profile_folder in cmd:
                  p.kill()
          except (psutil.AccessDenied, psutil.NoSuchProcess):
              pass
  ```

---

## 3. Quy trình thực hiện chuẩn 5 bước

### Bước 1: Backup & Dọn dẹp SQLite / Storage
1. **Backup:**
   - Copy `Default/Network/Cookies` -> `Default/Network/Cookies.bak_<target>`
   - Copy `Default/Login Data` -> `Default/Login Data.bak_<target>`
2. **SQLite Cookies:**
   ```sql
   -- Kiểm tra số lượng cookie trước khi xóa
   SELECT COUNT(*) FROM cookies WHERE host_key LIKE '%<target>%';
   -- Xóa và giải phóng dung lượng
   DELETE FROM cookies WHERE host_key LIKE '%<target>%';
   VACUUM;
   ```
3. **SQLite Login Data:**
   ```sql
   DELETE FROM logins WHERE origin_url LIKE '%<target>%';
   VACUUM;
   ```
4. **Xóa IndexedDB & Local Storage:**
   - Quét thư mục `Default/IndexedDB/` tìm folder chứa tên target (ví dụ: `https_chatgpt.com_0.indexeddb.leveldb`) và xóa bằng `shutil.rmtree`.
   - Quét `Default/Local Storage/leveldb/` nếu có file/folder riêng của origin.

### Bước 2: Khởi động Profile qua GPM API
```python
res = requests.get(f"http://127.0.0.1:19995/api/v3/profiles/start/{profile_id}", timeout=30)
data = res.json()
remote_addr = data["data"]["remote_debugging_address"]
```

### Bước 3: Kết nối Playwright CDP kiểm tra Session
1. **Kiểm tra session cần bảo toàn (ví dụ: Google Account):**
   - Vào `https://myaccount.google.com/`
   - Kiểm tra xem có redirect sang `accounts.google.com/signin` không (`is_redirect_signin == False`).
   - Kiểm tra text email chủ tài khoản có hiện diện trong DOM không.
   - Chụp ảnh màn hình làm bằng chứng lưu vào `cache/images/`.
2. **Kiểm tra target site đã sạch:**
   - Mở tab mới vào URL đích (ví dụ: `https://chatgpt.com/`).
   - Xác nhận không còn thông báo lỗi phiên cũ (`account_deactivated`).
   - Xác nhận xuất hiện các nút đăng nhập / đăng ký mặc định.

### Bước 4: Đóng Context & Dừng Profile qua GPM API
- Đóng browser context trong Playwright.
- Gọi `GET http://127.0.0.1:19995/api/v3/profiles/stop/{profile_id}`.

### Bước 5: Dọn dẹp Chrome mồ côi
- Quét và kill các tiến trình chrome mồ côi giữ profile_dir để tránh lock file cho các phiên sau.

---

## 4. Batch dọn dẹp hàng loạt toàn bộ profile (Offline SQLite Engine)

Khi cần xử lý hàng trăm profile (ví dụ: dọn dẹp session ChatGPT/OpenAI trên toàn bộ 400+ profile):
- **Không khởi động từng profile qua CDP**: Khởi động tuần tự qua CDP sẽ mất hàng giờ. Thay vào đó, quét và xử lý trực tiếp offline trên filesystem thông qua SQLite (`Cookies`, `Login Data`) và thư mục `IndexedDB`.
- **Script thực thi sẵn có:** `scripts/batch_clear_site_data_offline.py`
- **Các bước cốt lõi:**
  1. Dừng tất cả tiến trình `chrome.exe` ngầm thuộc `GPMLogin` / `gpm_browser` bằng `psutil` để tránh `[WinError 32]` file lock.
  2. Duyệt qua tất cả thư mục profile con trong `C:\Users\Kibe\AppData\Local\Programs\GPMLogin\profile` (bỏ qua `_backup`).
  3. Kiểm tra count trước; chỉ tạo bản sao lưu `.bak_<tag>` khi phát hiện có dữ liệu mục tiêu để tiết kiệm dung lượng đĩa.
  4. Thực thi `DELETE` và bắt buộc chạy `VACUUM` để dọn sạch wal/journal và giải phóng không gian lưu trữ.
  5. Xóa triệt để các thư mục `https_<target>*.indexeddb.leveldb` và `.blob` trong `Default/IndexedDB/`.
  6. Tuyệt đối không chạm vào cookie hay storage của các domain khác (Google, YouTube, Facebook, v.v.).
- **Tốc độ:** Xử lý 450+ profile chỉ mất ~4-5 giây.
