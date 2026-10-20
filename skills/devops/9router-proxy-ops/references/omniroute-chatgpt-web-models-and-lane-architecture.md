# OmniRoute ChatGPT Web Models & Lane Architecture

## 1. Overview
Provider `chatgpt-web` (alias `cgpt-web`) routes requests directly through `https://chatgpt.com` internal SSE protocol (`/backend-api/f/conversation`) using web session cookies (Plus/Pro subscriptions or Free verified accounts).

## 2. Model Mappings & Backend Slugs (SSOT: `open-sse/executors/chatgpt-web/models.ts`)

| OmniRoute Model ID | Backend Slug | Thinking Effort | Target Account Tier | Ghi chú |
|---|---|---|---|---|
| `chatgpt-web/gpt-5.6-sol-pro`<br>`cgpt-web/gpt-5.6-sol-pro` | `gpt-5-6-pro` | `standard` | Pro | Flagship model cao nhất của OpenAI trên Web |
| `chatgpt-web/gpt-5.6-sol-xhigh` | `gpt-5-6-thinking` | `max` | Pro / Plus | Mức tư duy tối đa |
| `chatgpt-web/gpt-5.6-sol-high` | `gpt-5-6-thinking` | `extended` | Pro / Plus | Mức tư duy mở rộng (mặc định Sol High) |
| `chatgpt-web/gpt-5.6-sol-medium` | `gpt-5-6-thinking` | `standard` | Pro / Plus | Mức tư duy tiêu chuẩn |
| `chatgpt-web/gpt-5.6-sol-instant` | `gpt-5-6` | `null` (none) | Pro / Plus | Phản hồi tức thì, không reasoning |
| `chatgpt-web/gpt-5.6-luna-free-thinking` | `auto` | `null` | Free | Hệ thống tự inject hint `["reason"]` |
| `chatgpt-web/gpt-5.6-luna-free` | `auto` | `null` | Free | Chế độ chat tiêu chuẩn trên tài khoản Free |

*Lưu ý về thế hệ tiền nhiệm (Legacy GPT-5.5)*:
- `gpt-5.5-pro`, `gpt-5.5-pro-extended` -> backend `gpt-5-5-pro`
- `gpt-5.5-instant`, `gpt-5.5-medium`, `gpt-5.5-high`, `gpt-5.5-xhigh` -> backend `gpt-5-5` / `gpt-5-5-thinking`

## 3. Combos & Routing Pools trên OmniRoute (`:20129`)
- **`gpt-web-sol`**: Combo Round-Robin xoay vòng các tài khoản Sol live verified, tự động định tuyến `chatgpt-web/gpt-5.6-sol-high` hoặc `chatgpt-web/auto`.
- **`chatgpt-web-pool`**: Pool xoay vòng toàn bộ các tài khoản ChatGPT Web live (hỗ trợ cả Pro/Plus và Free).
- **`gpt-web-luna`**: Pool Round-Robin chuyên biệt cho nhánh Free Thinking (`chatgpt-web/gpt-5.6-luna-free`).

## 4. Quá Trình Xác Thực & Sentinel Handshake
1. `exchangeSession()`: `GET /api/auth/session` đổi session cookie lấy JWT `accessToken` (cache ~5 phút).
2. `prepareChatRequirements()`: `POST /backend-api/sentinel/chat-requirements/prepare`.
3. `solveProofOfWork()`: Chạy SHA3-512 hash loop để giải seed & difficulty trả về token `gAAAAAB...`.
4. `conversation`: `POST /backend-api/f/conversation` kèm header `Bearer` + `sentinel-proof-token` + browser UA.
