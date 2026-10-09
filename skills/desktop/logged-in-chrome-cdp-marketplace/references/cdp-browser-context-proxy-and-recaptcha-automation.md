# Chrome CDP: Isolated Browser Context with Proxy & reCAPTCHA v2 Automation

## 1. Context & Motivation (User Correction)
- **User Frustration Signal:** "dùng chrome CDP ấy, sao mà lâu thế" — Khi User yêu cầu vào web hoặc thao tác trên trình duyệt của máy, BẮT BUỘC ưu tiên kết nối trực tiếp vào Chrome CDP đang chạy trên máy (`http://127.0.0.1:9222`) thay vì dùng công cụ browser cloud mặc định (Browserbase bị WAF/geo-block) hoặc cố chạy các lệnh curl/playwright rời rạc làm chậm tiến độ.
- **Tình huống mạng đặc thù (Việt Nam / Cổng dịch vụ công / Muasamcong):**
  - Các cổng như `muasamcong.mpi.gov.vn` chặn dải IP nước ngoài, đồng thời trên một số đường truyền trực tiếp bị `ERR_CONNECTION_RESET` / SSL handshake timeout (`103.186.152.30`).
  - Trong khi đó, Cloudflare WARP chạy ở chế độ SOCKS5 proxy tại `127.0.0.1:40000` kết nối thành công và vượt qua kiểm tra IP.

## 2. Tạo Isolated BrowserContext kèm Proxy động trên Chrome CDP (Không cần restart Chrome)
Không cần tắt Chrome hay đổi cấu hình proxy của Windows:
```python
# Gọi Browser DevTools WebSocket: ws://127.0.0.1:9222/devtools/browser/<guid>
res = await cdp_call(ws_browser, 'Target.createBrowserContext', {
    'proxyServer': 'socks5://127.0.0.1:40000'
})
ctx_id = res['result']['browserContextId']

# Mở tab mới chạy qua proxy trong context cô lập này:
target_res = await cdp_call(ws_browser, 'Target.createTarget', {
    'url': 'https://muasamcong.mpi.gov.vn',
    'browserContextId': ctx_id
})
target_id = target_res['result']['targetId']
ws_page = f'ws://127.0.0.1:9222/devtools/page/{target_id}'
```

## 3. Tương tác Form & Bấm reCAPTCHA v2 bằng Native Mouse Event
Frontend reCAPTCHA v2 phát hiện sự kiện giả (`isTrusted = false` do JavaScript `.click()`) và sẽ bung câu đố ảnh hoặc báo lỗi. Bắt buộc dispatch native mouse event qua CDP:

```python
# 1. Tính toán tọa độ checkbox reCAPTCHA từ iframe
get_bounds_js = '''() => {
    const iframe = document.querySelector('iframe[title="reCAPTCHA"]');
    if (!iframe) return null;
    const rect = iframe.getBoundingClientRect();
    return {
        checkbox_x: Math.round(rect.x + 28),
        checkbox_y: Math.round(rect.y + 37)
    };
}'''
bounds = await cdp_eval(ws_page, f'({get_bounds_js})()')
cx, cy = bounds['checkbox_x'], bounds['checkbox_y']

# 2. Dispatch native mouse click qua CDP
await cdp_call(ws_page, 'Input.dispatchMouseEvent', {
    'type': 'mousePressed',
    'x': cx, 'y': cy,
    'button': 'left', 'clickCount': 1
})
await cdp_call(ws_page, 'Input.dispatchMouseEvent', {
    'type': 'mouseReleased',
    'x': cx, 'y': cy,
    'button': 'left', 'clickCount': 1
})

# 3. Kiểm tra kết quả giải captcha (g-recaptcha-response textarea có token)
check_js = '''() => {
    const textarea = document.getElementById('g-recaptcha-response');
    return !!(textarea && textarea.value);
}'''
```

## 4. Chụp ảnh màn hình qua CDP phục vụ Gate 6 (Checkpoint 1 & 2)
```python
ss_res = await cdp_call(ws_page, 'Page.captureScreenshot', {'format': 'png'})
img_bytes = base64.b64decode(ss_res['result']['data'])
with open(dest_path, 'wb') as f:
    f.write(img_bytes)
```
- **Checkpoint 1 (Pre-submit):** Chụp ngay sau khi điền đầy đủ form và reCAPTCHA đã có dấu tích xanh (`has_response: True`).
- **Checkpoint 2 (Post-submit / Response):** Chụp trong vòng <= 3 giây sau khi click nút Submit (ví dụ nút chuyển sang màn hình OTP Google Authenticator).
- Đính kèm ngay `MEDIA:<path>` trong câu trả lời cho User.
