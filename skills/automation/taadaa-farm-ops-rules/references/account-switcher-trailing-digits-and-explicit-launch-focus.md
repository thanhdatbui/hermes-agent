# Account Switcher Trailing Digits Stripping Trap & Explicit Launch Focus Recovery

## 1. Account Switcher Trailing Digits Stripping Trap

### Hiện Tượng & Nguy Cơ
Trong các script kiểm soát tài khoản TikTok farm (`account_switcher.py`, `feed_swipe_smoke.py`), hàm `matches_switcher_identity` từng dùng logic:
```python
if v1.rstrip("0123456789+ ") == v2.rstrip("0123456789+ "):
    return True
```
Mục đích ban đầu là bỏ qua các ký hiệu badge thông báo unread (`9+`) hoặc hậu tố biến động. Tuy nhiên, khi một thiết bị chứa nhiều nick có cùng tiền tố nhưng khác số đuôi (ví dụ: máy có sẵn `khanhthu2275`, trong khi nick chỉ định chạy ca là `khanhthu1609`):
- `khanhthu1609.rstrip(...)` -> `"khanhthu"`
- `khanhthu2275.rstrip(...)` -> `"khanhthu"`
- `"khanhthu" == "khanhthu"` -> **Khớp sai (False Positive Match)**.

### Hậu Quả
- Script tưởng rằng tài khoản `khanhthu1609` đã có trên máy và bấm chọn `khanhthu2275`.
- Script tiếp tục lướt Feed trên nick sai, đến cuối ca khi đối soát profile (`verify_profile`) mới phát hiện lệch nick và fail-closed, gây mất 15-20 phút vô ích.
- Nghiêm trọng hơn: Script bỏ lỡ cơ hội nhận diện máy đang thiếu nick để tự động kích hoạt `auto_login_recovery`.

### Quy Chuẩn Xử Lý (Chốt Chặn Số Đuôi)
Bắt buộc kiểm tra số đuôi trước khi chấp nhận `rstrip`:
```python
m1 = re.search(r"\d+$", v1)
m2 = re.search(r"\d+$", v2)
if m1 and m2 and m1.group() != m2.group():
    # Khác số đuôi (e.g. 1609 != 2275) -> CẤM TUYỆT ĐỐI COI LÀ TRÙNG KHỚP
    return False
```

---

## 2. Launch Focus Recovery: Explicit SplashActivity Intent

### Hiện Tượng
Trên các dòng máy S7 / Android 7 cũ, sau khi thực hiện `am force-stop com.ss.android.ugc.trill`, việc khởi chạy lại app bằng:
```bash
monkey -p com.ss.android.ugc.trill -c android.intent.category.LAUNCHER 1
# hoặc
am start -a android.intent.action.MAIN -c android.intent.category.LAUNCHER -p com.ss.android.ugc.trill
```
thường xuyên gặp tình trạng:
- `monkey` chỉ đánh thức process nhưng activity không được kéo lên foreground (bị `com.sec.android.app.launcher` đè lên).
- `am start` không chỉ định rõ component `-n` bị hệ điều hành báo lỗi không giải quyết được Intent.
- Hậu quả: `_verify_tiktok_focus_with_retries` thử lại 10 lần đều thấy `focused_package == launcher` và fail-closed với lỗi `prepare-tiktok failed to focus TikTok after launch`.

### Quy Chuẩn Khởi Chạy Chuẩn Xác
Trong vòng lặp thử lại khởi chạy (`attempt in (2, 4, 6)`), BẮT BUỘC dùng lệnh Intent đích danh:
```bash
am start -n com.ss.android.ugc.trill/com.ss.android.ugc.aweme.splash.SplashActivity
```
Lệnh này kích hoạt trực tiếp `SplashActivity`, đưa TikTok lên foreground ngay lập tức 100% trong vòng <= 1.5 giây mà không phụ thuộc vào hành vi của launcher.
