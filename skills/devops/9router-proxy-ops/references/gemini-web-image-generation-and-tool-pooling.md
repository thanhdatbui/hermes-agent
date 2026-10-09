# Gemini Web (`gemini-web`) Session Provider, Image Generation & Tool Emulation trên OmniRoute (:20129)

## 1. Bản Chất Kỹ Thuật của Provider `gemini-web` trên OmniRoute
- Tương tự như `chatgpt-web`, `gemini-web` là web-session provider kết nối trực tiếp vào giao diện web `gemini.google.com` qua cookie phiên người dùng mà không cần Google Cloud / Vertex AI API key trả phí.
- **Mã nguồn thực thi**:
  - Executor chính: `open-sse/executors/gemini-web.ts`
  - Image generation handler: `open-sse/handlers/imageGeneration/providers/geminiWeb.ts`
  - Capability & validation: `open-sse/executors/gemini-web/capabilities.ts`

## 2. Cơ Chế Xác Thực & Quản Lý Session Cookie
- **Chuỗi Cookie yêu cầu**:
  - Bắt buộc: `__Secure-1PSID`
  - Khuyên dùng: `__Secure-1PSIDTS` (bảo đảm phiên kéo dài và tránh bị văng đăng nhập)
  - Cú pháp nạp vào OmniRoute: `__Secure-1PSID=<value>; __Secure-1PSIDTS=<value>`
- **Phát hiện Session Expired & Blocked (#9407, #10494)**:
  - Khi phiên cookie hết hạn hoặc bị Google chuyển hướng sang `accounts.google.com/ServiceLogin`, Playwright sẽ dính lỗi selector hoặc timeout.
  - OmniRoute chuẩn hóa lỗi này qua hàm `isExpiredOrBlockedGeminiWebSession(status)`: mã lỗi HTTP 400 hoặc 500 do Playwright vấp trang login/CAPTCHA sẽ tự động kích hoạt **Account Fallback** sang tài khoản tiếp theo trong pool, không làm crash request của client.

## 3. Tính Năng Tạo Ảnh AI Qua API (`POST /v1/images/generations` - #10466, #10494)
- **Cơ chế hoạt động**:
  1. Hermes hoặc client gửi yêu cầu chuẩn OpenAI: `POST http://localhost:20129/v1/images/generations` với model `gemini-web` (hoặc combo trỏ tới `gemini-web`).
  2. `buildGeminiWebImagePrompt`: Bắt buộc chèn directive sinh ảnh rõ ràng (`"Generate an image for this prompt: ... Use the image generation model. Do not search the web for existing images."`) vì giao diện web của Google chỉ kích hoạt Imagen khi có động từ tạo ảnh, nếu không sẽ trả về kết quả tìm kiếm web (web-search thumbnails).
  3. Executor nhập prompt vào `gemini.google.com` và hứng luồng phản hồi `StreamGenerate` (khung dữ liệu `wrb.fr`).
  4. Bộ lọc `parseStreamResponseImages`:
     - Bỏ qua toàn bộ ảnh thumbnail tìm kiếm tại trường `candidate[12][1]`.
     - Chỉ trích xuất link ảnh do Imagen sinh ra tại trường `candidate[12][7][0]` (`candidate[0][3][3]`).
     - Tự động gắn hậu tố `=s2048` vào URL `lh3.googleusercontent.com` để lấy ảnh kích thước đầy đủ (full-resolution).
     - URL ảnh của Google là public, client/Hermes có thể tải trực tiếp không cần cookie.

## 4. Emulated Tool Calling & Multi-turn Chat
- **Emulated Tool Calling (#7286, #7727)**:
  - Tương tự `chatgpt-web`, `gemini-web` sử dụng shim `open-sse/translator/webTools.ts`.
  - Hợp đồng tool của OpenAI được serialize vào prompt, model trả lời qua khối `<tool>{...}</tool>`, OmniRoute parse thành `tool_calls` chuẩn cho Hermes/Codex.
- **Flatten Multi-turn Context (#8371)**:
  - Do điều khiển browser thu nhận frame đầu tiên và không lưu upstream conversation ID bền vững, request multi-turn được làm phẳng (flatten) thành một transcript có gắn nhãn role (`User: ...`, `Assistant: ...`) trước khi gõ vào ô chat của Gemini Web.

## 5. Yêu Cầu Môi Trường & Proxy Binding
- **Playwright Chromium**: Cần có sẵn Playwright Chromium trên máy host. Nếu thiếu, executor trả về 503 (`npx playwright install chromium`) kèm header cooldown thay vì làm hỏng pool.
- **Proxy 1-1**: Bắt buộc gán proxy cho từng account `gemini-web` qua `/api/settings/proxies/assignments` (tránh IP VPS/datacenter dính bot-detection của Google).
