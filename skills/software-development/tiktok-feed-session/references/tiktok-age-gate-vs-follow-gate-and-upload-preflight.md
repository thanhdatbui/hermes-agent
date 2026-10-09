# TikTok Age Gate vs Follow Gate & Upload Preflight Pitfalls

## 1. Bối cảnh 2 tầng bảo vệ Nick TikTok (Age Gate vs Follow Gate)

Trên hệ thống Phone Farm (80-160 máy Android Samsung S7), mỗi máy nuôi 8 tài khoản phân bổ theo 8 Row/Ca chạy:
- **Tầng 1: Age Gate (Publishing Gate)**: Kiểm tra tuổi tài khoản trước khi cho phép đăng video đầu tiên.
- **Tầng 2: Follow Gate (Social Graph Gate)**: Điều kiện để tài khoản được phép thực hiện follow chéo (Module 1/Module 2) là **PHẢI ĐĂNG ĐỦ >= 10 VIDEO** và không rơi vào ca nghỉ Dưỡng sinh (Organic Rest ~33%).

### Nghịch lý Warm-up kéo dài khi Hard-Block 10 ngày
- Do 1 máy chia 8 nick (mỗi ca chỉ chạy 1 nick) và có chế độ Organic Rest xoay vòng 1/3 số ca, một nick thực tế mất **35 – 45 ngày (1.5 tháng)** mới đăng đủ 10 video.
- Trong 1.5 tháng đó, nick đã có lịch sử đăng nhập lặp lại, lướt feed, xem video, thả tim, đọc comment giãn cách qua nhiều tuần.
- **Hệ quả**: Nếu áp dụng Age Gate cứng 10 ngày (cấm đăng video trong 10 ngày đầu), tổng thời gian warm nick bị đội lên thành **gần 2 tháng**, gây lãng phí chu kỳ máy và giảm throughput farm.
- **Chiến lược tối ưu**:
  - Giữ nguyên **Follow Gate (>= 10 video)** làm rào chắn an toàn tối cao chống checkpoint/ban khi tương tác mạnh.
  - Hạ **Age Gate** từ 10 ngày xuống **2 – 3 ngày**: Sau khi reg, nick chỉ cần ngâm 48 – 72h, lướt feed nhẹ và hoàn thiện profile là có thể bắt đầu đăng video đầu tiên để kích hoạt sớm chu trình 10 video.

---

## 2. Pitfall Kỹ thuật: Fail-closed do Parser Ngày tạo (`upload_preflight.py`)

### Hiện tượng
Watchdog báo cáo hàng loạt máy bị bỏ qua đăng video với nhãn "Khác" hoặc log `status=skipped, reason=account_creation_date_unverifiable`, dù kiểm tra trong sheet Excel (`taikhoan_dat_v2_updated .xlsx`) cột **NGÀY TẠO** đã có dữ liệu.

### Nguyên nhân gốc rễ
Hàm `parse_date_safely` trong `upload_preflight.py` chỉ thử các format date thuần (`%d/%m/%Y`, `%Y-%m-%d`, `%Y/%m/%d`), không xử lý trường hợp chuỗi datetime có kèm timestamp:
```python
# Lỗi: Chuỗi '2026-09-13 00:05:25' không khớp %Y-%m-%d -> trả về None
for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%m/%d/%Y"):
    ...
```
Khi trả về `None`, logic `check_upload_cooldown_eligibility` kích hoạt cơ chế an toàn **fail-closed** và đánh dấu tài khoản là `account_creation_date_unverifiable`, dẫn đến chặn đăng video sai sót.

### Cách khắc phục chuẩn
Trước khi lặp qua các format ngày, chuẩn hóa chuỗi bằng cách tách lấy phần ngày trước khoảng trắng:
```python
s = str(val).strip()
s_clean = s.split()[0] if " " in s else s
for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%m/%d/%Y"):
    try:
        return datetime.strptime(s_clean, fmt).date()
    except (ValueError, TypeError):
        pass
```

---

## 3. Kỷ luật Báo cáo Watchdog (Bóc tách thay vì gom "Khác")
Khi tổng kết đăng video:
- Không gom chung `account_creation_date_unverifiable` và `account_cooling_period` vào một mục "Khác".
- Bóc tách rõ:
  - `Chưa xác minh tuổi nick (N máy)`: Cần kiểm tra dữ liệu sheet / parser.
  - `Đang ngâm cooldown (N máy)`: Đúng lịch ngâm chờ nhả.
  - `Đang dưỡng sinh (N máy)`: Organic rest đúng quy định.
