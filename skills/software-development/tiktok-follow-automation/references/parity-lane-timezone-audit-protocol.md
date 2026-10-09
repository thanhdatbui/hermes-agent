# Parity Lane Timezone & State Audit Protocol

## 1. Múi Giờ và Phân Rã Ngày Giờ Chạy Farm (Asia/Ho_Chi_Minh vs UTC)
- **Quy tắc Vàng về Múi Giờ:**
  - Hệ thống Phone Farm và các cron runner chạy hoàn toàn theo **Giờ Việt Nam (`Asia/Ho_Chi_Minh` / GMT+7)**.
  - Các file trạng thái `follow_state_*.json` lưu timestamp dạng ISO 8601 UTC (`+00:00` hoặc `Z`), ví dụ: `2026-10-02T23:30:00+00:00`.
  - **CẤM TUYỆT ĐỐI** so sánh/lọc chuỗi thô (`ts.startswith('2026-10-02')` hoặc `ts[:10]`). 
  - Ca sáng 06:30 - 08:30 sáng ngày 03/10 (VN) trong file JSON sẽ mang timestamp `2026-10-02T23:30:00+00:00`. Nếu parse chuỗi thô sẽ báo cáo sai thành "Row 1 chạy vào ngày chẵn 02/10".

- **Cách parse chuẩn khi audit dữ liệu state:**
```python
from datetime import datetime
from zoneinfo import ZoneInfo

VN_TZ = ZoneInfo("Asia/Ho_Chi_Minh")

def parse_vn_date(ts_str: str) -> str:
    # ISO string UTC -> VN date YYYY-MM-DD
    dt = datetime.fromisoformat(ts_str)
    return dt.astimezone(VN_TZ).strftime("%Y-%m-%d")
```

## 2. Quy Tắc Parity Lane (Chẵn / Lẻ) Theo Row
- **Ngày Lẻ (01, 03, 05, 07,...):** Chỉ các Row lẻ (Row 1, Row 3, Row 5, Row 7) được xếp lịch chạy nuôi và follow.
- **Ngày Chẵn (02, 04, 06, 08,...):** Chỉ các Row chẵn (Row 2, Row 4, Row 6, Row 8) được xếp lịch chạy nuôi và follow.
- Tuyệt đối không bao giờ có chuyện Row 1 chạy vào ngày chẵn hoặc Row 2 chạy vào ngày lẻ. Khi thấy dữ liệu bất thường, kiểm tra ngay timezone offset trước khi kết luận.

## 3. Chống Báo Cáo Khống & Phân Tách Số Liệu Minh Bạch
- **Tách rõ Tích Lũy Đa Ngày vs Hoạt Động Hàng Ngày:**
  - Không được gom tổng số acc chạy trong tuần (lũy kế) để nói như thể "mỗi ngày có 60 acc già chạy".
  - Báo cáo phải ghi rõ: "Mỗi ngày thực tế chỉ có X nick Row 1 (ngày lẻ) hoặc Y nick Row 2 (ngày chẵn) bấm follow thành công".
- **Phân loại trạng thái nick chính xác:**
  1. *Bị chặn do Gate:* Video < 10 hoặc Age < 30 ngày.
  2. *Relapse Immediate (0 follow):* Vừa thả ra phiên đầu là bị TikTok nhả ngay phát đầu (FOLLOW_FAILED), quay đầu vào cooldown lại.
  3. *Relapse Warm-up (1-5 follows):* Thả ra ăn được vài follow cữ warm-up rồi bị nhả ở các lượt tiếp theo.
  4. *Healthy (Streak = 0):* Chạy đều đặn không bị nhả.
