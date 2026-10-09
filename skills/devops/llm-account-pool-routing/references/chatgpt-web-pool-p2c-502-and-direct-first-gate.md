# ChatGPT Web Pool P2C 502 Pathology, Round-Robin Balancing, and Direct-First Gate

Tài liệu này ghi lại chi tiết:
1. Bản chất sự cố P2C trên pool 16+ accounts ChatGPT Web dùng chung 1 model string.
2. Phân biệt lỗi 502 Cloudflare cookie challenge vs Mobile proxy port.
3. Cấu hình Combo chuẩn giải quyết dứt điểm dồn tải 502 mà không cần sửa engine.
4. Quy tắc điều phối Direct-First & Capability-Match Gate (chống quan liêu over-engineering).

---

## 1. Bản chất sự cố P2C trên Web Pool (`gpt-5.6-sol-high`)

### Triệu chứng
- Pool 16 accounts ChatGPT Web (chung model `chatgpt-web/gpt-5.6-sol-high`) qua proxy di động riêng lẻ (ví dụ MobiProxy port 5105, 5113...).
- Một tài khoản bị lỗi mạng/proxy (HTTP 502 Bad Gateway), nhưng các request tiếp theo liên tục đè đúng tài khoản đó ra chạy đầu tiên (`first-try`), gây chậm trễ và liên tục failover (`200 healed` sau 2-6 attempts).

### Root Cause kép trong Code OmniRoute (`open-sse/services/combo/`):
1. **Granularity Abstraction Mismatch trong `targetSorters.ts` (`getP2CTargetScore`):**
   - Hàm `getP2CTargetScore` đọc điểm sức khỏe `metrics?.byModel?.[target.modelStr]`.
   - Vì cả 16 accounts trong pool đều khai báo chung model string `chatgpt-web/gpt-5.6-sol-high`, toàn bộ 16 accounts nhận chung 1 điểm số y hệt nhau.
   - Khi 2 accounts bốc ngẫu nhiên có điểm bằng nhau, tie-break fallback về `firstIndex` (phần tử đầu mảng tĩnh). Acc nằm ở đầu luôn bị chọn làm first-try.
2. **Transient Error 502 không ghi nhận Cooldown:**
   - Trong `targetExhaustion.ts`, mã lỗi `502` chỉ được phân loại là transient trong phạm vi duy nhất 1 request (`per-request exhaustion set`).
   - Kết thúc request (khi account sau cứu thành công trả về `200 healed`), chuỗi lỗi bị reset về 0 trong `failureTracker.ts`. Account lỗi vẫn giữ trạng thái `isActive: true` và điểm số không bị trừ ở request kế tiếp.
3. **Session Stickiness & Prompt Cache Affinity:**
   - OmniRoute băm SHA-256 prompt ghim request vào cùng 1 connectionId. Khi gặp 502, nếu không tắt stickiness, các turn tiếp theo của cùng client/script tiếp tục cố kết nối vào account cũ.

---

## 2. Phân biệt Lỗi 502: Cloudflare Challenge vs Mobile Proxy

Khi account ChatGPT Web báo lỗi 502 / 403:
- **CẤM KẾT LUẬN VỘI VÃ là proxy di động chết.**
- **Bản chất thực tế:** Proxy di động (ví dụ port 5105) vẫn sống và curl IP bình thường. Nhưng Cookie phiên web (`__Secure-next-auth.session-token`) hoặc cookie bảo mật Cloudflare (`cf_clearance`, `__cf_bm`, `_cfuvid`) đã bị Cloudflare trên `chatgpt.com` bắt giải captcha / challenge lại.
- Khi OmniRoute gửi request qua proxy đến ChatGPT Web, Cloudflare chặn lại và trả về HTML Challenge $\to$ OmniRoute không parse được JSON response và dội ra `502 Bad Gateway`.
- **Cách khắc phục:** Mở Profile GPM tương ứng, truy cập `chatgpt.com` để Cloudflare nhả `cf_clearance` mới, sau đó copy cookie cập nhật lại vào connection trong OmniRoute. Tạm thời set `isActive: false` trên connection để loại khỏi candidate pool.

---

## 3. Cấu hình Combo chuẩn giải quyết dứt điểm dồn tải (Không sửa engine)

Chuyển strategy sang **`round-robin`** với các cờ chống dồn lỗi sau:

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
    "queueTimeoutMs": 1000,
    "retryDelayMs": 500,
    "targetTimeoutMs": 60000
  }
}
```

### Tại sao Round-Robin giải quyết được bài toán?
- **Cursor tiến tuần tự:** Mỗi request hoàn tất, con trỏ `rrCounters` tiến lên $1 \to 2 \dots \to 16$. Nếu một account bị lỗi, request kế tiếp bắt đầu từ account tiếp theo, phải đi hết 1 vòng 15 accounts khác mới quay lại account lỗi.
- **`failoverBeforeRetry: true` + `maxRetries: 0`:** Gặp 502 lập tức nhảy sang account kế tiếp trong pool với độ trễ 0ms, không retry tại chỗ.
- **Tắt Stickiness triệt để:** `disableSessionStickiness: true` và `stickyRoundRobinLimit: 0` ngăn chặn việc ghim cứng vào 1 connection.

---

## 4. DIRECT-FIRST & CAPABILITY-MATCH GATE (Chống Quan Liêu Điều Phối)

Trích xuất từ sự cố Coordinator bị User phê bình vì over-engineering khi nhận lệnh "gọi Sol hỏi":

> *"Đừng triệu hồi quân đội để mở một cánh cửa."*

### 5 Nguyên tắc vàng:
1. **Phân loại theo SIDE EFFECT, không theo động từ User:**
   - Hỏi model / query API / đọc log / đọc file = **READ-ONLY TRIAGE**.
   - Coordinator tự làm trực tiếp O(1) qua 1 lệnh HTTP/browser/tool. **CẤM dispatch Worker.**
2. **Kiểm tra chi phí nghi thức:**
   - Nếu tự làm mất $\le 2$ tool calls $\to$ **Tự làm ngay.**
   - Chỉ dispatch khi có lý do thực sự: scope ghi độc quyền, việc chạy batch nền lâu (>30s), hoặc cần cô lập context code lớn.
3. **Khớp quyền trước khi dispatch (Capability Matching):**
   - Liệt kê hành động bắt buộc của task (ghi file? chạy curl?).
   - Nếu task cần ghi file/chạy network mà Worker bị Sandbox Gate khóa **READ-ONLY** (`TASK_KIND: INVESTIGATE`) $\to$ **CẤM dispatch.** Đó là tự tạo mâu thuẫn dẫn đến thất bại ngay từ khâu giao việc.
4. **CẤM gài `FAIL_FAST` bẫy Worker:**
   - `FAIL_FAST` là để chặn vòng lặp vô hạn, không phải để ép Worker bỏ cuộc và giơ tay xin hàng trước khi kịp làm việc.
5. **Đúng Model chỉ định:**
   - User bảo gọi Sol High / Claude CLI $\to$ Gọi đúng model chỉ định, cấm tự ý hạ cấp xuống model thấp (Sol Medium/Instant) mà không giải thích trước lý do timeout/latency.
