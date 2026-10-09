# Cơ Chế Dưỡng Sinh Ngẫu Nhiên Từng Nick (Per-Account Organic Rest 1/3)

## 1. Bối cảnh & Lý do thay thế Modulo 6 toàn Farm
- **Hạn chế của Modulo 6 cũ:**
  - Cứ đến Day 2 hoặc Day 5 trong chu kỳ 6 ngày, toàn bộ 80 máy đồng loạt không follow, không upload (Pure Feed).
  - Thuật toán kiểm duyệt cụm (Cluster Bot Detection) của TikTok dễ dàng phát hiện pattern khi toàn bộ dải IP/Proxy cùng chuyển trạng thái đồng loạt.
- **Giải pháp Per-Account Organic Rest:**
  - Giữ cố định lịch ngày Chẵn (Row 2, 4, 6, 8) / ngày Lẻ (Row 1, 3, 5, 7) để giữ Routine người dùng theo khung giờ.
  - Phân tán trạng thái Dưỡng sinh ngẫu nhiên độc lập cho từng nick nhưng nhất quán trong ngày.

## 2. Công thức băm xác suất chuẩn xác 1/3 (~33.33%)
- Tỷ lệ cày/nghỉ của 1 nick trong Modulo 6 cũ: 2 ngày cày, 1 ngày nghỉ -> Xác suất dưỡng sinh chuẩn là $1/3 \approx 33.33\%$.
- Hàm băm xác định:
```python
def _is_account_organic_rest_day(machine: Any, row: Any, date_str: str | None = None) -> bool:
    try:
        m_num = int(machine or 0)
    except (ValueError, TypeError):
        m_num = 0
    try:
        r_num = int(row or 1)
    except (ValueError, TypeError):
        r_num = 1
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")
    h = hashlib.md5(f"{date_str}:{m_num}:{r_num}".encode("utf-8")).hexdigest()
    return (int(h[:8], 16) % 3) == 0
```
- **Đặc tính Deterministic:** Cùng 1 ngày `YYYY-MM-DD`, cả Phiên 1 (Sáng) và Phiên 2 (Chiều) của cùng 1 nick (Machine, Row) đều ra chung 1 kết quả `is_organic_rest` thống nhất.
- Cache kết quả vào `child_ctx.config["_is_organic_rest"]` giữa các hook (Follow Hook và Upload Hook) để tránh trôi ngày lúc giáp ranh nửa đêm.

## 3. Quy tắc Safe-Skip khi Dưỡng Sinh
- **Follow Hook:**
  - Trả về `status: "skipped"`, `reason: "organic-rest-day-pure-feed"`.
  - Giữ nguyên `reason: "rest-day-follow-disabled-pure-feed"` nếu do cờ toàn cục `TAADAA_REST_DAY_NO_FOLLOW`.
- **Upload Hook:**
  - Trả về `status: "skipped"`, `reason: "organic-rest-day-no-upload"`.
  - Tự động bỏ qua mà không ghi nhận lỗi.

## 4. Định dạng báo cáo Cron Watchdog (`feed_session_watchdog.py`)
- Báo cáo phân rã rõ ràng thay vì in một dãy số máy bị skip:
  - Hiển thị block:
    ```text
    • Chế độ Dưỡng Sinh (Organic Rest ~33%):
      🌿 Nghỉ dưỡng sinh (26 máy): M2, M5, ... (Chỉ lướt feed, 0 follow, 0 up)
    ```
  - Mục Follow chéo: `+ Bỏ qua (47): Đang dưỡng sinh (26); Chưa đủ 10 video (21)`
  - Mục Đăng Video: `+ Bỏ qua (49): Đang dưỡng sinh (26); Chưa render/thiếu video (23)`
