# Google AI Pro Silent Revocation & 9Router-OmniRoute Cross-Sync

## 1. Google AI Pro Promotional/Trial Silent Revocation

### Triệu chứng & Bản chất
- Số lượng tài khoản Pro trên Dashboard Quota của OmniRoute (:20129) đột ngột giảm (ví dụ: từ 22 về 21 acc).
- Email người dùng KHÔNG nhận được bất kỳ thông báo lỗi thanh toán hay hủy gói nào từ Google Payments / Google Play.
- Tài khoản thường là các gói dùng thử dài hạn (18 tháng qua đợt khuyến mãi/sinh viên/đối tác/family).

### Chẩn đoán qua API Upstream (`/api/usage/<connectionId>`)
Khi kiểm tra response `subscriptionInfo` trả về từ Google Cloud Code (`retrieveUserQuota`):
```json
{
  "plan": "Antigravity starter quota",
  "subscriptionInfo": {
    "currentTier": {
      "id": "free-tier",
      "name": "Antigravity"
    },
    "paidTier": {
      "id": "free-tier",
      "name": "Antigravity Starter Quota",
      "upgradeSubscriptionText": "This account is ineligible for higher rate limits through a Google AI plan at this time.",
      "upgradeSubscriptionUri": "https://antigravity.google/docs/faq#why-am-i-ineligible-for-google-one-ai-quotas-even-though-i-am-a-subscribed-to-a-plan"
    }
  }
}
```

### Nguyên nhân cốt lõi
1. **Thu hồi quyền lợi khuyến mãi (Promotion Ineligibility):**
   - Khác với gói cá nhân thanh toán bằng thẻ tín dụng hàng tháng (sẽ văng email từ chối thẻ khi gia hạn fail), việc thu hồi hạn mức dùng thử 18 tháng diễn ra ngầm tại tầng backend quyền lợi của Google AI. Gói Google One ở tầng tài khoản người dùng có thể vẫn còn hiệu lực hoặc chuyển về Free mà không có email cảnh báo.
2. **Quy định Family Group:**
   - Trong nhóm Google One Family, chỉ có **Chủ nhóm (Family Manager)** mới được cấp hạn mức Google AI Pro trên Antigravity / Gemini Code Assist. Thành viên con bị Google chặn quyền nhận quota Pro trong công cụ lập trình (`ineligible`).
3. **Quét Anti-Abuse ngầm:**
   - Khi tài khoản bị phát hiện có lưu lượng bất thường hoặc truy cập từ nhiều IP proxy, Google âm thầm cắt quyền Pro riêng trên Antigravity và hạ về `free-tier` (Starter Quota) để chống lạm dụng.

---

## 2. Đồng bộ chéo tài khoản giữa 9Router (:20128) và OmniRoute (:20129)

### Kiến trúc lưu trữ độc lập
- **9Router SQLite DB:** `C:/Users/Kibe/AppData/Roaming/9router/db/data.sqlite` (bảng `providerConnections`).
- **OmniRoute SQLite DB:** `C:/Users/Kibe/.omniroute/storage.sqlite` (bảng `provider_connections`).

### Kịch bản cứu hộ (Cross-Router Salvage)
Khi một tài khoản Pro bị xóa khỏi OmniRoute trước đó (ví dụ để bảo vệ khỏi tải farm bùng nổ, hoặc do blacklist nhầm) nhưng vẫn còn token live trên 9Router:
1. **Kiểm tra trạng thái trên 9Router:**
   - Truy vấn `providerConnections` trên 9Router: kiểm tra `provider = 'antigravity'`, `email`, `isActive = 1`.
   - Bắn test probe qua `POST http://127.0.0.1:20128/api/providers/<id>/test` xác nhận `valid: true`.
   - Kiểm tra `GET http://127.0.0.1:20128/api/usage/<id>` xác nhận `paidTier.id == 'g1-pro-tier'`.
2. **Sao chép Credential sang OmniRoute:**
   - Thay vì bắt người dùng phải mở trình duyệt hoặc login GPM để OAuth lại từ đầu (đặc biệt với tài khoản cá nhân không có profile GPM trên máy như `jinrakal`), trích xuất `refresh_token`, `access_token`, `expires_at`, `project_id`, `scope` từ bảng `providerConnections` của 9Router để nạp trực tiếp vào `provider_connections` của OmniRoute.
3. **Cập nhật Combo & Blacklist:**
   - Xóa email khỏi `antigravity_blacklist` trong `oauth_pipeline_status.json`.
   - Cập nhật connection vào danh sách models của combo `ag-gemini-pool-3` (model `antigravity/gemini-3.8-flash-tiered`).
   - Loại bỏ các connection đã bị hạ cấp Starter (như `toloan`) khỏi combo Pro để giữ vững throughput.
