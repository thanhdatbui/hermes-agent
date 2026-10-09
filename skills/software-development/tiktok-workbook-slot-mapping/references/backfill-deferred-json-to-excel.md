# Backfill TikTok Reg Deferred JSON to Excel & Xử Lý Lệch Slot (2026-09-29)

## 1. Hiện Tượng & Nguyên Nhân Gốc (Root Cause)
- **Hiện tượng**: Báo cáo Preflight Reg Bù (ví dụ: `[PREFLIGHT REG BÙ ROW 6]`) liên tục báo lỗi `Máy đã đủ 8 acc (Lệch Excel - Cần kiểm tra backfill)`. Máy không thể reg thêm vì switcher app TikTok đã kịch trần 8 tài khoản, nhưng file Excel `taikhoan_run_safe.xlsx` và `taikhoan_dat_v2_updated .xlsx` vẫn ghi `None` / trống slot.
- **Nguyên nhân 1 (Exclusive Lock vs OneDrive)**:
  - Khi `_run_all_targets.py` hoàn thành reg, bước `write_deferred_results_sequential` gọi `_acquire_workbook_write_lock` mở file bằng Win32 `CreateFileW` với mode độc quyền (`dwShareMode = 0`).
  - Do các file Excel nằm trong thư mục `D:\OneDrive\TaadaaData\...`, tiến trình chạy ngầm của OneDrive hoặc người dùng mở Excel khiến việc xin lock thất bại và văng `FAILED_SYNC_OSError` (`[WinError 32] The process cannot access the file because it is being used by another process`).
- **Nguyên nhân 2 (Silent Failure / Không Retry)**:
  - `_run_all_targets.py` chỉ in log `[AUTO-SYNC-WARN] Lỗi khi tự động đồng bộ vào Excel: ...` và kết thúc batch, đánh dấu `workbook_write: FAILED_SYNC_OSError`.
  - Kết quả đăng ký thành công vẫn nằm nguyên trong file `tracking_result_*.json` ở runtime artifact (`D:/Taadaa/runtime/<host>/artifacts/runs/social-batch-all/<run_id>/batch_1/stt_<M>/`) mà không có cơ chế tự động thử lại hay hàng đợi bù.
- **Nguyên nhân 3 (Vòng lặp Reg Bù Mù)**:
  - Sổ theo dõi thiếu -> Preflight quét thấy thiếu slot -> Lại kích hoạt reg bù -> Lên máy thấy đủ 8 nick -> Báo lỗi lặp đi lặp lại.

## 2. Quy Trình Đối Soát & Backfill Chuẩn Xác

### Bước 1: Quét Toàn Bộ File JSON Thành Công Chưa Ghi Excel
Chạy script đối soát O(1) qua Python kiểm tra các run gần nhất trong `artifacts/runs/social-batch-all`:
```python
import json
from pathlib import Path
import openpyxl

host = "admin"  # hoặc "kibe"
trk_path = Path(rf"D:\OneDrive\TaadaaData\{host}\taikhoan_dat_v2_updated .xlsx")
wb = openpyxl.load_workbook(trk_path, read_only=True)
ws = wb["Tài Khoản"] if "Tài Khoản" in wb.sheetnames else wb.active

existing_uids = {str(r[2] or "").strip().lower().lstrip("@") for r in ws.iter_rows(values_only=True) if r and len(r) >= 3 and r[2]}
existing_mails = {str(r[5] or "").strip().lower() for r in ws.iter_rows(values_only=True) if r and len(r) >= 6 and r[5]}

base = Path(f"D:/Taadaa/runtime/{host}/artifacts/runs/social-batch-all")
missing_items = []
for p in sorted(base.glob("20*")):
    for b in p.glob("batch_*"):
        for s in b.glob("stt_*"):
            for j in s.glob("tracking_result_*.json"):
                data = json.loads(j.read_text(encoding="utf-8"))
                if data.get("status") == "SUCCESS":
                    uid = str(data.get("tiktok_id") or "").strip().lower().lstrip("@")
                    mail = str(data.get("email") or "").strip().lower()
                    stt = int(data.get("stt"))
                    if uid not in existing_uids and mail not in existing_mails:
                        missing_items.append((p.name, stt, uid, mail, str(j)))
```

### Bước 2: Backup Workbook Trước Khi Ghi
BẮT BUỘC backup file Excel sang `.bak_backfill_<timestamp>` trước khi can thiệp.

### Bước 3: Nạp Bù Vào Sổ Gốc `taikhoan_dat_v2_updated .xlsx`
1. Đọc dữ liệu từ file JSON: `tiktok_id`, `email`, `mail_password`, `password`, `created_date`, `serial`.
2. Tính `expected_tik`:
   - Cụm Admin (máy >= 201): `expected_tik = (stt - 201) * 8 + slot`
   - Cụm Kibe (máy 1-80): `expected_tik = (stt - 1) * 8 + slot`
3. Tra cứu dòng tương ứng `(stt, expected_tik)`:
   - Nếu đã có dòng trống ID: update vào dòng đó.
   - Nếu chưa có dòng (như cụm Admin): append dòng mới ở cuối sheet với đủ 10 cột chuẩn:
     `[stt, expected_tik, uid, pwd, 2fa, mail, mail_pwd, dob, created, serial]`.

### Bước 4: Đồng Bộ Sang `taikhoan_run_safe.xlsx`
BẮT BUỘC gọi `sync-safe-workbook.py` với đúng biến môi trường `TAADAA_HOST_ID`:
```bash
# Đối với cụm Admin:
export TAADAA_HOST_ID=admin
python "D:/Taadaa/tiktok-luot nuoi acc/scripts/sync-safe-workbook.py" \
  --source "D:/OneDrive/TaadaaData/admin/taikhoan_dat_v2_updated .xlsx" \
  --output "D:/OneDrive/TaadaaData/admin/taikhoan_run_safe.xlsx" \
  --tik-dir "D:/OneDrive/TaadaaData/admin"

# Đối với cụm Kibe:
export TAADAA_HOST_ID=kibe
python "D:/Taadaa/tiktok-luot nuoi acc/scripts/sync-safe-workbook.py" \
  --source "D:/OneDrive/TaadaaData/kibe/taikhoan_dat_v2_updated .xlsx" \
  --output "D:/OneDrive/TaadaaData/kibe/taikhoan_run_safe.xlsx" \
  --tik-dir "D:/OneDrive/TaadaaData/kibe"
```

### Bước 5: Kiểm Chứng Lại Preflight
Gọi hàm kiểm tra `get_missing_machines_for_row(row_idx)` để xác nhận danh sách missing không còn chứa các máy vừa nạp bù.
