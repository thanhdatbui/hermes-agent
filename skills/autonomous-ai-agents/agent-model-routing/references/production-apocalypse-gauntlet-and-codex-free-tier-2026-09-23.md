# Production Apocalypse Gauntlet & Codex Free Tier Architecture (2026-09-23)

## 1. Kết Quả Vòng Thẩm Định Tối Cao: "Production Apocalypse Gauntlet"
Do Giám khảo Trưởng Sol High (`chatgpt-web/gpt-5.6-sol-high`) trực tiếp ra đề và chấm điểm theo chuẩn Production SRE khắt khe cho đội hình vô địch `cx/gpt-5.6-luna-high`.

| STT | Bài toán Tận thế | Điểm | Kết luận | Đánh giá kiến trúc then chốt |
|---|---|:---:|:---:|---|
| **1** | **429 Storm & Global Backoff Collapse** | **91/100** | **PASS** | 4 tầng phòng thủ: Adaptive rate control (AIMD), centralized Token Bucket (Redis/Lua), backpressure và retry budget có jitter. Cấm worker bypass Coordinator để tránh Retry Storm. |
| **2** | **SQLite Split-Brain & Crash giữa Checkpoint** | **93/100** | **PASS** | Kiến trúc sống còn: **SQLite local per machine + WAL mode + FULL sync + transaction atomic** (`BEGIN IMMEDIATE -> COMMIT`). Tuyệt đối không share SQLite qua network. Dùng fencing token và WAL replay bảo đảm Zero Data Corruption (giữ vững lưới 8 slot/máy). |
| **3** | **Login Flow Mutation Defense** | **92/100** | **PASS** | **Không cố "đuổi theo" Captcha/challenge lạ**. Tầng Auth phát hiện mutation so với baseline $\to$ Fail-stop an toàn ngay lập tức $\to$ fleet circuit breaker để tránh bị TikTok quét checkpoint hàng loạt tài khoản. |
| **4** | **Regional Power Loss (40 máy mất điện)** | **94/100** | **PASS** | Kiềng 3 chân: **Lease expiry + Fencing token (Epoch) + Idempotent execution**. Ngăn chặn hoàn toàn zombie worker và duplicate claim khi 40 node cùng hồi sinh. |
| **5** | **Coordinator Brain Damage (Sập 30 phút)** | **94/100** | **PASS** | Tư duy SRE: "Coordinator chết không có nghĩa worker phải chết". Khi sống lại, tuyệt đối cấm "Panic Reset" mà đi qua chu kỳ: **Observe $\to$ Reconcile (đọc checkpoint bền vững) $\to$ Resume**. |
| **TỔNG** | **5 BÀI TOÁN TẬN THẾ** | **464/500 (92.8đ)** | **100% PASS** | 🏆 **VERDICT: PRODUCTION APPROVED** |

---

## 2. Bản Chất Quota & Chi Phí Của Codex vs ChatGPT Web (Đính chính chuẩn xác)
- **Chi phí tiền mặt ($0 Fee)**: Cả tài khoản Codex và ChatGPT Web trong pool `storage.sqlite` đều là tài khoản Free (`workspacePlanType: 'free'`), không gắn thẻ tín dụng, không trừ USD.
- **Sự thật về Quota Web vs Codex**:
  - **ChatGPT Web Free KHÔNG PHẢI "Unlimited / Free luôn"**: OpenAI áp hạn ngạch cửa sổ trượt (Rolling Window, vài chục tin nhắn / 3–5 tiếng). Khi hết lượt, nó bóp quota hoặc giáng cấp xuống non-thinking. Hệ thống sở dĩ gọi liên tục không thấy hết là nhờ **pool 17 tài khoản Web xoay vòng Round-Robin**, không phải do OpenAI thả không giới hạn!
  - **Khả năng Thinking trên Web**: **CÓ HỖ TRỢ THINKING** (`chatgpt-web/gpt-5.6-sol-high` và `chatgpt-web/gpt-5.6-luna-free-thinking` đều gọi được và có thinking tokens thật). Tuy nhiên, Web chỉ dùng **Emulated Tool Calling** qua thẻ `<tool>` (dễ rớt format JSON khi dispatch phức tạp) và có nguy cơ dính **Cloudflare Sentinel 403** / Session Expired khi nã tải liên tục.
  - **Codex Free**: Cấp theo hạn ngạch chu kỳ (**Codex Scope Allowance** có ngày reset cố định như `codexScopeRateLimitedUntil`). Dùng hết acc sẽ bị khóa cổng Codex đến chu kỳ sau. Bù lại, Codex hỗ trợ **Native Tool Calling 100%**, Prompt Cache Affinity và độ ổn định kết nối vượt trội (OAuth trực tiếp, không dính Cloudflare).
