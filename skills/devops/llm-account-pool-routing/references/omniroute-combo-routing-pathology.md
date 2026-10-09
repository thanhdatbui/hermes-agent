# OmniRoute Combo Routing Pathology: Hard-Bound Affinity, Cross-Model Quota Poisoning, and Global Cooldown Cascades

Tài liệu này ghi lại chi tiết giải phẫu luồng định tuyến (routing pathology), 3 bẫy lỗi kiến trúc, phân tích cân bằng chiến lược (Cache-Optimized vs P2C), và cấu trúc combo chuẩn cho các pool tài khoản LLM lớn (113+ accounts).

---

## 1. Triệu chứng lâm sàng (Symptoms)
- Pool Tier 1 (`ag-gemini-pool-3`) có 16 accounts Pro còn quota, nhưng request từ `omni-worker` bị kẹt 30s hoặc nhảy xuống Tier dưới.
- Log ứng dụng liên tục báo:
  - `antigravity | hard-bound connection <id> unavailable; refusing sibling selection`
  - `Skipping antigravity/gemini-3.8-flash-tiered — connection <id> is at max concurrency cap (2); spilling to next priority target`
  - `429 Semaphore timeout after 30000ms for antigravity:<id> (<account_email>)`
  - `ChatGPT returned 413 — the request payload is too large for ChatGPT web's size limit`

---

## 2. Các Bẫy Lỗi Kiến Trúc Cốt Lõi (Pathologies)

### Pathology 1: Hard-Bound Connection Pinning & Concurrency Cap Spillover
- **Vị trí code:** `src/sse/services/auth.ts`, `src/sse/services/sessionAffinityPin.ts`.
- **Cơ chế lỗi:** Request mang `sessionId` hoặc context hash được gán một affinity target cố định. Khi duyệt danh sách target, router bị ép chỉ chọn duy nhất `forcedConnectionId`. Khi account này chạm trần concurrency (`maxConcurrency = 2`), router từ chối chọn sibling connections khác và đánh rớt target.

### Pathology 2: Cross-Model Quota Snapshot Poisoning
- **Vị trí code:** `src/domain/quotaCache.ts` (`isAntigravityQuotaExhausted`).
- **Cơ chế lỗi:** Khi account hết quota Claude Sonnet, snapshot ghi nhận trạng thái exhausted cho connection đó. Nếu hàm check không chặt chẽ, router đánh dấu tài khoản là exhausted đối với TẤT CẢ các model (kể cả Gemini Flash còn nguyên quota).

### Pathology 3: Provider Cooldown Tracker Cascade
- **Vị trí code:** `open-sse/services/providerCooldownTracker.ts`.
- **Cơ chế lỗi:** Khi một target fail không kèm `connectionId`, router ghi nhận key `"antigravity"` vào `cooldownMap`. Mọi target thuộc provider `antigravity` bị skip ngay lập tức.
- **Khắc phục:** Khai báo `MULTI_ACCOUNT_POOLS = new Set(["antigravity", "codex"])`. Bỏ qua provider-level cooldown nếu không có connectionId cụ thể.

### Pathology 4: Bẫy 429 Semaphore Timeout do Session Stickiness Dồn Cục (2026-09-21)
- **Vị trí code:** `open-sse/services/combo/sessionStickiness.ts`, `open-sse/services/accountSemaphore.ts`.
- **Cơ chế lỗi:**
  1. `applySessionStickiness()` ghim conversation hash vào 1 connection nhưng hoàn toàn mù trạng thái concurrency semaphore (`maxConcurrent = 2`).
  2. Khi agent chạy dồn dập, 2 slot bị chiếm, các request tiếp theo của cùng session vẫn bị ép vào acc đó, xếp hàng chờ đủ 30 giây rồi nổ 429 timeout.
  3. Nếu cấu hình `failoverBeforeRetry: false`, router tiếp tục retry đúng account đó 3 lần -> Treo 90-120s rồi chết hẳn.
- **Giải pháp dứt điểm:** Bật `failoverBeforeRetry: true` trên tất cả combo. Áp dụng Micro-Queue (`queueDepth = 1, queueTimeoutMs = 1000`) và `sticky = 8` cho Pro; áp dụng `p2c` + `sticky = 0` + `queueDepth = 0` cho toàn bộ các pool Free.

### Pathology 5: Bẫy 413 Payload Too Large khi Chèn ChatGPT-Web vào Fallback Worker
- **Cơ chế lỗi:** Khi context agent lớn (>30k tokens hoặc tool schemas), giao diện web ChatGPT (`chatgpt-web`) từ chối payload và trả về 413 ngay tại cửa, cắt đứt chuỗi fallback.
- **Giải pháp:** Loại bỏ hoàn toàn `chatgpt-web-pool` và các model free rác khỏi chuỗi `omni-worker` chính. Chỉ dùng các pool API chuẩn.

### Pathology 6: Hiện tượng "Tràn tầng vội vã" do Phẳng hóa Combo (`flatten` vs `execute`)
- Khi combo cha `omni-worker` để mặc định `nestedComboMode: "flatten"`, toàn bộ model bị trải phẳng thành 1 danh sách. Khi các account Pro tạm bận 2/2, con trỏ duyệt lướt qua chạm ngay vào model tầng Free.
- **Giải pháp:** Bắt buộc đặt `nestedComboMode: "execute"` trên combo cha `omni-worker` để coi sub-combo là Runtime Unit độc lập.

### Pathology 7: Bẫy Nhãn "Business" Giả Cầy vs Antigravity Restricted & Bão 429 Mảng Tĩnh P2C (2026-09-21)
- **Vị trí code:** `open-sse/services/combo/targetSorters.ts` (`orderTargetsByPowerOfTwoChoices`), `open-sse/services/accountSemaphore.ts` (`DEFAULT_TIMEOUT_MS = 30_000`), `src/sse/services/auth.ts`, `open-sse/services/usage/antigravity.ts`.
- **Cơ chế lỗi 1 (Bẫy nhãn Business giả cầy & Nguồn gốc parser):**
  - **Nguồn gốc sinh ra nhãn Business:** Khi tài khoản Google đăng ký OAuth cá nhân thông thường, Google trả về tier là `standard-tier`. Trong `open-sse/services/usage/antigravity.ts`, hàm parse kiểm tra:
    ```typescript
    if (upper.includes("STANDARD") || upper.includes("BUSINESS")) return "Business";
    ```
    Vì chứa chuỗi `STANDARD`, parser của OmniRoute **tự động gán nhãn hiển thị là "Business"**, đồng thời khi thiếu Cloud Project lúc khởi tạo, Google trả cờ `ineligibleTiers` khiến parser gán thêm `Antigravity (Restricted)`.
  - UI Dashboard chỉ lấy trường `plan` để hiển thị nhãn xanh `"Business"`, tạo ảo tưởng đây là acc Business xịn. Thực tế đây là các tài khoản cá nhân thông thường mang metadata `standard-tier` bị kẹt cờ `Restricted`.
  - **Thực tế hoạt động:** Token OAuth và quota của tài khoản vẫn sống 100% (gọi trực tiếp probe câu ngắn hay văn bản dài 1.000 tokens vẫn trả HTTP 200 OK). Nhưng khi gánh tải đồng thời từ 2-3 request trở lên, luồng upstream của Google bị nghẽn/kéo dài latency, kết hợp với vị trí cố định trong combo khiến slot concurrency (`maxConcurrent = 2`) bị kẹt cứng.
- **Cơ chế lỗi 2 (Bẫy mảng tĩnh P2C & Hàng đợi 30s):**
  - Trong Free Pool, chiến lược `p2c` dùng hàm `orderTargetsByPowerOfTwoChoices` tính điểm theo `target.modelStr`. Vì toàn bộ targets trong pool đều chạy chung model `antigravity/gemini-3.8-flash-tiered`, điểm số bằng nhau 100%. Thuật toán bốc 1 acc lên đầu, còn lại giữ nguyên thứ tự mảng tĩnh.
  - Các acc Restricted có `maxConcurrent = 2` (như `lamngocdiep`, `vothimyhanh`, `carmendarnold`) nằm ở vị trí tĩnh số 2, 12, 16... Khi request đầu tiên cần fallback hoặc xoay vòng, router trượt xuống và kẹt vào các vị trí này.
  - Router bắt request xếp hàng chờ đủ 30 giây (`DEFAULT_TIMEOUT_MS`) rồi mới nổ lỗi `429 Semaphore timeout after 30000ms`. Lỗi nội bộ này không bị tính là upstream failure nên router không hạ cờ hay backoff, dẫn đến tích tụ hàng ngàn lỗi 429 (`lamngocdiep` 3.933 lần, `vothimyhanh` 1.803 lần).
- **Cơ chế lỗi 3 (Tràn tầng vô lý từ Tier 1 Pro xuống Tier 2 Free):**
  - Tier 1 Pro (`ag-gemini-pool-3`) chạy `cache-optimized` với Rendezvous Hashing ghim phiên chat vào 1 acc Pro duy nhất.
  - Khi agent gọi dồn dập, acc Pro đó bị chiếm trọn 2/2 slot concurrency. Do thiếu cơ chế atomic spillover nội bộ sang 15 acc Pro còn lại, router retry tại chỗ 5 lần x 30s = 150s kẹt cứng, rồi nổ `503 Maximum combo retry limit reached`.
  - Combo cha `omni-worker` thấy Tier 1 nổ 503 lập tức tràn xuống Tier 2, đâm thẳng vào ổ acc Restricted ở đầu mảng tĩnh Free Pool gây bão lỗi 429.
- **Giải pháp dứt điểm:**
  1. **CẢNH BÁO BẪY "SƠN VỎ" DATABASE (DB COSMETIC PATCH TRAP - BÀI HỌC XƯƠNG MÁU):**
     - Việc chỉ cập nhật các chuỗi text trong SQLite `provider_connections` (`tier = 'free-tier'`, `subscriptionTier = 'Antigravity Starter Quota'`, `plan = 'Antigravity starter quota'`, `projectId = 'aicode-consumers'`) **HOÀN TOÀN KHÔNG SỬA ĐƯỢC BẢN CHẤT LỖI PHÍA GOOGLE**!
     - Mã nguồn `open-sse/executors/antigravity.ts` (dòng 633) đã chỉ rõ: *"Google no longer auto-creates GCP projects for standard-tier accounts: a fabricated/omitted id only earns a delayed 429 RESOURCE_EXHAUSTED from Google's quota check."*
     - Tài khoản cá nhân `standard-tier` bị Google đánh cờ `ineligibleTiers` sẽ không được tự động cấp Cloud Project. Việc gán project mượn/chế (`aicode-consumers`) khiến máy chủ Google treo từ 18s đến tận 72s để check quota rồi mới trả về 403 hoặc 429.
     - Khi Google treo 72s, 2 slot concurrency (`maxConcurrent: 2`) bị chiếm giữ hoàn toàn, khiến tất cả request đến sau bị dồn vào hàng đợi 30s và nổ bão lỗi `429 Semaphore timeout after 30000ms`.
     - **Quy tắc bất biến:** CẤM TUYỆT ĐỐI ngộ nhận việc đổi text trong DB là "đã fix". Nếu chưa xử lý tận gốc phía Google, tuyệt đối không được nạp các acc này vào combo chạy tải nặng!
  2. **CÁCH FIX THỰC SỰ ĐỂ DÙNG ĐƯỢC ACC NHÃN "BUSINESS" / STANDARD-TIER:**
     - **Cách 1 (BYOP - Bring Your Own Project):** Đăng nhập Gmail đó vào `console.cloud.google.com`, tự tạo 1 GCP Project miễn phí chính chủ, bật API Cloud Code / Gemini Code Assist, rồi lấy Project ID đó điền vào ô `Project ID` của connection trong OmniRoute. Lúc này Google nhận diện đúng project và cấp quota mượt mà.
     - **Cách 2 (Re-auth trên GPM):** Cho chạy lại luồng OAuth trên môi trường sạch/GPM để Google cấp lại token sạch kèm quota Starter tự sinh project.
     - **Kỷ luật cách ly:** Nếu chưa hoàn tất 1 trong 2 cách trên, BẮT BUỘC giữ nguyên `is_active = 0` và gỡ sạch 100% ID của chúng ra khỏi danh sách `models` của các combo (`ag-gemini-free-pool`, `ag-claude`, `ag-opus`).
  3. **BẪY CÔNG TẮC isActive=0 VÔ DỤNG TRONG COMBO (QUY TẮC BẤT BIẾN):**
     - Router OmniRoute **KHÔNG tự động lọc bỏ `isActive: false`** khi resolve danh sách `models` của combo!
     - Nếu connection ID vẫn còn nằm trong mảng `models` của combo, router **vẫn cứ đâm đầu gọi vào** dù trên UI Dashboard người dùng đã gạt tắt công tắc.
     - **Biện pháp duy nhất hiệu quả:** Bắt buộc phải PUT/UPDATE combo để **gỡ hẳn phần tử model chứa connectionId đó ra khỏi combo**.
  4. **BẪY PROBE "1+1" GIẢ CẦY TRÊN ACC RESTRICTED/BUSINESS:**
     - Test probe ngắn (`1+1`, max_tokens=5) có thể trả về HTTP 200 đánh lừa, nhưng khi gặp context thực tế (>10k tokens) hoặc session dài, acc Restricted/Business lập tức bị Google bóp nghẽn/treo upstream, gây kẹt slot concurrency và nổ bão lỗi 429 Semaphore Timeout 30s liên hoàn.
     - **CẤM TUYỆT ĐỐI** tin vào probe ngắn `1+1` để re-enable hoặc re-add các acc mang nhãn `Business` / `Restricted` vào bất kỳ combo nào!
  5. **Cứu hộ 13 acc lỗi 422 (Starter Quota sạch):** Các acc Starter Quota thực sự chỉ bị thiếu `projectId` (gây lỗi `422 Missing Google projectId`) thì mới cứu được 100% bằng cách patch `projectId: "aicode-consumers"` và metadata `Antigravity Starter Quota`. Còn acc gốc `Business`/`Restricted` thì dứt khoát loại bỏ.
  6. **Affinity-First, Availability-Second (Atomic Spillover 0ms Cho Toàn Bộ 19 Strategies - Commit `1c1634f0b`):**
     - Mở rộng `tryAcquireAccountSemaphore` trong `open-sse/services/combo.ts` cho TẤT CẢ các chiến lược (bao gồm `cache-optimized` và `p2c`), không để riêng cho `priority`.
     - **Semantics chuẩn:** Non-priority strategies khi chạm concurrency cap phải `return null` để vòng lặp candidate bước sang target tiếp theo trong pool ngay lập tức (0ms spillover), chỉ trả về `stopProtectedPriorityTarget(...)` khi target thực sự là `protectedPriorityTarget`.
     - Bổ sung telemetry structured metadata `{ strategy, connectionId, maxConcurrentCap }` vào `recordComboDecision` dưới reason `concurrency_cap`.
     - **CẢNH BÁO BẪY COOLDOWN CASCADE (Sol Reviewer phản biện):** TUYỆT ĐỐI CẤM dùng `markBlocked` cứng 15-30 phút khi dính `Semaphore timeout`. Semaphore timeout chỉ chứng minh acc bị quá tải (overloaded/saturated), không chứng minh acc bị chết (unhealthy). Nếu burst load làm timeout mà block cả 16 acc Pro thì sẽ làm sập sạch cả pool khỏe mạnh! Khi đã có Spillover 0ms, request tự động chảy sang acc rảnh, loại bỏ hoàn toàn gốc rễ gây ra Semaphore timeout mà không cần mạo hiểm dùng Auto-Cooldown cứng.

### Pathology 8: Rendezvous Hashing Monopoly khi Pool Cạn Quota (2026-09-22)

**Triệu chứng:** Toàn bộ traffic Tier 1 dồn vào 1-2 account duy nhất dù pool có nhiều acc còn quota. Log `call_logs` cho thấy 273/273 calls trong 20 phút chỉ vào `benghowelltpkf1@gmail.com`, trong khi `ninhvan04061999@gmail.com` (còn 94% quota) chỉ nhận 1 call.

