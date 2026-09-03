# Signup / registration false-positive removal

## Bối cảnh & Vấn đề
Video quảng cáo in-feed (`Được tài trợ`) có thể chứa CTA như `Đăng ký` / `Sign up`. Cơ chế cũ quét text toàn màn hình bằng `login_terms`, phát sinh `manual-needed:login-overlay` và dừng feed dù tài khoản vẫn đang đăng nhập.

## Giải pháp chuẩn khi user yêu cầu “bỏ cơ chế đó”
Đây là yêu cầu gỡ cơ chế, không phải chỉ thêm ngoại lệ cho một nhãn quảng cáo:
1. Xóa `Đăng ký` / `Sign up` khỏi keyword login và xóa mọi classifier branch sinh `manual-needed:login-overlay`.
2. Quy mọi login marker còn hợp lệ về `manual-needed:login`; giữ riêng các detector lockscreen, account-switcher, captcha/verification, save-login và typed popup.
3. Xóa safety reason, calibration/recovery guard và terminal marker chỉ phục vụ `login-overlay`.
4. Xóa detector/dismisser signup landing hoặc signup prompt nếu không còn call site; không xóa detector quảng cáo, campaign, subscriber-only hoặc live eligibility nếu chúng phục vụ hành vi khác.
5. Cập nhật fixture: feed có `Được tài trợ` + `Đăng ký` phải trả `for-you`, `manual_needed=False`; prompt `Log in` trên feed phải trả `manual-needed:login` nếu đó vẫn là policy mong muốn.

## Verification
- `git grep -n -i 'login-overlay\|signup_prompt\|sign up for tiktok\|đăng ký tiktok' -- python_runner docs` phải không còn kết quả trong cơ chế đã gỡ.
- Chạy classifier/safety/popup/calibration/feed-popups tests và compileall; test thực tế XML quảng cáo Machine 53 phải trả `for-you`.
- Full suite cần gọi với `PYTHONPATH=<repo>;<repo>/python_runner` trên Windows/MSYS nếu test import cả `python_runner` và `core`.
- Nếu full suite có timeout hoặc failure ở mock/device orchestration không liên quan, báo riêng với traceback; không sửa lan sang task này.

## Pitfalls
- Không giữ giải pháp cũ `is_infeed_ad_cta` nếu user đã nói bỏ hẳn cơ chế; đó chỉ là workaround.
- Không replace-all chuỗi ngắn như `"manual-needed:login-overlay",` trong file lớn; dùng context duy nhất để tránh phá nhiều block.
- Không commit thay đổi CAPTCHA/verification hoặc file do người khác sửa ngoài scope.

