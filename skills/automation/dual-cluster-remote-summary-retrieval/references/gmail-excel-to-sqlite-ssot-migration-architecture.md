# Triển Khai Chuyển Đổi SSOT: Từ Excel sang SQLite (`farm_master.db`) Toàn Diện

## 1. Bối Cảnh Phân Mảnh Dữ Liệu Farm (Excel vs SQLite)
- **Thực trạng phát hiện (2026-11-05):** 
  - TikTok Nuôi Feed và TikTok Bật 2FA đã chuyển đổi sang dùng `farm_master.db` làm SSOT.
  - Tuy nhiên, toàn bộ luồng **Đăng ký Gmail (`register gmail`)** và các script **Bật 2FA Gmail** (`post_morning_gmail_2fa_watchdog.py`, `enable_2fa_for_new_account.py`, `enable_gmail_2fa_device.py`) vẫn đang đọc/ghi trực tiếp trên file Excel OneDrive (`gmail_clean_v2.xlsx`, `taikhoan_run_safe.xlsx`, `PROXYgandienthoai.xlsx`).
- **Hậu quả:** Thường xuyên dính lỗi khóa file (`PermissionError`, `RecallOnDataAccess`), đụng độ tiến trình (race condition), phụ thuộc vào OneDrive hydration và làm lệch dữ liệu giữa 2 PC Kibe và Admin.

## 2. Thiết Kế Chuyển Đổi Chuẩn SSOT cho Gmail

### A. Bảng Cơ Sở Dữ Liệu Đích (`mailboxes` trong `farm_master.db`):
- `email TEXT PRIMARY KEY`
- `provider TEXT` (mặc định `'gmail'`)
- `password TEXT`
- `twofa_secret TEXT` (ghi nhận key 2FA sau khi bật)
- `oauth_refresh_token TEXT`
- `oauth_client_id TEXT`
- `oauth_status TEXT`
- `owner TEXT` (`'kibe'` hoặc `'admin'`)
- `source TEXT` (e.g. `'register-gmail'`)
- `run_id TEXT`

### B. Thay Đổi Tại Khâu Merge Kết Quả (`merge_success_results.py`):
1. **SSOT First:** Ghi trực tiếp các tài khoản vừa tạo thành công vào bảng `mailboxes` của `farm_master.db` trên node local:
   ```python
   def sync_success_items_to_sqlite(items):
       db_path = os.environ.get("FARM_MASTER_DB", r"D:\Taadaa\data\farm_master.db")
       if not os.path.exists(db_path):
           return
       conn = sqlite3.connect(db_path)
       cursor = conn.cursor()
       run_id = os.environ.get("GMAIL_RUN_ID") or datetime.now().strftime("%Y%m%d_%H%M%S")
       for item in items:
           if "password" not in item and item.get("source_file"):
               item = {**load_result_file(item["source_file"]), **item}
           email = item["email"].strip().lower()
           password = str(item["password"]).rstrip()
           stt = int(item["stt"])
           twofa_secret = str(item["secret_key"]).strip() if item.get("secret_key") else None
           owner = "admin" if stt >= 200 else "kibe"
           source = "register-gmail"
           cursor.execute(
               """
               INSERT OR REPLACE INTO mailboxes (email, provider, password, twofa_secret, owner, source, run_id)
               VALUES (?, 'gmail', ?, ?, ?, ?, ?)
               """,
               (email, password, twofa_secret, owner, source, run_id)
           )
       conn.commit()
       conn.close()
   ```
2. **Mirror 1 chiều:** Nếu cần file Excel để phục vụ các quy trình xem thủ công, chỉ export một chiều từ SQLite ra file Excel/CSV, tuyệt đối cấm dùng file Excel làm nguồn chân lý.

### C. Thay Đổi Tại Các Watchdog Bật 2FA Gmail:
1. Đổi truy vấn nguồn từ `openpyxl.load_workbook(CLEAN_V2_EXCEL)` sang SQL:
   ```sql
   SELECT email, password FROM mailboxes 
   WHERE provider = 'gmail' AND (twofa_secret IS NULL OR twofa_secret = '') AND owner = ?
   ```
2. Khi bật 2FA thành công trên thiết bị:
   ```sql
   UPDATE mailboxes SET twofa_secret = ? WHERE email = ?
   ```

### D. Đồng Bộ Giữa 2 Node LAN (`sync_2fa_to_admin.py`):
- Tận dụng cơ chế replication 2 chiều qua LAN (`sync_2fa_to_admin.py` tích hợp trong cronjob `hourly-stale-post-receipts-reconcile` - ID: `8d6b3c18dd64`):
  1. **Reconcile Pull:** Kéo các tài khoản mailbox thuộc dải Admin (`owner = 'admin'`) từ SQLite Admin về cập nhật vào SQLite Kibe qua `INSERT INTO mailboxes ... ON CONFLICT(email) DO UPDATE`.
  2. **Reconcile Push:** Đẩy các tài khoản mailbox thuộc dải Kibe (`owner = 'kibe'`) từ SQLite Kibe sang SQLite Admin.
- **Nguyên tắc Single-Writer:** Kibe chỉ ghi đè dải máy/tài khoản của Kibe, Admin chỉ ghi đè dải máy/tài khoản của Admin. Triệt tiêu 100% nguy cơ tranh chấp ghi hay split-brain.
