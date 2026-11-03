# Gemini-Web Reasoning Control & Workload Isolation Protocol (2026-11-03)

## 1. Cơ Chế Điều Khiển Suy Luận (Reasoning Effort) Trên OmniRoute
Mã nguồn backend OmniRoute (`open-sse/executors/gemini-web.ts`) ánh xạ tham số `reasoning_effort` trực tiếp vào Slot 17 của protobuf payload gửi tới Google Gemini StreamGenerate:
- `"reasoning_effort": "high"` $\to$ Slot 17 = `[[0]]` (Maximum thinking).
- `"reasoning_effort": "low"` $\to$ Slot 17 = `[[4]]` (Low thinking).
- `"reasoning_effort": "none"` $\to$ Slot 17 = `null` (Tắt thinking).
- Mặc định / không truyền $\to$ Slot 17 = `[[2]]` (Default minimal thinking).

## 2. Kỷ Luật Phân Tách Tải & Cấu Hình Từng Luồng
Pool 20 tài khoản Gemini Pro Web được dùng chung nhưng phân hóa rõ rệt về cấu hình request:

1. **Luồng Advisor (`consult_advisor.py`) & Planner (`gate_b_planner.py`):**
   - **Bắt buộc gửi:** `"reasoning_effort": "high"`.
   - **Mục đích:** Kích hoạt thinking sâu để phân tích rủi ro, phản biện kiến trúc và tính toán anchor code diff duy nhất cho patch O(1).
   - **Giao thức:** SSE Streaming (`stream: True`) để nhận từng token real-time, tránh idle socket timeout.

2. **Luồng Nén Ngữ Cảnh (Context Compression - `gemini-web`):**
   - **TUYỆT ĐỐI KHÔNG BẬT REASONING:** Để `none` hoặc mặc định. Payload nén khổng lồ (20k–60k tokens), nếu bật suy nghĩ sâu sẽ kéo dài thời gian tóm tắt > 40s làm nghẽn hàng đợi proxy 4G và gây lỗi 503 retry cascade.
   - **Timeout:** 300s (`auxiliary.compression.timeout = 300`) để nuốt trọn payload qua proxy 4G.
   - **Cắt tỉa cơ học (Pre-pass):** Tự động rút ruột các lệnh terminal cũ thành 1 dòng tóm tắt `[terminal] ran ... -> exit 0` trước khi gửi lên LLM nén.

## 3. Đồng Bộ Tài Khoản Giữa Các Combo
- Khi scale-up số lượng tài khoản (ví dụ từ 15 lên 20 acc), bắt buộc phải kiểm tra và cập nhật đồng thời cả hai combo trên CSDL `storage.sqlite`:
  - `gemini-web` (dùng cho nén và planner).
  - `gemini-web-argon-pool` (dùng cho advisor và worker).
- Cả hai combo đều áp dụng chiến lược `cache-optimized` và tắt session stickiness (`sticky: False`) để tản đều tải xoay vòng qua dải proxy Mobi 4G.
