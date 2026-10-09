# Playwright CDP: Microsoft login.live.com Form Submission Pattern

## Bối cảnh & Vấn đề
Khi tương tác tự động với form đăng nhập Microsoft (`https://login.live.com`) qua Playwright / Chrome CDP (ví dụ kịch bản `gpm_change_hotmail_security.py`):
- Click vào nút Submit `#idSIButton9` dễ gặp tình trạng không ăn lệnh hoặc miss click do animation, timing delay, dynamic button re-rendering, hoặc mất focus giữa chừng.

## Giải pháp Chuẩn hóa
Sau khi `fill` dữ liệu vào `input`, thay vì gọi `page.click("#idSIButton9")`, dùng phím `Enter` trực tiếp trên chính input element:

```python
# Điền email & Enter
email_input = page.locator('input[type="email"], #i0116')
email_input.wait_for(state="visible", timeout=8000)
email_input.fill(email)
email_input.press("Enter")
time.sleep(3)

# Điền password & Enter
pwd_input = page.locator('input[type="password"], #i0118')
pwd_input.wait_for(state="visible", timeout=20000)
pwd_input.fill(current_pass)
pwd_input.press("Enter")
time.sleep(4)
```

## Lợi ích
- Kích hoạt sự kiện submit native của input field ngay lập tức.
- Không bị phụ thuộc vào trạng thái rendered / visual bounds của nút `#idSIButton9`.
- Giảm tỷ lệ retry và timeout khi đăng nhập tài khoản Hotmail / Microsoft qua GPM CDP.
