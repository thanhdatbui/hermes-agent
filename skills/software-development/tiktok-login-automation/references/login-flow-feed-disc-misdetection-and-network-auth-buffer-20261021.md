# Case Study: Feed Disc Misdetection, 4G Proxy Auth Lag & Login Success Timeout (2026-10-21)

## 1. Hiện Tượng & Bối Cảnh
Trong đợt vận hành Ca 1 Row 7 trên cụm Kibe (`tiktok-feed-session-watchdog`), Máy 24 gặp lỗi `Kẹt Account Switcher`.
Khi điều tra root cause và kích hoạt recovery đăng nhập tự động (`python D:/Taadaa/Tiktok_Reg/tiktok_login_v1.py 24 --email trinhgiang7694 --ss`), hệ thống liên tiếp vấp phải các bẫy ngầm trong `social_reg_v1.py` và `tiktok_login_v1.py`:
1. Mở app thành công, đăng nhập thành công vào feed chính nhưng script crash với lỗi: `STOPPED: [10] BLOCKED_PROFILE_HANDLE_MISSING`.
2. Lần chạy lại tiếp theo bị văng lỗi: `[AUTH_BLOCKED] Mật khẩu đã được điền nhưng TikTok vẫn ở màn hình password (nghi vấn sai pass hoặc form error)! CẤM ĐIỀN LẠI LẦN 2! DỪNG NGAY!`.
3. Khi app đã ở màn Home Feed nhưng script vẫn timeout: `Timeout chờ login success: JasmynQuines487694@hotmail.com`.

---

## 2. Phân Tích Root Cause Chi Tiết

### Root Cause 1: Nhận Diện Nhầm Đĩa Nhạc Video Feed Thành Tab Hồ Sơ (`_profile_tab_node` trong `social_reg_v1.py`)
- Khi đăng nhập thành công hoặc khi cần chuyển từ Feed sang Hồ sơ, script gọi `go_to_profile(device_id)`.
- Hàm `_profile_tab_node(xml)` tìm kiếm các node có thể bấm ở góc dưới bên phải (`cand["coord"][0] > 750`).
- Bộ lọc cũ chỉ yêu cầu: `cy >= 1700` và `w >= 50`.
- Trên video feed TikTok, icon đĩa nhạc quay (`desc='Âm gốc của ...'`, `resource-id='com.ss.android.ugc.trill:id/pog'`) nằm ở tọa độ `(999, 1712)`, có `w=120`, `cy=1712 > 1700`.
- Vì nằm ngoài cùng bên phải (`x=999`), nó được chọn làm `best_rightmost` fallback và script bấm thẳng vào đĩa nhạc thay vì tab Hồ sơ (`bounds=[864,1794][1080,1920]`, tâm `972, 1857`).
- Hậu quả: App mở sang trang chi tiết Âm thanh / Comment sheet, script không tìm thấy thông tin profile của nick và văng `BLOCKED_PROFILE_HANDLE_MISSING`.

### Root Cause 2: Phán Đoán Sai Mật Khẩu Do Độ Trễ Xác Thực Trên Proxy 4G (`drive_login_screens` trong `tiktok_login_v1.py`)
- Sau khi nhập password và bấm nút `Tiếp tục`, TikTok gửi request xác thực về máy chủ.
- Trên môi trường Farm qua Proxy 4G xoay IP, quá trình xác thực mất từ 3 đến 8 giây.
- Vòng lặp `drive_login_screens` kiểm tra ngay ở vòng tiếp theo (sau 5s `D_LONG`). Tại thời điểm này, app vẫn đang hiển thị màn hình password (chờ server phản hồi).
- Script cũ kiểm tra cờ nhị phân `if password_submitted:` và thấy từ khóa `mat khau` trong XML, lập tức kết luận là sai mật khẩu hoặc lỗi form, ghi nhận `PASSWORD_RETRY_BLOCKED` và hủy đăng nhập ngay lập tức.

### Root Cause 3: Timeout 30s Quá Ngắn Khi ATX-Agent Gặp Trễ Trên Galaxy S7 (`wait_login_success` trong `social_reg_v1.py`)
- Mặc định `wait_login_success(timeout=30)`.
- Trên máy Samsung Galaxy S7 (Android 7/8), khi chuyển đổi Activity giữa Login và Feed, ATX-agent service port 7912 cần 2-3 nhịp retry (mỗi nhịp 3-5 giây) để đồng bộ hierarchy dump.
- Chỉ 2 lần dump XML đã tiêu tốn hơn 20 giây. Khi app đã thực sự chuyển vào Home Feed, bộ đếm thời gian 30s đã cạn, dẫn tới timeout giả dù tài khoản đã đăng nhập hoàn tất.

