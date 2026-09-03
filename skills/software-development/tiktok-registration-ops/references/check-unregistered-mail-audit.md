# Thống kê và kiểm tra Mail chưa reg TikTok khi Inventory bị lỗi

Khi thực hiện kiểm tra hoặc thống kê danh sách mail chưa đăng ký TikTok (hoặc khi `_detect_clean.py` bị chặn do `TARGET_INVENTORY_MISSING_SERIAL` trong `taikhoan_run_safe.xlsx`):

## Quick Audit Script
Chỉ cần đọc và đối chiếu 2 file `gmail_clean_v2.xlsx` (nguồn) và `taikhoan_dat_v2_updated .xlsx` (tracking) thông qua logic chuẩn:

```python
import openpyxl
from project_paths import SOURCE_WORKBOOK, TRACKING_WORKBOOK
from scripts.tiktok_target_eligibility import (
    load_source_rows,
    load_registered_mailboxes,
    mailbox_key,
    SUPPORTED_DOMAINS,
    _cell_text,
)

source_rows = load_source_rows(SOURCE_WORKBOOK)
registered = load_registered_mailboxes(TRACKING_WORKBOOK)

unregistered = []
for row in source_rows:
    stt = row.get("stt")
    email = _cell_text(row.get("email"))
    password = _cell_text(row.get("password"))
    key = mailbox_key(email)
    if not key.endswith(SUPPORTED_DOMAINS) or not password:
        continue
    if key not in registered:
        mtype = "gmail" if key.endswith("@gmail.com") else "hotmail"
        unregistered.append((int(stt) if str(stt).isdigit() else stt, email, mtype))

unregistered.sort(key=lambda x: x[0] if isinstance(x[0], int) else 999)
print(f"Tổng số mail chưa reg: {len(unregistered)}")
for stt, email, mtype in unregistered:
    print(f"- Máy {stt}: {email} ({mtype})")
```
