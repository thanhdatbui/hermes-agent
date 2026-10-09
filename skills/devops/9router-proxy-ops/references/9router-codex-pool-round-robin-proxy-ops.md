# 9Router Codex Pool Ops & Per-Account Egress Proxy Routing

## Overview
Khi điều phối dàn tài khoản ChatGPT/Codex trên 9Router (`http://127.0.0.1:20128`), tuyệt đối không để request gửi qua IP direct máy nhà (`1.53.55.190`) hoặc dồn toàn bộ pool vào chung 1 proxy IP, vì OpenAI sẽ revoke session hàng loạt (`token_revoked` / `account_deactivated`).
- **CẤM TUYỆT ĐỐI LÁI SANG POOL WEB:** Khi người dùng yêu cầu xử lý pool Codex OAuth / 9Router, CẤM lôi pool web (`cgpt-web`, `chatgpt-web`) ra thay thế hoặc giải thích lòng vòng.
- **NGUỒN ACC SẠCH ĐÃ VER SỐ:** Ưu tiên bốc tài khoản từ `provider_connections` (provider = 'codex') của OmniRoute (`~/.omniroute/storage.sqlite`) vì toàn bộ các nick này đã từng vượt Phone Verification Gate (SMS) thành công.
- **XỬ LÝ TÀI KHOẢN BỊ BAN:** Khi phát hiện tài khoản bị OpenAI khóa vĩnh viễn (`account_deactivated`), dọn sạch khỏi các bảng kết nối của LLM proxy (9Router, OmniRoute), nhưng BẢO TOÀN 100% profile GPM Hotmail gốc (nick là tài sản farm).
- **XỬ LÝ TÀI KHOẢN BỊ REVOKE (401):** Bắt buộc chạy luồng Re-OAuth tự động (mở GPM profile qua proxy tương ứng + lấy OTP Hotmail qua Microsoft Graph API) để cấp lại token mới.

---

## 1. Kiến trúc Schema 9Router SQLite (`C:\Users\Kibe\AppData\Roaming\9router\db\data.sqlite`)

### Proxy Pools (`proxyPools`)
- Chứa danh sách các proxy egress độc lập (ví dụ dàn proxy 4G Mobi `5101` $\to$ `5138` và Mikrotik).
- Format trường `data`:
  ```json
  {
    "name": "Proxy Mobi 5111",
    "proxyUrl": "http://user:pass@test.taadaa.click:5111/",
    "type": "http"
  }
  ```

### Connections (`providerConnections`)
- Bắt buộc liên kết từng connection với `proxyPoolId` tương ứng trong `data.providerSpecificData`:
  ```json
  {
    "accessToken": "eyJhbG...",
    "refreshToken": "rt.1...",
    "expiresAt": "2026-10-15T...",
    "testStatus": "active",
    "expiresIn": 864000,
    "providerSpecificData": {
      "chatgptPlanType": "free",
      "proxyPoolId": "<uuid-of-proxy-pool>"
    }
  }
  ```

---

## 2. Giải mã Token từ OmniRoute (`~/.omniroute/storage.sqlite`)

OmniRoute mã hóa các trường token (`access_token`, `refresh_token`) theo định dạng:
`enc:v1:<iv_hex>:<ciphertext_hex>:<authTag_hex>`

- **Khóa giải mã:** Lấy từ environment variable `STORAGE_ENCRYPTION_KEY` của tiến trình OmniRoute (`node.exe` cổng `20129`).
- **KDF:** `Scrypt(secret=STORAGE_ENCRYPTION_KEY, salt=b"omniroute-field-encryption-v1", length=32, n=16384, r=8, p=1)`.
- **Cipher:** `AESGCM(key)`. Giải mã bằng `aesgcm.decrypt(iv, ciphertext + auth_tag, None)`.

---

## 3. Lọc Tài khoản Live & Kiểm tra Trạng thái (Live Test Stream)

