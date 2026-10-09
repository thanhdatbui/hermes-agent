# Quy Chuẩn Kiểm Tra Ngày Ngâm Tài Khoản (Account Aging & Creation Date Mapping)

Tài liệu hướng dẫn tra cứu ngày tạo thực tế của tài khoản Gmail trên Farm Kibe S7, tránh bẫy cột checklive và đối soát an toàn với kho `gmail_clean_v2.xlsx`.

---

## 1. Bối Cảnh & Bẫy Chết Người (Critical Pitfall: Cột "Cập Nhật")
- Trong file điều phối `D:\OneDrive\TaadaaData\kibe\master_gmail_manager.xlsx` (sheet `Kibe_Farm_S7`):
  - Cột 15 (index 14) mang tiêu đề **`Cập Nhật`**.
  - Cột này lưu timestamp ngày quét gần nhất của tool checklive (ví dụ: `2026-09-20`).
  - **HẬU QUẢ**: Nếu watchdog/script kiểm tra điều kiện ngâm `>= 7 ngày` bằng cách lấy `(d_today - d_created).days` từ cột `Cập Nhật`, toàn bộ tài khoản LIVE đều bị tính là 0 ngày tuổi (`(2026-09-20 - 2026-09-20).days = 0 < 7`). Toàn bộ danh sách candidate bị loại bỏ 100%, gây tê liệt pipeline login GPM!

---

## 2. Nguồn Ngày Tạo Chuẩn (`gmail_clean_v2.xlsx`)
- **Đường dẫn**: `D:\OneDrive\TaadaaData\kibe\gmail_clean_v2.xlsx`
- **Cấu trúc cột quan trọng**:
  - Cột 2 (index 1): `tài khoản gmail` (Email).
  - Cột 6 (index 5): `ngày tháng năm sinh` (Ngày sinh).
  - Cột 7 (index 6): `ngày tạo` (Lưu kiểu `datetime` hoặc chuỗi `YYYY-MM-DD`).
- **Đặc điểm kho**: Toàn bộ 450 tài khoản trong file này đã được tạo/nhập kho từ tháng 02/2026 đến tháng 06/2026 (tuổi > 80–180 ngày), hoàn toàn thỏa mãn điều kiện ngâm an toàn `>= 7 ngày`.

---

## 3. Pattern Code Chuẩn Cho Watchdog & Script Điều Phối

### Helper Map Cache Ngày Tạo
```python
from datetime import datetime, date
from pathlib import Path

CLEAN_GMAIL_XLSX = Path(r"D:\OneDrive\TaadaaData\kibe\gmail_clean_v2.xlsx")

def load_clean_v2_creation_dates() -> dict[str, dict]:
    """Helper map cache ngày tạo từ gmail_clean_v2.xlsx (email -> info)."""
    clean_map: dict[str, dict] = {}
    if not CLEAN_GMAIL_XLSX.exists():
        return clean_map
    try:
        import openpyxl
        wb = openpyxl.load_workbook(CLEAN_GMAIL_XLSX, data_only=True, read_only=True)
        ws = wb.active
        for r in ws.iter_rows(min_row=2, values_only=True):
            if not (r and r[1] and "@" in str(r[1])):
                continue
            em = str(r[1]).strip().lower()
            c_val = r[6] if len(r) > 6 else None
            b_val = r[5] if len(r) > 5 else None
            c_date = None
            if c_val:
                if isinstance(c_val, (datetime, date)):
                    c_date = c_val.date() if isinstance(c_val, datetime) else c_val
                else:
                    try:
                        c_date = date.fromisoformat(str(c_val).strip()[:10])
                    except Exception:
                        pass
            clean_map[em] = {
                "created_date": c_date,
                "has_birth": bool(b_val),
                "in_clean": True,
            }
        wb.close()
    except Exception as e:
        pass
    return clean_map
```

### Quy Tắc Duyệt Candidate An Toàn
```python
clean_v2_dates = load_clean_v2_creation_dates()
d_today = date.fromisoformat(today_str[:10])

# Kiểm tra điều kiện ngâm
if em_l in clean_v2_dates:
    c_date = clean_v2_dates[em_l].get("created_date")
    if c_date:
        if (d_today - c_date).days < 7:
            continue  # Chưa đủ 7 ngày ngâm an toàn, bỏ qua
    # Nếu c_date is None: mặc định coi như đủ ngâm an toàn vì thuộc kho clean_v2 nhập từ tháng 6/2026
else:
    source_val = str(r[12] or "").lower()
    if "legacy" in source_val:
        pass  # Nguồn rua_legacy đã ngâm lâu năm, an toàn
    else:
        continue  # Không có trong clean_v2 và không phải legacy -> Fail-closed để an toàn
```
