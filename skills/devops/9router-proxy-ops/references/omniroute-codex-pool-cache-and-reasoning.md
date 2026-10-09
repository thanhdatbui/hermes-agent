# OmniRoute Codex Pool, Prompt Cache Optimization & Reasoning Effort

Kinh nghiệm vận hành pool tài khoản OpenAI Codex CLI trên OmniRoute (`:20129`) và tích hợp với Hermes Agent.

## 1. Phạm vi hỗ trợ model của OpenAI Codex Backend
OpenAI Codex backend (`https://chatgpt.com/backend-api/codex/responses`) phân định rõ:
- **`codex/gpt-5.6-terra` & `codex/gpt-5.6-luna`**: Hoạt động hoàn hảo qua OAuth tài khoản ChatGPT (HTTP 200).
- **`codex/gpt-5.6-sol`**: **BỊ TỪ CHỐI** với lỗi `HTTP 400 Bad Request`:
  `{"detail":"The 'gpt-5.6-sol' model is not supported when using Codex with a ChatGPT account."}`
  -> Muốn dùng model Sol (general chat/reasoning), phải dùng qua pool `chatgpt-web-pool` (session token web cookie), KHÔNG dùng qua Codex OAuth.

## 2. Cấu hình Prompt Cache Affinity & Session Stickiness (`cache-optimized`)
Để tận dụng tối đa cơ chế cache prompt (giảm độ trễ, tiết kiệm quota reasoning và tiền token), combo pool tài khoản Codex phải đặt cấu hình:
- **Strategy**: `cache-optimized` (thay vì `p2c` hay `round-robin` ngẫu nhiên làm phân mảnh cache).
- **Config object**:
  ```json
  {
    "maxRetries": 1,
    "retryDelayMs": 200,
    "targetTimeoutMs": 90000,
    "stickyRoundRobinLimit": 8,
    "disableSessionStickiness": false,
    "disablePromptCacheAffinity": false,
    "maxGlobalAttempts": 7,
    "nestedComboMode": "execute",
    "failoverBeforeRetry": true
  }
  ```
  - `disableSessionStickiness: false`: Ghim chặt các request trong cùng 1 session vào 1 account duy nhất.
  - `disablePromptCacheAffinity: false`: Khi prompt prefix/system prompt giống nhau, OmniRoute tự động route tới đúng account đã từng xử lý prefix đó để ăn prompt cache từ upstream OpenAI.
  - `stickyRoundRobinLimit: 8`: Số turn giữ stickiness trước khi cân nhắc rebalance hoặc failover.

## 3. Điều khiển mức Reasoning Effort cho Codex qua Model Suffix
OmniRoute xử lý reasoning effort cho Codex thông qua parser `splitCodexReasoningSuffix` (`open-sse/executors/codex/reasoningSuffix.ts`):
- Hỗ trợ các hậu tố: `-none`, `-low`, `-medium`, `-high`, `-xhigh`, `-max`, `-ultra`.
- Khi gán model trong combo thành:
  - `codex/gpt-5.6-terra-medium`
  - `codex/gpt-5.6-luna-medium`
  - `codex/gpt-5.6-luna-high`
  OmniRoute sẽ tự động bóc tách:
  - Wire `model`: `gpt-5.6-terra` / `gpt-5.6-luna`
  - Wire `reasoning`: `{"effort": "medium"}` hoặc `{"effort": "high"}`
  giúp hạ/tăng mức suy nghĩ của model theo đúng yêu cầu mà không phụ thuộc vào client inject param.

## 4. Tích hợp Provider Omni trên Hermes Agent
Khi cấu hình provider `omni` trong `config.yaml` của Hermes:
- Với `discover_models: false`, Hermes chỉ load các model được khai báo cứng trong config.
- Bắt buộc dùng `hermes config set` để cập nhật đồng bộ 3 nơi:
  1. `custom_providers.<index>.models.<model_name>.context_length <length>`
  2. `providers.omni.models.<model_name>.context_length <length>`
  3. `model.aliases.<model_name> custom:omni/<model_name>` (cho phép gõ nhanh `/model <model_name>`)
- Đồng thời set reasoning override tương ứng trong Hermes:
  `hermes config set agent.reasoning_overrides.<model_name> medium` (hoặc `high`).

