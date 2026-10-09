# TikTok Video Upload Cadence & Inventory Depletion Estimation

> 📌 **Ground Truth Ledger & Automation Roots**:
> - **Sổ cái upload liên tiến trình**: `C:\ProgramData\Taadaa\tiktok-upload-concurrency-v1\shift_upload_history.json` (được bảo vệ bởi `slot-*.lock` và `shift_upload_history.json.lock`).
> - **Khóa thư mục video**: `D:\TIKTOK-videonuoinick\<folder>` (Folder = `(Machine - 1) * 8 + Slot_Index`).
> - **Workbooks tiến độ**: `D:\OneDrive\TaadaaData\kibe\Tik1.xlsx` .. `Tik8.xlsx` (Cột `Video Đã Đăng`).

---

## 1. Cơ Chế Điều Phối Nhịp Đăng Video (Upload Cadence Mechanics)

### A. Lịch xoay tua ngày Chẵn / Lẻ (Day Parity)
Xác định trong `C:\Users\Kibe\AppData\Local\hermes\scripts\tiktok_runner.py`:
- **Ngày Lẻ (`date % 2 == 1`)**: Chạy Row Lẻ (`Row 1, 3, 5, 7`).
- **Ngày Chẵn (`date % 2 == 0`)**: Chạy Row Chẵn (`Row 2, 4, 6, 8`).
- **Tần suất cơ sở**: Mỗi tài khoản chỉ được lên lịch chạy **1 lần mỗi 2 ngày** (cách 1 ngày nghỉ 1 ngày).

### B. Giới hạn cứng 1 video / ca / nick (`_ShiftUploadLedger`)
- Nằm tại `python_runner/flows/multi_machine_feed_session.py`.
- Mỗi ca có 2 phiên (Phiên 1 và Phiên 2):
  - Khi Phiên 1 đăng video thành công, mã hash `logical_day:machine:account` được ghi vào `shift_upload_history.json`.
  - Phiên 2 cùng ca tự động phát hiện `already_uploaded_in_shift` và **skip an toàn**, tuyệt đối không đăng lặp video thứ 2 trong cùng 1 ca.

### C. Bộ lọc ngày nghỉ dưỡng sinh (Organic Rest Day Gate)
- Hàm `_is_account_organic_rest_day(machine, row, date_str)`:
  ```python
  h = hashlib.md5(f"{date_str}:{m_num}:{r_num}".encode("utf-8")).hexdigest()
  return (int(h[:8], 16) % 3) == 0
  ```
- **Xác suất 1/3 số ngày chạy là ngày nghỉ dưỡng sinh**:
  - Vào ngày này: Nick chỉ lướt feed rửa trust, **0 Follow, 0 Upload** (`organic-rest-day-upload-disabled`).
  - Trừ khi tài khoản đang được gắn cờ `account_boost` (cắn đề xuất viral).

---

## 2. Thống Kê Thực Tế Từ 3.905 Lượt Đăng Thành Công (Empirical Stats)

Dựa trên phân tích 3.241 khoảng cách giữa 2 lần đăng liên tiếp của từng tài khoản trong `shift_upload_history.json`:
- **Cách 2 ngày**: **53.4%** (lượt chạy kế tiếp đăng thành công, không dính dưỡng sinh).
- **Cách 4 ngày**: **27.4%** (lượt chạy kế tiếp dính 1 ngày nghỉ dưỡng sinh, lùi sang lượt sau).
- **Cách 6 ngày**: **8.5%** (dính 2 lượt dưỡng sinh / skip liên tiếp).
- **Cách 1 ngày**: 3.0% (ngoại lệ khi bù ca hoặc chuyển tháng 31 sang ngày 1).

👉 **Nhịp đăng trung bình thực tế toàn Farm**: **3.31 ngày / 1 video / nick** (~ **0.30 video/ngày/nick**, tức **9 – 10 video/tháng/nick**).  
*(Trường hợp nhanh nhất lý thuyết không vướng dưỡng sinh: 1 video / 2 ngày = 0.50 video/ngày/nick).*