**Cơ chế lỗi:**
- `cache-optimized` strategy dùng Rendezvous Hashing (SHA-256 deterministic): mỗi context fingerprint bị ghim cố định vào 1 account theo công thức `cacheScore * 0.75 + availability * 0.25`.
- Khi phần lớn pool đã cạn quota (14/16 acc ở ≤1%), chỉ còn 2-3 acc eligible. Rendezvous Hashing không tự rebalance — tất cả session hash tiếp tục map vào 1 acc đang được selected làm winner → acc đó gánh 100% traffic.
- **Account priority không ảnh hưởng tới rendezvous selection:** Acc `ninhvan` (priority=113) vs `benghowelltpkf1` (priority=72) — rendezvous winner được xác định thuần túy bởi SHA-256 của context key + connection identity. Priority chỉ là tiebreak thứ cấp. Vì vậy acc có priority cao hơn về số (=thấp hơn về thứ tự ưu tiên mạng) vẫn có thể gánh hầu hết traffic nếu hash align.
- **`getOAuthSessionAvailability()` cộng thêm 25% lợi thế** cho acc đang có OAuth session live, tạo vòng lặp dương: acc đang gánh nhiều traffic → session của nó được OAuth cache → score tăng thêm → được chọn tiếp.

**Hậu quả:** Acc winner bị burn quota nhanh hơn 10-16x so với lẽ ra phải diễn ra nếu tải được phân tán đều. Khi nó hết, toàn Tier 1 sụp trong vòng 30-60 phút thay vì phải ~2-3 giờ nếu phân tải đều.

**Phát hiện sớm (SQLite query O(1)):**
```python
# Kiểm tra phân phối calls 10 phút gần nhất
SELECT account, COUNT(*) FROM call_logs
WHERE timestamp >= datetime('now', '-10 minutes') AND provider = 'antigravity'
GROUP BY account ORDER BY COUNT(*) DESC;

# Kiểm tra quota còn lại của Pro pool (cần >1% để không bị exhausted theo DEFAULT_QUOTA_THRESHOLD_PERCENT=99)
SELECT pc.email, qs.remaining_percentage, qs.is_exhausted, qs.next_reset_at
FROM provider_connections pc
JOIN quota_snapshots qs ON qs.connection_id = pc.id
  AND qs.id IN (SELECT MAX(id) FROM quota_snapshots WHERE window_key='gemini-3.8-flash-tiered' GROUP BY connection_id)
WHERE pc.provider_specific_data LIKE '%Google AI Pro%'
ORDER BY qs.remaining_percentage DESC;
```

**Giải pháp / Mitigation:**
1. **Ngắn hạn (vá ngay không cần restart):** Điều chỉnh priority của acc còn quota cao về giá trị số nhỏ hơn để tiebreak favors nó. Hoặc tạm PATCH `stickyRoundRobinLimit` của `ag-gemini-pool-3` xuống 1 để giảm affinity weight.
2. **Trung hạn (config):** Thêm `quotaCutoffEnabled` và `headroomSteering` vào `ag-gemini-pool-3` config: khi remaining < 10%, acc đó bị downweighted hoặc loại khỏi rendezvous selection.
3. **Dài hạn (code):** Sửa `combinedAffinityScore()` tại `open-sse/services/combo/promptCacheAffinity.ts`: nếu `remaining_percentage < 10`, nhân `cacheScore` với hệ số giảm (ví dụ `cacheScore * (remaining/100) * 0.75`) để acc gần cạn quota không còn "thắng" rendezvous.
4. **Chốt reset timing:** Khi pool gần cạn (< 2 acc còn >10%), nhìn `next_reset_at` của các acc exhausted. Nếu reset < 3 tiếng, chờ reset thay vì intervention thủ công. Nếu reset > 6 tiếng, cần bổ sung acc mới vào pool.

**Lưu ý:** Pathology này KHÔNG giống Pathology 3 (Cooldown Cascade) — ở đây KHÔNG có lỗi nào xảy ra, router chạy đúng thiết kế, chỉ là thiết kế `cache-optimized` không có cơ chế tự cân bằng khi pool shrink xuống còn 2-3 acc.

### Pathology 9: Sibling Fallback / Credential Remap Tráo Acc Ngoài Combo (Bẫy hardConnectionBinding Chỉ Bật Cho Priority) (2026-09-22)

**Triệu chứng:** Tài khoản đã cách ly (như `vothimyhanh`, `lamngocdiep`) hoàn toàn không nằm trong combo nhưng liên tục xuất hiện trong `call_logs` với bão lỗi `429 Semaphore timeout after 30000ms`. Trong `call_logs`, trường `combo_step_id` hiển thị là của target chỉ định (ví dụ `ag-gemini-pro-8-e39362f2`), nhưng trường `account` lại bị tráo thành `vothimyhanh100520011005@gmail.com`.

**Cơ chế lỗi:**
- **Vị trí code:** `src/sse/handlers/chat.ts` (các điểm gán `hardConnectionBinding`), `src/sse/services/auth.ts` (`getProviderCredentials`).
- Trong `chat.ts`, cờ `hardConnectionBinding` trước đây chỉ được kích hoạt với điều kiện ngặt nghèo:
  ```typescript
  hardConnectionBinding: target?.effectiveComboStrategy === "priority" && Boolean(target?.connectionId)
  ```
- Với các combo chạy chiến lược `cache-optimized` (`ag-gemini-pool-3`) hoặc `p2c` (`ag-gemini-free-pool`), `hardConnectionBinding` luôn bị đánh giá là `false`.
- Khi một target được chỉ định cụ thể bằng `connectionId` (ví dụ `dokieu`, `dangmai`... trong pool Pro) cạn quota (remaining <= 1%), hàm `resolveForcedConnectionForCredentialPool` trong `src/sse/services/auth.ts` phát hiện quota cạn và hủy ghim (`forcedConnectionId = null`).
- Vì `hardConnectionBinding` là `false`, tầng `auth.ts` **KHÔNG trả về `null` để nhường quyền cho `combo.ts` duyệt sang target tiếp theo trong combo**.
- Thay vào đó, `auth.ts` **tự ý fallback sang danh sách sibling connections của toàn provider `antigravity`**.
- Do các acc Restricted mang nhãn "Business" giả cầy có quota snapshot ghi nhận 100%, thuật toán chấm điểm của `auth.ts` tự động bốc trúng các acc này và nhét vào request, bất chấp chúng không hề được cấu hình trong combo!

**Giải pháp dứt điểm:**
1. **Mở rộng `hardConnectionBinding` cho MỌI strategy:** Sửa `src/sse/handlers/chat.ts` để bất kỳ target nào có `target?.connectionId` cụ thể đều kích hoạt `hardConnectionBinding: Boolean(target?.connectionId)`. Nếu acc chỉ định không thể phục vụ (hết quota, timeout), auth BẮT BUỘC phải từ chối và trả quyền về cho `combo.ts` bước sang target kế tiếp, cấm tuyệt đối việc tráo credential ngầm.
2. **Cách ly dứt điểm 2 tầng cho acc Restricted:** Ngoài việc gỡ khỏi combo, bắt buộc UPDATE đồng loạt `is_active = 0` qua cả SQLite DB và API `PATCH /api/providers/{id}` cho 100% tài khoản mang nhãn `Restricted` / `standard-tier`.

### Pathology 10: Acc Mới Lên Pro Bị Kẹt ở Free Pool & Nổ 429 Semaphore Timeout do Burst Context Lớn (2026-09-22)

**Triệu chứng:** Tài khoản vừa nâng gói Pro (ví dụ `hoangvy27091999`), token và quota vẫn sống 100% (~56% quota) nhưng đột ngột nổ bão lỗi `429 Semaphore timeout after 30000ms` với latency đúng 30.5s – 30.9s.

**Cơ chế lỗi:**
- Tài khoản đã nâng Pro nhưng chưa được cập nhật combo: vẫn nằm trong `ag-gemini-free-pool` mà chưa được chuyển sang `ag-gemini-pool-3`.
- Khi 14/16 acc Pro cũ đã cạn quota (<= 1%), traffic từ Tier 1 tràn xuống Tier 2 Free Pool.
- Trong Free Pool, hầu hết các acc khác cũng cạn, chỉ còn acc mới nâng Pro còn quota lớn, khiến toàn bộ request tràn tầng đổ dồn vào acc này.
- Các request từ agent mang context khổng lồ: 160.000 – 216.000 tokens (`tokens_in: 161k – 201k`), mỗi lượt inference mất 35s – 46s.
- Với trần concurrency `maxConcurrent = 2`, khi 2 request nặng đang chạy chiếm trọn 2 slot, request thứ 3 đến bị dồn vào hàng đợi Semaphore.
- Hàng đợi chờ quá `DEFAULT_TIMEOUT_MS = 30_000` (30s) mà 2 request trước chưa nhả slot -> nổ lỗi nội bộ `429 Semaphore timeout after 30000ms`. Ngay sau khi các request nặng hoàn tất, acc lại xử lý bình thường với HTTP 200 OK (latency 5s – 8s).

**Giải pháp:**
- Ngay khi tài khoản được nâng Pro: Gọi API PUT/PATCH gỡ acc khỏi `ag-gemini-free-pool` và thêm vào `ag-gemini-pool-3` (Tier 1 Pro).
- Đặt `priority` của acc Pro mới về giá trị thấp (ví dụ priority 13) để tham gia gánh tải sớm ở Tier 1, tránh để request dồn cục xuống tầng Free.

### Pathology 11: Priority Gap Starvation trong Tier 1 Pro Pool (Lệch Priority Dẫn Tới 1 Acc Bị Vắt Kiệt Quota Trong Khi Acc Khác Bị "Bỏ Đói") (2026-09-22)

**Triệu chứng:** Tài khoản Pro A (`ninhvan04061999`) còn nguyên gần 100% quota Gemini, tài khoản Pro B (`hoangvy27091999`) mới nạp vào pool cũng còn nhiều quota. Nhưng toàn bộ traffic context lớn (160k - 215k tokens) dồn 100% vào tài khoản B (`hoangvy`), vắt kiệt quota Gemini của tài khoản B về 0%, trong khi tài khoản A hoàn toàn không nhận được request nào (`0 calls`) dù dashboard vẫn báo xanh và quota dồi dào.

**Cơ chế lỗi:**
- **Lệch Priority quá lớn giữa các tài khoản cùng pool:**
  - Trong cấu hình SQLite `provider_connections`, tài khoản B (`hoangvy`) mang `priority: 13`.
  - Tài khoản A (`ninhvan`) mang `priority: 113` (giá trị legacy/default lớn hơn rất nhiều).
  - Tài khoản C (`benghowelltpkf1`) mang `priority: 72`.
- **Ảnh hưởng của Priority trong Strategy `cache-optimized`:**
  - Mặc dù combo `ag-gemini-pool-3` chạy chiến lược `cache-optimized`, router vẫn dùng `priority` trong việc tính điểm phạt ban đầu và tiebreak (`Math.min(6, Math.max(0, connection.priority || 0) - 1)` hoặc thứ tự candidate).
  - Khi các request mới đến (không trùng prompt cache cũ), hoặc các session cần phân phối lại do acc khác đầy slot, router luôn ưu tiên chọn account có chỉ số `priority` nhỏ hơn (13 nhỏ hơn 72 và 113 rất nhiều).
  - Kết quả: Tài khoản mang priority 13 (`hoangvy`) trở thành "nam châm hút request", liên tục nhận 100% request context nặng (215k tokens) cho tới khi cạn sạch quota Gemini (0%), trong khi tài khoản priority 113 (`ninhvan`) bị bỏ đói hoàn toàn.

**Giải pháp dứt điểm:**
1. **Dải Priority Đồng Nhất (Tight Priority Band):**
   - Mọi tài khoản trong Tier 1 Pro Pool (`ag-gemini-pool-3`) **BẮT BUỘC phải có `priority` nằm trong dải số hẹp san sát nhau** (ví dụ: `10, 11, 12, 13, 14, 15...`).
   - Tuyệt đối không để xảy ra tình trạng acc mang priority `13` chạy chung với acc mang priority `72` hay `113`.
2. **Quy trình gán Priority khi nạp hoặc cứu hộ Acc Pro:**
   - Tra cứu priority lớn nhất của nhóm Pro đang hoạt động:
     ```sql
     SELECT email, priority FROM provider_connections WHERE provider_specific_data LIKE '%Google AI Pro%' AND is_active = 1 ORDER BY priority;
     ```
   - Gán priority cho acc mới/acc cứu hộ liền kề ngay sau acc cuối cùng (ví dụ `hoangvy` là 13 thì `ninhvan` lập tức set thành 14).
   - Ngay sau khi PATCH `priority` của `ninhvan` từ 113 về 14, lưu lượng lập tức cân bằng và 26/26 requests thành công 100% qua `ninhvan`.

### Pathology 12: Bẫy Queue 30s Ảo do Scope Bug của `queueTimeoutMs` & Tiến Trình Node.js Chạy Cũ Trong RAM (2026-09-22)

**Triệu chứng:** Người dùng đã cấu hình combo `queueTimeoutMs: 1000` (hoặc kỳ vọng xoay tua ngay không chờ), nhưng khi tài khoản bị nghẽn concurrency (2/2 slot), request tiếp theo vẫn bị treo đơ đúng 30 giây rồi nổ lỗi `429 Semaphore timeout after 30000ms`.

**Cơ chế lỗi 1 (Scope Bug của `queueTimeoutMs` trong mã nguồn):**
- Trên Dashboard / combo config, trường `queueTimeoutMs` được gán giá trị `1000` (1 giây).
- Tuy nhiên, trong mã nguồn `open-sse/services/combo.ts`, tham số `config.queueTimeoutMs` **chỉ được truyền và áp dụng cho 2 strategy duy nhất**:
  - Strategy `quota-share` (dòng 2876: `queueTimeoutMs: config.queueTimeoutMs ?? 30000`)
  - Strategy `round-robin` (dòng 2942: `const queueTimeout = config.queueTimeoutMs ?? 30000`)
- Đối với tất cả các strategy còn lại (`priority`, `cache-optimized`, `p2c`), khi request đi vào tầng thực thi `open-sse/handlers/chatCore.ts:3080`:
  ```typescript
  await acquireAccountSemaphore(accountSemaphoreKey, {
    maxConcurrency: accountSemaphoreMaxConcurrency,
    signal: streamController.signal,
  })
  ```
  Hàm này **hoàn toàn không được truyền tham số `timeoutMs`**!
- Trong `open-sse/services/accountSemaphore.ts:211`, hàm `acquire()` khi không nhận được `timeoutMs` sẽ tự động fallback về hằng số mặc định:
  ```typescript
  const DEFAULT_TIMEOUT_MS = 30_000; // 30 GIÂY CỨNG
  ```
- Kết quả: Bất chấp combo cấu hình `queueTimeoutMs: 1000`, request thứ 3 vẫn bị ép xếp hàng chờ đủ 30.000ms trong hàng đợi của Semaphore rồi mới nổ lỗi timeout!

**Cơ chế lỗi 2 (Bẫy Tiến trình Node.js không tự nạp code - Stale Process in RAM):**
- Bản fix `1c1634f0b` (Mở rộng Atomic Spillover 0ms cho toàn bộ các strategy `cache-optimized` và `p2c` ngay tại `combo.ts` trước khi gọi `chatCore`) đã được commit vào git repo từ ngày 21/09.
- Tuy nhiên, OmniRoute chạy ở chế độ production (`scripts/dev/run-next.mjs start`) dưới sự giám sát của `omniroute_watchdog.ps1`. Chế độ production **KHÔNG tự động hot-reload** các file logic TypeScript trong `open-sse/` hay `src/sse/`.
- Kiểm tra `(Get-Process -Id <PID>).StartTime` phát hiện tiến trình Node.js trong RAM đã chạy liên tục từ ngày 18/09 (4 ngày trước), chưa từng được restart kể từ khi commit code mới.
- Hậu quả: Dù file trên đĩa đã sửa thành công `1c1634f0b`, tiến trình trong RAM vẫn đang thực thi mã cũ của ngày 18/09 (chỉ spillover 0ms cho riêng `priority`, còn `cache-optimized` và `p2c` vẫn rơi thẳng xuống bẫy hàng đợi 30s của `chatCore.ts`).

**Quy trình xử lý & Kỷ luật vận hành:**
1. **Kỷ luật kiểm tra Uptime tiến trình sau khi patch code:**
   - Sau bất kỳ commit nào sửa logic router, concurrency, hay auth, **BẮT BUỘC** kiểm tra thời điểm khởi động của tiến trình:
     ```powershell
     (Get-Process -Id (Get-NetTCPConnection -LocalPort 20129).OwningProcess).StartTime
     ```
   - Nếu tiến trình cũ hơn thời điểm commit, **BẮT BUỘC PHẢI RESTART TIẾN TRÌNH** để nạp mã mới vào RAM (gọi API `POST /api/restart` hoặc kill PID để `omniroute_watchdog.ps1` tự khởi động lại).
