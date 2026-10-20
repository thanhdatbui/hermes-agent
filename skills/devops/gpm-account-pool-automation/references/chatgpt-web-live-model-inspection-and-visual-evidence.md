# ChatGPT Web Live Model Inspection & Visual Evidence Protocol

## 1. Vấn đề cốt lõi & Các cạm bẫy thực tế

### Cạm bẫy 1: Suy diễn model từ code router / proxy mapping tĩnh (Proxy-Inference Fallacy)
- Khi operator yêu cầu "mở profile GPM vào ChatGPT Web xem model mới nhất", agent thường có xu hướng tìm đường tắt: đọc file mapping `open-sse/executors/chatgpt-web/models.ts` hoặc query API `/v1/models` của OmniRoute/9Router rồi kết luận.
- **Hậu quả**: Proxy router thường giữ các định danh alias hoặc map cũ/nội bộ (`gpt-5.6-sol-pro`, `gpt-5.5`). Trong khi đó, OpenAI cập nhật giao diện web trực tiếp và độc lập (thực tế đã hiển thị tính năng mới và tiêu đề **`GPT-6 with Intelligent UI`** với các demo cards như "3D Periodic Table", "Galaxy Map"). Việc phán đoán qua code tĩnh là sai lệch hoàn toàn so với hiện trường web.

### Cạm bẫy 2: Bẫy Profile Guest / Chưa đăng nhập (Unauthenticated Popup Choke)
- Khi mở profile GPM chưa có session ChatGPT hoặc cookie bị hết hạn, giao diện ChatGPT chỉ ở chế độ Guest.
- Dropdown chọn model sẽ chỉ hiển thị nhãn mặc định `ChatGPT` kèm popup chặn: *"Try advanced features for free / Get smarter responses, upload files, create images, and more by logging in"*. Không thể thấy được model switcher thật.
- **Cách khắc phục**:
  - Tra cứu các profile có session cookie sống: Kiểm tra trực tiếp file `Default/Network/Cookies` của các profile GPM trong `C:\Users\Kibe\AppData\Local\Programs\GPMLogin\profile\*\Default\Network\Cookies` tìm các profile có `host_key LIKE '%chatgpt.com%' AND name LIKE '%session%'`.
  - Hoặc đối soát với các connection đang `is_active = 1` của provider `chatgpt-web` trong SQLite OmniRoute (`storage.sqlite`).

### Cạm bẫy 3: Vi phạm Gate 6 (Trả lời trần thuật suông, không có ảnh)
- Mọi tác vụ kiểm tra giao diện web/browser đều nằm dưới quy chế **Gate 6 (MAX BLIND STEPS = 1)**.
- Báo cáo kết quả UI mà không gửi kèm ảnh chụp thực tế `MEDIA:<path>` là vi phạm trực tiếp quy chuẩn vận hành của hệ thống.

---

## 2. Quy trình kiểm tra chuẩn xác (Step-by-Step)

1. **Khởi động Profile GPM có Session:**
   ```python
   # GPM Local API port 19995, bắt buộc skip_proxy_check=true
   import requests
   res = requests.get(f"http://127.0.0.1:19995/api/v3/profiles/start/{profile_id}?skip_proxy_check=true", timeout=30)
   cdp_addr = res.json()["data"]["remote_debugging_address"]
   ```

2. **Kết nối Playwright qua CDP & Kiểm tra trạng thái Authenticated:**
   ```python
   import playwright.sync_api as pw
   with pw.sync_playwright() as p:
       browser = p.chromium.connect_over_cdp(f"http://{cdp_addr}")
       page = browser.contexts[0].pages[0] if browser.contexts[0].pages else browser.contexts[0].new_page()
       page.goto("https://chatgpt.com", timeout=30000)
       page.wait_for_timeout(3000)
       
       # Xác nhận đã đăng nhập: không còn nút 'Sign up for free' / 'Log in'
       is_logged_in = page.evaluate("() => !document.body.innerText.includes('Sign up for free')")
   ```

3. **Tương tác bóc tách Model & Chụp ảnh Evidence:**
   - Đọc các nút bấm model, nhãn H1/H2 trên giao diện (`Try GPT-6`, `GPT-6 with Intelligent UI`).
   - Thiết lập viewport chuẩn (`1280x800`) và chụp ảnh màn hình ra đường dẫn vật lý:
     ```python
     page.set_viewport_size({"width": 1280, "height": 800})
     page.screenshot(path=r"C:/Users/Kibe/chatgpt_model_evidence.png")
     ```

4. **Soi Mắt Đọc Ảnh (Pre-send Vision Verification Invariant):**
   - Dùng `browser_navigate("file:///C:/Users/Kibe/chatgpt_model_evidence.png")` rồi gọi `browser_vision`.
   - Tiêu chuẩn thẩm định: Xác nhận đúng tiêu đề H1/model hiển thị, thấy rõ tên tài khoản trên sidebar, không bị popup che chắn, không bị đen màn hình hay lẹm chữ.

5. **Phản hồi User kèm Evidence & Dọn dẹp Profile:**
   - Trong phản hồi, gửi kèm thẻ `MEDIA:C:/Users/Kibe/chatgpt_model_evidence.png` cùng nội dung xác nhận ngắn gọn các chi tiết đã thấy tận mắt qua Vision.
   - Luôn đóng profile trong `finally` qua GPM stop API (`/api/v3/profiles/stop/{profile_id}`).