Để kiểm tra token có còn sống hay bị OpenAI thu hồi, gửi POST request trực tiếp tới backend Codex qua đúng proxy của account đó:
- **Endpoint:** `https://chatgpt.com/backend-api/codex/responses`
- **Headers:**
  - `Authorization: Bearer <access_token>`
  - `originator: codex_cli_rs`
  - `User-Agent: codex_cli_rs/0.136.0`
- **Body:** `{"model": "gpt-5.6-luna", "input": [...], "stream": true, "store": false}` (bắt buộc `stream: true`).

### Phân loại trạng thái:
1. **`response.created` / Stream nhận bình thường:** Tài khoản LIVE 100%. Nạp vào 9Router.
2. **HTTP 429 (`usage_limit_reached`):** Tài khoản SỐNG, phiên hợp lệ, chỉ đang tạm hết lượt free trong chu kỳ ngắn. **BẮT BUỘC giữ lại nạp vào 9Router**. Khi ở trong pool Round-Robin, 9Router sẽ tự động bỏ qua tài khoản đang cooldown và gọi tài khoản này khi hạn mức mở lại.
3. **HTTP 401 (`Encountered invalidated oauth` / `account_deactivated`):** Token đã bị thu hồi / nick bị khóa.
   - Khi token bị revoked, kiểm tra khả năng re-OAuth từ profile GPM có sẵn trước khi báo cáo hoặc loại bỏ.
   - Nếu tài khoản đã bị khóa vĩnh viễn (`account_deactivated`), dọn sạch khỏi database kết nối nhưng giữ nguyên GPM profile gốc.

---

## 4. Cấu hình Chiến lược Xoay Tải (Round-Robin Sticky)

Mặc định 9Router dùng `fill-first` (dồn cạn 1 acc rồi mới nhảy acc khác), dễ gây nghẽn 429 và dồn request vào 1 IP.
Cấu hình chuyển sang **`round-robin`** trong bảng `settings` (`id = 1`):
```json
{
  "fallbackStrategy": "round-robin",
  "stickyRoundRobinLimit": 2,
  "providerStrategies": {
    "codex": {
      "fallbackStrategy": "round-robin",
      "stickyRoundRobinLimit": 2,
      "rotateStrategy": "round-robin"
    }
  }
}
```
- Mỗi account chỉ xử lý tối đa 2 request liên tiếp (`stickyRoundRobinLimit: 2`), sau đó tự động xoay sang account tiếp theo trong pool dựa trên `lastUsedAt` và `consecutiveUseCount`.
- Khi một account bị 429, 9Router tự động failover sang account khả dụng tiếp theo trong vòng lặp mà không làm gián đoạn request của Hermes.
- Tải được san phẳng đều khắp toàn bộ pool, phân tán IP egress đều khắp các cổng proxy 4G Mobi độc lập.

---

## 5. Bài học Thực tế & Phòng chống Quét Ban Hàng Loạt (IP Direct Leak Post-Mortem)

### Đối soát Nguyên nhân Gốc rễ Trảm Acc
- Trong đợt rà soát lịch sử 91 kết nối Codex trên OmniRoute:
  - **Nhóm không gắn proxy (gọi thẳng IP nhà `1.53.55.190`):** 51/54 acc bị OpenAI khóa vĩnh viễn (`account_deactivated`), tỷ lệ ban **94.4%**.
  - **Nhóm có gắn proxy độc lập:** 10 acc SỐNG KHỎE, chỉ 4 acc bị ảnh hưởng.
  - **Kết luận:** OpenAI quét và trảm theo dấu vết IP máy chủ (`1.53.55.190`). TUYỆT ĐỐI KHÔNG để bất kỳ connection hoặc request kiểm tra nào đi direct IP không qua proxy.

