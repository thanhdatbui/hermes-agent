# ChatGPT Web Mobile Dialog Pointer Intercept & Deactivated Account Triage

## 1. ChatGPT Web Mobile Dialog Pointer Intercept (`#mobile-auth-dialog`)
### Hiện tượng
Khi điều khiển trình duyệt qua Playwright CDP để tự động login hoặc lấy cookie ChatGPT Web (`chatgpt.com`):
- Giao diện mobile / responsive tự động kích hoạt `<dialog id="mobile-auth-dialog">` hoặc Bottom Sheet.
- Playwright `locator.click()` thông thường vào nút "Đăng nhập" hoặc nút "Tiếp tục với Google" bị timeout 30s với lỗi:
  `Locator.click: Timeout 30000ms exceeded. <dialog id="mobile-auth-dialog"> intercepts pointer events`

### Nguyên nhân
- Hộp thoại dialog nằm ở layer trên đè lên các phần tử DOM khác và chặn toàn bộ pointer events vật lý mà Playwright dispatch.

### Giải pháp Javascript Evaluate
Thay vì click vật lý bằng Playwright locator, sử dụng `page.evaluate()` để kích hoạt sự kiện `.click()` trực tiếp trên DOM node:
```python
# 1. Click nút Đăng nhập kích hoạt dialog
page.evaluate('''() => {
    const btn = document.querySelector('button[commandfor="mobile-auth-dialog"][data-mobile-auth-entry-action="login"]') ||
                Array.from(document.querySelectorAll('button, a')).find(el => el.innerText.includes('Đăng nhập') || el.innerText.includes('Log in'));
    if (btn) btn.click();
}''')

# 2. Click nút Google bên trong dialog
page.evaluate('''() => {
    const g = document.querySelector('button[data-provider="google"]') ||
              Array.from(document.querySelectorAll('#mobile-auth-dialog button, dialog button, button')).find(el => el.innerText.includes('Google'));
    if (g) g.click();
}''')
```

## 2. Phát Hiện Tài Khoản Bị Deactivate Qua OAuth Error Callback
### Hiện tượng
Sau khi click chọn tài khoản Google trong luồng OAuth, trang bị redirect sang:
`https://auth.openai.com/error?payload=<base64>&session_id=...`
### Xử lý
Giải mã Base64 trường `payload`:
```json
{"errorCode": "account_deactivated", "occurredAt": "2026-10-14T23:34:38Z", "product": "chat", "kind": "AccountDeactivated"}
```
- Nếu `errorCode == "account_deactivated"`: Đánh dấu tài khoản chết / bị ban vĩnh viễn trên server OpenAI, chuyển trạng thái `is_active=0` và ghi nhận vào blacklist, cấm retry vô ích.

## 3. Lỗi 404 Model Not Found Trong OmniRoute
### Hiện tượng
OmniRoute trả về lỗi `[404]: ChatGPT returned 404 — usually the model is no longer available on this account`.
### Nguyên nhân
- Tài khoản ChatGPT Free không hỗ trợ backend model `gpt-5.6-sol-high` (chỉ dành cho Pro/Plus).
- Đối với tài khoản Free trong pool: Bắt buộc cấu hình model mapping sang `chatgpt-web/gpt-5.6-luna-free` hoặc `auto`.
