# Context Compression Boundary & OmniRoute Backend-Only Build UI Loss Pitfall (2026-11-03)

## 1. Ranh giới kiến trúc: Nén ở Hermes Client vs Cấm chế cháo ở Proxy
- **Quy tắc phân tầng:** Việc quản lý ngữ cảnh, nén lịch sử chat (Context Compression) là trách nhiệm **100% của Client (Hermes)** (`agent/context_compressor.py`).
- **CẤM:** Tuyệt đối không được thêm các tầng nén, cắt tỉa payload (`compressToolResults`, `lite.ts`) vào proxy router (OmniRoute / 9Router).
  - Proxy chỉ có nhiệm vụ forward request, cân bằng tải và failover tài khoản.
  - Chế cháo middleware nén ở proxy làm biến dạng schema JSON đa phương thức (ảnh Base64 + function calls), gây lỗi upstream HTTP 400 `INVALID_ARGUMENT`.
- **Cấu hình chuẩn của User trên Hermes:**
  - `compression.threshold`: **`0.6`** (~600k tokens mới kích hoạt nén).
  - `compression.protect_last_n`: **`50`** (bảo vệ nguyên vẹn 50 tin nhắn và tool-calls gần nhất chống Context Drift).
  - `compression.protect_first_n`: **`3`**.

## 2. Tử huyệt Build Backend-Only trên OmniRoute Next.js: "Sửa Backend làm mù Frontend"
- **Hiện tượng:** Sau khi sửa code backend của OmniRoute trong `open-sse/`, nếu chạy lệnh `npm run build:backend`, API proxy `:20128/v1/chat/completions` chạy được nhưng giao diện Web Dashboard (`:20128` hoặc `:20129`) sẽ bị **trắng trang, 404, hoặc crash layout**.
- **Căn nguyên mã nguồn (`scripts/build/backendOnlyPages.mjs`):**
  - Cờ `OMNIROUTE_BUILD_BACKEND_ONLY=1` kích hoạt `stubDashboardPages()`: Tạm thời thay thế toàn bộ 126 file UI Dashboard Next.js (Monaco Editor, Recharts, Mermaid) bằng các server stubs rỗng trước khi `next build`.
  - Kết quả: Thư mục standalone chỉ có API backend, toàn bộ client-entry manifest và code giao diện Web bị đè mất.
- **Kỷ luật vận hành:**
  - CẤM chạy `npm run build:backend` khi hệ thống đang cần dùng Web Dashboard.
  - Khi cần build hoàn chỉnh OmniRoute, bắt buộc chạy build đầy đủ với RAM Node cấp phát:
    ```bash
    cross-env NODE_OPTIONS="--max-old-space-size=4096" npm run build
    ```

## 3. Bản Nâng Cấp "Nén Khôn Cơ Học" (Zero-LLM Cache Preservation)
Tại `D:/Taadaa/Hermes/agent/context_compressor.py` (Phase 1):
- Ngay khi chạm mốc 600k tokens (`threshold: 0.6`), Hermes thực hiện pre-pass cơ học rút ruột các lệnh tool cũ (`_prune_old_tool_results`): thay hàng chục nghìn dòng log bằng 1 dòng `[terminal] ran <cmd> -> exit <code_output>`.
- **Cơ chế ngắt thông minh:** Nếu sau khi tỉa thô mà `estimate_messages_tokens_rough(messages) < self.threshold_tokens`, compressor **DỪNG NGAY LẬP TỨC**, trả về messages mà KHÔNG gọi LLM tóm tắt:
  ```python
  if estimate_messages_tokens_rough(messages) < self.threshold_tokens:
      if not self.quiet_mode:
          logger.info("Mechanical pruning brought tokens below threshold; skipping LLM summarizer to keep prompt cache.")
      return messages
  ```
- **Lợi ích:** 80% trường hợp phình context được giải tỏa ngay lập tức mà không tốn token, bảo tồn 100% Prompt Cache của Gemini và không làm mất trí nhớ kỹ thuật.

## 4. Lựa Chọn Model Nén Phụ & Timeout Chuẩn Xác
- **Bẫy Context Window của Sol Web (`gpt-web-sol`):** Sol Web chỉ có context window 32k-64k. Dù Hermes có bộ lọc `_CONTENT_MAX = 6000` chars/msg, nhưng nếu phiên chat kéo dài hàng trăm tin nhắn thì payload gửi sang Sol Web vẫn có thể vượt trần 32k gây lỗi `400/413 Context Overflow`.
- **Giải pháp: Dùng `gemini-web` (Argon Gemini Web):**
  - Trần context đầu vào 1.000.000 tokens (1M), nuốt trọn mọi payload lớn mà không bao giờ lo tràn context.
  - Tốc độ xử lý ~6.9s cho payload 66k tokens (264k chars).
  - Cấu hình chuẩn:
    ```bash
    hermes config set auxiliary.compression.model gemini-web
    hermes config set auxiliary.compression.timeout 300
    ```
- **Timeout 300s:** Nâng `auxiliary.compression.timeout` lên 300 giây (5 phút), dẹp bỏ hoàn toàn các mốc timeout ngắn (45s/120s) tránh tình trạng rớt mạng nội bộ hoặc nghẽn socket làm gãy tiến trình nén.
- **Không cần restart Gateway:** Hermes Gateway có cơ chế cache-busting tự động nhận diện thay đổi của các key `compression.*` và `auxiliary.compression.*` trong `config.yaml` để nạp compressor mới cho lượt tiếp theo mà không cần khởi động lại process.
