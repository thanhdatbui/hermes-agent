# OmniRoute Model Catalog Hidden Quota Suppression Trap

## Symptom
Trên giao diện OmniRoute Dashboard (`/dashboard/usage` - Provider Limits / Quota Cards), các thẻ tài khoản Antigravity vẫn hiển thị đầy đủ thanh hạn ngạch Claude (`Claude Opus 4.6 Thinking`, `Claude Sonnet 4.6`), nhưng **toàn bộ thanh hạn ngạch Gemini biến mất hoàn toàn**, không hiển thị bất kỳ model Gemini nào.

## Root Cause & Architecture
1. **Model Catalog vs Quota Binding:**
   - Trong database OmniRoute (`C:\Users\Kibe\.omniroute\storage.sqlite`), bảng `key_value` lưu trữ cấu hình ghi đè mô hình tại:
     `namespace = 'modelCompatOverrides'` và `key = '<provider>'` (ví dụ `antigravity`).
   - Khi mô hình bị ẩn trong danh mục (ở trang `/dashboard/providers/[id]` -> phần **Mô hình có sẵn / Available Models** bằng cách bấm icon con mắt `visibility_off` hoặc nút **"Ẩn tất cả / Hide all"**), OmniRoute lưu danh sách JSON dạng:
     `[{"id": "gemini-3.7-flash-tiered", "isHidden": true}, {"id": "gemini-pro-agent", "isHidden": true}, ...]`

2. **Cơ chế lọc hiển thị Quota trên Frontend (`useVisibleQuotaData`):**
   - Hook `useVisibleQuotaData.ts` trên trang Usage tự động fetch danh mục qua `/api/provider-models?provider=antigravity`.
   - Hàm `collectHiddenQuotaModelIds` thu thập toàn bộ `record.id` có `isHidden === true`.
   - Hàm `filterHiddenModelQuotas` duyệt qua object `quotas` của từng connection và **loại bỏ triệt để** bất kỳ quota key nào trùng với danh sách model bị ẩn.

3. **Bẫy Upstream Quota Buckets của Google Antigravity:**
   - API hạn ngạch upstream của Google (`retrieveUserQuota`) trả về quota theo các bucket định danh gốc:
     - `gemini-3.7-flash-tiered` (đại diện cho dòng Gemini Flash)
     - `gemini-pro-agent` (đại diện cho Gemini 3.1 Pro High)
     - `gemini-3.1-flash-lite` (đại diện cho Flash Lite)
   - Nếu operator hoặc AI agent dùng browser click **"Ẩn tất cả"** để dọn dẹp danh sách model cho đỡ loãng rồi chỉ unhide alias như `gemini-3.7-flash-high`, thì các key bucket gốc (`tiered`, `pro-agent`, `lite`) vẫn mang `isHidden: true`.
   - Kết quả: `filterHiddenModelQuotas` âm thầm lọc sạch toàn bộ hạn ngạch Gemini trên dashboard.

## Diagnostic Recipe
Kiểm tra trực tiếp trong SQLite bằng Python O(1):
```python
import sqlite3, json

conn = sqlite3.connect(r'C:\Users\Kibe\.omniroute\storage.sqlite')
cur = conn.cursor()
cur.execute("SELECT value FROM key_value WHERE namespace = 'modelCompatOverrides' AND key = 'antigravity'")
row = cur.fetchone()
if row:
    items = json.loads(row[0])
    hidden = [x['id'] for x in items if x.get('isHidden')]
    print("Hidden models:", hidden)
```

## Remediation
### Cách 1: Thao tác Web UI
1. Mở `http://<omniroute_host>:20129/dashboard/providers` -> Chọn nhà cung cấp **Antigravity**.
2. Cuộn xuống mục **Mô hình có sẵn (Available Models)**.
3. Chuyển bộ lọc sang **"Chỉ các mô hình bị ẩn"**.
4. Bấm bật lại biểu tượng con mắt (`visibility`) cho các model: `gemini-3.7-flash-tiered`, `gemini-pro-agent`, `gemini-3.1-flash-lite`.
5. F5 lại `/dashboard/usage`, các thanh quota Gemini sẽ xuất hiện lại ngay lập tức.

### Cách 2: Cập nhật trực tiếp Database SQLite
Cập nhật `modelCompatOverrides` chuyển `isHidden = False` cho các bucket model chính của Antigravity.

## Safety Rule cho Coordinator & Worker
- **CẤM TUYỆT ĐỐI** dùng browser automation click "Ẩn tất cả" (`Hide all`) trên giao diện Provider của OmniRoute để giải quyết bài toán "loãng model" của client (Hermes/Telegram).
- Muốn thu gọn model hiển thị trên client, phải cấu hình allowlist/catalog ở tầng client (Hermes `config.yaml` / `providers.omni.models`), không được ẩn ở tầng provider model catalog của OmniRoute vì sẽ phá vỡ hiển thị hạn ngạch trên Dashboard.
