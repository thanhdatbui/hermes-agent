# Gemini Web Argon Pool, Thinking Resolution & Reasoning Invariants (2026-11-03)

## 1. Bản Chất Thực Tế Của "Argon 4" Trên Web vs HTTP REST
- **Giao diện Web (`gemini.google.com/app`):**
  * Trên UI web khi đăng nhập tài khoản Google AI Pro (`dokieu`, `phungthibichngoc`), menu chọn model hiển thị 4 mức rõ ràng: `3.5 Flash-Lite`, `3.8 Flash`, `3.1 Pro`, và **`4 Argon`** (đã kiểm chứng qua Playwright CDP + WinRT OCR).
- **Trên tầng mạng HTTP REST (`gemini-web.ts`):**
  * OmniRoute tương tác với Google qua endpoint ngược `StreamGenerate` (`f.req`). Trong cấu trúc mảng Protobuf, enum `MODE_CATEGORY` ở Slot `[79]` chỉ chấp nhận từ 1 đến 6 (Category 3 là Pro).
  * Khi chọn `4 Argon` trên web, Google chuyển sang giao thức WebChannel nhị phân riêng (`geminiweb-pa.clients6.google.com/v1/processSession`).
  * **Kết luận kỹ thuật:** Model `gemini-web/gemini-3.1-pro` trong combo `gemini-web-argon-pool` thực chất đang chạy trên trọng số **Gemini Pro (Category 3)** kẹp tài khoản Google AI Pro qua proxy 4G Viettel.

## 2. Cơ Chế Điều Khiển Suy Luận (Reasoning / Thinking Slot)
- Trong `open-sse/executors/gemini-web.ts`, hàm `resolveThinkingSlot()` điều khiển cờ suy luận tại Slot `[17]`:
  * `high` $\to$ `[[0]]` (Deep Thinking)
  * `low` $\to$ `[[4]]`
  * Mặc định / `medium` $\to$ **`[[2]]` (Standard Thinking)**.
- Google áp dụng cờ suy luận này trực tiếp vào luồng xử lý server-side (trên web không trả token breakdown riêng như API).

## 3. Bản Chất Lỗi Timeout Giả (Queueing Stalemate) Dù Đã Ép Timeout
- Khi người dùng gửi request tham vấn song song cả 3 Advisors, nhánh Gemini Web bị timeout không phải do trần timeout client nhỏ, mà do:
  * Combo `gemini-web-argon-pool` (15 accounts) áp dụng chiến lược `cache-optimized` phân phối độc quyền.
  * Nếu một tài khoản trong pool đang bị ngâm session xử lý một tác vụ nền khác (chạy deep thinking), request mới sẽ bị **xếp hàng đợi (queueing) tại cổng OmniRoute `:20129`**.
  * Trong script `consult_advisor.py`, luồng `_consult_gemini_inner` có `first_token_timeout=90s`. Thời gian xếp hàng trong hàng đợi cộng với thời gian suy luận vượt quá 90s $\to$ client tự ngắt trước byte đầu tiên.
  * **Giải pháp:** Gọi tường minh cờ `-a all` với cơ chế timeout độc lập cho từng nhánh để đảm bảo cả 3 Cố vấn cùng phản hồi đầy đủ.

## 4. Đồng Bộ Cấu Hình Advisor & Planner
- Cả `consult_advisor.py` (Advisor Claude) và `gate_b_planner.py` (Planner Claude) đều dùng chung một backend điều phối: `claude_worker.py --role reviewer` / `--role planner` (hoặc trực tiếp qua CLI `claude -p`).
- Việc gán `--effort medium` cho vai trò `planner` và `reviewer` trong `claude_worker.py` giúp:
  * Giảm mạnh độ trễ (latency) của cả Hội đồng Advisor lẫn Planner từ ~90s xuống ~15-20s.
  * Tiết kiệm token hạn mức 5h của Claude Code, tránh chạm trần Quota Guard (85%).
  * Worker sửa code (`role == 'worker'`) vẫn giữ nguyên `--effort high` để đảm bảo độ sâu suy luận code.

## 5. Cú Pháp F-String Trên Python 3.11 Runtime
- Môi trường Farm chạy **Python 3.11.15**, chưa hỗ trợ trùng lặp dấu nháy trong f-string như Python 3.12+.
- **Quy tắc bắt buộc:** F-string có biểu thức lồng nhau (join, dict key lookup) BẮT BUỘC dùng **nháy kép `f"..."` bọc ngoài và nháy đơn `'...'` bên trong**:
  ```python
  # SYNTAX ERROR trên Python 3.11:
  header = f'ALERT ({', '.join(reasons)}) - {win['name']}'

  # ĐÚNG VÀ AN TOÀN TRÊN PYTHON 3.11:
  header = f"ALERT ({', '.join(reasons)}) - {win['name']}"
  ```
- Luôn kiểm tra bằng `python -m py_compile <file>` trước khi hoàn tất patch.
