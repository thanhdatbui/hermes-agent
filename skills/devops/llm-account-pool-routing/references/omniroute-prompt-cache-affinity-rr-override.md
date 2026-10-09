# OmniRoute Prompt Cache Affinity Override Round-Robin Pathology

## 1. Triệu chứng & Bối cảnh (Symptoms & Context)
- **Cấu hình mong muốn:** Combo `ag-gemini-pool-3` gồm 70 accounts Antigravity/Gemini được cấu hình `strategy: round-robin`, `disableSessionStickiness: true`.
- **Hiện tượng thực tế:** 
  - Toàn bộ request từ client (Hermes Agent, farm workers) dồn 95-99% vào duy nhất 1 tài khoản (`dokieu04092004@gmail.com`, sau đó là `thanhdatbui19951@gmail.com`).
  - Các tài khoản khác hoàn toàn khỏe mạnh (`is_active = 1`, không cooldown) nhưng không nhận được request.
  - Dù client mở nhiều session khác nhau (`session_tag` khác nhau) trên các máy hoặc luồng khác nhau, tất cả vẫn đổ dồn về cùng 1 tài khoản.
  - Thỉnh thoảng có 1-2 request "nhảy" sang tài khoản khác (`lelinh`, `chungan`) rồi lập tức quay ngược lại tài khoản chính.

---

## 2. Nguyên nhân gốc rễ (Root Cause in OmniRoute Core)

### A. Cơ chế Prompt Cache Affinity trong `combo.ts` và `promptCacheAffinity.ts`
1. **Trích xuất Prefix Hash (`prefixAnalyzer.ts`):**
   ```typescript
   for (let i = 0; i < messages.length; i++) {
     if (msg.role === "system") {
       prefixEndIdx = i; // CHỈ LẤY SYSTEM PROMPT ĐỂ HASH
     } else {
       break; // Dừng ngay khi chạm vào user message
     }
   }
   ```
   - Client Hermes hoặc các agent luôn gửi một `System Prompt` mở đầu cố định (chứa agent persona, instructions, tool definitions).
   - Dù ở **nhiều session khác nhau**, user hỏi nội dung khác nhau, thì `prefixText` của System Prompt là **HOÀN TOÀN GIỐNG NHAU** -> cho ra cùng 1 `prefixHash`.

2. **Rendezvous Hashing chọn cố định 1 Account Winner:**
   - Hàm `normalizedRendezvousScore(key, identity)` tính điểm băm giữa `prefixHash` và `connection:<connectionId>` của 70 accounts.
   - Với cùng 1 prefix prompt, thuật toán luôn trả về **duy nhất 1 connection có điểm cao nhất** (Winner).
   - Danh sách 70 accounts được sắp xếp lại, đẩy Account Winner lên vị trí index 0.

3. **Ghi đè triệt tiêu con trỏ Round Robin (`combo.ts` dòng 3175–3185):**
   ```typescript
   let rrStartIndex = startIndex;
   if (rrAffinity.applied) {
     rrStartIndex = 0; // ÉP BỘ ĐẾM VỀ 0 BẤT KỂ BIẾN ĐẾM rrCounters
   }
   ```
   - Do `rrStartIndex` bị ép cứng về 0, toàn bộ logic xoay vòng `(rrStartIndex + offset) % modelCount` sẽ luôn thử account tại vị trí 0 trước tiên. Biến đếm vòng tròn `rrCounters` bị vô hiệu hóa hoàn toàn.

---

## 3. Giải thích các hiện tượng phụ (Edge Cases)

### Hiện tượng 1: "Tại sao có request nhảy sang acc khác (le***, chu***) 1-2 lần rồi lại quay về?"
- **Cơ chế Semaphore & Concurrency:** Khi nhiều session bắn song song, tài khoản chính (`thanhdatbui`) chạm ngưỡng giới hạn luồng đồng thời (in-flight semaphore).
- Request đến sau khi acc chính đang bận sẽ fallback sang vị trí tiếp theo trong danh sách ưu tiên.
- Nếu acc tiếp theo bị Google trả HTTP 429 (`chungan`), hệ thống tiếp tục nhảy sang acc kế tiếp (`lelinh` nhận HTTP 200).
- **Lý do bị hút ngược lại:** Ngay khi acc chính xử lý xong request trước và nhả semaphore, request mới bay tới thấy acc chính rảnh sẽ lập tức chọn lại acc chính (vì acc chính vẫn là #1 trong bảng điểm Rendezvous Hashing).

### Hiện tượng 2: "Tại sao đổi từ `dokieu` sang `thanhdatbui`?"
- Khi acc `dokieu` bị gián đoạn, cạn quota hoặc client đổi template system prompt giữa các phiên bản agent, điểm hash Rendezvous thay đổi hoặc acc trước đó bị loại khỏi pool hợp lệ, dẫn đến 1 acc khác (`thanhdatbui`) vươn lên thành #1 và tiếp tục hút trọn các request tiếp theo.

---

## 4. Cách khắc phục dứt điểm (Remediation)

### Cách 1: Tắt Prompt Cache Affinity qua UI Dashboard (:20128/:20129)
1. Truy cập Web Dashboard `http://127.0.0.1:20128` (hoặc IP LAN).
2. Vào **Settings** -> Tab **Combo Defaults**.
3. Tìm mục **Enable Prompt Cache Affinity** và chuyển sang **Off** (bỏ chọn).
4. Lưu cấu hình.

### Cách 2: Tắt qua REST API
Gọi trực tiếp endpoint API của OmniRoute:
```bash
curl -X PATCH http://127.0.0.1:20129/api/settings \
  -H "Content-Type: application/json" \
  -d '{"promptCacheAffinityEnabled": false}'
```

### Kết quả sau khi tắt:
- Biến `rrAffinity.applied` nhận giá trị `false`.
- OmniRoute chạy Round Robin thực thụ: `modelIndex = (startIndex + offset) % modelCount`, tịnh tiến `rrCounters` sau mỗi request thành công.
- Tải được chia đều 100% trên toàn bộ 70 tài khoản trong pool.
