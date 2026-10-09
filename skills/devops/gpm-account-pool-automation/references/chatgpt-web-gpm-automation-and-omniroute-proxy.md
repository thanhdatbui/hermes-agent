# ChatGPT Web & Codex Automation via GPMLogin (Playwright CDP)

## 1. Cơ chế xác thực & Phân biệt Quota trên OmniRoute (:20129)

| Tiêu chí | `chatgpt-web` (GPM Web) | `codex` (CLI / OAuth) |
|---|---|---|
| **Cơ chế token** | Cookie `__Secure-next-auth.session-token` (`eyJhbG...`) | OAuth Refresh Token (`rt.1...`) / JWT `access_token` |
| **Model hỗ trợ** | `gpt-5.6-luna-free`, `gpt-5.6-luna-free-thinking`, `gpt-5.6-sol-high`, `gpt-5.6-terra-high` | `gpt-5.6-sol`, `gpt-5.6-terra-high`, `gpt-5.5` |
| **Quota Pool** | **Hoàn toàn độc lập** với Codex. Hết quota Codex (`503 reset after 700h`) thì Web VẪN SỐNG 100%. | Quota developer hàng tháng, cắm ít acc rất dễ bị 503 cạn kiệt (~29 ngày). |
| **Cơ chế bảo mật** | Ít bị checkpoint bắt verify SĐT. | Thường gặp checkpoint verify SĐT / password ở bước cuối OAuth consent. |

---

## 2. Pitfalls nghiêm trọng trong luồng Automation (Playwright CDP)

### Pitfall 1: Form Onboarding Ngày sinh mặc định năm 2026 (Chặn tuổi / COPPA)
- **Hiện tượng**: Tại `https://auth.openai.com/about-you`, giao diện tiếng Việt hiển thị component `react-aria-DateField` gồm 3 ô: `div[data-type="day"]`, `div[data-type="month"]`, `div[data-type="year"]`.
- **Nguyên nhân cốt lõi**: Giá trị khởi tạo mặc định lấy ngày hiện tại (năm 2026). Tuổi = 0 -> OpenAI báo đỏ: *"Chúng tôi không thể tạo tài khoản với thông tin đó"* hoặc gây lỗi `token_exchange_failed`.
- **Cách xử lý chuẩn**:
  - Bắt buộc dùng `page.keyboard.press("Control+A")` trên từng ô để xóa sạch số mặc định trước khi gõ.
  - Gõ năm sinh trong khoảng `1996` – `2002` (đảm bảo đủ 24–30 tuổi).
  - Kiểm tra thêm dạng ô nhập trực tiếp `input[name="age"]` (nếu giao diện tiếng Anh/biến thể).

### Pitfall 2: Màn hình "Phiên của bạn đã kết thúc" (`https://auth.openai.com/u/login`)
- **Hiện tượng**: Trang web hiện thông báo *"Phiên của bạn đã kết thúc. Tiếp tục bằng cách đăng nhập hoặc sử dụng ChatGPT.com mà không cần tài khoản"*.
- **Nguyên nhân**: Khi redirect OAuth bị delay hoặc timeout, OpenAI đẩy về màn hình này.
- **Cách xử lý**: Nhận diện selector `button:has-text("Đăng nhập"), a:has-text("Đăng nhập")` và click để quay lại luồng login bình thường.

### Pitfall 3: Lấy nhầm Cookie Anon/Guest Token
- **Hiện tượng**: Cookie `session-token` lấy được nhưng UI web vẫn hiện đầy đủ nút *"Đăng nhập"* và *"Đăng ký miễn phí"*.
- **Quy tắc phân biệt token**:
  - Token đã đăng nhập chính thức: Bắt đầu bằng `eyJhbG...` (JWT auth token).
  - Token anon/guest: Bắt đầu bằng tiền tố khác hoặc không có user payload hợp lệ.
- **Quy tắc kiểm tra UI**: Trên màn hình chính `chatgpt.com`, số lượng nút login (`button:has-text("Log in"), button:has-text("Đăng nhập")`) phải bằng **0**.

### Pitfall 4: Lỗi `token_exchange_failed` do dồn IP Proxy
- **Hiện tượng**: Redirect về `https://auth.openai.com/error?payload=...` với payload giải mã là `{"kind": "AuthApiFailure", "errorCode": "token_exchange_failed"}`.
- **Nguyên nhân**: Chạy quá nhiều worker song song (>= 5 workers) dồn request đổi code sang token trên cùng dải MobiProxy.
- **Quy tắc**: Giới hạn tối đa **2–3 workers song song**, giãn cách 3–5s giữa các lần mở profile.

---

## 3. Gán Proxy 1:1 cho từng Account trên OmniRoute (:20129)

Khi nạp tài khoản vào OmniRoute, BẮT BUỘC gán proxy tương ứng của Gmail/Profile GPM đó vào connection:

```python
# 1. Trích xuất port từ raw_proxy của GPM (ví dụ test.taadaa.click:5113:mobi13:pass)
m_port = re.search(r':(\d{4,5})', raw_proxy)
port = int(m_port.group(1))

# 2. Tìm proxy trong OmniRoute registry
r_reg = requests.get('http://127.0.0.1:20129/api/settings/proxies').json()
matched = [p for p in r_reg.get('items', []) if p.get('port') == port]
proxy_id = matched[0]['id']

# 3. Gán assignment vào connection (Scope: account)
requests.put('http://127.0.0.1:20129/api/settings/proxies/assignments', json={
    'proxyId': proxy_id,
    'scope': 'account',
    'scopeId': connection_id
})

# 4. Kích hoạt cờ proxyEnabled trên connection
requests.put(f'http://127.0.0.1:20129/api/providers/{connection_id}', json={'proxyEnabled': True})
```

---

## 4. Dọn dẹp tiến trình GPM sau mỗi tài khoản (Anti-Taskbar Flood)

Để chống tràn taskbar và rò rỉ RAM:
1. Gọi API đóng profile: `GET http://127.0.0.1:19995/api/v3/profiles/stop/{profile_id}`.
2. Quét diệt triệt để process `chrome.exe` thuộc thư mục `gpm_browser` (tuyệt đối không kill nhầm tool khác).
