# Chờ màn hình Tạo mật khẩu sau khi nhập OTP Email trong luồng đổi pass (13/09/2026)

## 1. Bối cảnh & Vấn đề
Trong luồng xoay mật khẩu phụ (`ensure_account_password_saved()`) của `live_phase_b_adapter.py`:
- Khi tài khoản gặp cổng "Xác minh danh tính" dạng OTP qua Email, runner tự động lấy OTP từ Gmail/Outlook app trên thiết bị và gọi `input_otp_digits(self.adb, otp_code)`.
- Trước bản vá, sau khi gõ OTP xong, code thực hiện:
  ```python
  time.sleep(1.0)
  self._tap_value("Tiếp", prefix=True)
  time.sleep(1.0)
  continue
  ```
- **Hậu quả:** 
  - Sau khi tap "Tiếp", lệnh `continue` bắt đầu lại vòng lặp 8 lượt điều hướng. 
  - Nếu TikTok mất hơn 1.0 giây để chuyển từ màn OTP sang màn "Tạo mật khẩu" / "Thay đổi mật khẩu", lượt dump tiếp theo có thể rơi vào trạng thái trung gian hoặc giao diện chưa nhận diện được, dẫn đến việc kích hoạt lệnh `KEYCODE_BACK` lùi ra ngoài Settings và kết thúc ở soft-return mà không bao giờ hoàn tất đặt mật khẩu mới.
  - Ngoài ra, việc tap nút "Tiếp" sau khi điền đủ 6 số OTP trên một số bản TikTok có thể tự động submit mà không cần bấm Tiếp, hoặc nút "Tiếp" biến mất ngay khi ký tự cuối được nhập, khiến `_tap_value("Tiếp")` có thể ném ngoại lệ nếu không được bọc an toàn.

## 2. Bản vá chuẩn (Contract)
Thay thế đoạn `continue` bằng cơ chế chờ đồng bộ màn hình tạo/đổi mật khẩu và gọi ngay `_complete_password_setup`:

```python
# Nhập 6 số OTP vào TikTok
input_otp_digits(self.adb, otp_code)
time.sleep(1.5)
try:
    self._tap_value("Tiếp", prefix=True)
except LiveAdapterError:
    pass
# Chờ màn hình Tạo mật khẩu / Thay đổi mật khẩu xuất hiện
pw_screen = self._wait_for(
    lambda xml: any(k in xml.casefold() for k in ["tạo mật khẩu", "create password", "thay đổi mật khẩu", "change password"]),
    "PASSWORD_FORM_NOT_REACHED_AFTER_OTP",
)
self._complete_password_setup(pw_screen)
return
```

## 3. Lợi ích
1. **Trực tiếp & dứt điểm:** Bỏ qua việc dựa vào các vòng lặp Back/Forward mạo hiểm sau khi đã xác thực OTP thành công.
2. **Kháng trễ mạng/máy yếu:** `_wait_for` poll định kỳ cho đến khi màn Tạo/Thay đổi mật khẩu hiển thị đầy đủ, không bị timeout do `sleep` cứng.
3. **An toàn nút Tiếp:** Bọc `try ... except LiveAdapterError: pass` chống crash nếu TikTok tự động submit sau ký tự thứ 6.
