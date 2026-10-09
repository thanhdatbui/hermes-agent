# Quy trình Tạo Profile GPMLogin Hàng Loạt từ Farm S7 & Khai Thác Toàn Bộ Dải IP

## 1. Bối cảnh & Vấn đề
Khi watchdog login GPM ban đêm (`post_evening_gpm_login_watchdog.py`) báo cáo:
`[LOGIN GPM ĐÊM - TỔNG KẾT] ✓ 0 | ✗ N | proxy_limit 2/port/ngày | Hoàn tất ca tối`
hoặc chỉ chạy được vài máy rồi ngắt, nguyên nhân phổ biến:
- Trong Master Excel (`master_gmail_manager.xlsx`) có rất nhiều Gmail (hơn 200 acc), nhưng trong DB GPMLogin (`profile_data.db`) chỉ mới tạo một số lượng nhỏ profile.
- Watchdog có cơ chế lọc an toàn: CHỈ xử lý những Gmail đã có sẵn profile trong GPM DB. Những Gmail chưa có profile sẽ bị bỏ qua ngay lập tức.
- Giới hạn bảo vệ proxy: Mỗi cổng proxy chỉ được login 2 lần/ngày. Khi số lượng profile có sẵn ít, các cổng đó chạm hạn mức nhanh chóng, làm ngắt ca tối dù dàn IP còn rất nhiều cổng rảnh.

## 2. Quy trình Tự Động Tạo Profile Hàng Loạt Chuẩn Farm
Để mở khóa toàn bộ dàn IP, cần đồng bộ tạo profile cho các Gmail sạch còn lại qua Local API v3 (port `19995`):

### Bước 1: Nạp Mapping Proxy Chuẩn
- Đọc file `D:\OneDrive\TaadaaData\kibe\PROXYgandienthoai.xlsx` (sheet `Proxy`):
  - Cột 0: Số Máy (mid)
  - Cột 1: Device Serial ADB
  - Cột 2: Chuỗi proxy đầy đủ (ví dụ: `test.taadaa.click:5105:mobi5:TaadaaMobi#2026!`)

### Bước 2: Kiểm Tra Thiết Bị S7 Thật Online
- Kiểm tra danh sách thiết bị online bằng `adb devices`.
- Chỉ tạo profile cho các máy S7 đang online ADB để đảm bảo khi watchdog chạy, nó có thể tương tác ADB/ATX nhấn nút "Có" hoặc lấy mã OOTP 10 số.

### Bước 3: Lọc Ứng Viên Sạch
Từ `D:\OneDrive\TaadaaData\kibe\master_gmail_manager.xlsx` (sheet `Kibe_Farm_S7`), lọc bỏ:
- Tài khoản trạng thái `DIE`, `BAN`, `SUSPENDED`.
- Tài khoản dính email recovery hoặc tên chứa `khoale` (Farm safety invariant).
- Tài khoản đã nạp thành công vào OmniRoute (`omniroute_success`).
- Tài khoản đang dính checkpoint hoặc sai mật khẩu (`wrong_password_or_checkpoint`).
- Tài khoản đã tồn tại trong GPMLogin DB.

### Bước 4: Gọi GPMLogin Local API v3
Sử dụng `GPMClient` (`D:\Taadaa\GPM auto\src\gpm_client.py`):
```python
client = GPMClient(base_url="http://127.0.0.1:19995/api/v3")
client.create_profile(
    name=f"{mid:02d} - {email} - {port}",
    raw_proxy=proxy_str,
    group_id=1
)
```
- Stagger: Chờ 1.5s - 2.0s giữa các lượt tạo để tránh nghẽn Local API.

## 3. Lợi ích
- Khi các profile được tạo chuẩn tên và gắn đúng proxy riêng, watchdog login đêm sẽ tự động nhận diện danh sách ứng viên mới với các cổng proxy chưa chạm hạn mức (0/2 lượt), giúp tận dụng tối đa 100% tài nguyên mạng của Farm.
