# Advisor Gate & Planning Quality Standards

## 1. Context & Motivation
- **Coordinator Quality Bottleneck**: Khi Coordinator tự ý lên plan mà không qua phản biện kiến trúc, chất lượng suy luận rất thấp, dễ rơi vào bẫy completion bias, tự vẽ plan ẩu rồi giao Worker làm việc mù quáng.
- **Advisor Gate Principle**: Với mọi bài toán phức tạp, lỗi hệ thống, hoặc task kiến trúc/refactor: **CẤM Coordinator tự nghĩ plan**. BẮT BUỘC phải tham vấn bộ não cấp cao (Claude CLI `claude -p` hoặc Sol / Gemini Pro) trước khi chốt Patch Contract O(1) cho Worker.

## 2. Standard 2-Stage Planning Pipeline
1. **Stage 1 (Advisor Consult)**:
   - Gửi hiện trường + lỗi thật cho Advisor (Claude CLI / Sol):
     - Xác định đúng 100% nguyên nhân gốc rễ (Root Cause).
     - Đề xuất giải pháp O(1) tinh gọn nhất (không over-engineer, không gây tê liệt).
     - Liệt kê các rủi ro và edge cases cần chặn.
2. **Stage 2 (Patch Contract Formulation & Worker Dispatch)**:
   - Coordinator tiếp thu phản biện của Advisor để chuẩn hóa Patch Contract duy nhất:
     - Anchor duy nhất tuyệt đối (`grep -o ... | wc -l == 1`).
     - `old_string` -> `new_string` chính xác.
     - Lệnh test focused < 30s.
   - Dispatch Worker thi công dứt điểm.

## 3. Gemini Web (Argon Pool) vs Antigravity API Quirk
- **Gemini Web (`gemini-web`)**:
  - Chạy qua Chromium CDP trên giao diện người dùng `gemini.google.com`.
  - Không hỗ trợ Native Function Calling / OpenAI tool schema. Nhồi tool calls vào sẽ gây timeout hoặc văng lỗi bối rối: *"I seem to be encountering an error. Can I try something else for you?"*.
  - Thích hợp cho: Chat văn bản thuần túy, phân tích prompt, tóm tắt tài liệu 1M-2M context không kẹp tool.
- **Antigravity API (`ag-gemini-pool-3` / `ag-sonnet`)**:
  - Hỗ trợ Full Native Tool Calling ở tầng weights.
  - Bắt buộc dùng làm Coordinator hoặc khi cần chạy `terminal`, `read_file`, `patch`, `closeout_gate.py`.
