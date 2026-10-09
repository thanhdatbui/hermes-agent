# Dynamic Advisor In-Loop Pattern & OmniRoute Review Combo

## 1. Bản chất: Dynamic Advisor vs Pre-Plan vs Post-Review

Trước đây hệ thống phân định:
- **Pre-Plan (T2)**: Model mạnh lập kế hoạch toàn cục / patch contract trước khi thi công (`sol_planner.py`).
- **Post-Review (Closeout Gate)**: Model mạnh soi diff, chấm điểm >= 85/100 sau khi thi công xong (`closeout_gate.py`).

**Dynamic Advisor (`advisor_consult`)** là tầng thứ 3 được bổ sung:
- **Thời điểm**: Ngay giữa tool loop khi Coordinator đang vận hành mà gặp decision point khó.
- **Vai trò**: Cố vấn kỹ thuật read-only (tư vấn giải pháp an toàn, so sánh blast radius, khuyến cáo dừng/tiếp tục).
- **Ranh giới bất biến**: Advisor **KHÔNG CÓ TOOL**, không đụng shell/ADB/filesystem/git, không tự approve hay ra lệnh cho Worker. Quyền điều phối và trách nhiệm hành động vẫn thuộc về Coordinator.

## 2. Trigger khi nào Coordinator được gọi Advisor

Coordinator chỉ gọi `advisor_consult` khi gặp một trong các điều kiện:
1. **Lock / Recovery / Concurrency**: Xung đột lock, thứ tự recovery, tranh chấp session/lease.
2. **Account / Session Safety**: Nguy cơ mất session/cookie tài khoản đang nuôi, phân vân giữa refresh session vs relogin vs quarantine.
3. **Evidence Conflict**: Log nói một đằng nhưng runtime/DOM/inspect nói một nẻo.
4. **Blast Radius Trade-off**: Có 2 hướng giải quyết nhưng một hướng rủi ro cao ảnh hưởng diện rộng, cần cố vấn phương án tối thiểu rủi ro.

**CẤM gọi Advisor cho:**
- Lỗi cú pháp, typo, selector rõ ràng, hotfix nhỏ T1.
- Inspect cơ bản, đọc log đơn giản, chạy canonical script.
- T0 khẩn cấp (STOP/KILL/HALT) cần phản xạ 0-LLM.

## 3. Kiến trúc Routing trên OmniRoute (:20129)

User chỉ thị rõ ràng: **Sử dụng trực tiếp combo `review` có sẵn trên OmniRoute `:20129`**.
Lý do:
- **Tier 0**: `chatgpt-web-pool` (`chatgpt-web/gpt-5.6-sol-high`) — chạy chính, 0đ quota Codex, reasoning đỉnh cao.
- **Tier 1**: `codex/gpt-5.6-terra-high` — fallback đầu tiên nếu Web pool nghẽn/timeout.
- **Tier sâu hơn**: `ag-opus-pool` và các free fallback — lưới an toàn chống lỗi rớt mạng/hết quota làm sập luồng Coordinator.

## 4. Đặc tả Hermes Tool `advisor_consult`

- **Endpoint**: `http://127.0.0.1:20129/v1/chat/completions` (override qua env `HERMES_ADVISOR_ENDPOINT`).
- **Model**: `review`.
- **Payload**: `tools: []`, `tool_choice: "none"`, `stream: False`, bounded timeout <= 30s.
- **Sanitization**: Tự động đệ quy redact password, api_key, access/refresh/session token, cookie, auth headers, Bearer tokens, token dạng `sk-`/`ghp-`/`xox-`.
- **Fail-safe**: Khi OmniRoute timeout hoặc trả lỗi HTTP, tool trả `status: "unavailable"` kèm telemetry (`request_id`, `latency_ms`), tuyệt đối không bịa đặt lời khuyên hay tự pass.
- **Toolsets**: Đăng ký trong `_HERMES_CORE_TOOLS` tại `toolsets.py` để mọi Coordinator session đều có thể sử dụng.