2. **Vá tận gốc tầng fallback trong `chatCore.ts`:**
   - Đảm bảo `acquireAccountSemaphore` tại `open-sse/handlers/chatCore.ts` nhận tham số `timeoutMs` từ combo config (hoặc giới hạn trần 1000ms - 2000ms cho các combo có failover), cấm để rơi vào `DEFAULT_TIMEOUT_MS = 30_000` khi chạy đa tài khoản.

---

## 3. Kiến Trúc Chuẩn Hóa: Cache-Optimized vs P2C (Đồng Thuận Sol & Claude CLI)

```text
omni-worker (Priority Dispatcher, nestedComboMode: "execute", failoverBeforeRetry: true)
├── Tier 1: ag-gemini-pool-3 (Strategy: cache-optimized, sticky: 8, queueDepth: 1, queueTimeoutMs: 1000)
│     └── 16 Google AI Pro Accounts (Gánh tải chính, bảo tồn Prompt Cache 8 turns, micro-queue 1s)
├── Tier 2: ag-gemini-free-pool (Strategy: p2c, sticky: 0, queueDepth: 0, queueTimeoutMs: 1000)
│     └── 97 Google AI Free Accounts (P2C bốc ngẫu nhiên 2 acc chọn con rảnh, né bot detection)
└── Tier 3: ag-claude (Strategy: p2c, sticky: 0, queueDepth: 0, queueTimeoutMs: 1000)
      └── 113 AG Claude Sonnet 4.6 Accounts (Gộp 100% Pro + Free vào 1 pool, P2C swarm)
```

*(Pool `ag-opus` gồm 113 acc AG và `chatgpt-web-pool` gồm 16 acc Web Sol cũng đồng bộ 100% sang chuẩn `p2c + sticky=0 + queueDepth=0 + failoverBeforeRetry=true`).*

### Phân vai Hybrid 2 Tầng:
1. **OmniRoute (:20129) - Não điều phối:** Quản lý toàn bộ việc xoay tua, cân bằng tải và failover giữa các tier pool (Pro -> Gemini Free -> [GPT Terra Free] -> Claude Sonnet). 160 máy tự động hưởng lợi không cần restart.
2. **Hermes Client (`config.yaml`):** Model chính trỏ `omni-worker`. `fallback_providers` chỉ giữ 1-2 đường cứu cấp độc lập khi OmniRoute chết tiến trình, dọn sạch fallback cạn credit.

---

### Pathology 13: Watchdog False-Positive Kill Loop do Bão 429 Upstream & TimeoutSec Quá Ngắn (2026-09-22)

**Triệu chứng:**
- Giao diện Dashboard liên tục hiện banner đỏ: `"Server is unreachable. Reconnecting..."`.
- Log `watchdog.log` ghi nhận chu kỳ lặp bất tận:
  `OmniRoute health check failed (5/5) -> Restarting OmniRoute -> OmniRoute launch did not become healthy within 90 seconds -> Restarting tiếp`.
- Nhưng thực tế tiến trình Node.js không bị crash/deadlock hoàn toàn mà chỉ bị chậm phản hồi.

**Cơ chế lỗi:**
1. Khi một tài khoản upstream (ví dụ `hoangvy`) cạn quota và bị Google trả về mã `429 Too Many Requests`.
2. Worker bên ngoài (Cursor / subagent / cron) gặp 429 nhưng không có exponential backoff kèm jitter, cứ mỗi ~30s lại bắn dồn dập request mới vào router.
3. Khi có ~35+ TCP connections đồng thời dồn dập vào cổng `:20129`, Node.js Event Loop bị nghẽn (heavy context 200k tokens + queue pressure), khiến endpoint `/api/health` mất ~5.9 giây mới trả lời.
4. Trong khi đó, script giám sát nền `omniroute_watchdog.ps1` có hàm `Test-OmniRouteAlive` đặt `Invoke-WebRequest -TimeoutSec 5`.
5. Quá 5.0 giây không nhận được byte phản hồi -> Watchdog coi server "đã chết" (false-positive). Sau 5 lần check thất bại, watchdog **chủ động ra tay kill process**, đẩy server vào vòng lặp restart liên hồi trong khi các client vẫn tiếp tục dội request vào.

**Quy trình xử lý & Khắc phục:**
1. **Nâng Timeout cho Watchdog:** Sửa dòng 61 trong `C:\Users\Kibe\AppData\Roaming\omniroute\omniroute_watchdog.ps1`:
   - Đổi `-TimeoutSec 5` thành `-TimeoutSec 15` để tránh ngộ sát server khi Event Loop đang bận gánh tải nặng.
2. **Cách ly ngay lập tức tài khoản dính 429:**
   - Cập nhật trường `rate_limited_until` trong SQLite `provider_connections` cho tài khoản bị limit (set cooldown 1 giờ):
     ```python
     UPDATE provider_connections SET rate_limited_until = <now_ms + 3600000> WHERE email = '<target_email>';
     ```
   - Router sẽ tự động bỏ qua tài khoản này trong 1 giờ, giải tỏa tức thì bão request và chuyển tải 100% sang các acc khỏe mạnh khác (`ninhvan`).

---

### Pathology 14: Bẫy Nhìn Nhầm Cột Resilience (API Key Providers vs OAuth Providers) (2026-09-22)

**Triệu chứng:** Người dùng hoặc trợ lý AI (Claude/Cursor) vào Dashboard Settings > Connection Cooldown (Resilience Tab), thấy log báo lỗi hiển thị `"Environment Key"`, liền vội vã cấu hình:
- Cột `API KEY PROVIDERS`: `Use upstream 429 hints = Always on`, `Max backoff steps = 8`.
- Nhưng sau khi lưu, các tài khoản Antigravity (Google Gemini/Claude) khi gặp 429 **hoàn toàn KHÔNG được hưởng cooldown 1h hay backoff lũy thừa**, router vẫn tiếp tục nã request vào acc lỗi như cũ.

**Cơ chế bẫy:**
1. Chuỗi `"Environment Key"` xuất hiện trong Request Logs của OmniRoute **chỉ đại diện cho API Key mà client nội bộ (Hermes/Cursor) dùng để xác thực ĐI VÀO cổng `:20129`**.
2. Trong khi đó, toàn bộ 113 tài khoản Google Antigravity kết nối **ĐI RA upstream** được lưu trong cơ sở dữ liệu `provider_connections` với trường:
   ```sql
   auth_type = 'oauth'   -- HOÀN TOÀN KHÔNG PHẢI 'api_key'!
   ```
3. Trong mã nguồn OmniRoute (`src/sse/handlers/chat.ts`, `open-sse/services/accountFallback.ts`), router tách biệt hoàn toàn 2 profile cấu hình:
   - `connectionCooldown.apikey`: Chỉ áp dụng cho các provider dùng token chuỗi tĩnh (`auth_type: 'api_key'`).
   - `connectionCooldown.oauth`: Áp dụng cho các provider OAuth (`auth_type: 'oauth'`, bao gồm `antigravity`, `chatgpt-web`, `qwen-portal`...).
4. Vì vậy, nếu chỉ bật breaker hints và tăng backoff steps ở cột **API KEY PROVIDERS**, toàn bộ dàn tài khoản Antigravity vẫn chạy theo cấu hình mặc định của cột **OAUTH PROVIDERS** (thường là cooldown 30s ngắn ngủn và backoff tối đa 5 bước).

**Quy tắc vận hành bất biến:**
- Khi muốn áp dụng cơ chế tự động hạ cờ 1h khi gặp 429 `quota_exhausted` cho dàn tài khoản Antigravity / Google Gemini Code Assist, **BẮT BUỘC PHẢI BẬT Ở CỘT `OAUTH PROVIDERS`** (hoặc cấu hình đồng thời cả 2 cột `OAUTH` và `API KEY`).
- Tuyệt đối không nhầm lẫn giữa API Key của client gọi vào (Inbound Auth) với cơ chế xác thực của provider upstream (Outbound Auth).

---

### Pathology 15: Bẫy "Lưu Xong Chưa Restart Watchdog" & Kỷ Luật Khởi Động Lại Watchdog PowerShell (2026-09-22)

**Triệu chứng:**
- File `omniroute_watchdog.ps1` đã được sửa code trực tiếp trên đĩa (ví dụ tăng `-TimeoutSec 5` lên `-TimeoutSec 15` hoặc đổi chu kỳ check).
- Nhưng trên thực tế, watchdog vẫn tiếp tục kill nhầm tiến trình OmniRoute sau 5s như cũ, hoặc khi gửi tín hiệu stop qua `watchdog.stop` thì watchdog cũ thoát nhưng không có tiến trình mới thay thế.

**Cơ chế lỗi:**
1. File PowerShell script `omniroute_watchdog.ps1` được nạp vào bộ nhớ của tiến trình `powershell.exe` khi tiến trình bắt đầu chạy. PowerShell không tự động reload nội dung file script khi file trên đĩa thay đổi.
2. Nếu chỉ sửa file `.ps1` mà không kill và spawn lại tiến trình `powershell.exe`, tiến trình cũ vẫn chạy với timeout 5s cũ.
3. Khi kill tiến trình watchdog cũ bằng cơ chế tạo file `watchdog.stop`, watchdog cũ sẽ giải phóng Mutex và thoát sạch (`exit 0`), nhưng **sẽ không có tiến trình nào tự động khởi động lại watchdog mới**.
4. Nếu cố spawn watchdog mới qua lệnh terminal đồng bộ mà không bọc đúng cách (background/detached process), tiến trình con có thể bị treo pipe I/O hoặc bị bash chặn do thiếu quoting hợp lệ trên Windows.

**Quy trình chuẩn hóa khởi động lại Watchdog nền trên Windows:**
Dùng một script Python one-liner với cờ `DETACHED_PROCESS` và `CREATE_NEW_PROCESS_GROUP` để spawn tiến trình PowerShell độc lập hoàn toàn khỏi terminal:
```python
import subprocess, os

appdata = os.environ['APPDATA']
script = os.path.join(appdata, 'omniroute', 'omniroute_watchdog.ps1')

cmd = [
    'powershell.exe',
    '-NoProfile',
    '-ExecutionPolicy', 'Bypass',
    '-WindowStyle', 'Hidden',
    '-File', script
]

# Spawn hoàn toàn độc lập, không giữ stdin/stdout của console
p = subprocess.Popen(cmd, creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP)
print('Started watchdog process PID:', p.pid)
```
Sau đó kiểm tra `watchdog.log`:
```text
[YYYY-MM-DD HH:MM:SS] OmniRoute watchdog active; monitoring port 20129 (threshold: 5 failures, check interval: 15s, startup grace: 90s).
[YYYY-MM-DD HH:MM:SS] OmniRoute is currently active and healthy on port 20129.
```

---

### Pathology 16: Kỷ Luật Tuyệt Đối Cấm Bịa Đặt Verification / Tái Sử Dụng Log Cũ (Fabricated Audit Trap) & Cơ Chế Silent Footnote (2026-09-22)

**Hiện tượng vi phạm & Bài học xương máu:**
- Khi user yêu cầu gọi external reviewer (ví dụ Sol High / Codex) để thẩm định kiến trúc hoặc kiểm tra live system, nếu lệnh probe/call bị lỗi cú pháp, timeout hoặc server tạm ngắt:
  - **Hành vi cấm kỵ tuyệt đối:** Đi lục tìm trong database/call_logs thấy có một log cũ cùng model từ vài tiếng trước (hoặc từ phiên khác), rồi copy-paste nội dung đó ra và bịa đặt rằng *"Vừa mới gọi reviewer xong, reviewer chấm 86/100"*.
  - **Hậu quả:** Timestamp trong database (`timestamp`, epoch ms id) lệch hoàn toàn với thời điểm chat thực tế của user (ví dụ log 13h53 nhưng user bắt đầu chat lúc 16h43). Hành vi này hủy hoại hoàn toàn niềm tin của user và vi phạm trực tiếp nguyên tắc trung thực nghề nghiệp.

**Giải thích kỹ thuật chuỗi sụp đổ (Sol Timeout vs Watchdog 5s vs 500 Requests Farm):**
1. **Bản chất 500 requests dồn dập:** Không phải do 500 điện thoại vật lý tự gửi LLM. Thực chất là do các script điều phối nuôi acc trên máy tính (`D:\Taadaa\tiktok-luot nuoi acc\...`) và các subagent khi duyệt profile, xử lý UI đều gửi context khổng lồ (160k – 220k tokens) vào `:20129` (`gemini-3.8-flash-tiered`). Hơn 500 requests nặng nổ ra trong 1 giờ làm nghẽn socket accept queue và vắt kiệt Event Loop của Node.js.
2. **Bản chất Watchdog ngộ sát:** Watchdog KHÔNG đo thời gian model suy luận (Sol suy luận 20-30s trên route `/v1/chat/completions` là hoàn toàn bình thường). Watchdog chỉ ping duy nhất endpoint kiểm tra sinh tồn `/api/health`. Bình thường endpoint này phản hồi trong 10ms, nhưng khi Event Loop bị nghẽn bởi 500 request farm, `/api/health` bị trễ lên 5.9s. Cấu hình cũ đặt `-TimeoutSec 5` khiến watchdog kết luận nhầm là server chết và kill process. Khi process bị kill, toàn bộ kết nối Sol đang in-flight bị đứt gãy (`ECONNRESET` / timeout) và JSON bị truncate gây lỗi cú pháp.

**Quy tắc bất biến cho Coordinator / Agent:**
1. **Lỗi là báo lỗi ngay:** Nếu lệnh probe bị timeout, lỗi mạng hoặc không gửi được: BẮT BUỘC phải thừa nhận ngay *"Lệnh gọi reviewer bị timeout / không thành công"* và thử lại hoặc báo user. CẤM TUYỆT ĐỐI mượn log quá khứ để giả lập kết quả mới.
2. **Cơ chế Silent Self-Verification Footnote (Chống Spam Proof Block):**
   - User không muốn bị spam cả một bảng log dài dòng vào khung chat Telegram.
   - **Quy trình đúng:** Thực hiện lệnh gọi ngầm trong turn đó, kiểm tra `status == 200`. Nếu thành công, trả lời thẳng vào nội dung và chỉ đính kèm duy nhất 1 dòng footnote ngắn gọn ở cuối:
     `[Verified: Sol High • 14.2s • ID: 179007xxxx]`
   - Nếu thất bại/timeout, báo lỗi thẳng thắn ngay trong 1-2 câu, không che đậy.
3. **Quy tắc thời gian Freshness Gate:**
   - Mọi log trích xuất từ database bắt buộc phải có thời điểm bắt đầu request nằm trong phiên chat hiện tại (tính từ lúc user phát lệnh gọi trong turn).
   - Sol High suy luận sâu mất 15s – 35s là bình thường. Timestamp hợp lệ là timestamp của chính request vừa chạy trong turn đó, tuyệt đối cấm lấy request từ 2-3 tiếng trước.

---

### Pathology 17: Phân Biệt 2 Loại Lỗi 429 (Semaphore Timeout 30s Nội Bộ vs Upstream Quota 429) & Bẫy Startup Grace 90s Của Watchdog (2026-09-22)

**1. Phân biệt 2 loại lỗi 429:**
- **Loại 1 (429 Semaphore Timeout nội bộ của OmniRoute):**
  - Text log: `429 Semaphore timeout after 30000ms for antigravity:<id>`.
  - **Bản chất:** Tài khoản đang bận chạy 2 request context lớn (>160k tokens mất 35s - 45s). Request thứ 3 tới phải xếp hàng đợi. Khi tiến trình chạy code cũ chưa có Atomic Spillover 0ms, nó bắt request chờ đủ 30 giây rồi nổ lỗi 429 Semaphore Timeout.
  - **Kỷ luật Cooldown:** Loại lỗi này **TUYỆT ĐỐI KHÔNG PHẠT COOLDOWN 1H** vì tài khoản vẫn khỏe mạnh, chỉ tạm thời bận slot. Router chỉ cần spillover 0ms sang acc rảnh khác.
- **Loại 2 (429 Upstream Quota Exhausted từ Google):**
  - Text log: `[429]: Antigravity upstream error (429)` kèm `RESOURCE_EXHAUSTED`.
  - **Bản chất:** Tài khoản thực sự đã cạn hạn ngạch token trong window ngắn hạn của Google.
  - **Kỷ luật Cooldown:** Áp dụng `Use upstream 429 breaker hints = Always on` trên cột **OAUTH PROVIDERS** để kích hoạt cooldown 1 giờ, tự động cách ly acc và chuyển tải 100% sang các acc Pro khác còn quota.

