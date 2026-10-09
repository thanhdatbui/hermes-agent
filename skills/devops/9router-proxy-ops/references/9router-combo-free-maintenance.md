# 9Router & OmniRoute Combo & Fallback Maintenance

## 1. Context & User Directive
- **Nguyên tắc bất biến:** TUYỆT ĐỐI KHÔNG tự ý gỡ bỏ provider `9router` hoặc model `9r-free` ra khỏi cấu hình `fallback_providers` của Hermes Agent (`config.yaml`).
- **Nhiệm vụ điều phối:** Khi một model trong combo free của 9Router bị lỗi hoặc upstream quá tải, Coordinator phải chủ động vào SQLite database của 9Router rà soát và cập nhật lại danh sách model khỏe thay vì xóa bỏ provider.

## 2. 9Router Architecture & Combo Database
- **Database Path:** `C:/Users/Kibe/AppData/Roaming/9router/db/data.sqlite`
- **Table:** `combos` (`id`, `name`, `models`, `createdAt`, `updatedAt`)
- **Key Combos:**
  - `9r-free`: Combo model free mặc định được Hermes sử dụng khi fallback.
  - `free`: Combo model free tương đương.

## 3. Top-Tier Model Selection Criteria for 9Router Free Pool
Khi rà soát các model trên 9Router (`http://127.0.0.1:20128/v1/models`), ưu tiên:
1. **Model nội bộ có độ ổn định cao:**
   - `ag/gemini-3.7-flash-high`: Tốc độ 1-2s, chuẩn xác, không bị lỗi SSE parse.
   - `gpt-5.6-luna`: Phản hồi tức thì, streaming mượt mà.
2. **Model CommandCode (cmc) nhạy bén:**
   - `cmc/moonshotai/Kimi-K2.5`: Tốc độ ~1.6s, hiểu ngữ cảnh và tiếng Việt tốt.
   - `cmc/zai-org/GLM-5`: Tốc độ ~1.6s.
   - `cmc/Qwen/Qwen3.6-Max-Preview`: Tư duy logic cao.
3. **Model OpenRouter Free công suất lớn:**
   - `openrouter/nvidia/nemotron-3-super-120b-a12b:free`: Siêu model 120B tham số.
   - `openrouter/nvidia/nemotron-3.5-lightning:free`: Tốc độ phản hồi cực nhanh.
4. **Các model cần tránh (Dễ gây timeout / overload):**
   - `openrouter/nvidia/nemotron-3-ultra-550b`: Thường xuyên dính lỗi upstream `Service temporarily overloaded`.
   - `openrouter/poolside/laguna-s-2.1:free`: Dễ dính `HTTP 429 Too Many Requests`.
   - `openrouter/thinkingmachines/inkling:free`: Dính lỗi `HTTP 403 Forbidden`.

## 4. Verification Recipe
Sau khi cập nhật danh sách model trong `combos`, luôn chạy script probe test trực tiếp endpoint streaming:
```python
import urllib.request, json
# Gửi test request tới http://127.0.0.1:20128/v1/chat/completions với stream=True
# Xác nhận nhận được token đầu tiên trong < 3 giây và không có exception.
```
