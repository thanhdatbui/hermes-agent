# Quy tắc chọn mục tiêu Cron Add 2FA: Quét cả tài khoản đã có 2FA nhưng mật khẩu còn yếu (13/09/2026)

## 1. Bối cảnh & Chỉ đạo từ Operator
- Trước ngày 13/09/2026: Bộ lọc mục tiêu `freeze_targets()` trong `run_batch_live_2fa.py` áp dụng điều kiện cứng `has_2fa = bool(_clean(values[two_fa_col - 1]))`. Nếu `has_2fa == True`, script lập tức `continue` bỏ qua toàn bộ tài khoản đó.
- Hệ quả: Các tài khoản đã bật 2FA thành công trong các đợt chạy trước nhưng mật khẩu trong cột D vẫn mang định dạng mật khẩu farm yếu / legacy lặp lại (như `Linhle1505@Ks`, `Anhhoang3009@`) hoặc bị trống mật khẩu sẽ không bao giờ được đưa vào hàng đợi để đổi pass.
- Chỉ thị Operator (13/09/2026):
  *"Từ giờ cron chạy add 2fa, nếu gặp acc dù có 2fa mà pass yếu cũng đổi pass cho tao, sau đó handle script đầy đủ bản đã fix đổi pass rồi chốt phiên."*

## 2. Tiêu chí phân loại "Mật khẩu yếu / Cần Rotate"
Sử dụng hàm canonical `password_needs_rotation(value: str | None) -> bool` trong `core/passwords.py`:
1. Mật khẩu trống hoặc `None`.
2. Mật khẩu khớp regex legacy farm:
   `^(?:[A-Za-z0-9_.]+@Ks|[A-Za-z]+\d{2,6}@\S*)$`
   - Dạng đuôi `@Ks` (ví dụ: `Linhle1505@Ks`, `marcusephillips52@Ks`).
   - Dạng tên + ngày tháng + `@` (ví dụ: `Anhhoang3009@`, `Thuyvu2402@`).
3. Các mật khẩu ngẫu nhiên mạnh (chuẩn 12-18 ký tự gồm chữ hoa, chữ thường, số, ký tự đặc biệt) sẽ được giữ nguyên (`needs_rotation == False`).

## 3. Quy chuẩn điều phối mục tiêu (Candidate Selection Logic)
Trong `run_batch_live_2fa.py`:
- Cột đọc bổ sung: Cột D (`PASS`).
- Điều kiện hợp lệ (`eligible`):
  ```python
  if not machine or not serial or not username:
      continue
  # Nếu đã có 2FA VÀ mật khẩu không cần rotate -> Bỏ qua
  if has_2fa and not password_needs_rotation(password_val):
      continue
  ```
- Định tuyến cờ worker:
  - Nếu `has_2fa == True` và `password_needs_rotation == True`: worker được gọi với cờ `--password-only` để chạy thẳng vào nhánh `ensure_account_password_saved()`, bỏ qua các bước kiểm tra 2FA không cần thiết.
  - Nếu `has_2fa == False`: worker chạy flow đầy đủ (kích hoạt Authenticator + rotate pass nếu cần).
