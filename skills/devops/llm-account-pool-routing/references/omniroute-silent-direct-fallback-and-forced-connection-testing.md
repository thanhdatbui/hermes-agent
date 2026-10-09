# OmniRoute Silent Direct Fallback & Forced Connection Verification Runbook

## 1. Sự Cố Rò Rỉ Direct IP Tầng OmniRoute (Silent Direct Fallback)
### Hiện tượng & Căn nguyên:
- Bảng `provider_connections` có cột `proxy_enabled = 1`.
- Tuy nhiên, bảng `proxy_assignments` **không có bản ghi** nào liên kết connection đó (`scope = 'account'`, `scope_id = <connection_id>`).
- Khi request đến, hàm `resolveProxyForConnection` trong `src/lib/db/settings.ts` quét qua các tầng:
  1. `scope = 'account'` (trống)
  2. `scope = 'provider'` (trống nếu chưa cấu hình)
  3. `scope = 'global'` (trống)
  $\rightarrow$ Cuối cùng rơi vào Step 12: `return { proxy: null, level: "direct", levelId: null }`.
- **Hậu quả tai hại:** OmniRoute không quăng lỗi, không chặn request, mà âm thầm gửi HTTP request bằng IP thật của máy chủ (`1.53.55.190`). Khi nhiều tài khoản cùng gọi qua IP máy chủ, OpenAI / Google quét dấu vết và trảm hàng loạt (tỷ lệ ban lên tới 94.4% đối với Codex trong sự cố 07/10/2026).

### Biện pháp phòng chống 2 lớp bắt buộc:
1. **Lớp 1 (Connection Level):** Khi tạo/sync bất kỳ connection nào vào OmniRoute (qua script như `chatgpt_gpm_direct_reg.py`), bắt buộc phải `INSERT INTO proxy_assignments (proxy_id, scope, scope_id, position, created_at, updated_at) VALUES (?, 'account', <connection_id>, 0, ...)` với một proxy sống từ `proxy_registry`.
2. **Lớp 2 (Provider Safety Net Pool):** Nạp toàn bộ danh sách proxy trong `proxy_registry` vào bảng `proxy_assignments` ở cấp provider (`scope = 'provider'`, `scope_id = '<provider_name>'` như `codex`, `chatgpt-web`, `antigravity`). Kể cả khi một connection lỡ mất proxy cá nhân, OmniRoute sẽ bốc ngẫu nhiên từ pool provider chứ tuyệt đối không bao giờ rớt xuống IP direct máy chủ.

---

## 2. Header Ép Connection Chuẩn Xác: `x-omniroute-connection`
### Cạm bẫy False-Positive khi test tài khoản:
- Nếu gửi request thông thường vào `/v1/chat/completions` (hoặc dùng nhầm header không được hỗ trợ như `x-connection-id`), bộ điều phối / load-balancer của OmniRoute sẽ tự động chọn một connection LIVE trong pool.
- Kết quả trả về `200 OK` ("Pong!"), khiến kỹ sư/agent lầm tưởng rằng connection đang test còn sống, trong khi thực tế tài khoản đó đã bị khóa vĩnh viễn (`account_deactivated`).

### Cú pháp ép test chuẩn xác:
Trong header HTTP của request gửi tới port 20129, bắt buộc truyền:
```http
x-omniroute-connection: <connection_id>
```
OmniRoute sẽ ghim cứng request vào đúng connection đó. Nếu tài khoản bị ban hoặc mất session, kết quả sẽ trả về `403 Sentinel / Account Deactivated` hoặc `401 Revoked` ngay lập tức, loại bỏ hoàn toàn việc ngộ nhận sức khỏe tài khoản.

---

## 3. Liên Đới Ban Tài Khoản & Quy Trình Đổi Sạch Proxy Tainted
### Hiệu ứng liên đới giữa Codex và ChatGPT Web:
- Khi OpenAI gắn cờ trảm tài khoản (`account_deactivated` qua email thông báo Trust & Safety), cả **OAuth Codex** lẫn **Session Cookie Web (`__Secure-next-auth.session-token`)** đều bị vô hiệu hóa cùng lúc.
- Tuyệt đối không suy diễn rằng Codex chết thì ChatGPT Web trên cùng email vẫn còn sống.

### Quy trình đổi sạch dải IP proxy từng gắn tài khoản bị ban:
1. **MobiProxy 4G (`test.taadaa.click`):**
   - Gọi endpoint `/proxy_recreat?proxy=test.taadaa.click:<PORT>&token=<TOKEN>`.
   - Giãn cách tối thiểu 2.0s – 2.5s giữa các lần gọi để tránh quá tải CPU box OpenWrt (MT7621).
   - Kiểm tra lại IP egress qua `http://api.ipify.org` đảm bảo IP mới khác hoàn toàn IP cũ.
   - *Lưu ý:* Cổng `5101` giữ DDNS `test.taadaa.click`; khi đổi cổng 5101, chờ 15s để DDNS phân giải sang IP mới.
2. **MikroTik PPPoE (`192.168.110.2`):**
   - Disable line PPPoE qua REST API: `PATCH /rest/interface/pppoe-client/<id>` với `{"disabled": true}`.
   - **Giữ trạng thái ngắt tối thiểu 35 – 40 giây** để BRAS nhà mạng (Viettel/FPT) giải phóng hoàn toàn lease IP cũ, tránh nhận lại IP cũ.
   - Enable lại line và kiểm tra IP mới trong `/rest/ip/address`.
   - Bắt buộc restart container Sing-box (`*6`) và container 3proxy (`*3`) để làm mới socket upstream.
