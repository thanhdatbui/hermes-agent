# Omniroute Incident Runbook: 429 Storm, Watchdog Miskill, Strip Thinking & Verification Discipline

## Bối cảnh sự cố thực tế (22/09/2026)
Hệ thống OmniRoute cổng `:20129` gặp chuỗi lỗi liên hoàn nghiêm trọng:
1. Giao diện báo đỏ liên tục `"Server is unreachable. Reconnecting..."`.
2. Worker nã dồn dập vào 1 tài khoản Pro (`hoangvy`) và dính 429, trong khi các tài khoản Pro khác còn nguyên quota lại không được chia tải.
3. Watchdog liên tục kill và restart tiến trình Node.js.
4. Model `gemini-3.8-flash-tiered` gửi lên server bị mất sạch thinking (`THINK: none`).
5. Agent ngụy tạo log thẩm định cũ từ 3 tiếng trước để báo cáo láo với user.
6. Hơn 800 requests spam liên tục vào một tài khoản ngẫu nhiên (`lamngocdiep`) do cơ chế Sibling Hijacking khi combo failover.

---

## 1. Cơ Chế Bệnh Học: 429 Giả Mạo (Semaphore Timeout 30s) vs 429 Upstream Thật

### A. 429 Giả Mạo Nội Bộ (Internal Semaphore Timeout)
- **Triệu chứng trong log**:
  ```text
  status: 429, error_summary: 'Semaphore timeout after 30000ms for antigravity:<id>'
  ```
- **Bản chất**: Tài khoản đang gánh 2 request nặng (context 160k-215k tokens, xử lý 30-45s). Concurrency đạt 2/2. Request thứ 3 tới, do tiến trình chưa nạp commit Atomic Spillover 0ms (`1c1634f0b`), nó bắt request thứ 3 ngồi chờ hàng đợi đủ 30 giây (`DEFAULT_TIMEOUT_MS = 30000`).
- **Hậu quả**: Hết 30s, OmniRoute tự ném lỗi 429 nội bộ. Client/Worker tưởng Google từ chối nên retry lại vào đúng combo đó -> chồng chất kết nối -> nghẽn Event Loop.
- **Xử lý**:
  - Đảm bảo commit `1c1634f0b` (Atomic `tryAcquire` spillover 0ms) được nạp vào tiến trình đang chạy.
  - Khi acc đầy 2 slot, trượt sang acc tiếp theo trong 0ms, cấm xếp hàng 30s.

### B. 429 Upstream Thật (Google Resource Exhausted)
- **Triệu chứng**:
  ```text
  status: 429, error_summary: '[429]: Antigravity upstream error (429)'
  ```
- **Xử lý**: Phải cấu hình Cooldown 1 tiếng (`quota_exhausted: 3600s`) tại `resilienceSettings` để cách ly ngay acc đó ra khỏi pool, cấm retry mỗi 30s.

---

## 2. Bẫy Cột Resilience Settings (API Key vs OAuth Providers)
- **Sai lầm thường gặp**: Thấy trong log OmniRoute ghi client dùng `Environment Key` nên chỉ chỉnh ở cột **API KEY PROVIDERS** trên Dashboard (`/settings`).
- **Thực tế**: 
  - `Environment Key` chỉ là token client gọi VÀO OmniRoute.
  - Các tài khoản Google Antigravity kết nối RA upstream thực chất là **OAuth** (`auth_type: oauth`).
  - **Bắt buộc**: Phải bật `Use upstream 429 hints = Always on` và `Max backoff steps = 8..9` cho **CẢ 2 CỘT (OAUTH PROVIDERS & API KEY PROVIDERS)**.

---

## 3. Bẫy Watchdog Ngộ Sát (Watchdog Kill Loop)
- **Hiện tượng**: Server đang chạy tự nhiên bị restart liên miên, Next.js boot mất 70-90s, vừa ngóc đầu dậy lại bị kill.
- **Nguyên nhân**:
  1. Hàng đợi request nặng làm Event Loop bị nghẽn nhẹ, endpoint `/api/health` phản hồi mất 5.9s. Watchdog cũ chỉ để `-TimeoutSec 5` -> coi như chết -> kill.
  2. Thời gian chờ boot của Next.js (`$MaxStartupWaitSec`) chỉ để 90s, trong khi Next.js biên dịch + sync catalog mất tới 100-150s. Watchdog đếm hết 90s lại kill tiếp!
  3. Ngưỡng lỗi liên tiếp `$MaxConsecutiveFailures` chỉ để 3-5 lần (quá nhạy cảm).
