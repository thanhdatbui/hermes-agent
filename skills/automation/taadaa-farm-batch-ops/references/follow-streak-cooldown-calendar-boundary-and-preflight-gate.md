# Chẩn Đoán Bỏ Qua Follow: Streak Cooldown Calendar Boundary vs Preflight Gate (<6 Video)

## 1. Hiện Tượng & Nghi Vấn Thường Gặp
Khi xem báo cáo watchdog `follow_session_watchdog.py`:
- *"Row 3 row 4 đều đang bị streak cooldown hay sao v?"*
- *"Streak 1 phạt có 24h mà sao hôm sau máy vẫn bị cooldown?"*
- *"Cụm Admin bị bỏ qua 48 máy 'Chưa đủ điều kiện' có phải do dính cooldown không?"*

---

## 2. Bản Chất Kỹ Thuật (Root Cause Analysis)

### A. Cơ chế Calendar Day Boundary của Streak Cooldown (`follow-released-daily-cooldown`)
Trong `python_runner/flows/multi_machine_feed_session.py`:
```python
if state.get("follow_failed"):
    failed_date = state.get("follow_failed_date") or state.get("last_failed_date")
    streak = max(1, int(state.get("fail_streak", 1) or 1))
    streak_days = 1 if streak <= 1 else (3 if streak == 2 else (5 if streak == 3 else 15))
    failed_day = datetime.strptime(str(failed_date)[:10], "%Y-%m-%d").date()
    # The policy expires after the entire calendar day failed_date + N.
    # Compare dates rather than midnight datetimes so the boundary day
    # remains blocked until the following calendar day.
    is_in_cooldown = is_in_cooldown or today <= failed_day + timedelta(days=streak_days)
```

**Tại sao Streak 1 (phạt 1 ngày / 24h) mà hôm sau vẫn bị chặn?**
1. **So sánh theo Calendar Date (`<=`):**
   - Nếu nick bị nhả follow vào ngày `31/10` (`failed_day = 2026-10-31`).
   - Với `streak = 1` $\rightarrow$ `streak_days = 1`.
   - `failed_day + timedelta(days=1) = 2026-11-01`.
   - Vào ngày `01/11`, điều kiện `today <= 2026-11-01` là **TRUE cho trọn vẹn cả ngày 01/11**.
   - Hạn phạt chỉ hết hiệu lực khi bước sang **00:00 ngày tiếp theo (02/11)**.
2. **Trường hợp vừa bị phạt trong ngày:**
   - Nếu nick bị nhả vào ca trưa (ví dụ `12:17 ngày 01/11`), `cooldown_until_at` được set là `2026-11-02T12:17:29`.
   - Đến ca chiều (14:00 ngày 01/11), nick mới chỉ nghỉ được ~2 tiếng nên chắc chắn vẫn bị gate chặn theo mốc 24h tuyệt đối.

### B. Phân Biệt "Cooldown Nhả Follow" vs "Chưa Đủ Điều Kiện"
- **`follow-released-daily-cooldown` (Cooldown nhả follow):**
  - Áp dụng cho nick **đã từng đi follow và bị TikTok nhả** (lưu trong `follow_state_<machine>_row_<row>.json`).
  - Mức phạt lũy tiến: Streak 1 = 1 ngày, Streak 2 = 3 ngày, Streak 3 = 5 ngày, Streak 4+ = 15 ngày.
- **`under-6-videos-follow-disabled` (Chưa đủ điều kiện):**
  - Áp dụng trước khi xét follow hook: Nick có `video_count < 6` hoặc `account_age_days < 21`.
  - **Không liên quan gì đến streak cooldown hay bị phạt**. Đây là dàn nick mới / đang nuôi dưỡng ban đầu, chặn đi follow sớm để tránh bị TikTok quét spam / nhả follow ngay lập tức.

---

## 3. Cách Tra Cứu O(1) Nhanh Chóng

### Kiểm tra Streak Cooldown của từng máy / hàng:
```python
import json, os
from datetime import datetime, timezone, timedelta

state_root = r"D:\Taadaa\tiktok-follow\runs\state"
# Đọc file state cụ thể:
with open(os.path.join(state_root, f"follow_state_{machine}_row_{row}.json"), "r", encoding="utf-8") as f:
    s = json.load(f)
print(f"Streak: {s.get('fail_streak')} | Fail date: {s.get('follow_failed_date')} | Until: {s.get('cooldown_until_date')}")
```

### Kiểm tra Kho Video Gốc & Video Render của Admin O(1) (Không quét đĩa):
```python
import json

# 1. Đọc snapshot tiến độ Admin đã cache
with open(r"D:\OneDrive\TaadaaData\admin\last_render_stats.json", "r", encoding="utf-8") as f:
    stats = json.load(f)
print(f"Video gốc: {stats['src_ge45']}/640 folder >= 45 clip (Tổng: {stats['src_mp4']})")
print(f"Tổng đã render Admin: {stats['total_rendered']} clip")

# 2. Đọc ledger upload hôm nay
with open(r"C:\ProgramData\Taadaa\tiktok-upload-concurrency-v1\shift_upload_history.json", "r", encoding="utf-8") as f:
    hist = json.load(f)
admin_today = [v for k, v in hist.items() if "2026-11-01" in k and int(v.get("machine") or 0) >= 201]
print(f"Admin upload hôm nay: success={sum(1 for v in admin_today if v.get('status') == 'success')}")
```