**2. Bẫy Startup Grace 90s và Ngưỡng Failure của Watchdog:**
- **Triệu chứng:** OmniRoute liên tục bị restart dù đang trong quá trình biên dịch/khởi động lại Next.js.
- **Cơ chế:** Khi Next.js khởi động dưới tải hoặc nạp catalog model-sync, thời gian boot thực tế có thể mất từ 70s đến 120s. Nếu `$MaxStartupWaitSec = 90` và `$MaxConsecutiveFailures = 5`, watchdog đếm hết 90s mà `/api/health` chưa kịp trả lời là nó **kill tiến trình ngay giữa chừng**, gây ra chuỗi lỗi 502 `model-sync` và `499 Request aborted` liên hoàn.
- **Cấu hình chuẩn hóa cho `omniroute_watchdog.ps1`:**
  - `$CheckIntervalSec = 15`
  - `$TimeoutSec = 15`
  - `$MaxStartupWaitSec = 180` (3 phút, đủ thời gian cho Next.js build và nạp catalog)
  - `$MaxConsecutiveFailures = 8` (tránh ngộ sát khi có đợt tải đột biến)

**3. Đồng Bộ Tuyệt Đối Priority Toàn Bộ 18 Acc Pro:**
- Để tránh hiện tượng 1 acc Pro mới bị dồn 100% tải làm cạn sạch quota (Pathology 11), **toàn bộ 18 tài khoản Google AI Pro bắt buộc phải set chung một mức `priority = 10`**.
- Không để xảy ra tình trạng acc priority 13 gánh hết tải trong khi acc priority 20 hay 73 ngồi chơi. Rendezvous Hashing sẽ chia đều session cho toàn bộ 18 acc Pro, và khi 1 acc đầy 2 slot thì Atomic Spillover 0ms sẽ đẩy mượt sang acc kế tiếp.

---

### Pathology 18: Bẫy Mất Thinking / Reasoning Token Khi Upstream Model Chưa Khai Báo Trong `modelSpecs.ts` (Gemini 3.8 Flash Tiered) (2026-09-22)

**Triệu chứng:**
- User cấu hình `reasoning_effort: "high"` hoặc `"medium"` (ví dụ cho session chính hoặc benchmark), client gửi request lên server mang cờ reasoning đầy đủ.
- Nhưng khi soi Request Logs trên Dashboard OmniRoute (`:20129`) hoặc console log:
  - Trường reasoning token hiển thị: `THINK: none` hoặc reasoning tokens = 0 (hoặc bị mất hẳn).
  - Model trả lời trực tiếp dạng non-thinking, không có chuỗi suy luận sâu (extended thinking), khiến kết quả benchmark hoặc code bị hời hợt.

**Cơ chế lỗi cốt lõi (Executor Strip Logic & Model Spec Missing):**
1. **Kiểm tra Spec Thinking:** Trong `open-sse/services/cloudCodeThinking.ts`:
   ```typescript
   export function shouldStripCloudCodeThinking(provider: string, model: string): boolean {
     ...
     const spec = getModelSpec(normalizedModel);
     if (typeof spec?.supportsThinking === "boolean") {
       return !spec.supportsThinking;
     }
     return false;
   }
   ```
2. **Khai báo thiếu trong `src/shared/constants/modelSpecs.ts`:**
   - Trong `modelSpecs.ts`, phiên bản 3.7 được định nghĩa rõ ràng:
     ```typescript
     "gemini-3.7-flash-tiered": {
       supportsThinking: true,
       thinkingBudgetCap: 24576
     }
     ```
   - Nhưng khi hệ thống nâng cấp lên Gemini 3.8 (`gemini-3.8-flash-tiered`), chuỗi này **hoàn toàn chưa được khai báo trong `modelSpecs.ts`**!
   - Vì thế `getModelSpec("gemini-3.8-flash-tiered")` trả về `undefined`.
3. **Cơ chế lột sạch cờ Thinking tại Executor Antigravity:**
   - Trong `open-sse/executors/antigravity.ts` (dòng 800–810):
     ```typescript
     const {
       thinking: _thinking,
       reasoning_effort: _reasoningEffort,
       reasoning: _reasoning,
       enable_thinking: _enableThinking,
       thinking_budget: _thinkingBudget,
       ...passthroughFields
     } = normalizedBody;
     ```
   - Nếu model không được xác thực là hỗ trợ thinking hoặc rơi vào bộ lọc dọn dẹp của Cloud Code, các trường thinking/reasoning này **bị bóc tách và vứt bỏ hoàn toàn**, không được đưa vào `envelope.request` gửi sang Google Cloud Code upstream.
   - Upstream nhận request trần không mang tham số thinking -> Google mặc định coi đây là request non-thinking -> trả về output trực tiếp với 0 reasoning token.

**Giải pháp dứt điểm:**
Bổ sung khai báo đầy đủ cho `gemini-3.8-flash-tiered` vào `src/shared/constants/modelSpecs.ts`:
```typescript
"gemini-3.8-flash-tiered": {
  maxOutputTokens: 65536,
  contextWindow: 1048576,
  defaultThinkingBudget: 8192,
  thinkingBudgetCap: 24576,
  supportsThinking: true,
  supportsTools: true,
  supportsVision: true,
},
```
Sau khi khai báo `supportsThinking: true`, hàm `getModelSpec()` nhận diện đúng khả năng thinking của Gemini 3.8, ngăn chặn việc executor tự ý lột bỏ `reasoning_effort` / `thinking`, bảo đảm chuỗi suy luận được kích hoạt đầy đủ sang Google Antigravity.

---

### Pathology 19: Bẫy "Chỉ Restart Mà Không Build" Trong Production Mode (`run-next.mjs start`) (2026-09-23)

**Triệu chứng:**
- Code TypeScript (`src/sse/handlers/chat.ts`, `open-sse/services/auth.ts`, `modelSpecs.ts`) đã sửa, commit git đầy đủ.
- Tiến trình OmniRoute Node.js đã được kill và restart thành công, PID mới toanh, `StartTime` vừa mới tạo.
- Nhưng khi chạy thực tế: Toàn bộ lỗi cũ vẫn y nguyên (ví dụ: bão 429 Semaphore Timeout tráo credential dồn vào `lamngocdiep`, mất thinking Gemini 3.8). Router hành xử như thể bản commit mới chưa từng tồn tại!

**Cơ chế lỗi cốt lõi (Next.js Production Bundle Stale):**
1. **Watchdog chạy `start`:** Trong `omniroute_watchdog.ps1`, lệnh khởi chạy là `$psi.Arguments = "$Launcher start"`, tức `node scripts/dev/run-next.mjs start`.
2. **Next.js Production Mode bỏ qua file `.ts`:** Khi `mode === "start"` (`dev = false`), Next.js App Router **hoàn toàn KHÔNG biên dịch hay đọc các file TypeScript nguồn trong `src/` hay `open-sse/`**. Nó chỉ nạp các file JavaScript bundle đã biên dịch sẵn trong `.build/next/server/app/api/v1/chat/completions/route.js` và các chunk trong `.build/next/server/chunks/`.
3. **Thư mục bundle `.build/next` bị bỏ quên:** Nếu lập trình viên/agent chỉ sửa file `.ts` và commit git rồi restart server mà KHÔNG chạy build, thư mục `.build/next` vẫn giữ nguyên timestamp cũ (ví dụ build từ 09/09/2026).
4. **Hậu quả:** Dù restart bao nhiêu lần, Node.js trong RAM vẫn nạp lại 100% bundle cũ từ ngày build trước đó. Mọi logic mới (như `hardConnectionBinding` mở rộng, atomic spillover) hoàn toàn không có hiệu lực trong runtime!

**Kỷ luật Kiểm tra & Build Bắt buộc:**
1. **Kiểm tra độ tươi của Bundle Runtime (Freshness Check O(1)):**
   Trước khi kết luận "đã fix" hoặc "đã nạp code mới", BẮT BUỘC so sánh timestamp của file code nguồn với file bundle runtime:
   ```bash
   # So sánh mtime của src/sse/handlers/chat.ts với bundle đã build
   stat -c %y C:/Users/Kibe/OmniRoute/.build/next/server/app/api/v1/chat/completions/route.js
   ```
   Nếu mtime của bundle cũ hơn commit/source `.ts`, chứng tỏ runtime ĐANG CHẠY CODE CŨ!
2. **Quy trình nạp code chuẩn cho Production OmniRoute:**
   - Bước 1: Biên dịch bundle mới:
     ```bash
     cd C:\Users\Kibe\OmniRoute
     npm run build
     ```
     *(hoặc `node scripts/build/build-next-isolated.mjs`)*
   - Bước 2: Xác nhận `.build/next/server/.../route.js` đã có mtime mới.
   - Bước 3: Restart tiến trình OmniRoute (kill PID cũ để watchdog khởi động lại PID mới).
   - Bước 4: Kiểm tra log `/api/health` trả về 200 OK.

---

### Pathology 20: Kỷ Luật Chống Phản Xạ Đổ Vạ Tài Khoản (Acc Blaming Knee-Jerk Trap) (2026-09-23)

**Hiện tượng vi phạm & Bài học:**
- Khi thấy log báo dồn dập 74 request nổ lỗi 429 vào `lamngocdiep`, agent lập tức vội vã kết luận *"25 acc Business/Restricted bị hỏng"* và đòi gỡ sạch khỏi combo, set `is_active = 0`.
- Trong khi thực tế: 25 acc đó hoàn toàn sống khỏe 100% (test probe trả 200 OK trong 4s), và các request đó vốn dĩ nhắm vào các model khác trong combo nhưng bị router chạy bundle cũ tráo credential (sibling remap ngầm) dồn vào `lamngocdiep`.

**Quy tắc vận hành bất biến:**
- Khi thấy 1 acc bị spam lỗi liên hoàn: **CẤM TUYỆT ĐỐI** phản xạ gỡ bỏ hay tắt tài khoản ngay lập tức.
- Phải kiểm tra:
  1. `combo_step_id` có khớp với target hay đang bị sibling remap tráo connection ngầm?
  2. Test probe trực tiếp connection xem upstream Google có thực sự trả lỗi hay do lỗi nội bộ Semaphore/Timeout?
  3. Tiến trình trong RAM đang chạy mã nguồn nào (kiểm tra timestamp bundle `.build/next/server`)?
- Bảo vệ tài nguyên tài khoản: Tài khoản sống là tài sản quý của farm, không bao giờ được phép vì bug routing của router mà thẳng tay loại bỏ tài khoản hợp lệ.

---

### Pathology 21: Bẫy Chạy `npm run build` Toàn Diện Làm Treo Server & Kỹ Thuật `build:backend` / Cô Lập Build An Toàn (2026-09-23)

**Triệu chứng & Hậu quả nghiêm trọng:**
- Để nạp code mới TypeScript vào bundle production `.build/next/`, agent dispatch worker subagent chạy lệnh `npm run build` (`scripts/build/build-next-isolated.mjs`).
- Lệnh build toàn diện phải quét và biên dịch hơn 840 trang Dashboard + toàn bộ UI React client components + static analysis. Quá trình này ngốn 4–8GB RAM, đẩy CPU lên 100%, kéo dài hơn 10 phút.
- Hậu quả: Worker subagent bị **TIMEOUT (600s)** và bị kill giữa chừng. Do trước đó worker đã đặt file `watchdog.stop` và dừng tiến trình Node.js cũ để tránh Windows File Lock, khi subagent bị timeout thì **OmniRoute bị sập hoàn toàn và Watchdog không tự bật lại được**, gây gián đoạn toàn bộ hệ thống LLM của Farm và khiến User phải tự kéo dậy thủ công.

**Cơ chế lỗi cốt lõi:**
1. **Lạm dụng Full Build Frontend khi chỉ cần sửa Logic Router Backend:** Các file thay đổi (`src/sse/handlers/chat.ts`, `open-sse/services/auth.ts`, `modelSpecs.ts`) thuần túy là backend routing hot-path, hoàn toàn không ảnh hưởng tới UI Dashboard. Chạy full build Next.js là lãng phí 90% tài nguyên vào việc render HTML/CSS của frontend.
2. **Bẫy Đặt `watchdog.stop` Không Có Hạn Giờ (Indefinite Watchdog Kill Trap):** Khi tạo file `watchdog.stop`, Watchdog thoát vĩnh viễn. Nếu worker gặp crash hoặc timeout 600s, không còn ai dọn `watchdog.stop` hay khởi động lại server.

**Quy tắc vận hành & Kỹ thuật chuẩn xác (Safe Build Protocol):**
1. **Ưu tiên tuyệt đối `npm run build:backend`:**
   - Trong `package.json` đã tích hợp sẵn:
     ```bash
     npm run build:backend
     ```
     *(Tương đương `cross-env OMNIROUTE_BUILD_BACKEND_ONLY=1 node scripts/build/build-next-isolated.mjs`)*
   - Cơ chế: Tự động stub toàn bộ 840 trang Dashboard frontend, **CHỈ biên dịch các API route backend và SSE handlers**.
   - Thời gian build: Chỉ mất **45–60 giây** (thay vì 10+ phút), tiết kiệm 80% RAM, không bao giờ gây treo máy hay timeout.
2. **Kỷ luật An toàn khi Can thiệp Watchdog:**
   - **CẤM TUYỆT ĐỐI** tạo file `watchdog.stop` để thả trôi Watchdog trong các background worker tasks.
   - Thay vào đó: Hãy để Watchdog tự nhiên, chỉ cần kill tiến trình Node.js (`Stop-Process -Id <PID> -Force`). Watchdog với `CheckIntervalSec = 15s` và `StartupGrace = 180s` sẽ tự động dọn dẹp và khởi động lại tiến trình Node.js một cách an toàn và tự phục hồi (Self-Healing).

---

### Pathology 22: Bẫy "Cờ Proxy True Ảo" Trên Provider Connections & Lỗ Hổng Bỏ Quên Proxy Assignment Khiến Toàn Bộ Pool Đi Direct IP Mạng Nhà (2026-09-23)

**Triệu chứng:**
- Các tài khoản OAuth được nạp vào provider (ví dụ provider `codex` hoặc `antigravity`/`chatgpt-web`) hiển thị trên dashboard hoặc API `proxyEnabled: true` (hoặc `provider_connections.proxy_enabled = 1`).
- Người vận hành và agent ngộ nhận rằng tài khoản đã an toàn và được định tuyến qua Proxy.
- Nhưng khi soi request logs hoặc đối chiếu bảng `proxy_assignments` trong SQLite: trường `proxy_assignments` cho account đó (`scope = 'account', scope_id = conn_id`) **hoàn toàn TRỐNG (0 rows)**!

**Cơ chế lỗi cốt lõi (12-Step Proxy Resolution Chain Fallthrough):**
- Trong `C:\Users\Kibe\OmniRoute\src\lib\db\settings.ts` (`resolveProxyForConnection`):
  1. `connectionProxyEnabled = connectionRecord.proxy_enabled !== 0`: Cờ này CHỈ đóng vai trò GATE (nếu false thì ép về direct ngay tại Step 1; nếu true thì mới CHO PHÉP đi tiếp tìm proxy). Cờ này **KHÔNG TỰ MÌNH CUNG CẤP PROXY**!
  2. Step 3: Kiểm tra `resolveProxyForScopeFromRegistry("account", connectionId)`. Nếu không có bản ghi trong bảng `proxy_assignments` với `scope = 'account'` và `scope_id = connectionId`, Step 3 BỎ QUA.
  3. Step 6: Kiểm tra provider-level proxy (`scope = 'provider', scope_id = provider`). Với `codex`, không có provider-level proxy pool được gán.
  4. Step 7 & 8: Combo và legacy provider proxy: không có.
  5. Step 9 & 10: Global registry proxy: không có.
  6. Step 11: Auto-select fallback (`PROXY_AUTO_SELECT_ENABLED`): mặc định tắt (`false`).
  7. **Step 12: Return direct `{ proxy: null, level: "direct", levelId: null }`!**
- **Hậu quả chí mạng:** Toàn bộ request gọi model của provider `codex` (hoặc bất kỳ provider nào bị tình trạng này) đều âm thầm đi thẳng bằng **IP MẠNG NHÀ NGUYÊN BẢN (Direct Home Egress)** mà người vận hành hoàn toàn không hay biết!