### Phân biệt Tài sản Farm vs Pool Routing
- Khi phát hiện acc bị ban trên LLM Proxy: **Chỉ có tập acc lịch sử trong proxy DB bị ảnh hưởng**. Toàn bộ kho tài khoản farm gốc trên GPMLogin và file `taikhoan_dat_v2_updated.xlsx` (640+ nick) vẫn an toàn nguyên vẹn 100%. CẤM hoang mang làm xáo trộn database farm.

### Thực tế Kiểm chứng: Account Deactivation Blast Radius & Header `x-omniroute-connection`
- **Tử huyệt test Load-Balancer (False 200 OK):** Khi probe OmniRoute mà không ép connection đích danh, OmniRoute tự động bốc nick khác đang sống để trả lời `Pong! 200 OK`, gây ngộ nhận là nick đang kiểm tra vẫn sống.
- **Header bắt buộc để ép connection:** BẮT BUỘC dùng header **`x-omniroute-connection: <cid>`** (OmniRoute `src/sse/handlers/chat.ts`). Dùng `x-connection-id` hoặc không truyền header sẽ bị bỏ qua và dẫn tới kết luận sai lệch.
- **Phạm vi tác động của `account_deactivated`:** Khi OpenAI gửi email thông báo vô hiệu hóa tài khoản (`trustandsafety@tm.openai.com`), **tài khoản bị khóa triệt để trên cả hai giao thức (Codex OAuth lẫn ChatGPT Web)**. Thử nghiệm thực tế với header `x-omniroute-connection` cho thấy 43 tài khoản bị ban Codex khi gọi Web đều trả về `HTTP 403 SENTINEL_BLOCKED / Account Deactivated`.
- **Bể tài khoản Web thực tế còn sống:** 59 tài khoản sạch (chưa từng dính đợt quét IP nhà) vẫn sống 100% và phản hồi ổn định. Cần chủ động set `is_active = 0` / `test_status = 'banned'` cho các nick đã bị OpenAI khóa để tránh làm chậm hệ thống.

### Xử lý Sự cố GPMLogin API Chặn Khởi Động Profile (`Yêu cầu cập trình duyệt`)
- Khi app GPMLogin có bảng thông báo modal ("Big Update", "Resource fixer tool") hoặc vừa cập nhật database fingerprint 411, API nền (`port 19995`) sẽ bị khóa tạm thời và trả về: `{"success": false, "message": "Yêu cầu cập trình duyệt [Chromium] [142]"}`.
- **Cách xử lý:** Bấm nút đỏ "Đóng thông báo" trên giao diện GPMLogin, sau đó bấm nút "Mở" bằng tay trên 1 profile bất kỳ để trigger tải/nạp Chromium core lần đầu. Toàn bộ API sau đó sẽ mở lại `success: true` bình thường.

### Lưu ý Khắc phục Lỗi Khóa DB Hermes (`state.db` >14GB)
- Khi SQLite `state.db` phình to >14GB, runtime có thể dính lỗi `busy_timeout` (3s) và báo nhầm *"session storage could not be written (often a full disk)"*.
- **Xử lý nhanh O(1):** Chạy lệnh giải phóng WAL lock: `PRAGMA wal_checkpoint(PASSIVE)` để xả log và khôi phục quyền ghi ngay lập tức mà không khóa phiên.

---

## 6. Quy trình Full-Sweep Khôi phục Token bằng Refresh Token Grant

Khi rà soát các tài khoản bị lỗi (401, timeout, SSL error), tuyệt đối không vội kết luận là tài khoản đã chết nếu chưa thử giải pháp **Refresh Token Grant**:
1. **Cơ chế OAuth Refresh của OpenAI Codex:**
   - **Endpoint:** `https://auth.openai.com/oauth/token`
   - **Method:** `POST`
   - **Headers:** `Content-Type: application/x-www-form-urlencoded`, `User-Agent: codex_cli_rs/0.136.0`
   - **Payload:**
     ```python
     req_data = urllib.parse.urlencode({
         "client_id": "app_EMoamEEZ73f0CkXaXp7hrann",
         "grant_type": "refresh_token",
         "refresh_token": refresh_token
     }).encode("utf-8")
     ```
