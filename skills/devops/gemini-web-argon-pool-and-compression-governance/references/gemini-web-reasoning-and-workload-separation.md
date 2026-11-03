# Gemini-Web Reasoning Effort & Workload Separation Invariants

## 1. Bản chất Reasoning Slot trên Gemini-Web (`executors/gemini-web.ts`)
OmniRoute tích hợp cơ chế thinking cho Gemini Web thông qua protobuf slot 17 (`inner[17]`):
- `"reasoning_effort": "high"` $\to$ `resolveThinkingSlot` trả về `[[0]]` (Maximum Thinking cho Gemini 3.1 Pro / Argon).
- `"reasoning_effort": "low"` $\to$ `[[4]]`.
- `"reasoning_effort": "none"` $\to$ `null` (Tắt hoàn toàn suy nghĩ).
- Mặc định $\to$ `[[2]]`.

## 2. Kỷ luật phân định Workload giữa các Combo Gemini-Web
Dù chung dàn 20 tài khoản Pro Web trên `:20129`, việc sử dụng phải phân định rõ ràng theo vai trò:

### A. Luồng Cố vấn (Advisor) & Lập Plan (Planner)
- **Files:** `D:/Taadaa/tools/consult_advisor.py`, `D:/Taadaa/tools/gate_b_planner.py`.
- **Cấu hình bắt buộc:** Bắt buộc gửi kèm `"reasoning_effort": "high"`.
- **Mục đích:** Kích hoạt phân tích rủi ro đa chiều và tính toán anchor code diff O(1) duy nhất (`count == 1`).

### B. Luồng Nén Ngữ Cảnh (Context Compression)
- **Module:** `D:/Taadaa/Hermes/agent/context_compressor.py`.
- **Cấu hình bắt buộc:** TUYỆT ĐỐI KHÔNG gửi `reasoning_effort` hoặc để `none`.
- **Lý do:** Payload nén rất lớn (20k - 60k tokens). Bật reasoning sẽ kéo dài latency > 40s, gây tắc nghẽn proxy 4G và kích hoạt vòng lặp retry 503 trên toàn pool.