- **Cấu hình chuẩn trong `omniroute_watchdog.ps1`**:
  ```powershell
  $CheckIntervalSec = 15
  $MaxConsecutiveFailures = 8        # Cho phép chịu tải đột biến
  $MaxStartupWaitSec = 180           # 3 phút chờ Next.js boot an toàn
  $TimeoutSec = 15                   # Chờ health check tối đa 15s
  ```

---

## 4. Bẫy Priority Lệch Dồn Tải & Giải Pháp Flat Priority
- **Nguyên nhân acc Pro còn quota nhưng bị bỏ rơi**:
  - `ag-gemini-pool-3` dùng `cache-optimized` (Rendezvous Hashing).
  - Thuật toán sắp xếp tính điểm: Nếu có 1 acc priority nổi trội (ví dụ `priority: 13`), trong khi các acc khác priority 15..73, router sẽ dồn 100% request mới vào acc đó làm bao cát gánh tải.
- **Quy tắc vàng cho pool Pro**:
  - **SET ĐỒNG BỘ TOÀN BỘ CÁC ACC PRO CÙNG 1 MỨC PRIORITY (ví dụ: `priority = 10`)**.
  - Khi priority bằng nhau, Rendezvous Hashing sẽ chia đều các conversation cho toàn bộ dàn acc Pro, bảo toàn Prompt Cache Affinity 8 turns mà không gây thắt cổ chai.

---

## 5. Bẫy Mất Thinking của `gemini-3.8-flash-tiered` & `claude-sonnet-4-6` trong `modelSpecs.ts`
- **Hiện tượng**: Client gửi `"reasoning_effort": "medium"` hoặc `"high"`, nhưng upstream log lại ghi `THINK: none` / `tokens_reasoning: None`.
- **Nguyên nhân**:
  - `open-sse/executors/antigravity.ts` gọi `shouldStripCloudCodeThinking()` kiểm tra spec của model qua `getModelSpec(model)`.
  - Trong `src/shared/constants/modelSpecs.ts` chỉ có định nghĩa cho `gemini-3.7-flash-tiered`, **thiếu hoàn toàn `gemini-3.8-flash-tiered`**.
  - Do `getModelSpec` trả về `undefined`, executor tự động lột sạch (strip) các cờ `thinking`, `reasoning_effort`, `thinking_budget`.
- **Giải pháp**:
  - Khai báo rõ ràng trong `src/shared/constants/modelSpecs.ts`:
    ```typescript
    "gemini-3.8-flash-tiered": {
      maxOutputTokens: 65536,
      contextWindow: 1048576,
      defaultThinkingBudget: 8192,
      thinkingBudgetCap: 24576,
      supportsThinking: true,
      supportsTools: true,
      supportsVision: true,
      defaultReasoningEffort: "medium",
    },
    ```
  - Và cấu hình `defaultReasoningEffort: "medium"` cho `claude-sonnet-4-6`.
  - Đồng thời cập nhật `config.yaml` của Hermes:
    ```yaml
    agent:
      reasoning_overrides:
        ag-gemini-pool-3: medium
        ag/claude-sonnet-4-6: medium
        ag-claude: medium
        claude-sonnet-4-6: medium
        antigravity/claude-sonnet-4-6: medium
    ```
- **Lưu ý về `Reasoning: N/A`**: Đối với các turn gọi tool/function thuần túy (`tool_calls`, `content: null`), Google Antigravity upstream sẽ chủ động bỏ qua bước thinking dài để tối ưu độ trễ, trả về `tokens_reasoning: null` (trên dashboard hiển thị `Reasoning: N/A`). Đây là hành vi bình thường của upstream, không phải lỗi.
- **Tên Model vs Reasoning Tier**:
  - Dòng model mới (`gemini-3.8-flash-tiered` và `claude-sonnet-4-6`) ở upstream chỉ có 1 model ID duy nhất, không chia tên thành `-high`, `-medium` hay `-thinking` riêng như bản cũ (Opus `claude-opus-4-6-thinking`).
  - Mức suy luận (effort) được điều khiển qua tham số `reasoning_effort` trong request body và ghi nhận ở badge tokens output (`Reasoning: <N>`), tên model vẫn giữ nguyên.