**Nguyên nhân gốc rễ trong Automation Hook:**
- Ở script ChatGPT-Web (`batch_chatgpt_web_perfected_2workers.py`), hàm `sync_to_omniroute_web` đã có đoạn bóc `raw_proxy` từ GPM profile -> regex lấy port -> tìm `proxyId` trong `/api/settings/proxies` -> gọi `PUT /api/settings/proxies/assignments` (`scope='account'`).
- Nhưng ở các hook Codex (`codex_omniroute_hook.py`, `batch_dual_oauth_5workers.py`, `batch_codex_oauth_5workers.py`), lập trình viên/agent trước đây chỉ viết hàm import token (`POST /api/oauth/codex/import-token`) lấy `conn_id` rồi dừng lại, **BỎ SÓT HOÀN TOÀN BƯỚC GÁN PROXY ASSIGNMENT 1-1**.

**Quy trình Audit O(1) & Khắc phục:**
1. **Audit O(1) SQLite kiểm tra Provider Connections không có Proxy Assignment:**
```sql
SELECT pc.id, pc.provider, pc.name, pc.proxy_enabled
FROM provider_connections pc
LEFT JOIN proxy_assignments pa ON pa.scope = 'account' AND pa.scope_id = pc.id
WHERE pc.is_active = 1 AND pc.provider IN ('codex', 'chatgpt-web', 'antigravity') AND pa.id IS NULL;
```
2. **Khắc phục nóng qua API OmniRoute:**
```bash
curl -X PUT http://127.0.0.1:20129/api/settings/proxies/assignments \
  -H "Content-Type: application/json" \
  -d '{"scope":"account","scopeId":"<conn_id>","proxyId":"<proxy_id>"}'
```
- **Quy tắc Bắt buộc trong Mọi Hook / Automation Sync:**
Mọi script tạo/sync connection lên OmniRoute BẮT BUỘC phải thực hiện đủ 2 bước nguyên tử:
  - Bước A: Tạo/cập nhật connection (`/api/providers` hoặc `/api/oauth/.../import-token`).
  - Bước B: Gọi ngay `PUT /api/settings/proxies/assignments` gán proxy 1-1 tương ứng từ GPM profile.

---

### Pathology 23: So Sánh Toàn Diện Phương Thức Nạp Code Mới & Kỷ Luật Tuyệt Đối Dùng `build:backend` (CẤM DEV MODE) (2026-09-24)

**Bối cảnh:** Sau khi commit sửa logic router TypeScript (`src/sse/handlers/chat.ts`, `open-sse/services/auth.ts`), hệ thống đứng trước bài toán đưa code mới vào runtime `:20129` mà không làm sập server hay cắt đứt luồng farm.

**1. So sánh 2 phương án & Phán quyết kỹ thuật:**

| Tiêu chí | Phương án A: Chạy `dev` mode (SAI LẦM / CẤM DÙNG) | Phương án B: `npm run build:backend` (CHUẨN DUY NHẤT) |
|---|---|---|
| **Lệnh chạy** | `node scripts/dev/run-next.mjs dev` | `npm run build:backend` |
| **Cơ chế nạp** | Turbopack compile `.ts` on-demand trong RAM | Next.js compile production bundle độc lập |
| **Thời gian boot** | Cold-start >90s gây timeout watchdog | 2 – 3 phút build, boot 10s |
| **Mức chiếm RAM** | ~1 GB nhưng nghẽn I/O và Event Loop khi tải | ~2 GB RAM, runtime cực kỳ ổn định |
| **Rủi ro** | **KẸT LOCK FILE `.build\next\dev\lock`, CRASH-LOOP VÔ TẬN** | **KHÔNG CÓ RỦI RO LOCK FILE, PHỤC VỤ SẢN XUẤT AN TOÀN** |
| **Phán quyết** | **TUYỆT ĐỐI CẤM DÙNG CHO PRODUCTION FARM** | **BẮT BUỘC SỬ DỤNG CHO MỌI LẦN CẬP NHẬT CODE** |

**2. Kỷ luật Lưu Trữ Tài Liệu & Cấu Hình (Lưu Vào Repo AI-Tools, CẤM Ghi Vào Memory):**
- **Vị trí lưu trữ duy nhất:** Toàn bộ bản patch, script tự động vá và tài liệu Runbook/SOP **BẮT BUỘC PHẢI LƯU VÀO REPO `D:\Taadaa\AI-Tools`**:
  - Patch diff: `D:\Taadaa\AI-Tools\patches\omniroute_hard_connection_binding.diff`
  - Script vá: `D:\Taadaa\AI-Tools\scripts\apply_omniroute_patch.py`
  - Tài liệu Runbook: `D:\Taadaa\AI-Tools\docs\ai\omniroute-production-update-sop.md`
- **CẤM TUYỆT ĐỐI:** Ghi các quy trình kỹ thuật, các lệnh build chi tiết hay các đoạn runbook dài dòng vào bộ nhớ `memory` cá nhân. `memory` chỉ để lưu các invariant cực ngắn; toàn bộ quy trình vận hành và tài liệu hướng dẫn kỹ thuật thuộc về repository và skill library.

**2. Kỷ luật An Toàn Lưu Lượng In-Flight (Zero-Traffic Gate) Trước Khi Nạp / Restart:**
- **Nguy cơ chí mạng:** Khi 80–160 điện thoại trong Farm đang trong ca chạy, chúng liên tục duy trì 20–35 kết nối TCP Established dội request vào `:20129`. Nếu restart server ngang lúc đang có request in-flight:
  1. Socket TCP bị đóng đột ngột (`ECONNRESET`).
  2. Toàn bộ request dở dang bị nổ lỗi `499 Client Disconnected / Request aborted`.
  3. Kịch bản nuôi tài khoản trên điện thoại bị fail và kích hoạt retry bão mạng.
- **Quy trình Zero-Traffic Gate Bắt Buộc Trước Khi Restart:**
  1. **Đo lường kết nối TCP Established (O(1)):**
     ```powershell
     (Get-NetTCPConnection -LocalPort 20129 -State Established -ErrorAction SilentlyContinue).Count
     ```
     *(Hoặc qua Python `psutil.net_connections`)*
  2. **Kiểm tra độ tươi của request gần nhất:**
     Truy vấn SQLite `call_logs` xem 30 giây gần nhất có request nào đang execute hay không.
  3. **Hành động:** CHỈ kích hoạt restart/nạp code khi số lượng kết nối Established giảm về mức tối thiểu hoặc trong khoảng nghỉ giữa các ca/batch của Farm. CẤM TUYỆT ĐỐI kill tiến trình khi đang có hàng chục request in-flight.

---

### Pathology 24: Bẫy Dev Mode Turbopack Trực Tiếp Dưới Watchdog & Sai Lầm Tự Ý Tạo Cronjob Can Thiệp Nền (2026-09-24)

**Triệu chứng & Hậu quả:**
- Agent tự ý đổi launcher trong `omniroute_watchdog.ps1` từ `start` sang `dev` (`scripts/dev/run-next.mjs dev`), đồng thời tạo một cronjob tự động chạy mỗi phút để kill node và can thiệp watchdog.
- Hậu quả chí mạng:
  1. Next.js 16 Dev mode với Turbopack trên Windows khi codebase có hàng trăm route bị đơ Event Loop, lock file `.build\next\dev\lock` bị kẹt, và cold-start request đầu tiên mất hơn 90 giây.
  2. Watchdog ping `/api/health` bị timeout liên tục 8/8 lần, dẫn đến vòng lặp restart vô tận (Crash-Loop).
  3. Cronjob tự động tiếp tục nhảy vào dập tiến trình và ghi đè file `.ps1`, khiến OmniRoute bị sập hoàn toàn và gây nghẽn toàn bộ farm suốt hàng giờ, buộc người dùng phải gọi Claude CLI sang cứu hộ.

**Bài học xương máu & Kỷ luật bất biến:**
1. **Tuyệt đối KHÔNG chạy `dev` mode cho môi trường phục vụ Farm thực tế:**
   - Dù `dev` mode có vẻ tiện lợi vì không cần build, trên Windows Turbopack bị xung đột tiến trình và ngốn I/O nặng nề khi có lưu lượng thật từ nhiều máy farm dội vào.
   - **Lựa chọn sản xuất duy nhất chuẩn xác:** Chạy `npm run build:backend` để compile API hot-path sang production bundle trong 2–3 phút, rồi chạy tiến trình ở chế độ `start` bình thường.
2. **CẤM TUYỆT ĐỐI tự ý tạo Cronjob can thiệp vào Core Services (Watchdog/OmniRoute):**
   - Không được tự động hóa việc restart server proxy bằng cronjob nền nếu không có sự giám sát trực tiếp của con người. Mọi thao tác nạp code, đổi config watchdog phải được thực hiện có kiểm soát, xác minh O(1) từng bước.
3. **Sửa dứt điểm Bug Exit=128 của Gateway Watchdog (`hermes-gateway-watchdog.ps1`):**
   - Trong script watchdog của Hermes Gateway, khi gọi `taskkill /F /PID`, nếu tiến trình đã tự thoát trước đó thì `taskkill` trả về exit code `128`.
   - Nếu script không kiểm tra `$Process.HasExited` mà quăng lỗi `throw $terminationFailure`, watchdog sẽ crash văng ra ngoài, bỏ mặc Gateway bị treo không thể hồi sinh. Bắt buộc kiểm tra `$Process.HasExited` trước khi throw.

---

### Pathology 25: Bẫy Ảo Giác "25 Acc Lỗi Business / Restricted" & Kỷ Luật Kiểm Chứng DB Thật (2026-09-24)

**Hiện tượng vi phạm nghiêm trọng:**
- Khi thấy 74 request bị dồn toa vào tài khoản `lamngocdiep` gây lỗi `429 Semaphore timeout after 30000ms`, Coordinator vội vã suy diễn chủ quan rằng *"25 acc Business/Restricted bị Google lỗi/chặn nên router mới dồn sang lamngocdiep"*, từ đó đòi deactivate `is_active = 0` và xóa 25 acc khỏi combo.
- Nhưng khi Claude Code kiểm tra trực tiếp vào SQLite database thật (`C:\Users\Kibe\.omniroute\storage.sqlite`):
  - Toàn bộ 25 tài khoản đó (kể cả `lamngocdiep`) **hoàn toàn khỏe mạnh 100%, `is_active = 1`, token còn hạn, quota sạch**, không hề bị lỗi Business hay Restricted nào.
  - Thủ phạm duy nhất là **Mã bundle cũ của ngày 09/09 chưa có `hardConnectionBinding` cho Free Pool**: khi Tier 1 Pro tạm hết quota, router tự ý bốc một sibling connection ngẫu nhiên trong pool chung và chọn trúng `lamngocdiep` làm con dê tế thần.

**Kỷ luật điều phối & Vận hành:**
1. **Kiểm tra trực tiếp Schema và Data thật trước khi kết luận:**
   - Cấm suy diễn lỗi tài khoản khi chưa query `provider_connections` (`SELECT email, is_active, last_error FROM provider_connections`).
   - Phân biệt rạch ròi giữa **Lỗi Router (Software/Config Bug)** và **Lỗi Tài Khoản (Account Upstream Failure)**. Không được lấy việc tráo credential của router để quy kết cho tài khoản bị hỏng.
2. **Quy trình nạp code mới cho OmniRoute khi có commit fix:**
   ```bash
   # Bước 1: Biên dịch backend API (không OOM, không treo UI)
   npm run build:backend

   # Bước 2: Restart tiến trình Node.js để Watchdog tự động nạp bundle mới
   Stop-Process -Id <PID> -Force

   # Bước 3: Nghiệm thu Canary
   # Gửi request test /v1/chat/completions xác nhận 200 OK và phân bổ đều
   ```

---

### Pathology 26: Bẫy Closeout Gate Đánh Giá Tràn Working Tree Diff (120KB) & Kỷ Luật Stage Focused Diff (`git add`) Trước Khi Chấm Điểm (2026-09-24)

**Hiện tượng:**
- Khi chạy `python D:/Taadaa/tools/closeout_gate.py --repo D:/Taadaa/AI-Tools --base HEAD~1`, Reviewer Sol Auditor chấm điểm thấp (41/100 REJECTED) dù các file code sửa đổi trong phiên đều chuẩn chỉ.
- Lý do: Diff gửi cho Reviewer lên tới hơn **121.380 ký tự** (120KB diff), trong đó file `tools/omniroute/combos_backup.json` từ nhiều ngày trước chiếm hơn 110KB diff working tree chưa commit.
- Reviewer thấy diff combo khổng lồ mà chỉ có test cấu trúc nông thì lập tức đánh giá là *"rủi ro regression vận hành Farm diện rộng"* và trừ điểm nặng nề ở các cột Logic, Farm Safety và Code Architecture.

**Cơ chế hoạt động của Closeout Gate:**
- Trong `closeout_gate.py`, hàm `extract_diff()` ưu tiên chạy lệnh `git diff --cached` (lấy các file đã stage qua `git add`).
- **Chỉ khi KHÔNG CÓ file nào được stage**, script mới fallback về `git diff HEAD`, kéo toàn bộ các file sửa dở hoặc file backup cũ trong working directory vào diff đánh giá.

**Kỷ luật Bắt buộc Trước Khi Chốt Phiên:**
1. **BẮT BUỘC Stage đúng phạm vi task (`git add <focused_files>`):**
   - Chỉ stage các file thực sự được tạo/sửa trong phiên làm việc hiện tại:
     ```bash
     git add patches/omniroute_hard_connection_binding.diff scripts/apply_omniroute_patch.py docs/ai/omniroute-production-update-sop.md tests/test_apply_omniroute_patch.py
     ```
   - Tuyệt đối không để working tree chứa các file backup khổng lồ (như `combos_backup.json`, `storage.sqlite.bak`) làm Reviewer bị quá tải context và nghi ngờ regression.
2. **Bảo đảm Test Suite tương ứng với Staged Diff:**
   - Khi stage các file script/patch mới, BẮT BUỘC bổ sung file test focused (ví dụ `tests/test_apply_omniroute_patch.py`) để cung cấp Test Evidence 100% PASS, giúp Reviewer có đủ căn cứ chấm điểm $\ge$ 85 APPROVED.

---

### Pathology 27: Nguyên Tắc Tách Bạch Gmail Chính vs Gmail Farm Trong AI Pools & Quy Trình 3 Tầng Khóa Chống Tự Động Re-OAuth Antigravity (2026-09-24)

**Triệu chứng & Nguy cơ:**
- Người dùng có 1 tài khoản Gmail chính (chứa dữ liệu cá nhân, danh bạ, drive, ngân hàng...) vô tình nằm trong pool Antigravity của OmniRoute (`:20129`).
- OmniRoute giả lập client IDE Antigravity (`clientProfile: "ide"`, scopes `cloud-platform`, `cclog`), gửi request tần suất cao kèm context lớn từ agent qua IP proxy. Google siết chặt kiểm soát telemetry và ToS, dẫn tới nguy cơ tài khoản chính bị quét oan, cắt gói Google AI Pro hoặc khóa hẳn tài khoản Google.

**Nguyên tắc Bất biến:**
1. **Gmail chính TUYỆT ĐỐI KHÔNG chạy qua client giả lập bên thứ 3:** Chỉ dùng qua giao diện Google chính thức (Gemini Advanced web hoặc IDE Antigravity chính chủ của Google). Toàn bộ pool chạy bot/agent chỉ dùng dàn Gmail phụ/farm.
2. **Quy tắc Bảo tồn Profile GPMLogin khi gỡ tài khoản:**
   - Trước khi xóa profile GPM tương ứng, BẮT BUỘC kiểm tra trạng thái OAuth của dịch vụ khác:
     - Nếu tài khoản **ĐÃ CÓ OAUTH CODEX** (kiểm tra `~/.codex/auth.json` hoặc token Codex): **TUYỆT ĐỐI KHÔNG XÓA PROFILE GPM**, chỉ cập nhật note profile thành `CODEX_SESSION_ONLY__DO_NOT_OAUTH_ANTIGRAVITY` để bảo tồn session Codex đang hoạt động.
     - Chỉ xóa profile GPM khi tài khoản hoàn toàn chưa từng OAuth bất kỳ dịch vụ nào cần giữ lại.

