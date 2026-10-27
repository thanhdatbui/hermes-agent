# Kỷ Luật Đảm Bảo Parity Tham Số ADB Path Và Độ Phân Giải Binary Giữa Hai Cụm Kibe - Admin (28/10/2026)

## 1. Hiện Tượng Thực Tế
- Báo cáo 2FA ban đêm toàn farm:
  - Farm Kibe (Máy 1-80): Hoàn tất 23 | Bỏ qua 10 | Lỗi 36
  - Farm Admin (Máy 201-280): Hoàn tất 0 | Bỏ qua 18 | Lỗi 71
- Cụm Admin hoàn toàn liệt (0% thành công trên 71 máy mục tiêu), trong khi thiết bị vật lý vẫn online đầy đủ trên ADB daemon `192.168.110.119:5037`.

## 2. Nguyên Nhân Kỹ Thuật (Root Cause)
1. **Lệch Tham Số Lệnh Gọi Watchdog (Command-Line Asymmetry):**
   - Trong `cron_night_tiktok_2fa_watchdog.py`:
     * Khi gọi Cluster Kibe: truyền đầy đủ cờ `--adb-path C:\Program Files (x86)\xiaowei\tools\adb.exe`.
     * Khi gọi Cluster Admin qua SSH: **hoàn toàn bỏ quên cờ `--adb-path`**, runner mặc định gán `--adb-path adb`.
2. **Lỗi Fallback Hardcoded User Profile:**
   - Trên máy chủ Admin, binary `adb` không nằm trong biến môi trường hệ thống `PATH`.
   - Hàm `resolve_adb_path` trong `python_runner/run_capture_phase_a.py` fallback về `DEFAULT_BUNDLED_ADB` vốn bị hardcode cứng đường dẫn của user Kibe (`C:\Users\Kibe\AppData\Local\Programs\GemPhoneFarm\...`), không tồn tại trên user `Admin`.
   - Cả hai cơ chế fallback đều trả về `"adb"`. Khi worker tiến hành subprocess gọi ADB, hệ điều hành văng lỗi `FileNotFoundError: [WinError 2] The system cannot find the file specified: 'adb'`. Toàn bộ 71 worker crash ngay lập tức.

## 3. Quy Tắc & Giải Pháp Bắt Buộc (Invariant)
1. **Parity Command-Line Watchdog:**
   - Lệnh SSH gọi cụm Admin bắt buộc phải truyền `--adb-path 'C:\Program Files (x86)\xiaowei\tools\adb.exe'` giống hệt Kibe.
2. **Đa Dạng Hóa Binary Resolution:**
   - Trong `resolve_adb_path`: Luôn kiểm tra thêm đường dẫn XiaoWei chuẩn farm `C:\Program Files (x86)\xiaowei\tools\adb.exe` và đường dẫn GemPhoneFarm theo dynamic user home (`%LOCALAPPDATA%`) thay vì hardcode cố định một user.
3. **Kiểm Tra Nhanh Trước Khi Rerun:**
   - Trước khi rerun cụm Admin, luôn chạy 1 target canary (hoặc dry-run O(1)) qua SSH để xác nhận process con tìm thấy binary ADB và kết nối thành công tới thiết bị.