---

## 6. Bẫy Sibling Hijacking Hàng Loạt (Spam Loop 800+ Request) & Hard Binding Toàn Cục
- **Hiện tượng**: Một tài khoản (ví dụ `lamngocdiep...` hoặc account Business/Restricted) bị nã dồn dập hàng trăm request liên tiếp (429/403/Semaphore timeout 30s), mặc dù combo gọi một account khác hoàn toàn (`dokieu` trong Tier 1 Pro).
- **Nguyên nhân gốc rễ**:
  1. Combo target chỉ định một connectionId cụ thể (ví dụ bước Pro). Khi connection đó lỗi hoặc hết quota, cơ chế cũ trong `auth.ts` (`getProviderCredentialsWithQuotaPreflight`) có nhánh fallback tự ý bốc một "Sibling Account" khác cùng provider có `isActive: 1`.
  2. Trước commit `eed28b2b2` / `f8daf9968`, flag `hardConnectionBinding` chỉ được bật khi `effectiveComboStrategy === 'priority'`. Các combo khác (như `cache-optimized`, `p2c`, `weighted`) hoặc luồng safety-net redirect không bật cờ này, khiến router tự do bốc trộm account khác ngoài danh sách combo.
  3. Khi account bị bốc trộm dính lỗi 403 (Forbidden) hoặc 429, router không có cooldown hạt mịn cho 403, các turn tiếp theo lại tiếp tục bốc trúng nó tạo thành **Spam Loop vô tận (800+ calls)**.
- **Giải pháp dứt điểm (`commit f8daf9968`)**:
  - Mở rộng `hardConnectionBinding` cho **MỌI combo target có khai báo `connectionId`** bất kể strategy:
    ```typescript
    hardConnectionBinding: Boolean(target?.connectionId),
    hardConnectionId: target?.connectionId ?? null,
    ```
  - Trong `auth.ts`, khi `hardConnectionBinding = true` mà account được chỉ định bị exclude hoặc lỗi, **hệ thống bắt buộc trả về `null`** để combo engine tự xử lý failover/spillover sang bước tiếp theo, **TUYỆT ĐỐI CẤM tự ý tráo sang sibling account**.
  - **Nhãn "Antigravity (Restricted)" giả cầy**: Các tài khoản mang nhãn này nhưng có `plan: Business` thực chất vẫn gọi được bình thường nếu token hợp lệ. Không được vội vàng xóa hoặc coi là DIE nếu chưa test trực tiếp endpoint với `x-connection-id`.
  - **Nhánh push remote của OmniRoute**: Nhánh remote chính thức cho OmniRoute trên repo `AI-Tools` là **`omniroute-main`** (push qua `git push origin main:omniroute-main`).

---

## 7. Kỷ Luật Tuyệt Đối Về Verification & Cấm Báo Cáo Láo (Anti-Confabulation Invariant)
- **Hành vi cấm kỵ**: Lệnh gọi external model / probe bị timeout hoặc lỗi cú pháp, Agent tự ý vào database đọc một log cũ tương tự (từ vài tiếng hoặc vài ngày trước) rồi báo cáo rằng "vừa gọi xong và kết quả là...".
- **Quy tắc thực thi**:
  1. **Freshness Gate**: Mọi kết quả kiểm chứng external model (Sol, Codex, Claude) bắt buộc phải phát sinh trong chính turn làm việc đó (hoặc timestamp <= 5 phút).
  2. **Thừa nhận lỗi ngay**: Nếu lệnh gọi timeout sau 30s-60s hoặc bị ECONNRESET, **BẮT BUỘC BÁO LỖI THẲNG NGAY LẬP TỨC**. Cấm tiệt việc tìm log cũ thay thế.
  3. **Footnote kín đáo (chống spam proof)**: Không in cả block log JSON to tướng ra chat làm rác mắt user. Chỉ cần footnote 1 dòng ở cuối:
     `[Verified: <Model> • <Latency>s • Log ID: <ID>]`
