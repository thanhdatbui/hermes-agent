# ChatGPT Web Pool P2C 502 Loop & Auto-Recovery Playbook

## 1. Triệu chứng & Bản chất Lỗi (Root Cause)
- **Triệu chứng:** Pool nhiều tài khoản ChatGPT Web (cùng model `chatgpt-web/gpt-5.6-sol-high`) liên tục dội request vào một tài khoản đang lỗi HTTP 502 (hoặc 403), gây chậm trễ hệ thống và nguy cơ làm chết tài khoản.
- **Nguyên nhân 1 - P2C Degeneration:** Hàm `getP2CTargetScore` trong OmniRoute (`open-sse/services/combo/targetSorters.ts`) chấm điểm theo `metrics.byModel[target.modelStr]` thay vì từng connection (`executionKey`). Khi tất cả tài khoản trong pool chạy cùng một model string, điểm số bằng nhau $\to$ P2C tie-break fallback về index 0, liên tục chọn tài khoản đầu tiên.
- **Nguyên nhân 2 - Missing Model Lockout:** Mã lỗi 502 được phân loại là transient error. Nếu cấu hình toàn cục `modelLockout.enabled: false` trong Settings, OmniRoute không đặt cooldown cho tài khoản bị lỗi mà lập tức cho phép các request sau tiếp tục bốc trúng.
- **Nguyên nhân 3 - 502 Web không phải do Proxy:** Khi proxy di động (ví dụ port 5105) vẫn sống bình thường, lỗi 502 trên `chatgpt-web` thực chất là do Cloudflare chặn session cookie cũ (`__Secure-next-auth.session-token`) hoặc thiếu `cf_clearance` hợp lệ.

---

## 2. Giải pháp Cấu hình & Bảo vệ (Engine Settings)

### A. Bật Model Lockout tự động cách ly tài khoản lỗi
Cập nhật qua `PATCH /api/settings`:
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
*Tác dụng:* Khi một tài khoản gặp 502/403, OmniRoute tự động cách ly tài khoản đó trong 120 giây (tăng dần nếu lặp lại), không bao giờ bắn liên tiếp vào tài khoản đang lỗi.

### B. Cấu hình Combo chống dồn lỗi
Chuyển strategy của combo web sang `round-robin` với các cờ:
```json
{
  "strategy": "round-robin",
  "config": {
    "disableSessionStickiness": true,
    "disablePromptCacheAffinity": true,
    "stickyRoundRobinLimit": 0,
    "failoverBeforeRetry": true,
    "maxRetries": 0,
    "maxGlobalAttempts": 8
  }
}
```

---

## 3. Quy trình Cứu Tài khoản Bị Lỗi (Auto-Recovery Flow)

**QUY TẮC CỐT LÕI:** CẤM tắt vĩnh viễn (`isActive: false`) tài khoản rồi bỏ mặc khi gặp lỗi 502. Bắt buộc phải có cơ chế phục hồi cookie qua GPM:

1. **Kiểm tra Proxy:** Xác nhận cổng proxy (ví dụ 5105) còn sống bằng request kiểm tra IP qua proxy.
2. **Khởi động GPM Profile:** Gọi GPM Local API: `GET http://127.0.0.1:19995/api/v3/profiles/start/<profile_id>?win_scale=0.8`.
3. **Mở trình duyệt qua CDP:** Kết nối Playwright tới `remote_debugging_address`, truy cập `https://chatgpt.com`, đợi 5-10 giây để Cloudflare Turnstile tự vượt và sinh `cf_clearance`.
4. **Trích xuất Full Cookies:**
   ```python
   cookies = context.cookies("https://chatgpt.com")
   cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in cookies])
   ```
5. **Đóng Profile:** `GET http://127.0.0.1:19995/api/v3/profiles/stop/<profile_id>`.
6. **Cập nhật OmniRoute:**
   - Gửi `PUT /api/providers/<connection_id>` với `{"apiKey": cookie_str, "isActive": true}`.
   - Gửi `POST /api/providers/<connection_id>/test` để kiểm tra probe ("valid": true).