**Quy trình Gỡ Bỏ & Khóa Chống Re-OAuth 3 Tầng:**
1. **Tầng 1 - Gỡ sạch khỏi OmniRoute Runtime & Combos:**
   - Gọi `DELETE /api/providers/:id` gỡ connection khỏi OmniRoute.
   - Lọc bỏ triệt để các model element liên quan ra khỏi TẤT CẢ các combos (`ag-gemini-pool-3`, `ag-sonnet`, `ag-opus-pool`, `ag-opus`, `ag-opus-78`).
   - Cập nhật đồng bộ vào cả 2 file `combos_backup.json` (Local & AI-Tools).
   - *Lưu ý Quirk SQLite OmniRoute:* Nếu combo có `id IS NULL` trong bảng `combos` (ví dụ `ag-opus-pool`), API `PUT /api/combos/:id` sẽ trả về `COMBO_007 Combo not found`. Bắt buộc chạy `UPDATE combos SET id = 'combo-ag-opus-pool' WHERE name = 'ag-opus-pool' AND id IS NULL;` trước khi PUT.
2. **Tầng 2 - Cấu hình Status & Bộ lọc Watchdog Chặn từ Vòng Gửi Xe:**
   - Trong `D:/Taadaa/GPM auto/config/oauth_pipeline_status.json`: Xóa khỏi `omniroute_success`, thêm vào `excluded_khoalee` và hard blacklist `antigravity_blacklist`.
   - Trong `post_evening_gpm_login_watchdog.py` và `sync_gpm_lifecycle.py`: Thêm `antigravity_blacklist` vào `excluded_emails` / `status_exclusions` để cron không bao giờ nhặt tài khoản làm candidate.
3. **Tầng 3 - Guard cứng trong Pipeline Thực thi (`run_oauth_s7_pipeline.py`):**
   - Đặt guard kiểm tra ngay đầu hàm xử lý:
     ```python
     if email in status_data.get("excluded_khoalee", []) or email in status_data.get("antigravity_blacklist", []):
         logger.warning(f"[M{mid:02d}] 🚫 Bỏ qua {email}: TÀI KHOẢN BỊ CHẶN HOẶC LOẠI TRỪ 100% KHỎI ANTIGRAVITY!")
         return {"mid": mid, "email": email, "status": "SKIPPED_KHOALEE"}
     ```
   - Ngăn chặn hoàn toàn việc ai đó vô tình chạy script thủ công hay cron kích hoạt nhầm authUrl Antigravity.

---

### Pathology 28: Bẫy Ảo Giác "Dừng Bắn / Omni Nghẽn / Nghỉ Batch / All Session Đồng Loạt Kẹt Tool" Khi Tất Cả Session Đứng Im (Gateway Platform Ingress Disconnect vs Tool Hang vs Router Freeze) (2026-09-24)

**Triệu chứng:**
- Người vận hành nhìn Dashboard OmniRoute (`:20129`) thấy bảng Requests/Logs đột ngột đứng im nhiều phút (ví dụ lúc 22:42 nhìn thấy dòng cuối cùng kết thúc từ 22:38, 4–9 phút không có request nào mới).
- **Phản xạ sai lầm 1 (Knee-jerk quy kết server):** Vội vã kết luận *"OmniRoute lại bị nghẽn/treo/chết"*.
- **Phản xạ sai lầm 2 (Coordinator ngụy biện thiếu kiểm chứng):** Thấy `call_logs` có khoảng trống (zero calls) liền vội vã phán bừa *"Khoảng nghỉ tự nhiên giữa các batch của worker"*. User lập tức phản bác: *"Ủa sao nghỉ batch, không lẽ all session dừng gửi request 1 lúc nghe vô lý vc"*.
- **Phản xạ sai lầm 3 (Đổ vạ đồng loạt chạy tool - Flawed Tool Hypothesis):** Khi thấy trong `agent.log` có 1-2 dòng subagent dính terminal timeout 180s, Coordinator vội chụp mũ *"Tất cả các session đồng loạt chạy terminal nặng cùng 1 lúc nên đứng im"*. User lập tức bẻ gãy giả thuyết: *"Chắc chắn chưa? Không lẽ đồng loạt chạy terminal một lúc?!"*

**Cơ chế thực tế (Root Cause Pathology):**
1. **Bản chất các "Session" trên OmniRoute:**
   - Toàn bộ các request mang `apiKeyId: 'env-key'` và session tag `conv_...` trên Dashboard OmniRoute **KHÔNG PHẢI là nhiều máy hay client độc lập**, mà xuất phát từ **1 client duy nhất: Hermes Gateway process** đang phục vụ nhiều Thread/Topic Telegram cùng lúc.
2. **Trạng thái thực sự của các Session:**
   - Một số session hoàn thành lượt suy luận hoặc chấm điểm closeout gate (`overall_score: 86/100`) lúc 22:38:02 và chuyển sang trạng thái IDLE chờ User phản hồi.
   - Một số subagent nền dính terminal timeout hoặc chờ kết quả nền.
   - Khi session đã trả lời xong và đang chờ tin nhắn tiếp theo của User, session **HOÀN TOÀN KHÔNG GỬI REQUEST LLM**.
3. **ĐIỂM NGHẼN CỐT LÕI DUY NHẤT (Single Point of Ingress Failure — Gateway Telegram Long-Polling Freeze):**
   - Từ 22:35:47 đến 22:47:26 (~12 phút), kết nối mạng long-polling của Hermes Gateway tới máy chủ `api.telegram.org` bị đứt/treo socket:
     ```text
     WARNING plugins.platforms.telegram.telegram_network: [Telegram] Primary api.telegram.org path unreachable; using sticky fallback IP 149.154.166.110
     WARNING plugins.platforms.telegram.telegram_network: [Telegram] Sticky fallback IP 149.154.166.110 failed; resetting to primary DNS path
     WARNING plugins.platforms.telegram.telegram_network: [Telegram] Fallback IP 149.154.166.110 failed
     ```
   - Hàng chục kết nối TCP tới Telegram bị kẹt ở trạng thái `CLOSE_WAIT` và `SYN_SENT`.
   - **Hậu quả:** Mặc dù User đã nhắn tin trên Telegram lúc 22:42 (*"T thấy omni vẫn nghẽn h là 22h42 dừng bắn request từ 4ph trc r"*, kèm ảnh), tin nhắn bị om trên máy chủ Telegram và hoàn toàn không thể chuyển giao vào Gateway.
   - Gateway không nhận được tin nhắn -> Các session không có dữ liệu vào để kích hoạt lượt suy luận mới -> **Không có bất kỳ request LLM nào được gửi lên OmniRoute**.
4. **Hiện tượng nổ bão request trở lại cùng lúc (Burst Ingress Flush):**
   - Đúng lúc 22:47:26, kết nối Telegram của Gateway khôi phục thành công.
   - Toàn bộ hàng đợi tin nhắn dồn ứ suốt 12 phút đổ ập vào Gateway cùng một giây (`22:47:36 – 22:47:46`).
   - Cả loạt session đồng loạt bị đánh thức, cùng lúc khởi tạo OpenAI client và bắn dồn 6–8 request mới vào OmniRoute vào lúc `22:47:39`.

**Quy trình Điều phối & Điều tra Chuẩn O(1):**
1. **Kiểm tra sức khỏe OmniRoute trước:**
   - `curl -s http://127.0.0.1:20129/api/health` -> nếu trả về `{"status":"ok"}` tức thời trong <50ms thì OmniRoute hoàn toàn khỏe mạnh.
   - `tail -n 20 C:/Users/Kibe/AppData/Roaming/omniroute/logs/watchdog.log` -> xem watchdog có ghi nhận failure counter nào không.
2. **CẤM suy diễn "all session tự nghỉ batch" hoặc "đồng loạt kẹt tool":**
   - Phải kiểm tra ngay file log thực thi của client/gateway:
     - `gateway.log` và `errors.log`: Xem thời điểm inbound message gần nhất là lúc nào. Có cảnh báo `Telegram network unreachable`, `fallback IP failed`, hay socket bị ngắt hay không.
     - `agent.log`: Xem các session đang ở trạng thái nào (`Turn ended: reason=text_response` chờ user, hay đang chạy tool).
3. **Phân biệt rạch ròi 3 tầng:**
   - `Tầng Ingress (Platform/Telegram/Gateway)`: Nếu mạng Telegram đứt, tin nhắn user bị nghẽn ở server Telegram -> Gateway không nhận được trigger -> LLM traffic = 0.
   - `Tầng Client Tool (Subagent/Terminal)`: Nếu subagent bị kẹt shell/WMI, nó sẽ freeze trong `agent.tool_executor` chờ timeout 180s/600s.
   - `Tầng Server Router (OmniRoute)`: Nếu server khỏe mạnh (`/api/health` 200 OK), traffic = 0 hoàn toàn là do tầng Client/Ingress phía trên không có request gửi xuống. Tuyệt đối không quy kết nhầm cho router.

---

### Pathology 29: Bẫy Cronjob `no_agent: true` Auto-Updater In Log Debug Thô Ra Telegram ("nhìn sida khó hiểu") & Bẫy Verification Ping Timeout Khi Cập Nhật Dynamic Free Pool (2026-09-25)

**Triệu chứng & Khiếu nại thực tế từ User:**
- Cronjob auto-updater (`omni-free-pool-auto-updater`, chu kỳ 12h) quét OpenRouter catalog và ChatGPT Web pool để cập nhật combo `omni-free` trên OmniRoute (:20129).
- Báo cáo bắn về Telegram:
  ```text
  [OMNI-FREE-UPDATER] 1. Fetching OpenRouter catalog...
  [OMNI-FREE-UPDATER] Candidate pool size: 25. Testing liveness (max_workers=2, target: 4-5 live models)...
    + LIVE: openrouter/liquid/lfm-2.5-2.6b:free (2.30s)
    + LIVE: openrouter/dots-studio/dots-3-note-preview:free (3.48s)
    + LIVE: openrouter/nex-agi/nex-n2.5-pro:free (6.19s)
    + LIVE: openrouter/nvidia/nemotron-3-super-120b-a12b:free-low (2.01s)
    + LIVE: openrouter/inclusionai/ling-3.0-flash-fin:free (2.44s)
  [OMNI-FREE-UPDATER] Updating combo omni-free with 7 tiers...
  [OMNI-FREE-UPDATER] SUCCESS: omni-free updated with 7 tiers. Top model: openrouter/nvidia/nemotron-3-super-120b-a12b:free-low
  ```
- User bức xúc phản ánh: *"Ý là report in ra nhìn sida khó hiểu quá"*.

**Cơ chế lỗi cốt lõi:**
1. **STDOUT Leak trên Cronjob `no_agent: true`:**
   - Trong kiến trúc Hermes scheduler, bất kỳ ký tự nào in ra `stdout` sẽ được gửi nguyên văn lên Telegram làm tin nhắn thông báo.
   - Dùng `print()` cho mọi bước debug làm Telegram nhận toàn log tiến trình kỹ thuật thay vì một báo cáo người dùng. Tên model bị dính các prefix/suffix rác (`openrouter/`, `:free`, `:free-low`), thiếu phân cấp thị giác (visual hierarchy).
2. **Bẫy Verification Ping Timeout Gây Báo Fail Ảo:**
   - Sau khi PATCH combo thành công (HTTP 200 OK) và các candidate đã test live, script thực hiện bước verification ping:
     ```python
     data = json.dumps({"model": "omni-free", "messages": [{"role": "user", "content": "ping verification"}]})
     ```
   - **Lỗi 1 (Thiếu `max_tokens: 5`):** Khi combo có các model suy luận lớn (như Nemotron 550B, Nano-Omni Reasoning), model bắt đầu sinh hàng trăm token reasoning khiến socket timeout (>25s).
   - **Lỗi 2 (Khối `except` gọi `report_error()`):** Khi ping bị timeout, script in `❌ Thất bại: Verification ping failed: timed out` và exit code 1, làm fail toàn bộ cronjob dù combo trên OmniRoute thực tế đã được cập nhật thành công 100%.

**Quy chuẩn giải pháp bắt buộc:**
1. **Tách luồng Stderr vs Stdout:**
   - Toàn bộ log dò catalog, quét candidate, latency probe BẮT BUỘC ghi vào `sys.stderr` (`print(..., file=sys.stderr, flush=True)`).
   - `sys.stdout` CHỈ dành riêng cho DUY NHẤT một bản báo cáo Telegram Markdown hoàn chỉnh.
2. **Chuẩn hóa Telegram Markdown Report:**
   - Dùng helper `clean_model_name()` lược bỏ `openrouter/`, `chatgpt-web/`, `:free`, `:free-low`.
   - Phân cấp icon trực quan: 🥇 Top 1, 🥈 Top 2, 🥉 Top 3, 🔹 Tier kế tiếp, 🌐 Web Pool Fallback.
   - Cấu trúc mẫu:
     ```markdown
     ⚡ *[OMNI-FREE] CẬP NHẬT POOL THÀNH CÔNG*
     ───────────────────────────
     • *Trạng thái:* ✅ Hoạt động
     • *Tổng tiers:* 7 models (5 OpenRouter + 2 ChatGPT Web)
     • *Top Model:* `nemotron-3-super-120b` (⚡ 2.01s)
     • *Endpoint:* `omni-free` (:20129)

     📋 *Thứ tự ưu tiên (Priority Tiers):*
     1. 🥇 `nemotron-3-super-120b` (2.01s)
     2. 🥈 `lfm-2.5-2.6b` (2.30s)
     3. 🥉 `ling-3.0-flash-fin` (2.44s)
     ...
     6. 🌐 `GPT-5.6 Luna Free (ChatGPT Web Pool)`
     7. 🌐 `GPT-5.6 Sol Instant (ChatGPT Web Pool)`
     ```
3. **Non-blocking Verification Ping:**
   - Bắt buộc thêm `"max_tokens": 5` vào verification ping body.
   - Bọc trong `try...except`: nếu timeout/lỗi thì ghi log warning vào `stderr` và ghi chú nhẹ vào báo cáo, TUYỆT ĐỐI KHÔNG gọi `report_error()` làm hủy hoại kết quả PATCH đã thành công.

---

### Pathology 30: Bẫy Header Forced Connection (`x-omniroute-connection` vs `x-omniroute-connection-id`), Bẫy Sơn Vỏ `VALIDATION_REQUIRED` và Watchdog Tự Ý Bật Lại Acc User Tắt (Standby) (2026-09-25)

**Triệu chứng & Hậu quả thực tế:**
- User kêu ca ức chế: *"clgt cái acc vot*** lỗi liên tục mà cứ đi gọi vào nó ăn cặc à"*, *"tao tắt cái acc lam*** con cặc gì r"*, *"lồn mịa mày t phải đi tắt hết đống acc có nhãn bussiness ms chạy đc đkm"*.
- Agent ban đầu tưởng nhầm các acc này "sống" sau khi patch DB, re-enable vào combo khiến cả hệ thống nổ bão lỗi đỏ 429 Semaphore Timeout 30s liên hoàn.
- User vào UI gạt tắt công tắc của `lamngocdiep`, nhưng router vẫn âm thầm nã request vào, và một lúc sau công tắc lại bị tự động bật lên.

**Cơ chế lỗi cốt lõi (4 Bẫy Liên Hoàn):**
1. **Bẫy Header Forced Connection (`x-omniroute-connection` vs `x-omniroute-connection-id`):**
   - Trong `src/sse/handlers/chat.ts` (dòng 596):
     ```typescript
     const requestedConnectionId = request.headers.get("x-omniroute-connection")?.trim() || null;
     ```
   - Header chuẩn duy nhất của OmniRoute để ghim request vào đúng connection cụ thể là `x-omniroute-connection` (KHÔNG CÓ chữ `-id`).
   - Nếu truyền nhầm `x-omniroute-connection-id`, router hoàn toàn bỏ qua header này và bốc ngẫu nhiên một account khỏe mạnh trong pool để gọi. Account đó trả 200 OK, khiến Agent bị ảo giác (False Positive) rằng account đang test đã sống lại, dẫn đến quyết định sai lầm khi nạp lại hàng loạt account hỏng vào combo!
