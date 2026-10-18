# Gemini 4 Argon WebChannel Wire vs StreamGenerate & Headless CDP Adapter

## 1. Bản chất Wire/Protocol của Gemini 4 Argon trên Web
- **Giao thức cũ (`StreamGenerate`):** Endpoint `/_/BardChatUi/data/assistant.lamda.BardFrontendService/StreamGenerate` chỉ hỗ trợ enum `MODE_CATEGORY` ở slot `[79]` gồm Flash (1), Thinking (2), Pro (3), Auto (4), Dynamic (5), Flash-Lite (6). **Không có enum nào kích hoạt trọng số của "4 Argon".**
- **Giao thức mới (`processSession`):** Khi chọn model `4 Argon` (Nhiệm vụ phức tạp) trên UI `gemini.google.com/app`, Google Web chuyển hoàn toàn sang WebChannel nhị phân 2 chiều: `POST https://geminiweb-pa.clients6.google.com/v1/processSession`.
- **Hệ quả kiến trúc:** Không thể giả cầy gọi 4 Argon qua HTTP payload phẳng cũ của OmniRoute. Muốn dùng đúng nhân 4 Argon xịn, bắt buộc chạy qua Browser CDP kết nối vào Profile GPM chứa phiên đăng nhập Google AI Pro thật.

## 2. Kiến trúc Local Daemon Headless CDP (:20135)
- **Profile Storage:** Dùng GPM profile (`4344af68-...`, tài khoản Pro có proxy Mobi 4G cố định) làm ngăn chứa cookie và vân tay.
- **Off-screen/Headless:** Khởi động GPM qua API `/api/v3/profiles/start/{id}`, kết nối Playwright CDP vào `remote_debugging_address`. Đặt viewport `1280x900` offscreen, không chiếm chuột/bàn phím.
- **OpenAI-Compatible Bridge:** Expose endpoint `POST http://127.0.0.1:20135/v1/chat/completions` (model: `gemini-4-argon`).
- **DOM Selector & Text Extraction:**
  - Input: `div[contenteditable="true"], rich-textarea p, div.ql-editor`
  - Send: `button[aria-label*="Gửi"], button[aria-label*="Send"], [data-test-id="send-button"]`
  - Generation state: Kiểm tra sự tồn tại của nút Stop (`button:has-text('Ngưng'), button[aria-label*='Stop'], [data-test-id='stop-button']`). Chờ nút biến mất mới bắt đầu extract.
  - Code/Response extract: Ưu tiên bóc `pre code, pre, .code-container, .markdown` trước khi fallback sang text nodes của conversation turn để bảo toàn code blocks.

## 3. Vận hành Lịch sử Chat: Normal vs Temporary Chat
- **Cuộc trò chuyện bình thường (Có lưu):** Mọi prompt và câu trả lời tự động ghi vào mục "Cuộc trò chuyện gần đây" trên sidebar Google Web. Tiện đối soát bằng mắt, nhưng cày batch liên tục sẽ làm phình to DOM và tăng rủi ro bị Google quét bot.
- **Temporary Chat (Tạm thời):** Bấm nút New Chat / Temporary Chat trước mỗi lượt gọi giúp giữ phiên 100% stateless, tránh nhiễm chéo biến số và code giữa các task, giữ tài khoản siêu sạch.

## 4. Pitfall: Chẩn đoán Chết Chùm vs Kẹt LRU trên Antigravity CLI Pool
- **Hiện tượng:** Tất cả lệnh gọi `ag_cli.py ask` đều dính `TimeoutExpired` sau 120s, log ghi `You are not logged into Antigravity`, dễ lầm tưởng cả 22 profile chết chùm do dùng chung token.
- **Sự thật hiện trường:** Mỗi profile `acc_01` -> `acc_22` sở hữu 1 Gmail và 1 bộ OAuth Refresh Token riêng biệt. Log "not logged in" chỉ là log transient lúc khởi động trước khi token refresh.
- **Nguyên nhân gốc rễ:** Thuật toán LRU trong `ag_cli.py` chọn profile có `last_used` nhỏ nhất. Khi một profile (như `acc_16`) bị nghẽn mạng 4G dẫn đến Timeout, script văng lỗi mà **không cập nhật `last_used` và không set cooldown**, khiến lượt gọi sau lại tiếp tục chọn đúng profile nghẽn đó $\to$ kẹt cứng vòng lặp.
- **Cách khắc phục bắt buộc:** Trong khối `except subprocess.TimeoutExpired`, phải lập tức gọi `set_profile_cooldown(name, duration=300)` và `record_profile_usage(name)` rồi `continue` để failover sang profile tiếp theo trong pool.
