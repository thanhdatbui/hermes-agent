# ChatGPT Web 413 Payload Too Large & Combo Cascade Resilience

## 1. Nguyên nhân cốt lõi HTTP 413 trên ChatGPT Web
- **Endpoint Web**: `https://chatgpt.com/backend-api/conversation` sử dụng reverse-engineered session token (`__Secure-next-auth.session-token`).
- **Cloudflare / WAF Ceiling**: Giới hạn payload cứng (~500KB - 1MB request body).
- **Agentic Bloat**: Khi request từ Agent mang theo:
  - System prompt dài (injected rules, instructions).
  - Tools definition JSON (schema của hàng chục tool: `terminal`, `patch`, `read_file`,...).
  - Conversation history nhiều turns / multi-file diffs.
  -> Payload vượt quá giới hạn web -> WAF chặn ngay lập tức với **HTTP 413 (Payload Too Large)** trước khi request chạm tới model.

## 2. So sánh Codex CLI / API chuẩn vs ChatGPT Web
| Đặc tính | ChatGPT Web (`chatgpt.com`) | Codex CLI / API chuẩn (`api.openai.com`) |
| :--- | :--- | :--- |
| **Giao thức** | Web Session qua cookie | REST API / OAuth chuẩn |
| **Giới hạn Request Body** | ~500KB - 1MB (Dễ dính 413) | Hàng chục MB (Context window 128k - 200k tokens) |
| **Hỗ trợ Agentic** | Kém khi context lớn | Hoàn hảo cho Agentic Coding / Subagents |
| **Vị trí trong Combo** | Fallback cấp thấp hoặc tách riêng cho Task ngắn | Ưu tiên cao hơn Web Pool khi cần payload lớn |

## 3. Quy tắc sắp xếp Combo tầng Fallback (`omni-worker`)
Khi thiết kế combo worker đa tầng:
1. **Tier 1 (Nhanh, Rẻ)**: `ag-gemini-pool-3` (Gemini Flash) - xử lý 90% tác vụ.
2. **Tier 2 (Hứng tải Payload lớn)**: `ag-claude` (Claude Sonnet 4.6) hoặc `codex` - nuốt trọn context dài và system prompt khi Gemini nghẽn semaphore/429.
3. **Tier 3 (Safety Net / Giới hạn payload)**: `chatgpt-web-pool` (12 accs Plus/Team) - Chỉ dùng làm cứu cánh hoặc cho các tác vụ ngắn, tránh đặt làm Tier 2 trực tiếp sau Flash để không gây cascade 413 khi tải cao.
4. **Tier 4**: Free tiers / dự phòng cuối.