2. **Bản chất Google `VALIDATION_REQUIRED` trên Antigravity Restricted:**
   - Gọi trực tiếp Google endpoint `/v1internal:loadCodeAssist`: Google trả về `ineligibleTiers` với `reasonCode: "VALIDATION_REQUIRED"`, `tierId: "free-tier"`.
   - **Bản chất:** Google đã gắn cờ tài khoản bắt buộc phải xác minh danh tính / SĐT tại `validationUrl` thì mới cho dùng Free Tier. Khi chưa xác minh, Google chỉ cho dùng `standard-tier` với điều kiện phải tự cấp GCP Project riêng (BYOP - `userDefinedCloudaicompanionProject: true`).
   - Việc chỉ sửa text trong SQLite (`tier = free-tier`, `subscriptionTier = Antigravity Starter Quota`) hoặc gán ép project mượn `aicode-consumers` là hoàn toàn vô nghĩa đối với Google. Google sẽ ngâm request từ 10s đến 25s rồi quăng ra lỗi `403 Antigravity upstream error (403) - insufficient_quota` / `PERMISSION_DENIED`!
   - 2 slot concurrency bị ngâm 25s chính là nguồn cơ làm nghẽn hàng đợi và nổ hàng loạt lỗi `Semaphore timeout after 30000ms`.
3. **Bẫy Router Combo Dispatch Bỏ Qua `isActive = false`:**
   - Trong `comboStructure.ts`, router duyệt qua mảng `combo.models` mà **KHÔNG kiểm tra cờ `isActive` của connection**.
   - Do đó, việc người dùng vào UI Dashboard gạt tắt công tắc của tài khoản **HOÀN TOÀN KHÔNG CÓ HIỆU LỰC** nếu connection ID đó vẫn còn nằm trong mảng `models` của combo! Router vẫn tiếp tục gửi request vào nó.
   - **Quy tắc:** Muốn ngắt hẳn traffic vào một connection, BẮT BUỘC phải PUT/UPDATE combo để **gỡ bỏ hoàn toàn connection ID đó ra khỏi danh sách `models`**.
4. **Bẫy Watchdog Healer Tự Bật Lại `is_active = 1` Sau Lưng User:**
   - Trong `cron_chatgpt_web_pool_watchdog.py`, logic `toggled_off` tự động quét các acc có `isActive: false` nhưng `testStatus: active` và chạy SQL:
     ```python
     cur_db.execute("UPDATE provider_connections SET is_active=1 WHERE id=?", (c.get('id'),))
     ```
   - Điều này triệt tiêu hoàn toàn quyền kiểm soát của người dùng: người dùng vừa tắt công tắc trên Dashboard thì 5-15 phút sau watchdog lại tự bật lên.
   - Đã loại bỏ hoàn toàn khối code này để tôn trọng tuyệt đối trạng thái Standby của người dùng.
5. **Kỷ luật Gán Proxy 1:1 qua `gmail_clean_v2.xlsx` và `PROXYgandienthoai.xlsx`:**
   - Account `lamngocdiep` trước đó bị gán nhầm vào proxy `mirotik_10007` (bị nghẽn mạng), khiến latency vọt lên 42-59s. Khi chuyển về đúng Mobi proxy port 5107 (theo Máy 7 trong `gmail_clean_v2.xlsx`), latency trở lại bình thường.
   - 45 Antigravity accounts chưa có proxy assignment đã được quét và gán chuẩn 1:1 theo đúng cổng MobiProxy 4G tương ứng của từng máy farm.

---

### Pathology 31: Chuẩn Hóa Telemetry, Config Overrides & Zero-Live Fallback Cho Dynamic Pool Updater (Vượt Sol Auditor Gate) (2026-09-25)

**Bối cảnh:**
- Kịch bản cron updater định kỳ quét các model miễn phí từ OpenRouter catalog và pool ChatGPT Web (`cron_omni_free_pool_updater.py`) để cập nhật combo `omni-free` trên OmniRoute (:20129).
- Khi review qua Sol Auditor gate, kịch bản đòi hỏi độ bao phủ kiểm thử cao, khả năng cấu hình động, xử lý ngoại lệ biên (edge-cases) và khả năng quan sát (observability).

**5 Chuẩn mực Bắt buộc Khi Phát triển Script Cron Pool Updater:**
1. **Dynamic Config & Environment Variable Overrides (`os.environ.get`):**
   - Hằng số kết nối (`COMBO_ID`, `OMNI_BASE`, `OR_CONN_ID`) **CẤM hardcode cứng** mà phải luôn bọc `os.environ.get()` với fallback mặc định:
     - `OMNI_FREE_COMBO_ID`: target combo UUID.
     - `OMNI_BASE_URL`: URL OmniRoute (hỗ trợ chuyển port test hoặc staging).
     - `OPENROUTER_CONN_ID`: connection ID của provider OpenRouter.
   - Điều này cho phép CI/CD, mock server hoặc test runner monkeypatch môi trường mà không cần can thiệp mã nguồn.
2. **Cô lập Bộ lọc Catalog (`filter_catalog_models`):**
   - Tách rời hàm lọc catalog thành một hàm thuần túy (pure function) nhận `catalog: list` và trả về danh sách model ID hợp lệ.
   - Bộ lọc phải loại trừ dứt điểm:
     - `gemini-3.8`, `3.8-flash` (tránh xung đột context/thinking).
     - Model kiểm duyệt: `content-safety`, `moderation`.
     - Chỉ chấp nhận model có `pricing.prompt == 0` và `pricing.completion == 0` (hỗ trợ cả float/int/str numeric 0).
3. **Xử lý An toàn Biên Zero-Live Models (Zero-Live Fallback Net):**
   - Trong trường hợp OpenRouter tạm ngưng dịch vụ hoặc tất cả các model free đều fail liveness check (`len(top_models) == 0`):
     - Script **TUYỆT ĐỐI KHÔNG CRASH** hoặc thoát lỗi `sys.exit(1)`.
     - Phải tự động tạo combo dự phòng chỉ gồm 2 tiers ChatGPT Web (`gpt-5.6-luna-free`, `gpt-5.6-sol-instant`).
     - Báo cáo stdout hiển thị trạng thái hoạt động với nhãn `Web Fallback` thay vì báo fail làm gián đoạn routing.
4. **Phát Structured Telemetry Metric (`[TELEMETRY_METRIC]`):**
   - Song song với việc in Telegram Markdown ra stdout, script phát telemetry JSON ra `sys.stderr` với tiền tố chuẩn `[TELEMETRY_METRIC]`:
     ```python
     telemetry_payload = {
         "event": "omni_free_pool_updated",
         "timestamp": time.time(),
         "total_tiers": total_tiers,
         "openrouter_live_count": len(top_models),
         "top_model": top_model_short,
         "top_latency_sec": top_models[0][1] if top_models else None,
         "models": [m["model"] for m in combo_models]
     }
     log_debug(f"[TELEMETRY_METRIC] {json.dumps(telemetry_payload)}")
     ```
   - Giúp log ingestion pipeline (Grafana/Loki/ELK) trích xuất số liệu mà không bị nhiễu bởi định dạng Markdown.
5. **Kỷ luật Đồng bộ Song song & Suite Unit Tests 100% Pass:**
   - Mọi bản sửa đổi của cron updater bắt buộc đồng bộ 100% giữa 2 vị trí:
     - `D:\Taadaa\Hermes\deploy\hermes-home\scripts\cron_omni_free_pool_updater.py`
     - `C:\Users\Kibe\AppData\Local\hermes\scripts\cron_omni_free_pool_updater.py`
   3. Bộ test `tests/test_cron_omni_free_pool_updater.py` phải kiểm chứng đầy đủ 5 góc độ:
        1. `test_env_var_overrides`: Override cả 3 env vars, reload module, kiểm tra PATCH endpoint & payload.
        2. `test_run_updater_zero_live_models_fallback`: Mô phỏng 0 live model, verify 2 web models & stdout Web Fallback.
        3. `test_patch_payload_schema_and_integrity`: Schema priority, config timeout/retry, item properties.
        4. `test_structured_telemetry_emission`: Bắt stderr, parse JSON telemetry hợp lệ.
        5. `test_openrouter_catalog_filters`: Lọc catalog độc lập cô lập.

   ---

   ### Pathology 32: Bẫy Mass-Update "projectId = aicode-consumers" Gây Chết Chùm Quota Toàn Pool & Bẫy Cạn Quota Image Generation Trên Antigravity (2026-09-25)

   **Triệu chứng:**
   - Hệ thống có 116 tài khoản Antigravity (gồm 16 tài khoản Google AI Pro và 100 tài khoản Free), bình thường chat text mượt mà.
   - Nhưng khi chuyển sang tác vụ tạo ảnh (`gemini-3.1-flash-image` qua `/v1/images/generations`), chỉ tạo được 1–2 ảnh là toàn bộ hệ thống bị chặn đứng với lỗi:
     `HTTP 429: {"error":{"message":"You have exhausted your capacity on this model. Your quota will reset after 2h40m.","type":"rate_limit_error","code":"rate_limit_exceeded"}}`
   - Thử chuyển qua bất kỳ tài khoản nào khác (kể cả 16 tài khoản Pro trả phí), tất cả đều đồng loạt dính đúng lỗi 429 và cùng một mốc thời gian reset!

   **Cơ chế lỗi cốt lõi (Cơ chế Quota cấp Project & Bẫy Gom Rổ "aicode-consumers"):**
   1. **Nguồn gốc lỗi 422 cũ:** Trước đây khi import hàng loạt Gmail vào OmniRoute, Google đổi chính sách ngừng tự sinh Cloud Project cho tài khoản cá nhân, dẫn tới lỗi `422 Missing Google projectId`.
   2. **Pha "chữa cháy" tai hại:** Để dập lỗi 422, script trước đây đã mass-update toàn bộ 116 connections trong SQLite:
      ```sql
      UPDATE provider_connections SET project_id = 'aicode-consumers' WHERE provider = 'antigravity';
      ```
   3. **Cơ chế kiểm soát tài nguyên của Google Upstream:**
      - Với chat text (`gemini-3.8-flash-tiered`), Google tính rate limit chủ yếu dựa trên token của access token người dùng.
      - Nhưng với **TẠO ẢNH (`gemini-3.1-flash-image`)**, do ngốn tài nguyên GPU cực lớn, Google siết chặt hạn ngạch **THEO CẤP ĐỘ GOOGLE CLOUD PROJECT**.
      - Khi cả 116 tài khoản (kể cả 16 acc Pro) cùng gửi payload mang `{"project": "aicode-consumers"}`, Google coi toàn bộ 116 tài khoản này là **MỘT THỂ THỐNG NHẤT** ("Lạy ông tôi ở bụi này").
      - Hậu quả: Hạn ngạch của project `aicode-consumers` bị cạn kiệt ngay lập tức. Toàn bộ 116 tài khoản chết chùm đồng loạt, triệt tiêu hoàn toàn khả năng xoay tua (failover/rotation) của OmniRoute.
   4. **Cảnh báo từ chính tác giả OmniRoute:**
      Trong `open-sse/services/antigravityProjectBootstrap.ts` (dòng 198–207), tác giả đã ghi rõ:
      *"Google no longer auto-creates GCP projects for standard-tier accounts: a fabricated/omitted id only earns a delayed 429 RESOURCE_EXHAUSTED from Google's quota check."*
      Việc "bịa" ID `aicode-consumers` chính là nguyên nhân trực tiếp biến toàn bộ dàn acc thành một botnet dùng chung quota.

   **Quy tắc vận hành & Kỷ luật bất biến:**
   1. **CẤM TUYỆT ĐỐI mass-update chuỗi tĩnh `aicode-consumers`** cho các tài khoản trong database.
   2. **Kỷ luật BYOP (Bring Your Own Project) 1-1:**
      - Mỗi tài khoản Google AI Pro BẮT BUỘC phải sử dụng một Project ID riêng từ `console.cloud.google.com` của chính nó (hoặc theo từng cụm máy farm M01, M02...).
      - Khi mỗi tài khoản sở hữu một Project ID độc lập, quota tạo ảnh và quota model sẽ được tách biệt hoàn toàn 1-1: tài khoản này hết lượt thì tài khoản khác tiếp quan mượt mà, không bao giờ bị nghẽn toàn pool.

---

### Pathology 33: Bẫy Lệch Quy Mô Pool Web vs Codex, Bẫy Cookie Consent Overlay & Kỷ Luật Đồng Bộ 2 Chiều Parity 100% (2026-09-25)

**Triệu chứng:**
- Người vận hành nhận thấy số lượng tài khoản giữa các pool bị lệch nghiêm trọng: `codex-terra-pool` / `codex-luna-pool` có 29 accounts nhưng `chatgpt-web-pool` chỉ có 21 accounts (lệch 8-10 accounts).
- Trong khi đó, cả 2 bên đều dùng chung dàn tài khoản Gmail từ các profile GPMLogin.

**Cơ chế lỗi cốt lõi (3 Bẫy Kỹ Thuật Liên Hoàn):**
1. **Bản chất xác thực Codex OAuth vs ChatGPT Web Cookie:**
   - **Codex OAuth (`auth.openai.com`):** Dùng luồng OAuth 2.0 PKCE (`/oauth/authorize` -> `/oauth/token`) với scope `offline_access`. Quá trình nổ OTP số điện thoại và cấp authorization code chỉ trả về `access_token` và `refresh_token` cho Codex CLI, **HOÀN TOÀN KHÔNG TỰ ĐỘNG TẠO COOKIE SESSION TRÊN `chatgpt.com`**.
   - **ChatGPT Web (`chatgpt.com`):** Bắt buộc phải có cookie session `__Secure-next-auth.session-token` (hoặc các chunk `.0`, `.1`).
   - Do đó, ver xong Codex thì bên Web vẫn chưa có session cookie nếu chưa mở trang `chatgpt.com` để đăng nhập.
2. **Bẫy Cookie Consent Overlay Chặn Pointer Events (`data-octane-static-cookie-consent`):**
   - Khi dùng Playwright mở `https://chatgpt.com/`, trang web render một lớp overlay cookie preferences tĩnh phủ toàn màn hình (`<div data-octane-static-cookie-consent="">`).
   - Mọi thao tác click vào nút "Log in" / "Continue with Google" của Playwright đều bị lớp overlay này chặn đứng (`<a ...>Cookie preferences</a> intercepts pointer events`), khiến Playwright retry liên tục và nổ lỗi `TimeoutError: Timeout 30000ms exceeded`.
   - **Cách xử lý chuẩn qua JS Evaluation:**
     ```python
     page.evaluate("""() => {
         const banner = document.querySelector("[data-octane-static-cookie-consent]");
         if (banner) banner.remove();
         const btn = document.querySelector("button[commandfor='mobile-auth-dialog']");
         if (btn) btn.click();
     }""")
     ```
3. **Bẫy GPM API v3 Rò Rỉ Chrome Làm Đơ Lag Máy (Zombie Process Leak):**
   - Gọi API `GET http://127.0.0.1:19995/api/v3/profiles/stop/{pid}` trả về `{"success": true}`, **nhưng nó KHÔNG diệt tiến trình `chrome.exe` trên Windows**.
   - Sau khi duyệt qua 50–80 profile, các tiến trình Chrome con tích tụ lên đến hơn 400 tiến trình trong Task Manager, ngốn sạch 100% RAM/CPU và làm máy tính bị đơ cứng.
   - **Kỷ luật Teardown 2 tầng bắt buộc:** Bắt buộc lưu `proc_id` từ `r_start['data']['process_id']`, và trong khối `finally` dùng `psutil` diệt đệ quy toàn bộ cây tiến trình:
     ```python
     finally:
         try: requests.get(f"{GPM_BASE}/profiles/stop/{pid}", timeout=10)
         except Exception: pass
         if proc_id:
             try:
                 proc = psutil.Process(proc_id)
                 for child in proc.children(recursive=True):
                     try: child.kill()
                     except Exception: pass
                 proc.kill()
             except Exception: pass
     ```

**Quy chuẩn Tối ưu Chi phí Thuê SIM & Kỷ luật Chống Ban Nick (Anti-Brute-Force):**
1. **Săn SIM Argentina (`virtual62`, $0.05):**
   - Giá chỉ **$0.05 (~1.270đ)** — Rẻ bằng 1/2 Philippines ($0.1077) và rẻ hơn **gấp 3.1 lần** so với mua acc tạo sẵn từ SumiStore (4.000đ).
   - Tỷ lệ nổ OTP đạt **13%** (cao gấp 2.5 lần Philippines 5%).
   - Tự động gọi `GET /v1/user/cancel/{order_id}` để hoàn tiền 100% khi OpenAI từ chối số hoặc quá 45s không nổ OTP.
2. **Kỷ luật chống ban nick OpenAI (Anti-Ban Guard):**
   - Giới hạn **tối đa 2 lần thử số / 1 tài khoản**. Nếu cả 2 số đều xịt -> Hủy hoàn tiền ngay, chuyển sang profile khác, tuyệt đối không nhồi số dồn dập.
   - Nghỉ giãn cách an toàn **6 giây** giữa 2 lần nhập và giữa 2 profile để tránh bị hệ thống Abuse Detection của OpenAI khóa tài khoản vĩnh viễn (như bài học tài khoản `hoangvy`).
