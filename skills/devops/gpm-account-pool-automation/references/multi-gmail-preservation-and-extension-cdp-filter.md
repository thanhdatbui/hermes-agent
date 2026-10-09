# Multi-Gmail Profile Preservation, Extension Offscreen Filter & Re-auth Flow

## 1. Bảo tồn Profile Đa Tài Khoản (Multi-Gmail Profiles) vs Profile Đơn lẻ
Khi khôi phục các profile cũ (như `01_Rua`, `02_Legacy`):
- Các profile này chứa nhiều tài khoản Google đã đăng nhập đồng thời (`thanhdatbui19951@gmail.com`, `duongkien12022001@gmail.com`, etc.) cùng cookie/history lâu năm.
- **Quy tắc bảo tồn:** Khi cấu hình dàn máy chuẩn 1:1 Kibe (ví dụ `01 - duongkien12022001@gmail.com`), **KHÔNG ĐƯỢC GHI ĐÈ** lên profile cũ `01_Rua`.
- Đăng ký profile cũ thành profile độc lập (ví dụ `01_Rua_Legacy` với `ProfilePath="x_rua_jidbq"`, `GroupId=1`), giữ nguyên 100% 124-key Fingerprint gốc từ `profile_data_backup.db` và chỉ map proxy chuẩn S7 (`test.taadaa.click:5101`).

---

## 2. Lỗi `net::ERR_ABORTED` do Extension Offscreen Page trên Playwright CDP

### Triệu chứng:
Khi kết nối `connect_over_cdp` vào profile Chrome có cài MetaMask hoặc Extension:
- `context.pages[0]` trỏ vào `chrome-extension://<id>/offscreen.html`.
- Gọi `page.goto("https://myaccount.google.com/")` bị lỗi: `Error: Page.goto: net::ERR_ABORTED`.

### Giải pháp Chuẩn (Bắt buộc lọc page):
```python
# Luôn lọc bỏ các page extension background/offscreen
regular_pages = [p for p in context.pages if not p.url.startswith("chrome-extension://")]
page = regular_pages[0] if regular_pages else context.new_page()
```

---

## 3. Xử lý Account Chooser & "Sử dụng một tài khoản khác" (Multi-account Chooser)

Khi profile có nhiều tài khoản cũ đã lưu trong `accountchooser`:
- Nếu tài khoản cần login đã có trong danh sách: Click trực tiếp vào thẻ tài khoản tương ứng (`page.locator(f'div[data-identifier*="{email_addr}"], li:has-text("{email_addr}")').first.click()`).
- Nếu cần nạp tài khoản mới mà UI bị kẹt ở account chooser: Click `"Sử dụng một tài khoản khác"` / `"Use another account"` bằng `force=True`:
  ```python
  opt = page.locator('li:has-text("Sử dụng một tài khoản khác"), div:has-text("Sử dụng một tài khoản khác")').last
  if opt.count() > 0 and opt.is_visible():
      opt.click(force=True)
  ```

---

## 4. Xử lý Màn hình Onboarding Selfie Video / Phone Recovery

Sau khi nhập mật khẩu / 2FA trên tài khoản cổ/aged, Google thường điều hướng tới:
`https://myaccount.google.com/verification/selfie/precollection` (*"Thêm video selfie dùng để đăng nhập"* / *"Add a selfie, just in case"*) hoặc yêu cầu thêm số điện thoại.

### Cách xử lý:
1. Quét tìm và click nút bỏ qua:
   ```python
   for _ in range(4):
       skip_btns = page.locator('button:has-text("Bỏ qua"), button:has-text("Để sau"), button:has-text("Not now"), button:has-text("Hủy"), button:has-text("Skip")')
       if skip_btns.count() > 0 and skip_btns.first.is_visible():
           skip_btns.first.click()
           time.sleep(3)
   ```
2. Sau đó điều hướng trực tiếp về `https://myaccount.google.com/` để xác nhận trạng thái LIVE.
