# Cross-Instance Token Migration & Google AI Pro Revocation Runbook

## 1. Cơ Chế Thu Hồi Gói Google AI Pro (Revocation Sweep vs Cancellation)
- **Triệu chứng**:
  - Số lượng tài khoản Pro trong pool (ví dụ `ag-gemini-pool-3`) bị giảm (ví dụ từ 22 xuống 21).
  - Quota API (`/api/usage/<connection_id>`) của tài khoản bị trả về:
    - `plan`: `"Antigravity starter quota"`
    - `paidTier.id`: `"free-tier"`
    - Thông báo lỗi chi tiết: `"This account is ineligible for higher rate limits through a Google AI plan at this time."`
  - Trên hòm thư Gmail hoàn toàn **KHÔNG CÓ EMAIL BÁO HỦY GÓI** từ Google Payments.
- **Bản chất kỹ thuật**:
  - Khác với gói cá nhân thanh toán bằng thẻ tín dụng hàng tháng (có mail thông báo thanh toán thất bại / hủy subscription), các gói Google One dùng thử (trial 18 tháng, gói sinh viên, đối tác, hoặc tài khoản con trong Family Sharing) bị quét thu hồi bởi bộ lọc kiểm soát lạm dụng (Anti-Abuse / Policy Flagging) ở tầng **Google Cloud Code / Antigravity Entitlement**.
  - Quyền lợi AI Pro bị ngắt ngay tại backend Antigravity, dù tài khoản Google One cá nhân có thể vẫn còn dung lượng Drive.
- **Kỷ luật xử lý**:
  - Lập tức cô lập tài khoản bị hạ cấp: loại bỏ `connectionId` khỏi mảng `models` trong combo Pro tương ứng (`PUT /api/combos/{combo_id}`) để tránh làm ô nhiễm lưu lượng định tuyến Pro sang quota Free.

---

## 2. Cross-Instance Token Migration (9Router :20128 -> OmniRoute :20129)
Khi cần khôi phục hoặc thay thế tài khoản Pro nhanh chóng mà không cần mở profile GPM/browser để người dùng đăng nhập lại từ đầu:
- **Kiểm tra 9Router (:20128)**: 9Router lưu trữ OAuth connection ở dạng JSON thô trong SQLite:
  - Đường dẫn: `C:\Users\Kibe\AppData\Roaming\9router\db\data.sqlite`
  - Bảng: `providerConnections`
  - Cột `data` chứa JSON: `accessToken`, `refreshToken`, `expiresAt`, `projectId`, `scope`.
- **Kiểm tra tính sống của Token**:
  - Gọi `/api/usage/{connection_id}` trên cổng 20128 để xác nhận token còn sống và tier hiện tại là `g1-pro-tier`.

### Cơ Chế Mã Hóa Của OmniRoute (Field-Level AES-256-GCM)
OmniRoute lưu trữ credential trong SQLite tại `C:\Users\Kibe\.omniroute\storage.sqlite` (bảng `provider_connections`), bắt buộc mã hóa AES-256-GCM nếu có cấu hình `STORAGE_ENCRYPTION_KEY`:
- **Thứ tự nạp file cấu hình (BẮT BUỘC)**:
  1. `C:\Users\Kibe\.omniroute\.env` (Ưu tiên số 1 - nơi daemon production lưu key thật).
  2. `C:\Users\Kibe\.omniroute\server.env` (Ưu tiên số 2).
  3. `C:\Users\Kibe\OmniRoute\.env` (Ưu tiên số 3 - **CẢNH BÁO**: file này thường để trống `STORAGE_ENCRYPTION_KEY=`, nếu đọc nhầm file này sẽ mã hóa bằng chuỗi rỗng dẫn đến lỗi `Antigravity access token not available` do server không giải mã được!).
- **Key Derivation (Chuẩn static salt v3.7.9+)**:
  ```javascript
  const crypto = require('crypto');
  const secret = process.env.STORAGE_ENCRYPTION_KEY;
  const staticKey = crypto.scryptSync(secret, 'omniroute-field-encryption-v1', 32);
  ```
- **Cipher Format**:
  - Thuật toán: `aes-256-gcm`, IV ngẫu nhiên 16 bytes.
  - Định dạng chuỗi lưu vào DB: `enc:v1:<iv_hex>:<ciphertext_hex>:<authTag_hex>`

### Cạm Bẫy Schema Trong Bảng `provider_connections` (SQLite)
- Cột token tên là `access_token` (KHÔNG PHẢI `token`).
- `created_at` và `updated_at` có ràng buộc `NOT NULL` và nhận chuỗi ISO 8601 (ví dụ `2026-10-13T13:21:42.000Z`). Cấm bỏ trống `created_at` hoặc dùng chuỗi raw SQL `datetime('now')` khi bind params.
- Cột `provider_specific_data` bắt buộc định dạng JSON hợp lệ:
  `{"clientProfile":"ide","projectId":"...","tier":"g1-pro-tier","apiKeyHealth":{},"subscriptionTier":"Google AI Pro","plan":"Pro"}`
- `priority` là integer, `is_active` = 1, `test_status` = `'active'`, `max_concurrent` = 5, `proxy_enabled` = 1.

### Quy Trình Di Trú O(1) Tự Động
Đã có sẵn script tự động hóa toàn bộ luồng di trú tại: `D:/Taadaa/tools/sync_pro_accounts.py`.
Khi cần đồng bộ thêm tài khoản, chỉ cần điều chỉnh danh sách email trong script hoặc chạy trực tiếp:
```bash
python D:/Taadaa/tools/sync_pro_accounts.py
```

Các bước cốt lõi script thực hiện:
1. **Trích xuất**: Đọc `accessToken`, `refreshToken`, `scope`, `projectId` của tài khoản mục tiêu từ 9Router SQLite.
2. **Mã hóa**: Dùng subprocess Node.js hoặc thư viện crypto tương thích để mã hóa cả `accessToken` và `refreshToken` theo đúng định dạng `enc:v1:...` với static key.
3. **Upsert vào OmniRoute**:
   - Nếu connection đã tồn tại trong `provider_connections`: Cập nhật `access_token`, `refresh_token`, `is_active = 1`, `test_status = 'active'`, `provider_specific_data` (tier `g1-pro-tier`, plan `Pro`).
   - Nếu chưa tồn tại: `INSERT` bản ghi mới với `provider = 'antigravity'`, `auth_type = 'oauth'`, `max_concurrent = 5`.
4. **Kiểm tra Blacklist Pipeline**:
   - Mở file `D:\Taadaa\GPM auto\config\oauth_pipeline_status.json`.
   - Nếu email nằm trong mảng `antigravity_blacklist` (ví dụ do từng được bảo vệ khỏi quota churn trước đó), xóa email khỏi mảng blacklist.
5. **Cập nhật Combo Pro**:
   - `GET /api/combos/{combo_id}`
   - Lọc bỏ connection cũ bị hạ cấp (`toloan`).
   - Thêm model mapping cho các connection mới:
     ```json
     {
       "connectionId": "<uuid>",
       "id": "ag-gemini-pool-3-model-<label>-<prefix>",
       "kind": "model",
       "label": "pro-<label>",
       "model": "antigravity/gemini-3.8-flash-tiered",
       "providerId": "antigravity",
       "weight": 0
     }
     ```
   - `PUT /api/combos/{combo_id}` để đồng bộ live routing ngay lập tức.