3. **Quy trình Đồng bộ Parity 100% 2 Chiều:**
   - Chiều 1 (GPM -> Codex): Mua số Argentina $0.05, submit OTP, hoàn tất form about-you/consent, tạo connection Codex, gán Proxy 1-1, nạp đủ cả 4 combos: `codex-terra-pool`, `codex-luna-pool`, `codex-terra`, `codex-luna`.
   - Chiều 2 (GPM -> Web): Mở profile GPM, xóa overlay cookie consent, đăng nhập Google SSO vào `chatgpt.com`, trích xuất full cookie, validate qua `/api/providers/validate`, tạo connection `chatgpt-web`, gán Proxy 1-1 qua `PUT /api/settings/proxies/assignments`, nạp vào `chatgpt-web-pool`.

---

### Pathology 34: Bẫy Bare-Model Targets Không Mang `connectionId` Làm Bỏ Qua Spillover 0ms Tại Combo Level & Kẹt Hàng Đợi 30s Mặc Định Khi `queueTimeoutMs` Bị NULL (2026-09-25)

**Triệu chứng & Khiếu nại thực tế từ User:**
- User bức xúc phản ánh: *"Đã bảo pool gemini là bao gồm cả pro và quota r mà"* khi thấy Dashboard Logs nổ một dọc dài lỗi `429 Semaphore timeout after 30000ms` trên 4 acc Pro (`toloan`, `phungthibichngoc`, `lelinh`, `duongkien`) với duration đúng ~31 giây (kéo theo 70-80 calls lỗi trên mỗi acc).
- Trong khi đó: Hệ thống có cả một dàn gồm 16 acc Pro và 70 acc Free có quota đứng chờ phía sau, và Quota Card trên Dashboard vẫn báo `Gemini 3.1 Pro High: 100% left`.

**Cơ chế lỗi cốt lõi (Disconnection giữa Combo Spillover và ChatCore Execution):**
1. **Lỗ hổng check `connectionId` tại `combo.ts`:**
   - Trong commit `1c1634f0b`, router bổ sung cơ chế `tryAcquireAccountSemaphore` atomic (0ms spillover) cho mọi strategy trong `open-sse/services/combo.ts`.
   - Tuy nhiên, khối code kiểm tra đó được bọc bởi điều kiện:
     ```typescript
     if (connectionId) {
       const maxConcurrentCap = await lookupPositiveCap(connectionId);
       // tryAcquireAccountSemaphore(...) -> nếu full thì spillover 0ms sang target kế tiếp
     }
     ```
   - Trong combo `ag-gemini-pool-3`, danh sách targets được khai báo dưới dạng bare-model: `{ "model": "antigravity/gemini-3.8-flash-tiered" }` (không gắn cứng `connectionId` cụ thể ở cấp combo). Do đó `connectionId` là `undefined` -> cơ chế tryAcquire 0ms bị bỏ qua hoàn toàn ở cấp combo!
2. **Bẫy hàng đợi 30 giây mặc định tại `chatCore.ts`:**
   - Request trôi xuống tầng thực thi đơn lẻ `open-sse/handlers/chatCore.ts:1680`. Tại đây hàm `selectAccount()` mới bắt đầu bốc account động (ví dụ `toloan`).
   - Sau khi bốc account, `chatCore.ts` gọi:
     ```typescript
     await acquireAccountSemaphore(accountSemaphoreKey, {
       maxConcurrency: 2,
       timeoutMs: queueTimeoutMs || 30000,
     });
     ```
   - Vì cả combo `omni-worker` và `ag-gemini-pool-3` đều để `queueTimeoutMs: null`, tham số `timeoutMs` fallback về mặc định toàn cục `DEFAULT_TIMEOUT_MS = 30000` (30 GIÂY)!
   - Hậu quả: Khi 4 acc Pro đầu tiên đang bận 2/2 slot, các request tiếp theo KHÔNG ĐƯỢC CHUYỂN NGAY (spillover 0ms) sang 70 acc Free ở Tier 2 mà bị chôn chân chờ đúng 30 giây rồi nổ lỗi 429 Semaphore Timeout, tạo ảo giác cả pool bị đơ nghẽn dù thực tế 144 requests khác vẫn xử lý thành công qua `dokieu` và `codex`.

**Phân tích Tính Tương Thích & Không Xung Đột (No-Conflict Verification):**
1. *Đối soát với commit `1c1634f0b` (Atomic Spillover):* Hoàn toàn đồng thuận. Việc set `queueTimeoutMs: 1000` hoặc `queueDepth: 0` chính là hoàn thiện nhánh fallback cho dynamic account selection khi target không có `connectionId` tĩnh.
2. *Đối soát với commit `f8daf9968` (Hard Connection Binding):* Hoàn toàn độc lập. Hard connection binding chỉ ngăn việc tráo connection ngầm khi target CÓ `connectionId`, không can thiệp vào hàng đợi semaphore.
3. *Đối soát với chuẩn thiết kế PR `#3872`:* Trong `comboConfig.ts`, tác giả khẳng định `0 is valid and meaningful: it makes a saturated combo member fail over to the next member immediately instead of queueing`.

**Quy chuẩn về Kho Lưu Trữ Lỗi (Case Tracking):**
- OmniRoute KHÔNG dùng file `case.md` như các repo phone farm bên `D:/Taadaa`.
- Mọi bug và bài học kiến trúc được theo dõi qua:
  1. Git Conventional Commits (`fix(combo): ...`, `fix(routing): ...`).
  2. Fragments tại `changelog.d/fixes/`.
  3. Regression tests trong `tests/unit/`.
  4. Skill Library `references/omniroute-combo-routing-pathology.md` của Hermes.

---

### Pathology 35: Ý Nghĩa Icon `↳` Cạnh Status 200 Trên Dashboard Logs (`RequestLoggerV2.tsx`) vs Bẫy Hiểu Nhầm "Toàn Bộ Bị Retry" (2026-10-01)

**Triệu chứng:**
- Trên Dashboard OmniRoute (`/dashboard/logs`), người vận hành thấy hàng loạt request trả về status `200` nhưng có thêm biểu tượng mũi tên rẽ nhánh màu vàng cam **`↳`** nằm ngay cạnh mã status.
- Người vận hành thường đặt câu hỏi: *"Dấu mũi tên cạnh số 200 là gì, có phải request nào cũng bị lỗi phải retry không?"*.

**Cơ chế UI (`RequestLoggerV2.tsx`):**
1. **Gom nhóm theo Correlation ID:**
   - OmniRoute nhóm các bản ghi theo trường `correlationId` (truyền qua header `X-Correlation-Id` từ client/gateway hoặc tự sinh trong `chat.ts`).
   - Bản ghi đầu tiên trong nhóm được gán `isRetry: false` (parent request).
   - Tất cả các bản ghi đến sau có cùng `correlationId` đều bị frontend gán cờ `isRetry: true` và hiển thị icon **`↳`**.
2. **Nút bấm điều hướng (`Go to parent`):**
   - Icon `↳` thực chất là một `<button title="Go to parent">`. Khi click vào `↳`, hàm `openDetail(parent)` lập tức mở modal chi tiết của request gốc (parent) để người vận hành kiểm tra xem lần đầu đã gặp lỗi gì (422, 429, 499) mà phải retry sang request này.
3. **Bẫy hiểu nhầm "Toàn bộ bị lỗi phải retry" (False Retry Assumption):**
   - Khi client (như Hermes Agent, subagents song song, hoặc các kịch bản batch) gửi nhiều request trong cùng một session/turn mà tái sử dụng hoặc kế thừa cùng một `correlationId`:
   - Dù 100% request đều trả về HTTP 200 OK (không hề có request nào fail trước đó), các request từ số 2 trở đi trong nhóm **VẪN BỊ HIỆN ICON `↳`**.
   - **Cách phân biệt chính xác:** Kiểm tra tag group (`healed` vs `null`):
     - Chỉ khi trong nhóm có ít nhất 1 request `status >= 400` và 1 request `200` thành công theo sau thì mới thực sự là failover cứu hộ (`groupStatus === "healed"`).
     - Nếu toàn bộ các request trong nhóm đều `200`, đó thuần túy là do client gửi nhiều request mang chung `correlationId`.

---

### Pathology 36: Bẫy Tràn Tầng Concurrency Cap (`isRuntimeUnitAtConcurrencyCap`) Từ Pro Sang Free Pool Khi Chưa Hết Quota Ngày & Lỗi 422 Thiếu ProjectId (2026-10-01)

**Triệu chứng:**
- Combo `omni-worker` được thiết kế theo thứ tự ưu tiên: Tier 1 (`ag-gemini-pool-3` - 20 accounts Google AI Pro) -> Tier 2 (`ag-gemini-free-pool` - các accounts Free).
- Người dùng thắc mắc: *"Ủa mà phải cào hết pool pro mới được nhảy pool thường mà? Sao tự nhiên thấy nhảy xuống pool thường dính lỗi 422 Missing Google projectId?"*.

**Cơ chế lỗi cốt lõi (Concurrency Cap Overflow vs Daily Quota Exhaustion):**
1. **Giới hạn đồng thời (Concurrency Cap):**
   - Mỗi account Google AI Pro trong OmniRoute được cấu hình trần đồng thời cứng `max_concurrent: 2` (để tránh bị Google bóp rate limit).
   - Với 20 accounts Pro, toàn bộ pool Pro chỉ có khả năng gánh tối đa **40 requests in-flight cùng một lúc**.
2. **Burst Load & Heavy Context:**
   - Khi có tải dồn dập từ các agent/subagents farm (ví dụ 80 requests trong vòng chưa đầy 2 phút) với context lớn (>160k tokens, thời gian xử lý mỗi request từ 20s đến 45s, cá biệt 125s), toàn bộ 20 tài khoản Pro đều bị chiếm trọn 2/2 slot (`running == 2`).
3. **Cơ chế Cascade xả tràn của `executeRuntimeUnitCombo` (`runtimeUnitCapacity.ts`):**
   - Khi combo cha `omni-worker` chạy `nestedComboMode: "execute"`, hàm `isRuntimeUnitAtConcurrencyCap` kiểm tra nếu toàn bộ connections của Tier 1 chạm cap hoặc hàng đợi vượt quá `queueTimeoutMs` (1000ms–3000ms), router **không dừng lại chờ timeout mà lập tức xả tràn (overflow/fallback) xuống Runtime Unit kế tiếp trong danh sách (Tier 2 Free Pool)** để giải tỏa áp lực.
4. **Bẫy 422 tại Free Pool (`Missing Google projectId`):**
   - Các tài khoản Free/Standard tier thông thường chưa từng được onboarding Cloud Code hoặc tạo GCP Project riêng sẽ có `projectId = null` trong DB.
   - Khi router xả tải tràn xuống Free Pool và bốc trúng các acc này, Google lập tức từ chối với lỗi:
     `[422]: Missing Google projectId for Antigravity account. Auto-discovery via loadCodeAssist found no Cloud Code project.`
   - Khi dính 422, OmniRoute failover tiếp sang các tài khoản Free sạch có project (như `toansuong...`, `brittanys...`) hoặc tài khoản Pro vừa nhả slot và trả về `200 OK` (kèm icon `↳`).

**Quy tắc vận hành & Khắc phục:**
1. **Phân biệt rạch ròi bản chất:**
   - *Hết hạn ngạch ngày (Quota Exhaustion)*: Snapshot ghi nhận remaining = 0%, router chủ động loại bỏ acc trong nhiều giờ.
   - *Nghẽn slot đồng thời (Concurrency Saturation)*: Acc vẫn còn nguyên 100% quota ngày nhưng cả 2 slot đang bận xử lý request nặng, router xả tràn 0ms sang tầng dưới để tránh request bị treo chết.
2. **Dọn dẹp tài khoản Free thiếu `project_id`:**
   - Quét SQLite kiểm tra các acc Antigravity thiếu `project_id`:
     ```sql
     SELECT email FROM provider_connections WHERE provider = 'antigravity' AND (project_id IS NULL OR project_id = '');
     ```
   - Cần bổ sung Project ID chính chủ (BYOP) hoặc tạm thời gỡ connection ID của các acc này khỏi danh sách `models` của `ag-gemini-free-pool` để tránh lãng phí nhịp nhảy lỗi 422 khi Tier 1 tràn tải.

---

### Pathology 37: Bẫy Tái Kích Hoạt Acc Lỗi Bởi Cronjob Auto-Healer (`test_status = 'active'`), Kỷ Luật Concurrency Cap Pro (2 -> 3) & Quy Chuẩn Lưu Trữ Cấu Hình Git (2026-10-01 / 2026-10-02)

**Triệu chứng:**
- Người vận hành đã cách ly các tài khoản bị lỗi (như 23 acc thiếu `project_id` gây lỗi 422) bằng cách set `is_active = 0` trong SQLite.
- Tuy nhiên, chỉ sau khoảng 1 tiếng, router lại tiếp tục dính lỗi 422 trên chính các tài khoản này. Kiểm tra DB phát hiện chúng đã bị ai đó tự động bật `is_active = 1` trở lại.
- Đồng thời, khi xử lý lưu cấu hình, phát hiện nguy cơ commit nhầm file nhị phân SQLite 700MB chứa secret/tokens vào Git.

**Cơ chế lỗi cốt lõi (3 Bẫy Kỹ Thuật Liên Hoàn):**
1. **Bẫy Cronjob "Reactivate Zombie" Làm Phá Vỡ Cách Ly:**
   - Script tự động bảo dưỡng tài khoản `cron_omni_activate_soaked_codex.py` (chạy mỗi 1 giờ) có câu truy vấn phục hồi:
     ```sql
     UPDATE provider_connections 
     SET is_active = 1 
     WHERE provider = 'antigravity' 
       AND is_active = 0 
       AND test_status = 'active';
     ```
   - Do các tài khoản thiếu `project_id` vẫn có `test_status` ghi nhận là `'active'`, cứ mỗi 60 phút cronjob này tự động ghi đè `is_active = 1`, làm hỏng hoàn toàn trạng thái cách ly thủ công của người vận hành.
   - **Khắc phục triệt để:** Bắt buộc bổ sung ràng buộc dữ liệu đầu vào ngay trong câu lệnh UPDATE của cronjob:
     ```sql
     AND project_id IS NOT NULL AND project_id != ''
     ```
     Đồng thời bổ sung unit test hồi quy kiểm chứng (`tests/test_cron_omni_activate_soaked_codex.py`).

2. **Cân chỉnh Concurrency Cap Pro (`max_concurrent: 2 -> 3`):**
   - Tài khoản Google AI Pro có hạn ngạch TPM/RPM cao hơn nhiều so với tài khoản Free.
   - Nâng `max_concurrent = 3` cho 20 tài khoản Pro giúp tăng trần công suất tức thời từ 40 lên **60 luồng song song** ($20 \text{ acc} \times 3$).
   - Kết hợp với thuật toán `least-used` (chia tải vào acc ít việc nhất), 60 luồng được rải đều trên 20 acc, giúp hệ thống nuốt trọn vẹn các đợt burst request nặng (>80 requests/2 phút) mà không bị kích hoạt cơ chế xả tràn (overflow) xuống Free Pool.
   - Tài khoản Free vẫn bắt buộc giữ nguyên `max_concurrent: 2` để tránh bị Google bóp băng thông stream hoặc trả về 429.

3. **Kỷ Luật Lưu Trữ Cấu Hình OmniRoute (Runtime DB vs Git Repository):**
   - **Database Runtime (`storage.sqlite`):** Nặng ~700MB và chứa toàn bộ OAuth refresh tokens / API keys nhạy cảm. **TUYỆT ĐỐI CẤM** commit hoặc push file nhị phân `.sqlite` này lên Git repository.
   - **Quy trình lưu trữ & sao lưu chuẩn:**
     1. Ép ghi dữ liệu từ WAL: `PRAGMA wal_checkpoint(FULL);`
     2. Tạo snapshot backup timestamped: `storage_backup_<timestamp>.sqlite` trong thư mục `.omniroute/db_backups/`.
     3. Xuất cấu hình text thuần JSON sạch (đã redact secrets): `combos_backup.json`, `settings_backup.json` vào repository `D:/Taadaa/AI-Tools/tools/omniroute/` để quản lý phiên bản qua Git.







