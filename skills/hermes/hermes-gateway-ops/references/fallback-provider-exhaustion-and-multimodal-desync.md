# Fallback Provider Exhaustion & Multimodal Payload Desync Trap (2026-11-02)

## 1. Hiện tượng & Triệu chứng
- Trên Telegram, bot liên tục văng thông báo lỗi:
  `⚠️ The model provider failed after retries. I kept raw provider details out of chat; check gateway logs for diagnostics.`
- Đặc biệt xảy ra tập trung ở các session có **payload nặng / multimodal** (ví dụ: các topic chuẩn hoá kênh chạy nhiều lệnh `browser_vision`, load ảnh canvas/frames và đọc lịch sử dài). Các session chat ngắn thuần text vẫn có thể hoạt động bình thường.
- Gateway thử retry nhưng văng lỗi ngay lập tức sau vài giây, không chờ hết timeout bình thường.

## 2. Nguyên nhân kỹ thuật gốc rễ (Root Cause)
1. **Nghẽn socket stream ở Primary Provider:**
   - Model chính (`ag-gemini-pool-3` trỏ qua Omni `:20129`) khi chịu tải payload lớn có thể bị chậm trễ stream hoặc quá tải phiên duyệt web trung gian.
2. **Chuỗi Fallback rỗng / khuyết tật tính năng (Fallback Chain Collapse):**
   - Trong `config.yaml`, chuỗi `fallback_providers` được cấu hình:
     ```yaml
     fallback_providers:
       - model: 9r-free
         provider: custom:9router
       - model: opencode-free
         provider: custom:9router
       - model: ag-gemini-pool-3
         provider: omni
     ```
   - **`9r-free` (9Router :20128):** Ánh xạ vào `cohere/north-mini-code:free` (hoặc model nhỏ tương tự). Model này context ngắn và **hoàn toàn không hỗ trợ Vision / image_url**. Khi nạp turn có chứa ảnh, request fail ngay lập tức hoặc bị API từ chối.
   - **`opencode-free` (9Router :20128):** Endpoint này dính rate limit cứng `HTTP 429 Too Many Requests`.
   - **Vòng lặp fallback:** Sau khi 2 fallback đầu văng lỗi trong tích tắc (< 2s), Gateway rơi về fallback cuối là lại gọi lại chính `ag-gemini-pool-3` đang bị nghẽn, dẫn tới kiệt sạch retry (`api_max_retries: 2`).
   - Gateway kích hoạt hàm `_gateway_provider_error_reply()` trong `gateway/run.py` và gửi thông điệp generic `The model provider failed after retries`.

## 3. Quy tắc cấu hình Fallback an toàn (Hard Rules)
1. **Phải tương thích khả năng xử lý (Capability Parity):**
   - Nếu Primary model hỗ trợ Vision (`supports_vision: true`, `image_input_mode: native`), các model trong `fallback_providers` BẮT BUỘC phải là model multimodal có hỗ trợ Vision (ví dụ `claude-sonnet-4-6`, `gemini-web-argon-pool`, `gpt-5.6-luna`), CẤM TUYỆT ĐỐI đưa các model text-only hoặc free tier nhỏ (`9r-free`, `cohere`) vào fallback chung của Coordinator.
2. **Kiểm tra Liveness & Rate Limit trước khi gán Fallback:**
   - Fallback provider phải được đo kiểm độ trễ và tỷ lệ 429/5xx định kỳ. Một endpoint 429 liên tục như `opencode-free` không được phép nằm trong fallback chain.
3. **Chống lặp lại Primary trong Fallback:**
   - Fallback chain không được chứa lại chính Primary model ở cuối danh sách nếu không có backoff/jitter, vì nó sẽ chỉ kích hoạt lại đúng lỗi nghẽn vừa gặp.
