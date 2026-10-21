# ChatGPT Web Live Model Inspection & Visual Evidence Protocol

## 1. Vấn đề cốt lõi & Các cạm bẫy thực tế

### Cạm bẫy 1: Suy diễn model từ code router / proxy mapping tĩnh & Bẫy nhầm thẻ Demo H1 (Header Hallucination)
- **Bẫy proxy-inference**: Đọc file mapping `open-sse/executors/chatgpt-web/models.ts` hoặc query API `/v1/models` của OmniRoute/9Router rồi kết luận. Proxy router giữ alias cũ/nội bộ (`gpt-5.6-sol-pro`, `gpt-5.5`) hoặc tên mapping quy ước.
- **Bẫy thẻ demo / header H1**: Nhìn thấy tiêu đề chat hay project card demo như **`GPT-6 with Intelligent UI`** đã vội vàng phán bừa là model selector.
- **Sự thật thực tế trên ChatGPT Web**:
  - Giao diện Free hiện tại không có dropdown model selector trên đầu; nó chỉ có nút bật suy luận **`Think`** (`reason`) và thanh toggle **`Chat / Work`**.
  - **Nguồn chứng thực tối cao (Ground Truth)**: Bắt buộc gọi `fetch('/backend-api/models')` ngay trong context trang authenticated để lấy danh sách model thực tế OpenAI cấp cho tài khoản:
    * Tài khoản Free: `gpt-5-6` (`GPT-5.6 Luna`), `gpt-6` (`GPT-6` / nhãn hiển thị `Latest • 6` / `6 Instant`).
    * Tài khoản Plus/Pro/Team: Hạ tầng Sol 6 (`gpt-5-6`, `gpt-5-6-thinking`, `gpt-5-6-pro`) với các mức suy luận Instant, Medium, High, Pro.

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
   - Lấy danh mục model chuẩn xác qua API nội bộ của trang web:
     ```python
     models_data = page.evaluate("() => fetch('/backend-api/models').then(r => r.json())")
     ```
   - Chụp ảnh màn hình giao diện thực tế (xác nhận nút `Think`, menu tài khoản Free/Plus) ra đường dẫn vật lý:
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

---

## 3. Cạm bẫy suy diễn Sol vs Luna khi ép slug Backend API (Black-Box Backend Routing Pitfall)

- **Bản chất tên gọi:**
  - `GPT-5.6 Sol`: Là nhãn hiển thị thực tế trên bộ chọn model (v2 picker) của tài khoản trả phí (**Plus / Pro**), phân tầng 5 lane suy luận (`instant`, `medium`, `high`, `xhigh`, `pro`) tương ứng các backend slug `gpt-5-6`, `gpt-5-6-thinking` (với các mức effort `standard`, `extended`, `max`), và `gpt-5-6-pro`.
  - `GPT-5.6 Luna`: Là nhãn hiển thị trong metadata `/backend-api/models` của tài khoản **Free** (gắn với slug `gpt-5-6` và `gpt-5-6-mini`).
- **Bẫy suy diễn khi ép slug:**
  - Khi client hoặc proxy (OmniRoute) gửi request ép thẳng slug `model: "gpt-5-6-thinking"` kèm `thinking_effort: "extended"` trên một **tài khoản Free**: Server OpenAI vẫn chấp nhận (`HTTP 200 OK`) và sinh chuỗi suy luận CoT dài.
  - Tuy nhiên, cụm máy chủ OpenAI thực tế xử lý request đó trên cluster compute nào (cấp nguyên vẹn compute của Sol hay ngầm downscale về compute của Luna CoT) là **hộp đen hoàn toàn (server-side black-box)**.
- **Kỷ luật phát ngôn & Báo cáo:**
  - Tuyệt đối CẤM khẳng định chắc nịch *"5.6 thinking chắc chắn là Luna"* hoặc *"chắc chắn là Sol"* khi chưa có telemetry máy chủ nội bộ của OpenAI.
  - Luôn bóc tách rõ 3 tầng độc lập:
    1. **Tầng Client Payload:** Model slug gửi đi (`gpt-5-6-thinking`, `gpt-5-6-pro`, `auto`).
    2. **Tầng UI / Plan Naming:** Nhãn hiển thị theo gói (`GPT-5.6 Sol` trên Plus/Pro picker vs `GPT-5.6 Luna` trên Free API).
    3. **Tầng Server Execution:** Hộp đen phân bổ tài nguyên của OpenAI — thừa nhận tính bất định khi không có bằng chứng nội bộ.
