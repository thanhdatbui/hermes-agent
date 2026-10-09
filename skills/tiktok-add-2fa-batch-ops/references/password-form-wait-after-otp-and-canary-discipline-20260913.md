# Triage & Bản Vá Lỗi Lọt Form Tạo Mật Khẩu Sau OTP Email & Kỷ Luật Canary Đổi Pass (13/09/2026)

## 1. Bối cảnh & Hiện tượng
Khi chạy canary kiểm chứng flow đổi mật khẩu phụ trên nick có pass cũ yếu (`Linhle1505@Ks`, Row 362 Máy 46):
- Luồng tự động lấy OTP Gmail đã hoạt động hoàn hảo và điền đủ 6 số OTP vào TikTok.
- Tuy nhiên sau khi submit OTP, TikTok cần 1.5–2s để chuyển sang màn hình "Tạo mật khẩu" / "Create password".
- Ở phiên bản cũ:
  1. Sau `input_otp_digits`, code gọi `continue` quay lại vòng lặp `for _ in range(8):`. Do màn hình chưa load xong và tiêu đề là "Tạo mật khẩu" (không phải "Thay đổi mật khẩu"), code không nhận diện được và thực hiện tiếp lệnh `KEYCODE_BACK`, làm app văng ra ngoài Launcher Home.
  2. Runner exit code 0 (`status: success`) nhưng pass trong Excel không hề được cập nhật, tạo cảm giác báo cáo ảo đánh lừa operator.

## 2. Các Bản Vá Quyết Định (Commits 4d6dcad, e6de084, cd4669f)
1. **Chờ & Submit Trực Tiếp Sau OTP (Commit `4d6dcad`):**
   - Không dùng `continue` lùi lại loop chung.
   - Ngay sau khi nhập 6 số OTP, gọi `_wait_for()` chờ form xuất hiện (`any(k in xml.casefold() for k in ["tạo mật khẩu", "create password", "thay đổi mật khẩu", "change password"])`).
   - Gọi ngay `self._complete_password_setup(pw_screen)` và `return` hoàn tất.
2. **Nhận diện tiêu đề "Tạo mật khẩu" (Commit `e6de084`):**
   - Mở rộng điều kiện nhận diện màn hình mật khẩu trong `ensure_account_password_saved`: bắt cả `"tạo mật khẩu"` và `"create password"` song song với `"thay đổi mật khẩu"`.
3. **Cờ CLI `--password-only` (Commit `cd4669f`):**
   - Thêm `--password-only` vào `run_capture_phase_b.py`.
   - Cho phép chạy canary tập trung độc lập vào luồng đổi mật khẩu mà không bị bypass khi nick đã bật 2FA (`already-enabled`).

## 3. Kỷ Luật Vận Hành Khi Nhận Lệnh Canary Từ Operator
- Khi Operator yêu cầu *"chạy canary test đổi pass trên máy hôm qua lỗi"*:
  + **BẮT BUỘC** kiểm tra xem nick đó đã bật 2FA chưa. Nếu nick đã có 2FA, **BẮT BUỘC dùng cờ `--password-only`** để ép runner chạy thẳng vào nhánh đổi pass.
  + **TUYỆT ĐỐI CẤM** chạy canary bình thường khiến runner rơi vào nhánh `already-enabled` rồi tự mãn báo "lấy OTP ngon" khi pass trong Excel chưa hề được đổi!
  + Tiêu chí hoàn thành duy nhất của canary đổi pass: **Cột D (PASS) trong Excel phải được cập nhật mật khẩu mới** và screencap xác nhận TikTok đã qua form.
