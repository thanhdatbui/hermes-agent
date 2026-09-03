# Hướng Dẫn Kiểm Tra & Báo Cáo Tiến Độ Ca Nuôi Acc (TikTok Feed Runs)

Tài liệu này tổng hợp quy trình kiểm tra trạng thái ca nuôi acc (sáng/trưa/tối) theo thời gian thực trên farm Taadaa.

---

## 1. Nguồn Dữ Liệu & Vị Trí Lưu Trạng Thái

Khi kiểm tra ca nuôi trong ngày (`YYYY-MM-DD`):

1. **Manifest & Lịch Nuôi Trong Ngày**:
   - `D:/Taadaa/runtime/kibe/cron-state/manifests/<YYYY-MM-DD>/ACTIVE.json`
   - `D:/Taadaa/runtime/kibe/cron-state/manifests/<YYYY-MM-DD>/assignment-v1-*.json`
   - Xác định: Ngày chẵn (Lane A: Row 2, 4, 2) hay Ngày lẻ (Lane B: Row 1, 3, 1), tổng số slot/máy tham gia.

2. **Tiến Trình Đang Chạy (Live Lease & PID)**:
   - `D:/Taadaa/runtime/kibe/cron-state/runner-live-lease/<YYYY-MM-DD>.json`
   - Chứa thông tin PID, Row đang chạy, danh sách `machines`, thời gian bắt đầu (`started_at`) và hạn lease (`expires_at`).

3. **Thư Mục Kết Quả Live Run**:
   - `D:/Taadaa/runtime/kibe/live/<YYYY-MM-DD>/`
   - Mỗi đợt chạy tạo một thư mục con dạng `row-<R>-<HHMMSS>/` (ví dụ `row-2-071501`, `row-2-091508`).

---

## 2. Script Một Dòng Kiểm Tra Nhanh (Python One-liner)

Chạy trong repo `D:/Taadaa/tiktok-luot nuoi acc`:

```python
import os, glob, json
from datetime import datetime

today = datetime.now().strftime('%Y-%m-%d')
live_dir = f'D:/Taadaa/runtime/kibe/live/{today}'

if os.path.exists(live_dir):
    runs = sorted(os.listdir(live_dir))
    for r in runs:
        r_path = os.path.join(live_dir, r)
        mans = glob.glob(os.path.join(r_path, '**/machines/machine_*/2026*/run_manifest.json'))
        stats = {}
        for m in mans:
            with open(m, 'r', encoding='utf-8') as fp:
                d = json.load(fp)
                st = d.get('final_status') or d.get('status') or 'UNKNOWN'
                stats[st] = stats.get(st, 0) + 1
        print(f"[{r}] Tổng máy: {len(mans)} | Thống kê: {stats}")
else:
    print("Chưa có live run cho ngày hôm nay.")
```

---

## 3. Cấu Trúc Báo Cáo Chuẩn Cho User

Khi user hỏi *"kiểm tra ca sáng/trưa/tối chạy như nào"*:
- Xác định rõ ca nuôi của hàng nick nào (Row 1..6) theo tính chất ngày chẵn/lẻ.
- Liệt kê theo từng đợt chạy (thời gian, tổng số máy, số máy SUCCESS, số máy MANUAL/Lỗi kèm phân loại nguyên nhân).
- Kiểm tra trạng thái Follow Hook (có kích hoạt Zero-Video Guard không) và Upload Hook (ở phiên 3).
- Báo cáo ngắn gọn, đúng số liệu thực tế từ artifacts và manifest.
