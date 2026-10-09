# Đối Soát Phân Bố Turn Nhả Follow (Turn Distribution) & Fast-Audit Qua State Files (2026-09-06)

## 1. Phương Pháp Trích Xuất Siêu Tốc Qua State Files (O(1) Per Account)

Khi điều tra tình trạng nhả follow hoặc số turn follow đi được trước khi bị nhả của toàn farm:
- **CẤM:** Quét đệ quy `find /d/Taadaa/runtime/kibe/live/...` hoặc dùng script `os.walk` qua hàng chục nghìn log uiautomator trong runtime (nguy cơ timeout 900s và treo I/O).
- **CHUẨN:** Đọc trực tiếp các file state tại `D:/Taadaa/tiktok-follow/runs/state/follow_state_<machine>_row_<row_index>.json`.
  - Interpreter: `D:/Taadaa/python-envs/automation/Scripts/python.exe`.
  - Các trường cốt lõi trong JSON:
    + `budget_date`: Ngày tính ngân sách hiện tại (`YYYY-MM-DD`).
    + `budget_used`: Số lượt follow thành công tích lũy trong ngày (đây chính là số turn follow đã hoàn thành).
    + `follow_failed`: Boolean (`true` nếu nick bị nhả / rate-limit trong ngày).
    + `fail_streak`: Số ngày liên tiếp bị nhả follow (1 = cooldown trong ngày, 2 = cooldown 4 ngày, >=3 = cooldown 7 ngày).
    + `last_failed_date`, `last_failed_at`: Thời điểm chính xác bị nhả follow.
    + `followed`: Danh sách UIDs kèm timestamp UTC đã follow thành công.

## 2. Benchmark Thống Kê Thực Tế Farm (Mẫu Đối Soát 96 Lượt Nhả Row 1 & Row 2)

Từ dữ liệu đối soát toàn diện ngày 2026-09-05 (Row 1 - 78 máy) và 2026-09-06 (Row 2 - 79 máy):

| Dải turn hoàn thành | Tỷ lệ trung bình | Đặc điểm & Bản chất kỹ thuật |
| :--- | :---: | :--- |
| **Turn 0** *(0 lượt)* | **50% – 60%** (54.2%) | Bị nhả ngay anchor / target đầu tiên qua Path B pull-to-refresh verification. Nút tự nảy lại `Follow`. Thường là nick bị Action-block / Shadowban sâu hoặc `fail_streak >= 2`. |
| **1 – 4 turns** | **15% – 18%** (16.7%) | Nick có trust score yếu, vừa tương tác follow vài lượt thì thuật toán TikTok bóp rate-limit ngay. |
| **5 – 9 turns** | **2% – 20%** (11.5%) | Hoàn thành được khối lượng tương tác cơ bản của 1 phiên follow trước khi dừng. |
| **10 – 14 turns** | **4% – 6%** (5.2%) | Hoàn thành gần trọn vẹn chỉ tiêu 1 phiên (chỉ tiêu 15-20 lượt/phiên). |
| **15 – 50 turns** | **6% – 19%** (12.5%) | Nick có trust score rất tốt, chạy bền qua 1-2 phiên (nhiều máy như M26, M46, M72 đạt 49–50 follow) trước khi chạm trần rate-limit ngày của TikTok (~50-60 lượt). |

## 3. Script Mẫu Trích Xuất Nhanh Phân Bố Turn Nhả Follow

```python
import json
from pathlib import Path

state_dir = Path("D:/Taadaa/tiktok-follow/runs/state")
target_date = "2026-09-06"
row_index = 2

files = sorted(state_dir.glob(f"follow_state_*_row_{row_index}.json"))
buckets = {"0": 0, "1-4": 0, "5-9": 0, "10-14": 0, "15+": 0}

for f in files:
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
        if data.get("budget_date") == target_date and data.get("follow_failed"):
            used = data.get("budget_used", 0)
            if used == 0:
                buckets["0"] += 1
            elif 1 <= used <= 4:
                buckets["1-4"] += 1
            elif 5 <= used <= 9:
                buckets["5-9"] += 1
            elif 10 <= used <= 14:
                buckets["10-14"] += 1
            else:
                buckets["15+"] += 1
    except Exception:
        pass

print("Distribution:", buckets)
```
