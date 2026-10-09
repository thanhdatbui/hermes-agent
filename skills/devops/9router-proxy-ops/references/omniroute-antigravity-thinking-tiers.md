# OmniRoute / Antigravity Thinking Tier & Combo Target Pitfalls

## 1. Antigravity Thinking Activation Mechanism
- **Model ID Suffix Requirement**:
  - `antigravity/claude-opus-4-6-thinking`: Thinking bật mặc định (do có hậu tố `-thinking`).
  - `antigravity/claude-sonnet-4-6`: Mặc định **NO THINKING** nếu không truyền explicit thinking budget / effort trong payload OpenAI-compatible.
  - Để kích hoạt thinking cố định ở cấp model ID trên Antigravity, bắt buộc dùng các tier model:
    - `antigravity/claude-sonnet-4-6-low`
    - `antigravity/claude-sonnet-4-6-medium`
    - `antigravity/claude-sonnet-4-6-high`
  - Với Gemini: `antigravity/gemini-3.8-flash-tiered` không tự bật thinking trừ khi map đúng tier hoặc dùng `antigravity/gemini-3.7-flash-high`.

## 2. OmniRoute Combo Target Mapping Pitfall
- Khi tạo combo pool (ví dụ `ag-claude`), nếu danh sách target models trỏ vào model ID cơ sở (`antigravity/claude-sonnet-4-6`), toàn bộ request gửi qua combo sẽ rơi vào chế độ chạy thường (No-thinking), dù phía client có cấu hình `reasoning_effort: medium` nếu bridge không serialize đúng tham số downstream.
- **Quy tắc kiểm tra bắt buộc**:
  - Không bao giờ chỉ nhìn vào client config (`config.yaml`) để kết luận model đang chạy thinking.
  - Phải inspect trực tiếp log dashboard (`:20129`) hoặc API response:
    - Kiểm tra `completion_tokens` vs `reasoning_tokens` / `prompt_tokens`.
    - Kiểm tra cột `MODEL` thực nhận trên Dashboard: phải hiện rõ `-thinking` hoặc `-high`/`-medium`. Nếu chỉ hiện `claude-sonnet-4-6` trần thì 100% đang chạy No-thinking.
