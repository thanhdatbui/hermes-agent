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
