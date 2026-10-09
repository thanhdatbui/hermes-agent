# OmniRoute Model Lockout & ChatGPT-Web 502/Cloudflare Resilience Runbook

## 1. Hiện tượng & Bản chất lỗi (Root Cause Anatomy)
- **Triệu chứng:** Khi một tài khoản trong pool ChatGPT-Web (`chatgpt-web/gpt-5.6-sol-high`) gặp lỗi mạng, proxy flap, hoặc dính Cloudflare Challenge (trả về HTTP 502 Bad Gateway hoặc 403 Forbidden), OmniRoute liên tục bắn lặp đi lặp lại request vào tài khoản đó, làm tắc nghẽn cả pool và có nguy cơ làm chết/khóa tài khoản.
- **Bản chất 1 - Cloudflare Session vs Proxy Socket:**
  - Lỗi 502/403 của ChatGPT-Web phần lớn KHÔNG PHẢI do proxy chết. Socket proxy vẫn hoạt động bình thường (`requests.get('api.ipify.org')` OK).
  - Lỗi là do cookie phiên (`__Secure-next-auth.session-token`) hoặc cookie Cloudflare (`cf_clearance`, `__cf_bm`) bị Cloudflare trên `chatgpt.com` bắt giải captcha / challenge. Node-fetch không bóc được JSON phản hồi mà nhận về trang HTML challenge -> OmniRoute dội ra lỗi 502.
- **Bản chất 2 - P2C Bug (Granularity Abstraction Mismatch):**
  - Trong `open-sse/services/combo/targetSorters.ts`, hàm `getP2CTargetScore` lấy metric sức khỏe theo `metrics.byModel[target.modelStr]`.
  - Cả 16 tài khoản đều mang chung model `chatgpt-web/gpt-5.6-sol-high`, nên tất cả tài khoản đều nhận chung một điểm số.
  - Khi 2 tài khoản bằng điểm, P2C tie-break về index đầu tiên của mảng -> luồng suy biến thành "luôn chọn acc đầu danh sách", đè đúng tài khoản vừa dính 502 ra bắn tiếp.
- **Bản chất 3 - Model Lockout bị tắt mặc định:**
  - Trong `src/lib/resilience/modelLockoutSettings.ts`, cấu hình mặc định là `DEFAULT_MODEL_LOCKOUT_SETTINGS.enabled = false`.
  - Khi không được kích hoạt rõ ràng trong settings DB, hàm `recordModelLockoutFailure` trong `open-sse/services/combo.ts` (dòng 2360 & 2454) hoàn toàn KHÔNG HOẠT ĐỘNG khi gặp 502/403 -> Tài khoản lỗi không bao giờ được ghi nhận cooldown.

---

## 2. Giải pháp kỹ thuật chuẩn hóa (Standard Production Fix)

### Bước 1: Kích hoạt `modelLockout` toàn cục qua API Settings
Gửi PATCH request tới `http://127.0.0.1:20129/api/settings`:
```json
{
  "modelLockout": {
    "enabled": true,
    "errorCodes": [403, 404, 429, 502, 503, 504],
    "baseCooldownMs": 120000,
    "maxCooldownMs": 1800000,
    "maxBackoffSteps": 10,
    "useExponentialBackoff": true
  }
}
```
* **Cơ chế:** Khi tài khoản gặp 502/403, OmniRoute lập tức kích hoạt `recordModelLockoutFailure` cách ly (lockout) chính xác `connectionId` đó trong 120 giây (tăng theo hàm mũ tối đa 30 phút nếu lỗi lặp lại), loại tài khoản khỏi candidate pool của mọi combo.

### Bước 2: Chuẩn hóa Combo Config sang `round-robin` + Failover 0ms
Gửi PUT request cập nhật các combo web (`chatgpt-web-pool`, `gpt-web-sol`, `gpt-web-luna`):
```json
{
  "strategy": "round-robin",
  "config": {
    "disableSessionStickiness": true,
    "disablePromptCacheAffinity": true,
    "stickyRoundRobinLimit": 0,
    "failoverBeforeRetry": true,
    "maxRetries": 0,
    "maxGlobalAttempts": 8,
    "targetTimeoutMs": 60000,
    "retryDelayMs": 500
  }
}
```
* `strategy: "round-robin"`: Chia đều tải 100% qua atomic counter `rrCounters`.
* `failoverBeforeRetry: true` + `maxRetries: 0`: Khi gặp lỗi, nhảy ngay 0ms sang tài khoản kế tiếp trong cùng request, cấm retry trên cùng tài khoản lỗi.
* `disableSessionStickiness: true` + `stickyRoundRobinLimit: 0`: Triệt tiêu băm SHA-256 prompt ghim request vào acc cũ.

### Bước 3: Cách ly tài khoản lỗi Cloudflare & Refresh Token
- Khi probe `/api/providers/:id/test` báo: `Cloudflare blocked the validator`:
  - Đặt tạm `isActive: false` trên connection để ngừng hoàn toàn request vào tài khoản đó.
  - Mở Profile GPM tương ứng qua proxy di động để vượt lại Cloudflare và lấy cookie/token mới cập nhật vào OmniRoute trước khi bật lại `isActive: true`.