## 5. Đặc Điểm Tài Khoản Free Tier & Tiền Tố Routing `cx/`
- **Bản chất Free Tier ($0 USD)**: Các tài khoản Codex OAuth đăng ký bằng tài khoản ChatGPT Free (`workspacePlanType: 'free'`) hoàn toàn không tốn tiền mặt / balance credit.
- **Sự thật về Quota: Codex Free vs ChatGPT Web Free (Đính chính chuẩn xác từ User)**:
  - **Codex Free**: OpenAI cấp hạn ngạch riêng theo chu kỳ tuần/tháng (**Codex Scope Allowance**). Khi cạn quota, tài khoản bị khóa cứng cổng Codex tới ngày reset (ví dụ trường `codexScopeRateLimitedUntil: "2026-10-12..."` trong SQLite `storage.sqlite`). Bù lại, Codex hỗ trợ **Native Tool Calling 100%**, Prompt Cache Affinity và **mở khóa toàn bộ Reasoning Effort Suffixes** (`-medium`, `-high`, `-max`).
  - **ChatGPT Web Free**: Áp dụng hạn ngạch theo cửa sổ trượt (Rolling Window, vài chục tin nhắn / 3–5 tiếng). **KHÔNG PHẢI "Unlimited / Free luôn"**; người dùng thấy dùng mãi không hết là nhờ **pool 17 tài khoản Web xoay vòng Round-Robin**. Web **VẪN CÓ THINKING** (`chatgpt-web/gpt-5.6-sol-high`, `chatgpt-web/gpt-5.6-luna-free-thinking`), nhưng chỉ hỗ trợ **Emulated Tool Calling** qua thẻ `<tool>` (dễ rớt format JSON khi task phức tạp) và có nguy cơ dính **Cloudflare Sentinel 403** / Session Expired khi nã tải liên tục.
- **Tử huyệt Routing Tiền tố (`cx/` vs `codex/`) & Timeout**:
  - Trên OmniRoute `:20129`, luôn ưu tiên gọi qua model ID trực tiếp có tiền tố **`cx/`** (ví dụ: `cx/gpt-5.6-luna-high`, `cx/gpt-5.6-luna-max`).
  - Gọi qua alias `codex/gpt-5.6-luna-*` dễ bị nghẽn timeout (>60s) do lớp resolver alias upstream nếu pool có connection đang bị stall.
  - Luna High / Max sinh 1.000–3.000 reasoning tokens ngầm/turn $\to$ HTTP timeout client bắt buộc phải $\ge 90s - 150s$ để tránh `TimeoutError`.

## 6. Cơ chế tách đôi Reasoning Effort giữa Coordinator (High) và Subagent Worker (Medium) trong Hermes
Trong Hermes Agent, session chính và subagent được điều khiển hoàn toàn độc lập qua 2 block trong `config.yaml`:
1. **Session chính (Coordinator)**:
   - Cấu hình: `agent.reasoning_effort: high` và `agent.reasoning_overrides: { omni-worker: high }`.
   - Cơ chế core: `hermes_constants.resolve_reasoning_config()` gán `parent_agent.reasoning_config = {'enabled': True, 'effort': 'high'}`.
   - Wire JSON: Plugin `omni` (`OmniProfile.build_api_kwargs_extras`) tự động inject `reasoning_effort: 'high'` ở top-level payload gửi sang OmniRoute.
   - Thẩm định Sol High & Claude Code: Bắt buộc HIGH theo nguyên lý **Cognitive Load Matching** và **Blast Radius**. Coordinator sai một quyết định có thể làm văng session/cookie tài khoản của cả fleet; cần tư duy sâu để giữ 5 Gates.
2. **Subagents ngầm (Worker khi `delegate_task`)**:
   - Cấu hình: `delegation.reasoning_effort: medium`.
   - Cơ chế core: Trong `tools/delegate_tool.py`, hàm `_build_child_agent` đọc `delegation.reasoning_effort`, bóc tách thành `child_reasoning = {'enabled': True, 'effort': 'medium'}` và inject trực tiếp vào `AIAgent` con.
   - Wire JSON: Plugin `omni` tự động inject `reasoning_effort: 'medium'` ở top-level payload gửi sang OmniRoute.
   - Thẩm định Sol High & Claude Code: Bắt buộc MEDIUM để tránh **Over-Reasoning Trap**. Worker giỏi là worker làm đúng 100% việc được giao (atomic write, SHA-256 byte stream, focused test <5s), không tự ý refactor hay mở rộng scope làm drift spec.

## 7. Bản Chất Tải Farm & Tránh Ảo Tưởng "160 Máy Nã LLM" (User Correction)
- **Tải thực tế của Phone Farm 160 máy**: Toàn bộ 160 thiết bị Android vận hành hoàn toàn bằng script tự động hóa nội bộ (Python, ADB, ATX agent, uiautomator2). Thiết bị KHÔNG HỀ gọi LLM.
- **LLM chỉ phục vụ cho Hermes Agent**: Duy nhất 1 Coordinator session (người dùng tương tác) và các Worker subagents (khi Coordinator gọi `delegate_task`).
- Tuyệt đối cấm hallucinate rằng "160 máy đồng loạt gọi LLM làm sập quota Codex". Rủi ro quota chỉ phát sinh khi Coordinator dispatch quá nhiều subagent song song trong một sự cố lớn.