### Root Cause 4: Không Có Fallback Bọc Bước Đọc Profile Sau Khi Login Thành Công (`update_tracking_with_fallback` trong `tiktok_login_v1.py`)
- Khi `wait_login_success` trả về `True` (bằng chứng XML xác nhận app đã vào Home feed), script gọi `ensure_profile_completed_and_track`.
- Nếu bước này gặp bất kỳ sự cố nào về UI (như bị popup che hoặc không đọc ra handle), script ném `RuntimeError` không được bắt, làm sập toàn bộ flow đăng nhập dù tài khoản đã active trên máy.

---

## 3. Quy Chuẩn Kỹ Thuật Khắc Phục (Best Practices)

### 1. Nâng Ngưỡng Nhận Diện Tab Dưới Cùng (Bottom Navigation Bar Invariant)
Mọi tab điều hướng đáy của ứng dụng TikTok (Trang chủ, Cửa hàng, Hộp thư, Hồ sơ) trên màn hình 1080x1920 đều nằm ở dải `y >= 1780`.
BẮT BUỘC lọc bỏ mọi view có `cy < 1780` hoặc `y1 < 1750` để triệt tiêu việc tap nhầm các thành phần nổi trên video feed:
```python
x1, y1, x2, y2 = map(int, m.groups())
cy = (y1 + y2) // 2
if cy < 1780 or y1 < 1750:
    continue
```

### 2. Thiết Lập Đệm Chờ Xác Thực Mạng Cho Form Password (Network Auth Buffer)
Không dùng cờ boolean tức thời `password_submitted`. Chuyển sang biến đếm số vòng chờ `password_submitted_rounds`:
```python
if any(h in flat for h in PASSWORD_HINTS):
    if password_submitted_rounds > 0:
        if password_submitted_rounds < 3:
            log(f"   [pass-wait] Chờ TikTok xác thực mật khẩu qua proxy (lần {password_submitted_rounds}/2)...")
            password_submitted_rounds += 1
            time.sleep(D_LONG)
            continue
        log(f"   [AUTH_BLOCKED] 🛑 Mật khẩu đã được điền nhưng TikTok vẫn ở màn hình password...")
        return
```

### 3. Nâng Timeout Chờ Login Success Tối Thiểu 75s
```python
def wait_login_success(device_id, email, stt=None, timeout=75):
```
Đảm bảo đủ thời gian cho app load feed, xử lý dialog khôi phục cấu hình và vượt qua các nhịp retry của ATX-agent.

### 4. Bọc Bảo Vệ Đọc Profile & Fallback Tracking ID Có Sẵn
```python
def update_tracking_with_fallback(device_id, stt, account):
    row = None
    try:
        row = ensure_profile_completed_and_track(...)
    except Exception as exc:
        log(f"   [tracking-fallback] ensure_profile_completed_and_track error: {exc}")
    if row is None and account.get("id"):
        return upsert_tracking_account(..., account["id"], ...)
    return row
```

---

## 4. Kỷ Luật Điều Phối Coordinator: Chống Báo Cáo Suông (User Correction 21/10/2026)
- **Lời chấn chỉnh của Operator:** *"Là sao mày đéo fix lỗi mà thông báo ăn lồn à"* và *"Là mày phải điều tra script r fix chứ"*.
- **Bài học vận hành:**
  1. Khi nhận báo cáo từ Watchdog có máy Fail, TUYỆT ĐỐI CẤM Coordinator chỉ chạy lệnh inspect hiện trường rồi tóm tắt lại "máy này bị lỗi A, máy kia bị lỗi B" để ném trả lại cho Operator.
  2. BẮT BUỘC: Đào sâu vào file log chi tiết (`log.jsonl`), đối chiếu file dump UI XML tại thời điểm xảy ra sự cố (`fail_*.xml`), đọc code logic thực thi trong script để tìm ra bug thật.
  3. Áp dụng ngay code fix O(1) vào script, chạy canary / live recovery và chỉ báo cáo khi đã có bằng chứng thực thi thành công.