- **Tử huyệt Routing OmniRoute (`cx/` vs `codex/`)**:
  - `cx/gpt-5.6-luna-high` và `cx/gpt-5.6-luna-max` kết nối trực tiếp đến backend Codex rất nhanh (10–25s).
  - Calling alias `codex/gpt-5.6-luna-high` hoặc `codex/gpt-5.6-luna-max` dễ bị timeout upstream (chờ >60s). Luôn dùng tiền tố **`cx/`**.

---

## 3. Tại Sao Luna High Thắng Luna Max & Terra High?
1. **Worker Layer (Luna High 2 - 1 Luna Max)**:
   - Luna Max suy nghĩ quá lâu (110s–160s, đốt 6.000–8.000 reasoning tokens) và bị bệnh **over-constrain** (tự đặt ràng buộc cứng nhắc về format tuple, ép file 3000 dòng).
   - Luna High thực dụng: bám Scope Lock, atomic write qua tempfile + `os.replace`, SHA-256 byte stream, focused test <5s.
2. **Coordinator Layer (Luna High 94đ vs Terra High 84đ & Max 78đ ở bài xung đột tài nguyên)**:
   - Terra High bị overthinking (tự thêm XPath fallback, thêm điều kiện thừa) và "ba phải" trong phân bổ tài nguyên.
   - Luna Max sai lầm chiến lược khi dồn Standby cho ca Reg mới trong lúc 100 máy ca Nuôi đang trễ mạng (bỏ rơi tài sản lớn nhất).
   - Luna High ra quyết định O(1) chuẩn SRE: ưu tiên tuyệt đối bảo vệ 100 máy Nuôi, dùng lease/epoch ngăn chặn double-run.

---

## 4. Cấu Hình Chuẩn Hermes: Coordinator High vs Worker Medium
Để Coordinator có tầm nhìn bao quát toàn farm trong khi Worker subagents không bị over-engineering:
```yaml
# config.yaml
model:
  default: omni-worker
  provider: omni

agent:
  reasoning_effort: high
  reasoning_overrides:
    omni-worker: high

delegation:
  model: omni-worker
  provider: omni
  reasoning_effort: medium     # Worker luôn chạy Medium (code sạch, test <5s)
  max_iterations: 15
  child_timeout_seconds: 600
  max_concurrent_children: 8
```
- **Lưu ý Giám khảo Plan Review / Closeout Gate**: BẮT BUỘC gọi `chatgpt-web/gpt-5.6-sol-high`. CẤM dùng `sol-instant` vì thiếu thinking tokens ngầm, dễ chấm cảm tính.

---

## 5. Cơ Chế Code Core Hermes Tách Đôi Reasoning Effort
Dưới đây là chi tiết mã nguồn trong Hermes Agent chứng minh tính tách rời hoàn toàn giữa Session chính và Worker con:
1. **Session chính (Coordinator)**:
   - `hermes_constants.resolve_reasoning_config(cfg, model)`: Đọc `agent.reasoning_overrides[model]`, nếu không có fallback về `agent.reasoning_effort`.
   - Gán vào `parent_agent.reasoning_config = {'enabled': True, 'effort': 'high'}`.
2. **Subagents ngầm (Worker khi `delegate_task`)**:
   - `tools/delegate_tool.py` (dòng 1255–1267):
     ```python
     parent_reasoning = getattr(parent_agent, "reasoning_config", None)
     child_reasoning = parent_reasoning
     delegation_effort = delegation_cfg.get("reasoning_effort")
     if delegation_effort:
         parsed = parse_reasoning_effort(delegation_effort)
         if parsed is not None:
             child_reasoning = parsed  # Ghi đè độc lập: {'enabled': True, 'effort': 'medium'}
     ```
   - Giá trị này được inject trực tiếp vào `AIAgent` của subagent (`reasoning_config=child_reasoning`), hoàn toàn đè bẹp mức `high` của cha!
3. **OmniRoute Payload & Target Trap**:
   - Khi gửi sang OmniRoute `:20129`, `reasoning_effort` được gửi trong payload `/v1/chat/completions`.
   - **Bẫy tên model**: Nếu model target trong combo không có `-thinking` (như `claude-sonnet-4-6` vs `claude-opus-4-6-thinking`), Antigravity backend mặc định chạy No-Thinking trừ khi có tham số `reasoning_effort` truyền vào. Vì vậy việc set tường minh `high` cho Coordinator và `medium` cho Worker đảm bảo 100% request được kích hoạt đúng mức thinking tương ứng.
