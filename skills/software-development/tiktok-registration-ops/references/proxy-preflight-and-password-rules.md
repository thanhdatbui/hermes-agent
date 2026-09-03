# Proxy Live Preflight & Password Storage Rules for TikTok Reg

## 1. Proxy Live Gate
- **Quy tắc:** Máy có mapping proxy bắt buộc phải có VPN tun0 UP VÀ live IP hợp lệ (ViChanger GET_IP verified).
- **Fail-closed:** Nếu proxy dead / unreachable -> chặn ngay lập tức trước khi mở app / reg TikTok (áp dụng logic `python_runner/core/vpn_preflight.py` bên repo `tiktok-luot nuoi acc`).

## 2. Lưu thông tin & Password Storage
- **Deferred Tracking Output:** Acc reg thành công trong batch lưu đầy đủ info vào `tracking_result_sttXX_*.json` (email, mail_password, tiktok_id/handle, password, serial, proof XML + screenshot).
- **Password Logic:**
  - Nếu flow đăng ký đi qua màn nhập password: nhập password ngẫu nhiên và lưu trường `password`.
  - Nếu flow đăng ký chỉ dùng OTP/magic-link mà **không xuất hiện màn nhập password** (`password_written = False`): **bắt buộc để trống pass (`password = ""`)**, tuyệt đối không lưu pass tự sinh khi account không có pass thật.
