# ChatGPT Web Automation in GPM: Pointer Interception, Native JS Evaluate & Account Deactivation

## 1. Bẫy Pointer Interception trên Mobile Auth Dialog (#mobile-auth-dialog)
Khi mở `https://chatgpt.com/` trên trình duyệt GPM (đặc biệt khi viewport hoặc user-agent được nhận diện là mobile / responsive):
- Hộp thoại đăng nhập dạng bottom sheet (`<dialog id="mobile-auth-dialog">` hoặc `<div role="dialog">`) **tự động mở sẵn trên màn hình**.
- Các nút Đăng nhập ở thanh điều hướng/sidebar bị dialog này che chắn hoàn toàn.
- Nếu dùng Playwright `page.locator(...).click()` thông thường, Playwright sẽ báo lỗi:
  ```text
  Locator.click: Timeout 30000ms exceeded.
  <dialog id="mobile-auth-dialog"> from ... subtree intercepts pointer events
  ```
  Tiến trình bị treo 30 giây timeout mà không bao giờ bấm được nút đăng nhập.

## 2. Giải pháp Native JS Evaluate Injection
Không dùng `locator.click()` tương tác qua con trỏ chuột mô phỏng. BẮT BUỘC dùng `page.evaluate()` để kích hoạt sự kiện click trực tiếp từ DOM engine:

```python
# 1. Kích hoạt nút mở modal (nếu chưa mở)
page.evaluate('''() => {
    const btn = document.querySelector('button[commandfor="mobile-auth-dialog"][data-mobile-auth-entry-action="login"]') ||
                Array.from(document.querySelectorAll('button, a')).find(el => el.innerText.includes('Đăng nhập') || el.innerText.includes('Log in'));
    if (btn) btn.click();
}''')

# 2. Bấm nút Continue with Google bên trong dialog
page.evaluate('''() => {
    const g = document.querySelector('button[data-provider="google"]') ||
              Array.from(document.querySelectorAll('#mobile-auth-dialog button, dialog button, button')).find(el => el.innerText.includes('Google'));
    if (g) g.click();
}''')
```

## 3. Nhận diện tài khoản bị OpenAI vô hiệu hóa (Account Deactivated)
Khi OAuth Google hoàn tất chuyển hướng về `auth.openai.com`, nếu tài khoản đã bị khóa, URL chuyển hướng sẽ có dạng:
`https://auth.openai.com/error?payload=<base64>&session_id=...`
Giải mã Base64 payload sẽ nhận được:
```json
{
  "errorCode": "account_deactivated",
  "occurredAt": "2026-10-14T23:34:38Z",
  "product": "chat",
  "kind": "AccountDeactivated"
}
```
**Quy tắc xử lý:** Đánh dấu tài khoản là `banned / deactivated` ngay lập tức, chuyển sang trạng thái dừng, không retry vô vọng để tránh tốn tài nguyên và nghẽn pool.

## 4. Chốt an toàn Proxy 1-1 (Fail-Closed) cho OmniRoute
- Phân biệt rõ host theo dải port:
  - Cổng `5101..5138` $\rightarrow$ `test.taadaa.click`
  - Cổng `10001..10035` $\rightarrow$ `mirotik1.taadaa.click`
- **Hard Fail-Closed:** Luôn resolve `proxy_id` và ghi `proxy_assignments` trước khi bật `is_active=1`. Nếu không tìm thấy proxy tương ứng trong `proxy_registry` $\rightarrow$ giữ nguyên `is_active=0`, cấm tuyệt đối tạo connection trần (bare connection) gây rò rỉ IP máy chủ.
