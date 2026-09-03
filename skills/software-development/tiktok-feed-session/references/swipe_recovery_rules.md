# Quy tắc xử lý Popup lạ & Swipe Recovery trong Feed Session

## 1. Bản chất quy tắc của Farm
- Trong feed session nuôi acc, nếu gặp màn hình lạ, popup quảng cáo, hoặc dialog không rõ (nhưng không phải màn hình nhạy cảm như Login, OTP, Captcha, Verification):
  - Quy tắc: **Thử vuốt lên (swipe) 2 lần để lướt qua video tiếp theo** như thao tác nuôi bình thường.
  - Không được ngắt phiên dừng máy ngay khi chưa thử swipe lướt qua.

## 2. Pitfalls cần tránh trong Code (feed_swipe_smoke.py / safety.py)
- **Thứ tự của `manual_guard`**:
  - `manual_guard.record()` không được đặt trước logic swipe recovery `_swipe_recovery_on_stuck`.
  - Nếu `manual_guard` đếm 2 nhịp liên tiếp có cùng lý do `unexpected popup/dialog marker detected` trước khi gọi `_swipe_recovery_on_stuck`, nó sẽ lập tức dừng phiên và giữ hiện trường.
- **Bao phủ ở các phase**:
  - Cần áp dụng cơ chế swipe recovery 2 lần ở cả phase `baseline`, `before_swipe`, và trong vòng lặp `swipe` giữa phiên.
