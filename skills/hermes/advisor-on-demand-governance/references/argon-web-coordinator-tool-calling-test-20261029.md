# Khảo Sát & Kiểm Chứng: Gemini Web Argon 4 Trên Hermes Coordinator

## 1. Bối cảnh & Yêu cầu
- Người dùng muốn thử nghiệm đưa **Gemini Web Argon 4** (`gemini-web-argon-pool` qua OmniRoute `:20129`) lên làm Coordinator chính trên Hermes Telegram.
- Đã cấu hình thêm model vào `providers.omni.models.gemini-web-argon-pool` trong file `D:/Taadaa/Hermes/deploy/hermes-home/config.yaml`.

## 2. Bằng chứng thực nghiệm (Empirical Evidence)

### A. Kiểm tra phản hồi văn bản thuần (Text-Only Query)
- **Request:** `{"messages": [{"role": "user", "content": "1+1 bằng mấy? Trả lời số."}]}`
- **Endpoint:** `http://192.168.110.123:20129/v1/chat/completions` (hoặc localhost)
- **Kết quả:** Phản hồi `2` trong 11s, hoạt động trơn tru.

### B. Kiểm tra phản hồi khi kèm Tool Calling Schema (Coordinator Function Calling)
- **Request:** Bổ sung schema `tools` chứa hàm `read_file(path)` vào payload chuẩn OpenAI.
  - Prompt: `"Đọc file D:/test.txt giúp tôi"`
- **Response thực tế từ OmniRoute / Gemini Web:**
```json
{
  "id": "chatcmpl-1793236090614",
  "object": "chat.completion",
  "created": 1793236090,
  "model": "gemini-3.1-pro",
  "choices": [
    {
      "index": 0,
      "finish_reason": "stop",
      "message": {
        "role": "assistant",
        "content": "Trước tiên, bạn cần kết nối với Google Drive để bật tiện ích này."
      }
    }
  ]
}
```

## 3. Phân tích nguyên nhân gốc rễ (Root Cause Analysis)
1. **Thiếu Native Function Calling:** Backend `gemini-web.ts` đảo chiều giao diện web `gemini.google.com` (gọi RPC `StreamGenerate`). Giao diện người dùng của Google không hỗ trợ nhận schema Function Calling chuẩn của OpenAI.
2. **Ảo giác Extension:** Khi thấy tham số công cụ liên quan đến tệp tin/đọc tệp, model trên giao diện Web tự hiểu nhầm sang Extension Google Drive và yêu cầu người dùng cấp quyền Extension thay vì trả về khối `tool_calls`.
3. **Mất khả năng điều phối:** Do `tool_calls` luôn rỗng (`null`), Hermes Coordinator không thể thực thi bất kỳ hành động nào trên hệ thống (không đọc file, không sửa code, không chạy shell, không dispatch worker).

## 4. Kết luận kiến trúc
- **Coordinator:** BẮT BUỘC duy trì **Antigravity CLI / Pool (Gemini 3.8 Flash High)** hoặc các model có Native Function Calling chuẩn API.
- **Worker:** **Gemini Web Argon 4** phát huy sức mạnh tối đa ở vai trò Autonomous ReAct Worker qua `gemini_web_worker.py` (sử dụng text-based ReAct parsing `ACTION: ...` thay vì OpenAI JSON tool calling).
