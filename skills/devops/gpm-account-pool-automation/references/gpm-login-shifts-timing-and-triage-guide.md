# GPM Gmail Login Shifts Timing, Concurrency & Failure Triage

## 1. Khung Giờ Hoạt Động & Cơ Chế Phân Bổ Ca
Watchdog `post-evening-gpm-login-watchdog` (`post_evening_gpm_login_watchdog.py`) không chạy liên tục mà vận hành so le vào các khung giờ rảnh an toàn giữa các ca nuôi feed của Farm:
- **Ca Sáng**: 09:30 – 11:20 (ngay sau Ca 1 nuôi feed kết thúc lúc 09:25).
- **Ca Chiều**: 15:30 – 17:20 (ngay sau Ca 2 nuôi feed kết thúc lúc 15:25).
- **Ca Tối**: 21:30 – 23:45 (ngay sau Ca 3 nuôi feed & upload avatar).

## 2. Benchmark Thời Gian Chạy Thực Tế vs Nhận Định Sai Của Operator
- **Thực tế thời gian chạy**: Watchdog chạy theo đợt cực nhanh (cuốn chiếu 6 batch × 5 workers song song). Ví dụ ca sáng xử lý 30 tài khoản chỉ mất **~25 phút** (09:30:51 đến 09:56:13, trung bình ~50 giây/tài khoản).
- **Cạm bẫy nhận định "chạy cả buổi sáng mới được 26 acc"**:
  + Trước 09:30: Watchdog hoàn toàn bị chặn bởi `is_within_time_window()` để nhường 100% tài nguyên cho máy farm chạy feed.
  + Sau 09:56: Toàn bộ các tài khoản còn lại trong hàng đợi (13 acc) bị khóa bởi điều kiện an toàn `is_machine_idle == False` (do các máy tương ứng đang dính device lock hoặc nằm trong buffer an toàn < 10 phút trước ca nuôi tiếp theo).
  + Khi chạm ngưỡng hết giờ ca (`is_late`), watchdog tự động chốt ca và gửi báo cáo tổng kết, nhường tài nguyên cho ca trưa.

## 3. Phân Loại Kết Quả & Triage Lỗi Nghiệp Vụ
Khi báo cáo tổng kết ca có `✓ S | ✗ F` (ví dụ `✓ 26 | ✗ 4`):
1. **Thành công (✓)**: Profile đã đăng nhập xong, cập nhật session cookie Google sống vào database `Default/Network/Cookies` và gán `GroupId = 10` trên GPMLogin.
2. **Thất bại (✗)**:
   - **Google 2SV Sensitive Cooldown 7 Days (`signin/rejected?rrk=77`)**: Google tạm khóa tính năng bảo mật do đổi IP/thiết bị mới. Ghi nhận vào `oauth_pipeline_status.json` và cách ly profile sang `GroupId = 11`.
   - **Session Cookie Timeout / Missing**: Playwright mở profile nhưng không bắt được cookie xác thực hợp lệ trong thời gian chờ hoặc profile bị trắng session.
   - **Proxy Quota Cap**: Mỗi cổng proxy 4G MobiProxy giới hạn cứng tối đa `MAX_LOGINS_PER_PROXY = 2` lần login/ngày để bảo vệ IP khỏi bị Google cắm cờ.

## 4. Kỷ Luật Báo Cáo Không Kèm Media Cho Tác Vụ GPM / Web
- Các tác vụ đăng nhập GPM, kiểm tra session cookie SQLite, đối soát log cronjob trên PC là tác vụ backend/browser, **không phải thao tác trên màn hình điện thoại farm**.
- Khi giải thích số liệu tiến độ GPM cho Operator, nêu rõ thời gian chạy thực tế theo mốc timestamp cụ thể (giờ bắt đầu - giờ kết thúc) và giải thích lý do số acc còn lại bị ngâm (chờ máy rảnh giữa các ca).
