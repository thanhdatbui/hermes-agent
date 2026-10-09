# Cockpit Tools Codex Model Capabilities & Benchmark Runbook

## 1. Supported Model Matrix & Account Tier Entitlements

| Model ID | Upstream Model Name | Tier / Plan Requirement | Benchmark Latency | Reasoning Support | Free Pool Status |
|---|---|---|---|---|---|
| `gpt-6-luna` | GPT-6 Luna | Free / Plus / Team / Pro | ~8s - 22s | Yes (Dynamic 40-270 tok) | **ACTIVE / FULL COMPATIBLE** |
| `gpt-5.6-terra` | GPT-5.6 Terra | Free / Plus / Team / Pro | ~30s - 45s | Yes (Deep 300-400 tok) | **ACTIVE** (Heavy / Higher timeout needed) |
| `gpt-5.6-luna` | GPT-5.6 Luna | Free / Plus / Team / Pro | ~15s - 23s | Yes (40-300 tok) | **ACTIVE / STABLE** |
| `gpt-5.5` | GPT-5.5 | Free / Plus / Team / Pro | ~2s - 5s | Base | **ACTIVE** |
| `codex-auto-review` | Codex Review | Free / Plus / Team / Pro | ~3s | Fast Reasoning | **ACTIVE** |
| `gpt-6-sol` | GPT-6 Sol (Flagship) | Paid ChatGPT Only | N/A | Hard Blocked on Free | HTTP 400 (`not supported with ChatGPT account`) |
| `gpt-5.6-sol` | GPT-5.6 Sol | Paid ChatGPT Only | N/A | Hard Blocked on Free | HTTP 503/400 (`not supported with ChatGPT account`) |
| `gpt-6-astra` | GPT-6 Astra | Paid ChatGPT Only | N/A | Hard Blocked on Free | HTTP 400 (`not supported with ChatGPT account`) |

> **Note on Naming & Aliases**:
> - Không tồn tại model mang tên `sol 6.1`, `gpt-6.1-sol`, `gpt-6-terra` trong binary upstream của Codex.
> - "Sol 6.1" thực chất là alias hoặc tên gọi dân dã của dòng `gpt-6-sol`.

## 2. Automated Hotmail Graph API OTP Workflow for Codex OAuth Re-Auth

Khi token Codex trong Cockpit bị revoke (`token_revoked` / HTTP 401), quy trình re-auth hoàn toàn tự động qua Microsoft Graph API:

1. **Khởi động GPM Profile tương ứng qua local GPM API**:
   - `GET http://127.0.0.1:19995/api/v3/profiles/start/{profile_id}`
   - Trích xuất `remote_debugging_address` (VD: `127.0.0.1:55951`).
2. **Kích hoạt OAuth trên Cockpit Tools UI**:
   - Mở modal Add Account ➔ OAuth Authorization ➔ Click `Refresh Auth Link` để mở cổng callback local `127.0.0.1:1455`.
3. **Playwright CDP Navigation**:
   - Điều hướng tới `https://chatgpt.com/codex/desktop-auth?...`
   - Nhập email tài khoản Hotmail và nhấn "Tiếp tục".
4. **Lấy mã OTP trực tiếp từ Microsoft Graph API bằng Refresh Token có sẵn**:
   - Đọc refresh token & client ID từ danh sách tài khoản đã mua (`hotmail_all_60_bought.txt`).
   - Lấy `access_token` mới qua `POST https://login.microsoftonline.com/common/oauth2/v2.0/token`.
   - Query hộp thư đến: `GET https://graph.microsoft.com/v1.0/me/mailFolders/inbox/messages?$top=5&$orderby=receivedDateTime desc`.
   - Regex trích xuất mã 6 số từ email của `noreply@tm.openai.com` / `noreply@tm1.openai.com`.
5. **Điền OTP & Chấp thuận Consent**:
   - Fill OTP vào form ➔ Click "Tiếp tục" ➔ Chọn Workspace cá nhân ➔ Chấp thuận Consent.
   - Redirect về `http://127.0.0.1:1455/auth/callback` hoàn tất cập nhật tài khoản vào `codex_accounts.json`.

## 3. Benchmarking & Routing Recommendations

- **Default Coding Worker**: `gpt-6-luna` (Độ trễ thấp, sinh code PEP8 sạch, tiết kiệm quota trên acc Free).
- **Architecture / Deep Reasoning Worker**: `gpt-5.6-terra` (Cần set client timeout >= 60s để tránh ngắt kết nối).
- **Proactive Model Discovery**: Khi kiểm tra danh mục model mới, luôn scan chuỗi nhị phân trong binary proxy (`cockpit-cliproxy.exe`) và test trực tiếp với payload tối thiểu thay vì chỉ đọc danh sách `/v1/models` tĩnh.
