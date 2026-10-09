# ChatGPT-Web & Codex SSO Automation with GPMLogin & OmniRoute

Tài liệu đúc kết từ phiên thực chiến tự động hóa đăng nhập Google SSO vào ChatGPT-Web và OpenAI Codex trên dàn profile GPMLogin, trích xuất auth token và gán proxy di động vào OmniRoute (cổng 20129).

## 1. Cơ chế Quota & Phân Biệt Nhà Cung Cấp trên OmniRoute

| Đặc tính | OpenAI Codex (`codex`) | ChatGPT-Web (`chatgpt-web`) |
| :--- | :--- | :--- |
| **Loại Token** | OAuth `access_token` + `refresh_token` (`rt.1...`) hoặc Web JWT tạm | Cookie `__Secure-next-auth.session-token` (bắt đầu bằng `eyJhbG...`) |
| **Display Label** | `ChatGPT Web (Codex)` | `ChatGPT Web (Plus/Pro)` (Hỗ trợ cả Free, Plus, Pro) |
| **Cơ chế Quota** | Quota Developer CLI độc lập. Hết quota báo `503 Unavailable (reset after 700h)` (~29-30 ngày). | Quota giao diện Web độc lập theo phiên hàng ngày. |
| **Tách Biệt Pool** | **CÙNG 1 TÀI KHOẢN**: Codex bị 503 hết quota nhưng Web vẫn gọi `200 OK` phà phà. Hai pool quota tách rời 100%. |
| **Model hỗ trợ** | `gpt-5.6-sol`, `gpt-5.6-terra-high`, `gpt-5.5` | `gpt-5.6-sol-high`, `gpt-5.6-sol-xhigh`, `gpt-5.6-terra-high`, `gpt-5.6-luna-free` |

## 2. Các Cạm Bẫy Onboarding & Điểm Nghẽn Auth

### A. Bẫy Năm Sinh 2026 trên `react-aria-DateField` (Tiếng Việt)
- **Triệu chứng:** Sau khi cấp quyền Google, OpenAI mở trang `auth.openai.com/about-you`. Nếu UI tiếng Việt, OpenAI dùng component `react-aria-DateField` gồm 3 ô riêng biệt: `div[data-type="day"]`, `div[data-type="month"]`, `div[data-type="year"]`. Giá trị mặc định của năm là năm hiện tại của máy tính (`2026`).
- **Hậu quả:** Tuổi = 0 (dưới 13 tuổi theo quy định COPPA). Bấm Tiếp tục bị báo đỏ: *"Chúng tôi không thể tạo tài khoản với thông tin đó"*. Nếu script không xóa số 2026, bot sẽ timeout và OpenAI văng lỗi `token_exchange_failed` hoặc timeout session.
- **Giải pháp chuẩn:**
  1. Click vào từng ô `data-type="day"`, `month`, `year`.
  2. Dùng `page.keyboard.press("Control+A")` để bôi đen toàn bộ giá trị cũ.
  3. Gõ ngày (10–28), tháng (01–12), và năm ngẫu nhiên **`1996` – `2002`** (24–30 tuổi).

### B. Bẫy Ô Tuổi Trực Tiếp `input[name="age"]` (Tiếng Anh/Việt)
- **Triệu chứng:** Một số phiên OpenAI hiện ô input trực tiếp: `<input name="age" type="number">`.
- **Hậu quả:** Nếu script chỉ tìm kiếm DateField mà bỏ qua `input[name="age"]`, ô tuổi bị để trống. OpenAI báo: *"Nhập độ tuổi hợp lệ để tiếp tục"*.
- **Giải pháp:** Kiểm tra song song cả hai dạng form (DateField 3 ô và input age). Nếu thấy `input[name="age"]`, click force, `Control+A` và gõ tuổi ngẫu nhiên `22`–`28`.

### C. Màn Hình "Phiên của bạn đã kết thúc" (`auth.openai.com/u/login`)
- **Triệu chứng:** Màn hình trắng tinh chỉ có logo OpenAI, tiêu đề *"Phiên của bạn đã kết thúc"* và một nút đen to **[Đăng nhập]**.
- **Nguyên nhân:** Do phiên đăng nhập trước bị timeout quá 60s hoặc dính lỗi đổi mã token.
- **Giải pháp:** Đây là màn hình chuyển tiếp trung gian, không phải checkpoint bế tắc. Chỉ cần phát hiện `u/login` hoặc text *"Phiên của bạn đã kết thúc"*, tự động click nút **[Đăng nhập]** / `[Log in]` là trình duyệt sẽ quay lại luồng auth để tiếp tục.

### D. Nhận Diện Đúng Auth Token vs Guest Token
- **Cookie Anon/Guest:** Bắt đầu bằng chuỗi không phải JWT chuẩn hoặc trình duyệt chưa đăng nhập (trên UI chatgpt.com vẫn còn nút "Đăng nhập" / "Log in").
- **Auth Token Chính Chủ:** Bắt đầu bằng **`eyJhbG...`** (Base64 header của JWT). Chỉ nạp vào OmniRoute khi token bắt đầu bằng `eyJhbG` và màn hình `chatgpt.com` có 0 nút "Đăng nhập".

## 3. Quản Lý Vòng Đời Trình Duyệt & Chống Tràn Taskbar
- **Nguyên nhân tràn Taskbar:** Mỗi profile GPM mở ra spawn một tiến trình `chrome.exe` (thư mục `gpm_browser`). Khi chạy đa luồng hoặc script bị ngắt, API stop không kill hết dẫn đến hàng chục cửa sổ mồ côi làm treo máy và nghẽn CPU/RAM.
- **Kỷ luật dọn dẹp bắt buộc (`finally` block):**
  1. Gọi API `GET /api/v3/profiles/stop/{id}`.
  2. Quét qua `psutil.process_iter`: nếu `chrome.exe` có đường dẫn chứa `gpm_browser` và command line chứa `profile_path` của tài khoản vừa chạy thì `kill()` dứt điểm.
  3. Giới hạn concurrency tối đa **2–3 workers**, tuyệt đối không chạy 5–10 workers dồn dập làm sập proxy và WAF OpenAI.

## 4. Tự Động Gán Đúng Proxy Di Động 1-1 trên OmniRoute
Khi nạp connection `chatgpt-web` vào OmniRoute:
1. Đọc `raw_proxy` từ profile GPM (trích xuất port, ví dụ `5113` từ `test.taadaa.click:5113`).
2. Tra cứu `GET /api/settings/proxies` trên OmniRoute để tìm `proxy_id` tương ứng với port đó.
3. Gán assignment cho connection:
   ```python
   requests.put("http://127.0.0.1:20129/api/settings/proxies/assignments", json={
       "proxyId": proxy_id,
       "scope": "account",
       "scopeId": connection_id
   })
   requests.put(f"http://127.0.0.1:20129/api/providers/{connection_id}", json={
       "proxyEnabled": True
   })
   ```
4. Việc này đảm bảo request gọi model từ OmniRoute sẽ đi qua đúng cổng MobiProxy 4G của chính Gmail đó, không lộ IP máy chủ và không bị rate-limit chéo.
