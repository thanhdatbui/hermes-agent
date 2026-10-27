# Hợp Đồng Đường Dẫn ADB & Lệnh Gọi SSH Cho Cụm Farm Admin (28/10/2026)

## 1. Hiện Tượng Thực Tế
- Báo cáo 2FA ban đêm toàn farm:
  - Farm Kibe (Máy 1-80): Hoàn tất 23 | Bỏ qua 10 | Lỗi 36
  - Farm Admin (Máy 201-280): Hoàn tất 0 | Bỏ qua 18 | Lỗi 71
- Toàn bộ 71 máy mục tiêu trên cụm Admin đều văng lỗi (0 máy thành công).

## 2. Nguyên Nhân Kỹ Thuật (Root Cause)
1. **Thiếu cờ `--adb-path` trong lệnh gọi PowerShell qua SSH của Watchdog:**
   - Trong `cron_night_tiktok_2fa_watchdog.py`, khi gọi `run_batch_live_2fa.py` trên Kibe, tham số `--adb-path` được truyền đầy đủ.
   - Tuy nhiên trong đoạn tạo `ps_admin_script` gửi sang cụm Admin qua SSH, cờ `--adb-path` bị bỏ sót.
2. **Khác biệt môi trường User Kibe vs User Admin:**
   - Trên máy chủ Admin, tiến trình chạy dưới user `Admin`, biến môi trường `PATH` không chứa thư mục công cụ XiaoWei / Android SDK.
   - Hàm `resolve_adb_path` trong `python_runner/run_capture_phase_a.py` có fallback `DEFAULT_BUNDLED_ADB` bị hardcode cứng đường dẫn của user Kibe (`C:\Users\Kibe\AppData\Local\Programs\GemPhoneFarm\...`), vốn hoàn toàn không tồn tại trên user `Admin`.
   - Khi runner mặc định tham số `--adb-path "adb"`, `shutil.which("adb")` trả về `None`, dẫn đến `AdbClient` gọi subprocess văng `FileNotFoundError: [WinError 2] The system cannot find the file specified: 'adb'` trên toàn bộ 71 worker.

## 3. Quy Tắc & Giải Pháp Đã Chuẩn Hóa
1. **Quy định tham số SSH Watchdog:**
   - Trong `cron_night_tiktok_2fa_watchdog.py`, định nghĩa biến rõ ràng:
     ```python
     ADMIN_ADB_PATH = os.getenv("TAADAA_ADMIN_ADB_PATH", r"C:\Program Files (x86)\xiaowei\tools\adb.exe")
     ```
   - Trong `ps_admin_script`, bắt buộc truyền rõ:
     ```powershell
     --adb-path '{_ps_quote(ADMIN_ADB_PATH)}'
     ```
   - Sau khi chỉnh sửa watchdog, bắt buộc chạy `python D:/Taadaa/Hermes/deploy/hermes-home/scripts/cron_sync_watchdog.py --force` để đồng bộ sang Kibe runtime và OneDrive Shared.
2. **Chuẩn hóa fallback đa người dùng trong `run_capture_phase_a.py`:**
   - Định nghĩa fallback ADB công khai cho XiaoWei và user Admin:
     ```python
     XIAOWEI_DEFAULT_ADB = Path("C:/Program Files (x86)/xiaowei/tools/adb.exe")
     ADMIN_BUNDLED_ADB = Path("C:/Users/Admin/AppData/Local/Programs/GemPhoneFarm/resources/app.asar.unpacked/resources/scrcpy/adb/adb.exe")
     ```
   - Trong `resolve_adb_path`: Ưu tiên kiểm tra `XIAOWEI_DEFAULT_ADB.is_file()` trước khi fallback về bundled GemPhoneFarm hoặc bare string `"adb"`.