---

## 3. Công Thức & Thời Gian Cạn Kho Video (Depletion Formulas)

### A. Nick Mới Tinh (Kho 40 – 45 clip chuẩn quy hoạch)
- **Công thức**: $T_{\text{days}} = \text{Số Video} \times 3.31$
- **Kho 40 clip**: $40 \times 3.31 \approx 132$ ngày (~ **4.4 tháng**).
- **Kho 45 clip**: $45 \times 3.31 \approx 149$ ngày (~ **5.0 tháng**).
*(Kịch bản chạy nhanh 2 ngày/clip: 80 – 90 ngày ~ 2.7 – 3.0 tháng).*

### B. Đánh Giá Tồn Kho & Hạn Cạn Kho Lũy Kế Theo Dàn Tik (Mốc 10/2026)
| Dàn Tik | Video Đã Đăng (TB) | Kho Render (TB) | Còn Lại (TB) | Thời Gian Cạn Kho (TB) |
|---|---|---|---|---|
| **Tik 1** | 23.0 clip (max 32) | 45.5 clip | **22.5 clip** (min 13) | **~74 ngày (~2.5 tháng)** *(Nick nhanh nhất còn ~43 ngày ~ 1.4 tháng)* |
| **Tik 2** | 11.7 clip (max 18) | 45.3 clip | **33.6 clip** (min 27) | **~111 ngày (~3.7 tháng)** |
| **Tik 3** | 9.8 clip (max 13) | 45.6 clip | **35.7 clip** (min 32) | **~118 ngày (~3.9 tháng)** |
| **Tik 4** | 8.1 clip (max 12) | 46.2 clip | **38.0 clip** (min 22) | **~126 ngày (~4.2 tháng)** |
| **Tik 5 – 8**| 2.9 – 3.8 clip | 42.5 – 44.9 clip | **39.0 – 41.9 clip** | **~130 – 140 ngày (~4.5 tháng)** |
| **Admin Tik1..8**| 0 – 1 clip | ~43.0 clip | **~43.0 clip** | **~140 – 150 ngày (~5.0 tháng)** |

---

## 4. Script Kiểm Tra Nhanh O(1) Tồn Kho Toàn Farm (Zero-Disk-Scan)

```python
import openpyxl, os
from pathlib import Path

kibe_dir = Path(r"D:\OneDrive\TaadaaData\kibe")
media_root = Path(r"D:\TIKTOK-videonuoinick")

for row_idx in range(1, 9):
    wb_p = kibe_dir / f"Tik{row_idx}.xlsx"
    if not wb_p.is_file():
        wb_p = kibe_dir / f"tik{row_idx}.xlsx"
    wb = openpyxl.load_workbook(wb_p, read_only=True, data_only=True)
    sheet = wb.active
    headers = [str(c.value or "").strip().lower() for c in sheet[1]]
    may_idx = next(i for i, h in enumerate(headers) if h in ("máy", "may", "machine"))
    posted_idx = next(i for i, h in enumerate(headers) if "đã đăng" in h or "da dang" in h)
    
    rems = []
    for r in sheet.iter_rows(min_row=2, values_only=True):
        if not r or r[may_idx] is None: continue
        m = int(r[may_idx])
        posted = int(float(r[posted_idx] or 0))
        folder_str = str((m - 1) * 8 + row_idx)
        f_dir = media_root / folder_str
        max_v = max([int(os.path.splitext(f)[0]) for f in os.listdir(f_dir) if f.endswith(".mp4") and os.path.splitext(f)[0].isdigit()] or [0]) if f_dir.is_dir() else 0
        rems.append(max(0, max_v - posted))
    wb.close()
    print(f"Tik {row_idx}: Con lai TB = {sum(rems)/len(rems):.1f} clip (Min={min(rems)}, Max={max(rems)})")
```
