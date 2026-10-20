# Độc Đạo Điều Phối Advisor Sol & Vòng Đời Biến Môi Trường (2026-10-20)

## 1. Giải Mã Thắc Mắc: "Tại Sao 1 Công Cụ Lại Có 2 Đường?"

Hệ thống ghi nhận sự xuất hiện của 2 file công cụ liên quan đến Advisor Sol:
1. `D:/Taadaa/Hermes/tools/advisor_tool.py` (Core Native Tool).
2. `D:/Taadaa/tools/consult_advisor.py` (External Streaming Script).

### Sự thật kiến trúc: "Available but not exposed" (CẤM XÓA `advisor_tool.py`)
Đường 1 (`advisor_tool.py`) có cờ `check_fn=lambda: False` tại dòng 155. Cờ này **KHÔNG PHẢI là vô hiệu hóa hay phế bỏ**, mà là kỹ thuật kiến trúc:
- **Ẩn khỏi LLM:** Không phơi tool vào catalog để LLM gọi bừa bãi trong lúc suy nghĩ.
- **Harness ngầm gọi:** Nhưng `Hermes/agent/conversation_loop.py` (`_maybe_append_advisor_for_final_response`) **bắt buộc nạp và gọi ngầm `advisor_consult` ở cuối turn** để tự động ghép khối `--- Advisor (Sol / review) ---`.
- **CẤM XÓA `advisor_tool.py`:** Xóa file này sẽ làm sập hoàn toàn cơ chế tự động ghép Advisor của Hermes Core.

Đường 2 (`consult_advisor.py`) là script CLI độc lập cho Coordinator chạy trực tiếp qua Terminal hoặc subagent khi cần chủ động truy vấn Sol với cơ chế SSE streaming.

### Bảng đối soát 2 kênh:

| Tiêu chí | Kênh 1: `advisor_tool.py` (Hermes Core Auto-append) | Kênh 2: `consult_advisor.py` (Coordinator CLI / Script) |
| :--- | :--- | :--- |
| **Cơ chế kích hoạt** | Tự động bởi Hermes Core sau khi Coordinator trả lời xong (`_maybe_append_advisor_for_final_response`). | Được Coordinator hoặc script bên ngoài chủ động gọi qua terminal: `python D:/Taadaa/tools/consult_advisor.py --query "..."`. |
| **Giao thức mạng** | HTTP POST JSON (`stream: False`). | **SSE Streaming (`stream: True`)**: Nhận từng chunk token qua HTTP stream. |
| **Kiểm soát timeout** | `DEFAULT_TIMEOUT = 85s` (đã nâng từ 55s lên 85s để đồng bộ với 80s readiness của OmniRoute). | **Idle Streaming Timeout 3 tầng**: `first_token: 80s`, `idle: 20s`, `total: 140s`, `wall-clock: 150s`. |
| **Trạng thái catalog** | `check_fn=lambda: False` $\rightarrow$ Hermes Core ẩn khỏi tool catalog của LLM nhưng gọi trực tiếp qua handler. | Script CLI độc lập, không đăng ký trong registry tool. |

---

## 2. Bản Chất Vấn Đề: "Đã Tăng Timeout Ở Session Khác Nhưng Vẫn Dính 45s"

Khi Operator thắc mắc đã sửa timeout ở session trước nhưng thực tế vẫn bị timeout 45s:

### 3 Nguyên nhân cốt lõi:
1. **Tiến trình OmniRoute trong RAM chưa restart (Hot-reload Trap):**
   - Node.js (`scripts/dev/run-next.mjs`) chỉ nạp file `.env` vào `process.env` đúng 1 lần khi khởi động.
   - Sửa file `.env` mà chưa restart service (hoặc chưa qua ca reboot farm) thì tiến trình live trong RAM vẫn giữ giá trị cũ (`ACCOUNT_SEMAPHORE_TIMEOUT_MS=45000`).
   - *Cách kiểm chứng:* Dùng Python `psutil.Process(pid).environ()` để đọc biến môi trường thực tế trong RAM của tiến trình Node.js port 20129.
2. **Fallback Hardcode trong mã nguồn:**
   - Trong `open-sse/services/accountSemaphore.ts`:
     ```typescript
     const DEFAULT_TIMEOUT_MS = Number(process.env.ACCOUNT_SEMAPHORE_TIMEOUT_MS) || 45_000;
     ```
     Nếu biến môi trường không được inject hoặc process khởi chạy không nạp env, code sẽ rơi về fallback cứng 45s.
3. **Hiện tượng Waterfall khi Pool gặp tài khoản hạn mức:**
   - Tăng timeout lên 80s–150s chỉ có tác dụng khi có tài khoản sạch sẵn sàng phục vụ.
   - Nếu trong pool có các tài khoản đang dính giới hạn 3h (`You've hit your limit`), mỗi tài khoản dính lỗi sẽ ngâm khoảng 15s–20s để thử lại trước khi rotate.
   - Xoay qua 2 tài khoản dính lỗi ($20s + 20s = 40s$) là chạm ngưỡng ngắt của hàng đợi, gây cảm giác "vẫn bị kẹt 45s".

---

## 3. Khuyến Nghị Vận Hành Cho Coordinator
1. Khi tư vấn hoặc trả lời về Advisor Sol, luôn nhớ **`consult_advisor.py` là single source of truth**, không dẫn chiếu nhầm `advisor_tool.py`.
2. Mọi thay đổi cấu hình timeout trong `.env` của OmniRoute phải đi kèm lệnh kiểm chứng `psutil` để xác nhận tiến trình live đã nạp cấu hình mới vào RAM.
