# Cơ Chế Ngày Dưỡng Sinh Hữu Cơ (Organic Rest Day - 1/3 Xác Suất)

## 1. Nguyên Lý Hoạt Động
Trong kịch bản nuôi tài khoản đa luồng `multi_machine_feed_session.py`:
Mỗi tài khoản được định danh bởi cặp `(machine, row)`. Để giảm rủi ro tài khoản bị gắn cờ do hành vi lặp lại rập khuôn (luôn follow hoặc luôn upload mỗi ngày), hệ thống áp dụng cơ chế ngày dưỡng sinh hữu cơ độc lập cho từng nick với xác suất ~33.33% (1/3).

Hàm tính toán:
```python
def _is_account_organic_rest_day(machine: int, row: int, date_str: str | None = None) -> bool:
    """Xác định ngẫu nhiên nhưng nhất quán trong ngày xem nick có phải ngày dưỡng sinh (1/3 xác suất) hay không."""
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")
    h = hashlib.md5(f"{date_str}:{machine}:{row}".encode("utf-8")).hexdigest()
    # int mod 3 == 0 -> xác suất đúng 1/3 (~33.33%)
    return (int(h[:8], 16) % 3) == 0
```

## 2. Đặc Điểm Kỹ Thuật
- **Nhất quán theo ngày (Deterministic per day):** Cùng một máy và dòng tài khoản trong một ngày sẽ luôn cho ra cùng kết quả True/False bất kể script chạy lại bao nhiêu lần.
- **Không cần cấu hình thủ công:** Không cần can thiệp file config hoặc database trạng thái, hash MD5 tự động phân bổ đồng đều 1/3 số nick nghỉ dưỡng sinh mỗi ngày và tự động xoay vòng sang các nick khác vào ngày tiếp theo.
- **Tác động lên các Hook:**
  - `_run_follow_hook`: Nếu trúng ngày dưỡng sinh, hook ghi nhận skipped với reason `organic-rest-day-pure-feed`, tài khoản chỉ lướt feed ngẫu nhiên mà không thực hiện hành động follow.
  - `_run_upload_hook`: Nếu trúng ngày dưỡng sinh, hook ghi nhận skipped với reason `organic-rest-day-no-upload`, tài khoản không tải lên video.
- **Tương thích cờ toàn cục:** Nếu môi trường đặt `TAADAA_REST_DAY_NO_FOLLOW=1` hoặc cấu hình đặt `rest_day_no_follow: true`, toàn bộ nick trên toàn máy vẫn được ép nghỉ follow như cũ.
