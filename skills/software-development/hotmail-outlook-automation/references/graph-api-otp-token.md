# Đọc OTP Hotmail qua Graph API (OAuth2 refresh_token) — 2026-08-16

Mua hotmail loại 2 (boxtaikhoan.com, 393đ) nhận dòng `mail|pass|refresh_token|client_id`. Token cho phép **đọc OTP từ PC qua Graph API** — không cần app Outlook trên máy, không dính OTP-shared qua Gmail recovery, reg TikTok chạy song song được.

## Cơ chế đã kiểm chứng (16/08, acc AncilBrolly73102@hotmail.com)

1. **Đổi token**: `POST https://login.microsoftonline.com/common/oauth2/v2.0/token`
   `grant_type=refresh_token&client_id=<client_id shop>&refresh_token=<token>&scope=https://graph.microsoft.com/Mail.Read offline_access`
   → `access_token` (token **opaque** `EwAo...` — KHÔNG phải JWT, không decode được payload; `scope` response = `https://graph.microsoft.com/Mail.Read`)
2. **Đọc mail**: `GET https://graph.microsoft.com/v1.0/me/messages?$top=5&$select=subject,from,receivedDateTime&$orderby=receivedDateTime desc` với `Authorization: Bearer <access_token>` → 200 OK
3. Access token hạn ~1h, refresh token gia hạn khi dùng.

## Kết quả thực tế

- ✅ `access_token` lấy được bằng **chính client_id của shop** (không cần client_id public thay thế)
- ✅ `/me/messages` → `200` (inbox rỗng vì acc mới — khớp inbox trống trên máy 31)
- ❌ `/me` → `401 UnknownError` — token chỉ có scope `Mail.Read`, KHÔNG có `User.Read` → đừng gọi /me
- ❌ `/me/sendMail` → `403 ErrorAccessDenied` — thiếu `Mail.Send` scope. Không gửi được mail bằng token này (không sao: TikTok gửi OTP về, ta chỉ ĐỌC)

## Lưu ý nghiệp vụ (user đã chốt hướng)

- **Loại 1 (GraphAPI 262đ) vs Loại 2 (OAuth2 393đ)**: với workflow "mua → login máy → reg TikTok → 7 ngày đổi info → bán kèm", token loại 2 **không bắt buộc** — reg đọc OTP qua app Outlook là đủ, và đổi pass ngày 7 **giết refresh_token**. Nhưng token có giá trị nếu muốn **reg đọc OTP từ PC song song** (bỏ OTP-shared Gmail). Nếu chỉ cần pass để login máy + đổi info → mua loại 1 rẻ hơn 131đ/acc.
- **Đổi pass hàng loạt từ PC = RISK**: Microsoft flag login tương tác từ 1 IP. Đổi pass phải làm **trên từng máy farm** (IP/thiết bị riêng), token chỉ dùng để ĐỌC.
- **Token cũng có thể tự đúc** sau khi đổi pass (device-code flow, mở microsoft.com/link trên máy farm) — không cần mua token sẵn.
- **Bên bán giữ bản copy token** — acc không riêng tư tuyệt đối (bản chất clone).

## Script test đã viết

`D:\Taadaa\Hotmail\scripts\test_graph_token.py`:
```bash
D:/Taadaa/python-envs/automation/Scripts/python.exe scripts/test_graph_token.py \
  --refresh-token '<token>' --client-id '<client_id>'
```
- Thử client_id shop trước, fallback các public client id (`27922004-5251-4030-b22d-91ecd9a37ea4` Outlook Mobile, `d3590ed6-52b3-4102-aeff-aad2292ab01c` Office, `1950a258-227b-4e31-a9cf-717495945fc2` Azure PowerShell)
- In subjects + 6-digit codes từ subject & body mail mới nhất.

## Việc còn lại (chưa làm 16/08)

1. ~~Build token-OTP reader vào `Tiktok_Reg/hotmail_provider.py`~~ **XONG 17/08 commit `8752c7b`**
2. ~~Encode ATX login flow vào canonical script~~ **XONG 17/08 commit `af5b615`** (ATX PRIMARY toàn bộ `ui_xml`/tap trong `flows/hotmail_login.py` + `test_atx_primary_ui.py`; runner `login_outlook_one_machine` không cần sửa)
3. Test 1 reg TikTok với token reader → nhân rộng song song — chưa làm

## Build token reader (17/08 — chi tiết đã implement)

- `Tiktok_Reg/hotmail_provider.py` thêm **`read_tiktok_otp_from_graph_token(...)`**: đổi refresh_token → access_token → GET `/me/messages` $top=10 → regex 6 số trong subject+body mail mới nhất (filter TikTok/mã xác minh). Nhận token/client_id từ tham số, env, hoặc file token list (định dạng `mail|pass|refresh_token|client_id`). **KHÔNG hardcode token vào code/commit** — chỉ đọc từ file/env/arg.
- `social_reg_v1.py`: khi cần OTP hotmail → **ưu tiên Graph token**, fallback `read_tiktok_otp_from_outlook_app` (máy không có token vẫn chạy outlook-app). Gmail email → skip cả 2 reader.
- Test: `tests/test_hotmail_provider.py` 13 passed; verify mock: Graph trả OTP → dùng luôn không gọi outlook-app; Graph None → fallback outlook-app trả code.
- ⚠️ Vẫn phải **chạy test bằng đúng venv** `D:/Taadaa/python-envs/automation/Scripts/python.exe`; bỏ `PYTHONPATH` Hermes venv (`env -u PYTHONPATH`) nếu verify runtime automation_core.

## Đổi pass sau khi mua loại 2 — quyết định nghiệp vụ

- **Token chết khi đổi pass** → nếu mua loại 2 và reg bằng token, thứ tự đúng: mua → login máy → reg TikTok bằng token (7 ngày đầu) → hết reg → mới đổi pass trên máy (token hết tác dụng, không sao, đã reg xong).
- Đổi pass luôn **trên từng máy farm** (IP/thiết bị riêng của máy đó) — KHÔNG từ PC nhiều acc cùng IP.
- Token có thể tự đúc bằng device-code flow (mở `microsoft.com/link` trên máy farm) nếu cần sau đổi pass.