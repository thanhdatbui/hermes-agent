# Bẫy Tài Khoản Có 2FA Nhưng Cột Password Bị Rỗng (`None`) Rơi Vào OTP Mail (2026-10-02)

## 1. Hiện Tượng & Câu Hỏi Người Dùng Thường Gặp
- **User thắc mắc**: *"Ủa chứ bữa sửa tiktok log in ưu tiên chọn log in qua 2fa rồi mà, sao giờ vẫn rơi vào luồng OTP mail rồi kẹt?"*
- **Triệu chứng thực tế**: Tài khoản đã có sẵn secret key 2FA Authenticator (TOTP) trong database Excel (`taikhoan_dat_v2_updated .xlsx`), code `tiktok_login_v1.py` đã có logic ưu tiên 2FA (`TWOFA_AUTHENTICATOR_HINTS`), nhưng khi chạy auto-login thì app TikTok lại hiện màn hình **"Xác minh email"** đòi nhập mã OTP gửi về hòm thư Gmail/Hotmail, sau đó timeout `[7c]` vì không lấy được OTP.

---

## 2. Nguyên Nhân Gốc Rễ: Cơ Chế Phân Luồng TikTok & Dữ Liệu Excel

### Cơ chế xác thực 2FA của TikTok:
1. **2FA Authenticator là BƯỚC 2 (Second Factor) của Đăng nhập bằng Mật khẩu**:
   - Luồng chuẩn: `TikTok ID / Email + MẬT KHẨU TIKTOK` $\rightarrow$ TikTok xác thực pass đúng $\rightarrow$ Mới hiển thị màn hình **"Xác minh 2 bước" (2-Step Verification / Authenticator App)** $\rightarrow$ Script gõ mã TOTP 6 số từ secret key $\rightarrow$ Hoàn tất đăng nhập.
2. **Luồng Đăng nhập bằng Email không có mật khẩu (Passwordless / Email OTP)**:
   - Khi điền Email vào ô đăng nhập ban đầu mà **không có mật khẩu**, TikTok hiểu là người dùng muốn đăng nhập bằng liên kết/mã tạm thời gửi về mail.
   - TikTok đưa thẳng người dùng vào màn hình **"Xác minh email" (Email OTP)**.
   - **Màn hình này KHÔNG PHẢI là màn hình 2FA**, không có trường nhập mã Authenticator và không hiển thị tùy chọn Authenticator!

### Bẫy code trong `tiktok_login_v1.py` khi cột `PASS` bị `None`:
Tại dòng 742:
```python
login_target = account["login_email"] if (force_otp or not (account.get("id") and account.get("tiktok_pass"))) else (account.get("id") or "").strip()
```
- Khi trong file Excel `taikhoan_dat_v2_updated .xlsx`, cột `PASS` (mật khẩu TikTok) bị để trống (`None`):
  - Biểu thức `not (account.get("id") and account.get("tiktok_pass"))` trả về `True`.
  - Script **bị tước mất quyền đăng nhập bằng ID + Pass**, buộc phải lấy `login_target = account["login_email"]`.
- Script điền email vào form login $\rightarrow$ TikTok mở màn hình **"Xác minh email"**.
- Tại màn hình OTP, script có kiểm tra xem có thể chuyển sang mật khẩu không:
  ```python
  has_pw = bool((account.get("tiktok_pass") or "").strip())
  if not force_otp and has_pw:
      find_text_tap(device_id, "Đăng nhập bằng mật khẩu")
  ```
  Nhưng vì `tiktok_pass` là `None`, `has_pw = False` $\rightarrow$ Script **không thể bấm chuyển sang form mật khẩu**.
- Do đó, script bắt buộc phải tìm OTP trong hòm thư mail (`handle_tiktok_email_otp`) và bị treo nếu mail chưa nạp vào máy hoặc TikTok shadow-drop không phát OTP.

---

## 3. Khắc Phục & Quy Tắc Vận Hành (Remediation & Invariants)

1. **Chuẩn hóa Dữ Liệu Excel Master (`taikhoan_dat_v2_updated .xlsx`)**:
   - Nếu tài khoản có mã `2FA`, **BẮT BUỘC PHẢI CÓ CỘT `PASS` (Mật khẩu TikTok)**.
   - Trường hợp `PASS` bị `None`: Đối soát lại với cột `PASS MAIL` hoặc mật khẩu lúc reg (thường reg bằng script lưu pass cùng pattern). Điền bổ sung mật khẩu TikTok để mở khóa luồng ID + Pass + 2FA.
2. **Quy tắc Fleet Chuẩn 8 Nick / Máy**:
   - Farm Kibe chuẩn hóa cứng **8 accounts / máy** tương ứng 8 dòng (Tik1..Tik8) trong `taikhoan_run_safe.xlsx`.
   - Cấm kết luận máy chỉ giữ tối đa 7 tài khoản khi thấy 7 nick đang login.
3. **Reconcile Fallback Bắt Buộc `--expected-username`**:
   - Khi auto-login fast recovery gọi `reconcile_tiktok_accounts.py` trên máy có nhiều dòng tài khoản, **BẮT BUỘC** phải truyền `--expected-username <username>` để tránh lỗi fail-closed:
     `CONFIG_ERROR: machine N: ambiguous machine-wide reconcile; explicit expected username is required`.
