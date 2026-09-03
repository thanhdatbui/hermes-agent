# Graph API token OTP reader (hotmail loại 2) — commit 8752c7b (2026-08-17)

Đọc OTP TikTok thẳng từ PC qua Microsoft Graph, KHÔNG cần outlook-app/điện thoại.
Áp dụng cho hotmail loại 2 mua từ boxtaikhoan: `mail|pass|refresh_token|client_id`.

## Vị trí

- `D:\Taadaa\Tiktok_Reg\hotmail_provider.py` → `read_tiktok_otp_from_graph_token(device, email, *, token, client_id, token_file, client_id_file, stt, artifact_dir, timeout=180)` + helpers public `resolve_graph_credentials`, `exchange_refresh_token`.
- `social_reg_v1._try_get_otp_outlook_app` → **graph-first**: gọi graph reader (timeout=150) → có OTP trả luôn; không resolve được token / không có OTP / exception → **fallback** `read_tiktok_otp_from_outlook_app` (outlook-app cũ, giữ nguyên cho máy không có token).
- Tests: `tests/test_hotmail_provider.py` (13 test, gồm 2 test cũ — chú ý canonical reader giờ LUÔN forward `password=None` kwarg).

## Nguồn credential (ưu tiên, FIRST match)

1. kwargs `token` / `client_id`
2. env `HOTMAIL_TOKEN_FILE` (+ `HOTMAIL_CLIENT_ID_FILE`)
3. per-mailbox `~/.hermes/hotmail_tokens/<mailbox>.token` (1 dòng: `refresh_token` hoặc `refresh_token client_id`)
4. env `HOTMAIL_TOKEN_LIST` — file mỗi dòng `mail|pass|refresh_token|client_id` (match theo email, `#` comment, bỏ dòng trống)

Không có token → trả `None` → caller fallback. Token KHÔNG log, KHÔNG ghi artifact, KHÔNG commit.

## Cơ chế

- Exchange: POST `https://login.microsoftonline.com/common/oauth2/v2.0/token`, grant_type=refresh_token, thử 3 scope theo thứ tự (verified 2026-08-16 cho consumer MSA):
  1. `https://graph.microsoft.com/Mail.Read offline_access`
  2. `Mail.Read offline_access`
  3. `https://graph.microsoft.com/Mail.Read openid profile offline_access`
- Đọc mail: GET `https://graph.microsoft.com/v1.0/me/messages` với `$top=10&$select=subject,body,receivedDateTime,from&$orderby=receivedDateTime desc`
- Extract: subject/body phải chứa marker TikTok (`tiktok`, `ma xac minh`, `ma xac nhan`, `verification code`, `otp`, `login code`...) + regex `(?<!\d)(\d{6})(?!\d)` (boundary guard — không match số trong dãy dài hơn, vd SĐT).
- **Chỉ dùng stdlib `urllib`** (không import requests — repo Tiktok_Reg không có dependency đó; test chạy bằng python hệ thống).
- Debug lỗi exchange/messages: env `HOTMAIL_GRAPH_DEBUG=1` (mặc định im lặng, fail-closed → fallback).

## Vận hành

- Bật cho batch: export `HOTMAIL_TOKEN_LIST=D:/.../tokens.txt` trước khi chạy `social_reg_v1.py` / runner (đặt ở nơi cron chạy).
- **Song song được**: loại 2 đọc OTP từ PC theo từng mailbox riêng → KHÔNG dính rule tuần tự (rule đó chỉ áp cho shared recovery mailbox qua Outlook app). Xem `taadaa-farm-ops-rules` mục 1.
- Smoke-test pattern: dùng DUMMY token (`RT_DUMMY_FOR_SMOKE_TEST`) — resolve PASS, graph call trả None graceful (invalid_grant), không crash. KHÔNG bao giờ đưa token thật vào test/verifier/commit.