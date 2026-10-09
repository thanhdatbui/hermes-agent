# OpenCode Muse Spark Text-Only Constraint, Fallback Hierarchy & Native Multimodal Safeguard (2026-09-28)

## 1. Hiện tượng & Lỗi thực tế (Incident Context)
Khi Gemini Coordinator (`ag-gemini-pool-3`) cạn sạch quota (HTTP 429), Hermes tự động kích hoạt cơ chế `fallback_providers`. Trong cấu hình cũ, fallback duy nhất được chỉ định là `custom:opencode` (model `muse-spark-1.3` qua port `:20130`).

Khi người dùng gửi ảnh qua Telegram trong phiên fallback này:
- OpenCode trả lời không thấy ảnh hoặc báo request trống (`"[The user attached an image. Here's what it contains:"` rỗng).
- Gặp lỗi timeout: `[Error: OpenCode request timed out after 120s]`.

## 2. Phân tích nguyên nhân cốt lõi (Root Cause)
1. **Model Modality:** Cả 8 model miễn phí của OpenCode (`muse-spark-1.3`, `nemotron-3-ultra`, `nemotron-3.5-lightning`, `mimo-v2.6-flash`, `ling-3.0-flash-fin`, `longcat-2.5-preview`, `big-pickle`, `space-bunny`) đều là **Text-Only LLM**. Upstream của OpenCode hoàn toàn không có Vision Encoder.
2. **Adapter Filtering:** File `D:/Taadaa/tools/opencode_bridge.py` trong hàm `extract_prompt_from_messages` trước đây chỉ duyệt các phần tử có `item.get("type") == "text"`. Toàn bộ payload `image_url` hoặc base64 ảnh đều bị vứt bỏ trước khi gọi `opencode run`.
3. **Hardcoded System Guardrail của Muse Spark:** Dù có cố gắng dựng bridge trung gian đọc OCR ảnh thành text rồi nhét vào prompt, Muse Spark khi thấy trong câu hỏi có từ khóa `màn hình`, `ảnh`, `hình ảnh` sẽ tự động kích hoạt câu từ chối mẫu từ chối xử lý:
   > *"Tôi không thể nhìn thấy màn hình của bạn trong cuộc trò chuyện này. Bạn chụp ảnh màn hình và gửi lên đây..."*
4. **Nghẽn Proxy:** Lệnh CLI `opencode run` được dẫn qua cụm 69 proxy farm (`oc_farm.py`). Khi có payload nặng hoặc request dồn dập, proxy dính concurrency limit hoặc rate-limit dẫn đến timeout 120s hoặc lỗi `UnknownError: Unexpected server error`.

## 3. Cấu hình Chuỗi Fallback Hermes chuẩn (Hermes Fallback Hierarchy)
Để đảm bảo khi Gemini hết quota thì session vẫn đọc được ảnh bình thường, Hermes cấu hình 2 tầng fallback trong `config.yaml`:
```yaml
fallback_providers:
  - model: cx/gpt-5.6-luna-high
    provider: custom:omni
  - model: muse-spark-1.3
    provider: custom:opencode
```
- **Tầng 1 (Primary Fallback):** `cx/gpt-5.6-luna-high` qua OmniRoute (`:20129`). Hỗ trợ Native Vision đầy đủ, reasoning mạnh, có pool 21 connection tài khoản xoay vòng, không bị nghẽn proxy, đọc hiểu ảnh screenshot hiện trường 100%.
- **Tầng 2 (Secondary / Emergency Fallback):** `muse-spark-1.3` qua OpenCode bridge (`:20130`). Chỉ dùng làm chốt chặn văn bản/code cuối cùng khi cả OmniRoute bị cô lập mạng.

## 4. Kết luận Vận hành & Cấm Kỵ
* **CẤM TUYỆT ĐỐI ép Muse Spark / OpenCode đọc ảnh:** OpenCode bản chất là công cụ dòng lệnh text/code, không có mắt nhìn và có guardrail từ chối cứng với câu hỏi liên quan đến ảnh.
* **Quy tắc Vàng:** Mọi nhu cầu phân tích ảnh / hiện trường giao diện bắt buộc phải chạy trên các model Native Multimodal (`ag-gemini`, `cx/gpt-5.6-luna-high`, `ag-sonnet`).

## 5. Sự cố Trượt Fallback sang Muse Spark Bị Treo & Phục Hồi Port 20130 (2026-09-29)
- **Hiện tượng**: Primary model gặp lỗi (`omni-worker` timeout/busy), Hermes tự động kích hoạt fallback sang `muse-spark-1.3 via custom:opencode`, nhưng request thất bại ngay lập tức (không phản hồi hoặc báo lỗi).
- **2 Nguyên nhân kết hợp**:
  1. **Bridge Port 20130 Offline**: Tiến trình nền `opencode_bridge.py` trên cổng `20130` không chạy (chưa khởi động sau reboot hoặc crash), khiến request gửi tới `http://127.0.0.1:20130/v1` bị từ chối kết nối (`HTTP 000 / Connection refused`).
  2. **Dính Payload Ảnh Trong Lịch Sử Turn**: Lịch sử hội thoại của turn trước có ảnh đính kèm (screenshot/media). Khi Hermes trượt fallback giữa chừng, toàn bộ context mang theo block ảnh gửi sang OpenCode text-only, dẫn đến lỗi văng hoặc từ chối xử lý.
- **Quy trình Khắc phục & Vận hành Nhanh**:
  1. Kiểm tra liveness cổng 20130: `curl -s http://127.0.0.1:20130/health`
  2. Nếu chết port: Chạy nền `python D:/Taadaa/tools/opencode_bridge.py` (background=true).
  3. Xác thực phản hồi: `curl -s http://127.0.0.1:20130/v1/chat/completions -H "Content-Type: application/json" -d '{"model": "muse-spark-1.3", "messages": [{"role": "user", "content": "1+1=?"}], "stream": false}'`.
  4. Nếu phiên có ảnh: CẤM trượt sang OpenCode, bắt buộc giữ model có vision trên OmniRoute (`:20129`) như `cx/gpt-5.6-luna-high`.
