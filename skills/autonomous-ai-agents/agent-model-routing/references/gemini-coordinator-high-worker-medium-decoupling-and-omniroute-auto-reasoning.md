# Gemini 3.8 Coordinator High vs Worker Medium Decoupling & OmniRoute Auto-Reasoning Invariants (2026-10-07)

## 1. Decoupled Reasoning Effort: Coordinator (High) vs Delegation Worker (Medium)

### A. Bối cảnh & Nghi vấn
User đặt câu hỏi: *"Có được không vậy? Tôi tưởng bị ép worker phải giống coordinator"*.

### B. Cơ chế Decoupling trong Hermes Core
Hermes phân tách độc lập 2 khối cấu hình trong `config.yaml`:
1. **Khối Coordinator phiên chính (`agent:`):**
   ```yaml
   agent:
     reasoning_effort: high
     reasoning_overrides:
       omni-worker: high
       ag-gemini-pool-3: high
   ```
   - Khi chat trực tiếp trên Telegram hoặc CLI, Hermes đọc `agent.reasoning_effort` (hoặc override tương ứng) $\rightarrow$ gửi `reasoning_effort: "high"` sang OmniRoute.
   - Google Antigravity phân bổ budget tư duy trần (24.576 tokens) cho Coordinator bao quát toàn farm, bắt lỗi logic và quản lý fleet state machine (`DRAINING`, `QUARANTINE_LANE`).
2. **Khối Subagent Worker (`delegation:`):**
   ```yaml
   delegation:
     model: ag-gemini-pool-3
     provider: omni
     reasoning_effort: medium
     max_iterations: 15
   ```
   - Khi Coordinator gọi `delegate_task(goal=...)`, Hermes khởi tạo child agent trong session cô lập.
   - Child agent đọc cấu hình từ `delegation.reasoning_effort`, ghi đè (override) giá trị của parent.
   - Subagent gửi `reasoning_effort: "medium"` $\rightarrow$ Google Antigravity cấp budget 8.192 tokens. Worker code nhanh (5–8s), bám sát Scope Lock O(1), không over-engineer hay ngâm turn.

### C. Độc lập 100% — Không Kéo Đè Lẫn Nhau
- Coordinator chạy `high` **hoàn toàn KHÔNG ép** Worker phải chạy `high`.
- Worker chạy `medium` **hoàn toàn KHÔNG làm hạ cấp** Coordinator về `medium`.
- Đã được chứng minh qua call logs của OmniRoute (`:20129`): request từ Telegram ghi nhận `reasoning_effort: high`, request từ subagent ghi nhận `reasoning_effort: medium`.

---

## 2. Gemini Dynamic / Tiered Reasoning & OmniRoute Auto Protocol

### A. Thực tế với `reasoning_effort: "auto"`
- Client (Hermes/OpenAI client) gửi `"reasoning_effort": "auto"` sang OmniRoute `:20129`.
- OmniRoute nhận 200 OK nhưng trong file `open-sse/translator/request/openai-to-gemini.ts` có bảng map:
  ```typescript
  const budgetMap = {
    none: 0,
    low: 1024,
    medium: 8192,
    high: highBudget, // 24576
    auto: highBudget, // <--- Hardcode auto -> 24576
  };
  ```
- OmniRoute tự gán cứng `thinkingBudget: 24576` vào payload gửi Google Antigravity. Upstream Google hiểu là ép mức High, không tự co giãn suy luận theo độ khó.

### B. Chuẩn Wire Protocol để đạt Dynamic Thật sự trên Gemini
- Upstream Google Antigravity schema validator bắt buộc `thinkingBudget` là số nguyên dương $\ge 0$.
- Tuyệt đối **CẤM** gửi `thinkingBudget: -1` hay `thinkingBudget: "auto"` $\rightarrow$ Google trả về `400 INVALID_ARGUMENT`.
- **Giải pháp chuẩn:** Khi `reasoning_effort === "auto"` hoặc model mang hậu tố `-tiered`, OmniRoute **phải bỏ hẳn key `thinkingBudget`**, chỉ gửi:
  ```json
  "thinkingConfig": {
    "includeThoughts": true
  }
  ```
  Lúc này Gemini 3.8 Flash Tiered mới thực sự tự quyết định số token suy luận theo độ khó của câu hỏi.

---

## 3. OmniRoute Combo `review` Timeout & Closeout Gate Fallback
- Khi chạy `closeout_gate.py` với OmniRoute (`:20129`), combo mặc định `review` có thể bị nghẽn (HTTP 499 / timeout 300s) nếu có model thành viên bị lỗi kết nối hoặc hanging (như `codex/gpt-5.6-terra-high` hoặc missing connection).
- **Khắc phục:** Truyền trực tiếp `--model ag-gemini-pool-3` (hoặc pool hoạt động ổn định) vào `closeout_gate.py`:
  ```bash
  python D:/Taadaa/tools/closeout_gate.py --repo <path> --base HEAD --base-url http://127.0.0.1:20129/v1/chat/completions --model ag-gemini-pool-3 --json-output
  ```
- `--base HEAD` đảm bảo chỉ diff đúng các thay đổi chưa commit trong phiên hiện tại, tránh kéo diff từ commit cũ.
