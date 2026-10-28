# Kiến Trúc Phân Vai: Vì Sao Gemini Web Argon 4 Không Thể Làm Coordinator

## 1. Bản Chất Kỹ Thuật: Web Protocol vs. API Protocol
* **Coordinator (Hermes Gateway)**:
  - Cần giao thức chuẩn OpenAI Chat Completions với **Native Function Calling**.
  - Request chứa system prompt đồ sộ, context history hàng chục lượt, và định nghĩa schema của 15+ công cụ (`terminal`, `read_file`, `write_file`, `patch`, `delegate_task`, `clarify`, `computer_use`, `cronjob`...).
  - Yêu cầu model phản hồi đúng cấu trúc JSON `tool_calls: [{id, type: "function", function: {name, arguments}}]`.
* **Gemini Web Argon 4 (`gemini-web-argon-pool`)**:
  - Chạy qua reverse headless stream (`open-sse/executors/gemini-web.ts`) giả lập phiên web `gemini.google.com` (gọi RPC nội bộ `StreamGenerate`).
  - Web UI của Google chỉ nhận text thuần và file upload, **hoàn toàn không hỗ trợ Native Function Calling**.
  - Khi được dùng làm **Worker** qua `gemini_web_worker.py`: Ta bọc prompt ReAct và dùng regex bóc tách chuỗi `ACTION: PATCH`, `ACTION: READ_FILE`... Cách này chạy rất tốt cho bài toán đơn lập 1-2 file, nhưng bất khả thi khi làm Coordinator toàn năng của cả hệ thống.

## 2. Giới Hạn Context Window & Cơ Chế Cắt Gọt (Rolling Context Drop)
* Session web của Google được thiết kế cho người dùng chat thông thường, tự động nén hoặc loại bỏ ngữ cảnh khi hội thoại quá dài để tiết kiệm RAM server.
* Nếu đưa lên làm Coordinator, khi context đạt 50k–100k tokens, Argon 4 sẽ bị "mất trí nhớ", rớt mất các rules an toàn, sơ đồ cơ sở dữ liệu và các chỉ thị quan trọng của User.
* Trong khi đó, **Antigravity CLI (Gemini 3.8 Flash High)** chạy trên Google Cloud Code Assist IDE API, hỗ trợ native context 1M tokens, prompt caching và context caching tức thì.

## 3. Độ Bền Luồng Stream Qua Egress Proxy 4G
* Khi Coordinator suy luận sâu và sinh văn bản phân tích dài, luồng HTTP stream qua proxy di động dễ bị ngắt:
  `[STREAM] GEMINI-WEB | gemini-3.1-pro | disconnect: request_signal_aborted / hedge-cancelled`
* Sự cố ngắt kết nối giữa chừng ở tầng Coordinator sẽ làm crash event loop của Gateway và gây lỗi hiển thị trên Telegram.

## 4. Định Vị Phân Vai Chuẩn Mực
1. **Coordinator Tối Cao**: **Antigravity Pool (Gemini 3.8 Flash High)**.
2. **Worker Tiên Phong Phản Ứng Nhanh**: **Gemini Web Argon 4** & **Qoder (DeepSeek-Flash)** (sửa code O(1), fix UI drift, 6s - 22s/task, 0đ quota).
3. **Architect & Safety Reviewer**: **Sol High (:20129)** & **Claude CLI On-Demand**.
