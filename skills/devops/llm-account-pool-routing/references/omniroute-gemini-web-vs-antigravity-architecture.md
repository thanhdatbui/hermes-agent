# OmniRoute: Phân biệt Kiến trúc Provider Antigravity vs Gemini-Web & Cơ chế ReAct Worker

## 1. Bản chất Kỹ thuật: Antigravity vs Gemini-Web trong OmniRoute (:20129)

Khi thiết kế và mở rộng cụm model Gemini cho các tác vụ AI Farm / Coordinator / Worker, cần phân biệt rạch ròi giữa 2 provider độc lập trong OmniRoute:

| Tiêu chí | Provider `antigravity` (`open-sse/executors/antigravity.ts`) | Provider `gemini-web` (`open-sse/executors/gemini-web.ts`) |
| :--- | :--- | :--- |
| **Bản chất backend** | Endpoint nội bộ Google Cloud Code / Gemini Code Assist (`daily-cloudcode-pa.googleapis.com`). | Giao diện web trực tiếp của Google (`https://gemini.google.com/app`). |
| **Loại chìa khóa (Auth)** | OAuth 2.0 (`access_token`, `refresh_token`, `id_token`), client profile IDE. | Session Cookie (`__Secure-1PSID`, `__Secure-1PSIDTS`). |
| **Cơ chế gọi** | HTTP REST API / SSE trực tiếp qua `fetch` (TLS giả lập IDE). | Browser Automation qua Playwright (`chromium.launch` headless). |
| **Tiêu tốn hạn mức** | **TRỪ QUOTA IDE:** Có trần RPM/TPM và trần 5h/Weekly của tài khoản Google One / AI Pro. | **HOÀN TOÀN MIỄN PHÍ:** Trò chuyện trực tiếp trên web, không trừ giọt quota IDE nào. |
| **Tool Calling / MCP** | Native Function Calling qua JSON schema. | Phải mô phỏng ReAct loop (DSL / Text Parsing / Markdown blocks). |
| **Độ trễ (Latency)** | Rất nhanh: 1.0s – 3.0s mỗi turn. | Chậm hơn: 15s – 30s mỗi turn (do Playwright tải DOM và chờ `StreamGenerate`). |

---

## 2. Bẫy Rủi ro khi Cấu hình `gemini-web` trên OmniRoute

### Bẫy 1: Playwright Launch thiếu Proxy (Rò rỉ IP Host)
- Trong mã nguồn `open-sse/executors/gemini-web.ts`:
  ```typescript
  const { chromium } = await import("playwright");
  browser = await chromium.launch({ headless: true });
  ```
- **Hậu quả:** Mặc định `chromium.launch` chạy bằng IP mạng trực tiếp của máy tính host. Nếu tài khoản Google AI Pro được nuôi và đăng nhập qua Proxy 4G Mobi (`test.taadaa.click:51xx`) trong GPMLogin, nhưng khi gọi `gemini-web` lại bắn từ IP mạng nhà/LAN, Google sẽ phát hiện nhảy IP đột ngột giữa hai session đồng thời -> Lập tức kích hoạt `VALIDATION_REQUIRED` hoặc khóa tài khoản.
- **Quy tắc khắc phục:** Bắt buộc phải truyền cấu hình proxy tương ứng của profile vào options của `chromium.launch({ headless: true, proxy: { server, username, password } })`.

### Bẫy 2: Nhầm lẫn Token OAuth GPM với Web Session Cookies
- Profile GPM sau khi hoàn thành quy trình OAuth IDE thường chỉ lưu session cookie của Google Auth (`accounts.google.com`), nhưng **chưa từng điều hướng và đăng nhập tại `gemini.google.com`**.
- Do đó, file Cookies của profile GPM không tự động có sẵn `__Secure-1PSID` của Gemini Web.
- **Quy tắc:** Muốn lấy cookie cho `gemini-web`, bắt buộc phải có ít nhất 1 lần mở `https://gemini.google.com/app` trên trình duyệt đó để Google set đủ bộ cookie `__Secure-1PSID`, `__Secure-1PSIDTS`.

---

## 3. Kiến trúc ReAct Worker Cứu sinh (Gemini Web Worker / Sol Worker)

Khi cả Claude CLI và Agy CLI đều chạm trần hạn mức quota, hệ thống kích hoạt tầng Worker ReAct thứ 3 qua bản Web:

1. **State Machine ở Local (Stateless Web):**
   - Không phụ thuộc vào session state của trình duyệt.
   - Script local (`sol_worker.py` / `gemini_worker.py`) quản lý toàn bộ mảng messages, history và tool outputs.
2. **Kỷ luật DSL Action:**
   - `ACTION: READ_FILE` -> Đọc file an toàn với line numbers.
   - `ACTION: PATCH` -> Áp dụng Search & Replace duy nhất, AST syntax verification trước khi ghi đĩa.
   - `ACTION: COMMAND` -> Chạy lệnh pytest / unittest focused.
   - `ACTION: DONE` -> **Chỉ được phép phát hành sau khi lệnh test trả về exit code 0.**
