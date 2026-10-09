# Quy trình chẩn đoán đối soát tài khoản Google AI Pro / Antigravity giữa GPM Profile và OmniRoute (:20129)

Tài liệu này ghi lại quy trình chẩn đoán O(1) khi người dùng thắc mắc: *"Đã nâng Google AI Pro (5TB) cho mail X nhưng trên OmniRoute vẫn hiển thị Free / không thấy Pro"*.

---

## 1. Triệu chứng & Nguyên nhân phổ biến

1. **Chưa OAuth import mail vào OmniRoute:**
   - Mail được nâng Pro trên trình duyệt GPM profile riêng biệt.
   - Nhưng người vận hành chưa thực hiện đăng nhập OAuth Google Antigravity cho mail này trong OmniRoute.
   - Kết quả: Mail hoàn toàn vắng mặt trong DB `storage.sqlite` (`provider_connections`), chỉ có các mail khác có tên tương tự (dễ nhầm lẫn, ví dụ `ninhy05102002` vs `ninhvan04061999`).

2. **Cơ chế nhận diện Tier Pro của OmniRoute:**
   - Khi hoàn tất OAuth Antigravity, OmniRoute gọi `POST /v1internal:loadCodeAssist`.
   - Hàm `extractCodeAssistSubscriptionTier` trích xuất `paidTier.name` hoặc `paidTier.id` (`g1-pro-tier`).
   - Hàm `syncAntigravitySubscriptionIfNeeded` lưu `tier: "g1-pro-tier"`, `plan: "Pro"` vào `provider_specific_data`.
   - Nếu mail chưa từng OAuth, OmniRoute không thể tự biết tài khoản Google đó đã nâng cấp Google One AI Pro.

3. **Chưa thêm Connection vào Combo Pro (`ag-gemini-pool-3`):**
   - Dù connection đã có nhãn `g1-pro-tier`, nếu chưa được gán vào danh sách `models` của combo `ag-gemini-pool-3`, request tới combo Pro sẽ không định tuyến qua tài khoản mới.

---

## 2. Quy trình kiểm tra đối soát O(1)

### Bước 1: Tra cứu trực tiếp trong SQLite DB của OmniRoute
Kiểm tra xem email đã tồn tại trong danh sách connection chưa:
```python
import sqlite3
conn = sqlite3.connect("C:/Users/Kibe/.omniroute/storage.sqlite")
cur = conn.cursor()
target_email = "ninhvan04061999@gmail.com"

cur.execute("SELECT id, email, name, provider, provider_specific_data FROM provider_connections WHERE email = ?", (target_email,))
row = cur.fetchone()
if not row:
    print(f"Connection {target_email} CHƯA TỒN TẠI trong OmniRoute!")
else:
    print("Connection details:", row)
```

### Bước 2: Đối soát với GPM Profile qua Local API (:19995)
Xác định chính xác profile GPM đang chứa mail cần kết nối:
```python
import urllib.request, json

page = 1
while True:
    req = urllib.request.urlopen(f"http://127.0.0.1:19995/api/v3/profiles?page={page}&per_page=100")
    res = json.loads(req.read().decode())
    data = res.get("data", [])
    if not data:
        break
    for p in data:
        if "ninhvan" in p.get("name", "").lower():
            print("Found GPM Profile:", p.get("id"), p.get("name"), p.get("raw_proxy"))
    page += 1
```

### Bước 3: Đồng bộ và đưa vào Combo Pro
1. Mở profile GPM tương ứng để mở session browser sẵn sàng OAuth.
2. Thêm Provider Google Antigravity trên Dashboard OmniRoute (`http://127.0.0.1:20129/dashboard/providers`) hoặc qua flow OAuth.
3. Sau khi auth thành công, kiểm tra `GET /api/providers/<connection_id>` để xác nhận `tier: "g1-pro-tier"`.
4. Gọi `PUT /api/combos/22975610-b162-41b9-b6b3-30be076265bd` để thêm model mới vào `ag-gemini-pool-3` với `connectionId` tương ứng.
