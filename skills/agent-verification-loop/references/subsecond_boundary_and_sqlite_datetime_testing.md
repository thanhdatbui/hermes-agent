# Subsecond Precision Boundary & SQLite Time Formats in Test Suites

## 1. Bản chất sự cố lệch Microsecond
Khi các module xử lý thời gian kiểm tra boundary `end_of_day` (`23:59:59`):
- Nếu định nghĩa `end_of_day = dt.replace(hour=23, minute=59, second=59, microsecond=999999)`:
  - Một datetime đầu vào có subsecond như `2026-10-15 23:58:59.500000` cộng thêm `1 phút` thành `2026-10-15 23:59:59.500000`.
  - Phép so sánh `buffered_dt > end_of_day` trả về `False` (vì `.500000 < .999999`), khiến giá trị lọt qua mà không được cap.
  - Tuy nhiên khi format ra chuỗi `%Y-%m-%d %H:%M:%S` cho SQLite, phần subsecond bị cắt cụt, tạo ra trạng thái giả mạo hoặc vi phạm logic boundary.

## 2. Giải pháp kỹ thuật chuẩn mực
- Chuẩn hóa `end_of_day = dt.replace(hour=23, minute=59, second=59, microsecond=0)` ngay từ đầu.
- Khi đó `23:59:59.500000 > 23:59:59.000000` trả về `True`, kích hoạt cap chuẩn xác về `23:59:59`.

## 3. Quy chuẩn viết Regression Test
Bắt buộc có assertion chứng minh bug cũ thực sự xảy ra trước khi nghiệm thu fix:
```python
def test_subsecond_capping_regression_proof():
    dt = datetime(2026, 10, 15, 23, 58, 59, 500000)
    buffered = dt + timedelta(minutes=1)
    # Chứng minh với end_of_day cũ, giá trị không được cap
    old_end = dt.replace(hour=23, minute=59, second=59, microsecond=999999)
    assert not (buffered > old_end), "Bug cũ: 23:59:59.500000 bị lọt không cap"

    # Chứng minh với end_of_day mới, giá trị được cap chính xác
    fixed_end = dt.replace(hour=23, minute=59, second=59, microsecond=0)
    assert buffered > fixed_end, "Fix mới: được cap về 23:59:59"
```