2. **Bắt buộc gửi qua Proxy Egress:** Mọi request refresh token bắt buộc phải đi qua đúng proxy tương ứng của tài khoản đó để tránh lộ IP máy chủ.
3. **Phân loại kết quả Refresh:**
   - `200 OK`: Nhận `access_token` mới, `refresh_token` mới và thời hạn `expires_in` (thường 864000s / 10 ngày). Thử gọi tiếp model backend để xác nhận LIVE 100%.
   - `401 Unauthorized / invalid_grant / "Your session has ended"`: Refresh token đã bị thu hồi hoặc hết hạn vĩnh viễn $\rightarrow$ Tài khoản chết thật.
4. **Nạp vào 9Router:**
   - Tra cứu proxy port từ `Profiles.JsonData["Proxy"]` trong GPMLogin (`profile_data.db`).
   - Tìm `proxyPoolId` tương ứng trong bảng `proxyPools` của 9Router.
   - Thêm hoặc cập nhật bản ghi vào `providerConnections` trên 9Router (`data.providerSpecificData.proxyPoolId`).
   - Cập nhật ánh xạ `proxy_assignments` trong OmniRoute để bảo toàn hai đầu.

---

## 7. Kỷ luật Tẩy sạch IP Bị Dính Nick Die (Tainted Proxy Rotation)

Khi tài khoản bị OpenAI trảm (`account_deactivated`), IP của cổng proxy đó đã bị hệ thống chống gian lận của OpenAI đưa vào danh sách nghi vấn:
- **Nguyên tắc Invariant:** Toàn bộ các cổng proxy từng dính tài khoản bị khóa BẮT BUỘC phải phát lệnh đổi IP ngay lập tức trước khi cho phép gán tài khoản mới hoặc chạy tiếp.

### 1. Đối với cụm MobiProxy 4G (`test.taadaa.click:5101..5138`):
- Gọi endpoint: `http://test.taadaa.click/proxy_recreat?proxy=test.taadaa.click:<port>&token=<token>`
- Giãn cách tối thiểu **2.0s - 2.5s** giữa các cổng để tránh làm nghẽn CPU của router OpenWrt (MT7621).
- **Lưu ý đặc biệt với Cổng 1 (`5101`):** Cổng 5101 giữ bản ghi DDNS của domain `test.taadaa.click`. Khi đổi IP cổng 5101, chờ 15 giây cho modem quay số và bản ghi DDNS tự động cập nhật, sau đó kiểm tra lại bằng `socket.gethostbyname('test.taadaa.click')` để đảm bảo domain trỏ đúng về IP mới.

### 2. Đối với cụm MikroTik PPPoE (`10001..10035`):
- Gửi lệnh ngắt kết nối line qua REST API: `PATCH /rest/interface/pppoe-client/<id> {"disabled": true}`.
- **Bắt buộc giữ ngắt tối thiểu 35–40 giây:** Nhà mạng (Viettel/FPT) yêu cầu thời gian chờ để giải phóng hoàn toàn session lease trên BRAS. Bật lại quá nhanh (<15s) sẽ bị cấp lại đúng IP cũ.
- Bật lại line: `PATCH /rest/interface/pppoe-client/<id> {"disabled": false}`.
- **Bắt buộc khởi động lại Container 3proxy (*3) và Sing-box (*6):** Sau khi các line PPPoE đổi IP, các socket upstream cũ bị đứt $\rightarrow$ Khởi động lại 2 container để thiết lập lại luồng mạng sạch.
- **Nghiệm thu đối soát:** Kiểm tra IP public qua `api.ipify.org`, lập bảng đối soát đảm bảo 100% cổng mục tiêu đã đổi khác IP cũ trước khi chốt phiên.
