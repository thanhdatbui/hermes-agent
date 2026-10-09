# OmniRoute v3.8.x Live Log Triage, In-Pool vs Sibling Leakage, and Quota UI False Alarms

## 1. Các Endpoint Chuẩn Trên OmniRoute v3.8.x (Tránh 404)
- **Log Request thực tế:**
  - `GET /api/usage/call-logs?limit=50` (Endpoint thật do UI Dashboard Logs `/dashboard/logs` gọi).
  - CÁC ENDPOINT 404 (KHÔNG TỒN TẠI): `/api/logs`, `/api/request-logs`, `/api/requests`, `/api/log`.
- **Tổng quan sức khỏe Token:**
  - `GET /api/token-health` -> Trả về `{ total, healthy, errored, warning, status }`. Dùng kiểm chứng nhanh khi UI báo đỏ diện rộng.
- **Danh sách Provider Connections:**
  - `GET /api/providers` -> Trả về `{ connections: [...] }` chứa `id`, `email`, `isActive`, `testStatus`, `tier` (`g1-pro-tier` vs `free-tier`/`standard-tier`), `lastError`.
- **Cấu hình Combos:**
  - `GET /api/combos` -> Trả về `{ combos: [...] }` chứa danh sách target `models: [{ connectionId, label, weight, model, providerId }]`, `strategy`, `config`.

---

## 2. Giải Mã Hiện Tượng "Dashboard Quota Báo Expired Hàng Loạt"
- **Triệu chứng:** Người dùng mở `/dashboard/quota` thấy một hàng dài tài khoản Antigravity báo đỏ `Token expired`, tưởng rằng toàn bộ pool bị die hoặc mất token.
- **Bản chất kỹ thuật:**
  - Giao diện Quota hiển thị **toàn bộ provider connections** có trong cơ sở dữ liệu (bao gồm cả tài khoản free cũ, tài khoản phụ, tài khoản test đã hết hạn từ lâu).
  - Pool chính (ví dụ `ag-gemini-pool-3`) chỉ ghim một tập con (sub-pool gồm ~16-22 tài khoản Pro). Các tài khoản Pro này vẫn có `isActive: true`, `testStatus: "active"`, và đang xử lý request `200` bình thường.
  - **Quy tắc:** Tuyệt đối không phán đoán sức khỏe pool dựa vào màu sắc các card trên `/dashboard/quota`. Bắt buộc gọi `GET /api/token-health` và đối soát `connections` thuộc combo mục tiêu.

---

## 3. Quy Trình Đối Soát `inPool` vs Sibling Leakage
Khi người dùng phản ánh: *"Pool Gemini còn quota mà cứ nhảy vào acc lỗi / 429 / 403 hoài"*:

### Bước 1: Lấy danh sách connectionId thuộc Pool
Từ `GET /api/combos`, trích xuất `Set` các `connectionId` của combo (ví dụ `ag-gemini-pool-3`).

### Bước 2: So sánh với log gần nhất
Gọi `GET /api/usage/call-logs?limit=100`, lọc các request gọi model mục tiêu (ví dụ `gemini-3.8-flash-tiered`):
- Kiểm tra `connectionId` của từng request:
  - Nếu `inPool == true`: Request đi đúng vào danh sách tài khoản Pro của combo. Xem trạng thái (`200`, hoặc `429 Semaphore timeout after 1000ms`).
  - Nếu `inPool == false`: Request **đã bị văng ra ngoài pool**!
- Kiểm tra `comboName`:
  - `comboName: null`: Client/Worker đang gửi request trực tiếp vào `antigravity/gemini-3.8-flash-tiered` thay vì gọi qua alias combo `ag-gemini-pool-3`. Khi gọi thẳng provider, router OmniRoute sẽ chọn account Antigravity toàn cục (bao gồm cả acc free, acc dính 401/403/429 ngoài pool).
  - `comboName: "ag-gemini-pool-3"` nhưng status `503 Service temporarily unavailable: all targets were skipped by pre-dispatch filters`: Tất cả target trong combo bị loại (do concurrency cap hoặc rate limit tạm thời), router kích hoạt failover/sibling fallback không an toàn.

### Bước 3: Phân định hành động sửa chữa
1. **Ép Worker/Client dùng đúng Combo Alias:** Đảm bảo cấu hình gọi model là `ag-gemini-pool-3` (hoặc combo tương ứng), không để client gọi thẳng provider ID.
2. **Khóa Hard Connection Binding trong Combo:** Đảm bảo router không tự ý bốc sibling account ngoài danh sách `models` của combo khi gặp lỗi hoặc bận.
3. **Phân biệt Semaphore 429 vs Upstream 429:**
   - `Semaphore timeout after 1000ms/30000ms for antigravity:<id>`: Acc trong pool chỉ bị kẹt slot xử lý cục bộ, cần tăng/tối ưu queue hoặc spillover, không phải chết token.
   - `[429]: Antigravity upstream error (429)`: Tài khoản thực sự bị Google bóp quota, cần cô lập tạm thời bằng cooldown.