## 8. Kiến Trúc Fallback Kép: OmniRoute In-Flight Failover + Hermes Emergency Safety Net
Chuẩn SRE triển khai fallback sang `Codex Luna High` (User chốt 2026-09-24: Luna High ưu tiên Tier 3 TRƯỚC Claude Sonnet, đổi tên `ag-claude` thành `ag-sonnet`):
1. **Tầng OmniRoute (In-Flight Failover trong 1 HTTP Request)**:
   - Cấu hình trong combo `omni-worker`:
     - Tier 1: `ag-gemini-pool-3` (16 Gemini Pro - Cache-Optimized Sticky 8)
     - Tier 2: `ag-gemini-free-pool` (87 Gemini Free - P2C Swarm)
     - 🎯 **Tier 3**: `codex/gpt-5.6-luna-high` (Codex Pool - Ưu tiên cứu nguy TRƯỚC Sonnet)
     - Tier 4: `ag-sonnet` (89 Sonnet 4.6 accounts - Đã đổi tên từ `ag-claude` và gỡ bản duplicate)
   - Lợi ích: Khi dàn Google bị quá tải/429, OmniRoute chuyển thẳng sang Luna High cấp Senior (92-94 điểm) để giải quyết ngay lập tức, không để Sonnet chặn trước Luna. Hermes không bị gián đoạn hay phải reconstruct session context.
2. **Tầng Hermes (Emergency Session Safety Net)**:
   - Cấu hình tại root của `C:\Users\Kibe\AppData\Local\hermes\config.yaml`:
     ```yaml
     fallback_model:
       provider: custom:omni
       model: cx/gpt-5.6-luna-high
       base_url: http://192.168.110.123:20129/v1
       api_key: sk-omniroute
     ```
   - Cơ chế: Nếu toàn bộ cụm `omni-worker` bị sập hoàn toàn (connection refused hoặc proxy lỗi), hàm `_try_activate_fallback()` trong Hermes sẽ tự động chuyển agent sang `cx/gpt-5.6-luna-high`.
   - **Kế thừa Subagent & Bảo Toàn Luna High Cho Worker**: 
  - Thắc mắc cốt lõi: *"Nếu Worker set reasoning là medium dành cho Gemini, khi failover sang Luna thì làm sao Luna vẫn là Luna High?"*
  - **Tại tầng OmniRoute (In-flight Failover)**: Parser `splitCodexReasoningSuffix` ưu tiên tuyệt đối hậu tố cứng `-high` của model trong combo (`codex/gpt-5.6-luna-high`). Khi request mang `reasoning_effort: medium` fallback vào Tier 3, OmniRoute tự động ghi đè và ép upstream OpenAI chạy ở mức Thinking HIGH (đo đạc thực tế: 111 reasoning tokens).
  - **Tại tầng Hermes Agent (`_try_activate_fallback`)**: Khi chuyển sang model fallback `cx/gpt-5.6-luna-high`, Hermes chạy `resolve_reasoning_config(load_config(), agent.model)`. Hermes tra cứu `agent.reasoning_overrides` và tái gán `agent.reasoning_config = {'enabled': True, 'effort': 'high'}`. Đồng thời plugin `omni` đã khai báo alias `custom:omni` để nạp đúng `OmniProfile` chuyển đổi payload chuẩn.
  - **Swap tay tức thì**: Hermes đã nạp alias `luna-high` / `cx-luna` trỏ tới `custom:omni/cx/gpt-5.6-luna-high`. Khi cần chuyển thẳng sang Luna High, gõ lệnh: `/model luna-high`. Vì vậy, Worker khi nhảy sang Luna luôn được bảo đảm chạy ở mức Luna High 100%!

## 9. Đánh Giá So Găng Luna High vs Luna Max (Sol High Thẩm Định Độc Lập)
- **Nhánh Thợ gõ (Worker)**: **`cx/gpt-5.6-luna-high` thắng áp đảo `cx/gpt-5.6-luna-max` (2 - 1)**.
  - Luna Max bị bệnh **Over-constrain**: tự đặt ra ràng buộc tuple cứng nhắc, kiểm tra kiểu dữ liệu rườm rà khiến code thiếu linh hoạt và dễ vỡ khi file thật có sai khác nhỏ.
  - Độ trễ kinh hoàng: Luna Max ngẫm nghĩ 112s - 163s cho một hàm Python đơn giản, trong khi Luna High chỉ mất 22s - 35s.
- **Nhánh Tổng tư lệnh (Coordinator)**: **`cx/gpt-5.6-luna-high` là điểm vàng thực chiến (Sweet Spot - 94/100)**.
  - Phản ứng nhanh (15s - 25s), O(1) kỷ luật, bảo toàn tài sản ca Nuôi (100 nick) trước ca Reg mới.
  - Đã xuất sắc vượt qua trọn vẹn 5 bài kiểm thử trong **Production Apocalypse Gauntlet** do Sol High chấm điểm:
    1. 429 Storm: AIMD adaptive rate + Token bucket Redis.
    2. SQLite Split-brain: Local WAL mode + atomic commit rollback.
    3. Login Flow Mutation: Fail-stop an toàn, không cố giải Captcha lạ gây quét hàng loạt.
    4. Sập nguồn 40 máy: Fencing epoch token chặn duplicate job khi máy reboot.
    5. Coordinator Brain Damage: Clean reconciliation qua checkpoint bền vững, cấm panic reset.
