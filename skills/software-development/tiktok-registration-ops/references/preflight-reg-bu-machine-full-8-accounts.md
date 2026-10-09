# Quy trình xử lý lỗi MACHINE_FULL_8_ACCOUNTS trong Preflight Reg Bù (ensure_row_accounts.py)

## 1. Hiện tượng & Triệu chứng
Trong quá trình chạy preflight reg bù (`ensure_row_accounts.py <row>`, thường là Row 8):
- Runner báo lỗi: `Máy đã đủ 8 acc (Lệch Excel - Cần kiểm tra backfill)`
- Chi tiết ngoại lệ trong `stdout.log` / `stderr.log`:
  `RuntimeError: [04_add_account] MACHINE_FULL_8_ACCOUNTS: Thiết bị đã đạt giới hạn 8 tài khoản TikTok`
- Nguyên nhân kỹ thuật: TikTok chỉ cho phép tối đa 8 tài khoản đăng nhập đồng thời trên 1 thiết bị. Khi đã đủ 8 nick, app ẩn nút "Thêm tài khoản" ("Add account"), khiến `social_reg_v1.py` không thể mở form đăng ký mới.

## 2. Phân loại 3 nguyên nhân cốt lõi (Root Causes)
Tại sao Excel (`Tik8.xlsx` / `taikhoan_run_safe.xlsx`) báo còn trống slot (chỉ có 7 nick), nhưng thiết bị lại có 8 nick?
1. **Thiếu Backfill (Legitimate Account)**: Nick thứ 8 đã được đăng ký hoặc đăng nhập trước đó và đã lưu trong SQLite `tiktok_tracker.db` (`farm_account_info`), nhưng chưa được sync/backfill ngược vào file Excel Master.
2. **Nick ký sinh (Parasite Account)**: Thiết bị bị dính nick từ máy khác hoặc nick thử nghiệm cũ không nằm trong danh sách 8 slot của máy (ví dụ các mục tiêu trong `watchdog_idle_parasite_reconcile.py`).
3. **Mất kết nối ADB (Device Offline)**: Máy rớt USB/ADB khiến lệnh kiểm tra bị timeout (`UI_XML_TIMEOUT`), không thể hoàn thành chu trình.

## 3. Quy trình Triage & Khắc phục O(1) chuẩn cho Coordinator

### Bước 1: Kiểm tra kết nối thiết bị
```bash
python D:/Taadaa/tools/inspect_machine.py <N>
```
Nếu báo `device offline`: Dừng ngay và báo user kiểm tra phần cứng/hub USB.

### Bước 2: Soi màn hình Switcher bằng WinRT OCR
Runner luôn lưu ảnh tại `D:/Taadaa/Tiktok_Reg/screenshots_social/<STT>_03_dropdown_*.png`:
```bash
python "C:\Users\Kibe\AppData\Local\hermes\skills\productivity\windows-native-ocr\scripts\winrt_ocr.py" "D:/Taadaa/Tiktok_Reg/screenshots_social/<STT>_03_dropdown_<timestamp>.png"
```
Đọc danh sách toàn bộ các username đang đăng nhập trên máy.

### Bước 3: Đối soát SQLite tiktok_tracker.db
```bash
python -c "import sqlite3; conn = sqlite3.connect('D:/Taadaa/data/tiktok_tracker.db'); cur = conn.cursor(); cur.execute('SELECT username, tik, updated_at FROM farm_account_info WHERE may = ?', (<N>,)); print(cur.fetchall())"
```

### Bước 4: Hướng xử lý theo kịch bản
- **Nếu là nick hợp lệ chưa backfill**: Cập nhật nick vào `Tik8.xlsx` và `taikhoan_run_safe.xlsx`. Kích hoạt `taikhoan_sync_cron_launcher.py`.
- **Nếu là nick ký sinh**: Thêm vào cấu hình TARGETS của `D:/Taadaa/tools/watchdog_idle_parasite_reconcile.py` để tự động logout khi máy rảnh.
- **Tuyệt đối tuân thủ**: Báo cáo kèm bằng chứng ảnh `MEDIA:<path>` theo Gate 6.
