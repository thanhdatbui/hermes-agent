# SumiStore Gemini Pro Sniper: Group 10 Profile Selection, 4-Tier Proxy Alignment & Dynamic Price Drift (2026-10-23)

## 1. Cạm Bẫy GroupId = 0 (GPM Trash) vs GroupId = 10 (Google_Live_Ready)
- **Hiện tượng:** Khi truy vấn trực tiếp bảng `Profiles` trong SQLite `profile_data.db` của GPM để tìm Gmail có cookie sống (`SID`, `HSID`, `SSID`), nếu không lọc theo `GroupId`:
  - Script dễ bốc nhầm các profile đã bị xóa hoặc ném vào thùng rác (`GroupId = 0`).
  - Khi gọi GPM Local API để khởi chạy (`GET /api/v3/profiles/start/{id}?skip_proxy_check=true`), API trả về lỗi:
    ```json
    {"success": false, "data": null, "message": "PROFILE_IN_TRASH"}
    ```
    dẫn đến `data.get("data")` trả về `None` và script văng lỗi `AttributeError: 'NoneType' object has no attribute 'get'`.
- **Quy chuẩn bắt buộc:**
  - Chỉ lọc các profile thuộc **`GroupId = 10` (`Google_Live_Ready`)**.
  - Đây là group duy nhất chứa các tài khoản Gmail đang active, được nuôi dưỡng định kỳ và không nằm trong thùng rác.
  - Đồng thời đối soát loại trừ toàn bộ danh sách `gmail_die_tong.txt` và các tài khoản đã lên Pro trong cả 2 pool (OmniRoute `provider_connections` + AGY CLI sandbox).

---

## 2. Kỷ Luật Đối Soát Proxy 4 Tầng & Bắt Buộc Scope='account' Trên OmniRoute
- **Cạm bẫy rò rỉ IP Direct:**
  - Trong OmniRoute (`~/.omniroute/storage.sqlite`), cờ `proxy_enabled = 1` trên bảng `provider_connections` **CHỈ LÀ ĐIỀU KIỆN CẦN, KHÔNG ĐỦ**.
  - Nếu không có bản ghi tương ứng trong bảng `proxy_assignments` với `scope = 'account'` (hoặc `scope = 'connection'`) gắn kết `scope_id = <connection_id>` với `proxy_id` trong `proxy_registry`, OmniRoute sẽ fallback về IP trực tiếp của máy host (Direct IP Leak), làm lộ danh tính IP Datacenter tới Google upstream và kích hoạt cờ `VALIDATION_REQUIRED` / 403.
- **Quy chuẩn đối soát 4 tầng 1:1:**
  1. **Tầng 1 (Phone Farm S7):** Cổng proxy gán cho máy M (ví dụ `5122` cho M18) trong `PROXYgandienthoai.xlsx`.
  2. **Tầng 2 (GPM Profile):** `raw_proxy` khớp định dạng `test.taadaa.click:51XX:mobiXX:Pass!`.
  3. **Tầng 3 (OmniRoute):**
     - `provider_connections`: `proxy_enabled = 1`.
     - `proxy_assignments`: `scope = 'account'` (và `scope = 'connection'`), `scope_id = <connection_id>`, trỏ đúng `proxy_id` của cổng `51XX` trong `proxy_registry`.
  4. **Tầng 4 (AGY CLI Sandbox):** Sau khi nâng cấp Pro, cấu hình sandbox `acc_XX` trong `profiles_config.json` với proxy `http://mobiXX:Pass@test.taadaa.click:51XX`.

---

## 3. Trượt Giá API SumiStore & Kiểm Tra Số Dư Động
- **Thực tế biến động giá:** Gói `SP-TY9J9GO9` (*Link Gemini Pro 18M*) có thể trượt giá tùy theo đợt cung ứng của shop (từ 9.000đ lên 17.000đ).
- **Quy tắc an toàn:**
  - Tuyệt đối không hardcode ngưỡng kiểm tra số dư tĩnh `if bal < 9000:`.
  - Bắt buộc đọc trường `price` từ endpoint chi tiết sản phẩm (`https://sumistore.me/api/tele-products/SP-TY9J9GO9`) và so sánh `if bal < prod_price:`.
  - Khi số dư vừa đủ cho 1 account (ví dụ `bal = 17,000đ` và `price = 17,000đ`), script cho phép sniper chạy bình thường nhưng cảnh báo nếu số dư không đủ cho đợt mua tiếp theo.

---

## 4. Xác Minh Google Family Details Trong Preflight
- Ngoài việc kiểm tra landing page `one.google.com/home` không bị redirect sang `ServiceLogin`, preflight bắt buộc điều hướng đến:
  ```text
  https://myaccount.google.com/family/details
  ```
- Kiểm tra nội dung DOM / OCR:
  - Phải có tiêu đề *"Gia đình của bạn trên Google"* và nút *"Bắt đầu"* tạo nhóm gia đình.
  - Tuyệt đối không dùng tài khoản đã có nhóm gia đình hoặc từng rời nhóm gia đình gần đây (Google Family 12-month cooldown).
