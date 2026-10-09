# Dashboard Machine Filter Substring Collision & DB Reconciliation (2026-09-25)

## 1. Bối cảnh & Hiện tượng (Incident)
- Người vận hành quan sát dashboard (`tiktok_dashboard.py`) tại bảng Sức khoẻ cụm máy (Heatmap), click chọn hoặc bấm "🔍 Xem Nick" ở Máy 16 (`m16`).
- Kết quả hiển thị bung ra **9 tài khoản**, trong khi quy chuẩn thiết bị Samsung S7 trên farm chỉ chứa tối đa 8 nick (Slot 1–8).
- Nghi vấn ban đầu: Máy bị gán thừa nick, parasite account, lỗi nạp trùng slot, hoặc database bị lệch/corrupt.

## 2. Phân tích nguyên nhân gốc rễ (Root Cause)
1. **Frontend Search Collision:**
   - Hàm `jumpToMachine(m)` tự động gán giá trị ô tìm kiếm: `searchInput.value = 'm' + m` (ví dụ `m16`).
   - Hàm lọc `filterData()` trong frontend template trước đó sử dụng logic tìm chuỗi con trên username:
     ```javascript
     const matchQuery = !query ||
         (item.created_at && item.created_at.includes(query)) ||
         item.username.toLowerCase().includes(query) ||
         ...
     ```
   - Tài khoản thứ 9 xuất hiện trong kết quả là **`@lenam16696`**.
   - Phân tích chuỗi: `@lenam16696` chứa cụm ký tự `m16` (`lena[m16]696`). Khi `query = 'm16'`, biểu thức `item.username.toLowerCase().includes('m16')` trả về `true`!

2. **Thực tế Database & Thiết bị (Source of Truth):**
   - Truy vấn SQLite `D:/Taadaa/data/tiktok_tracker.db`:
     - Bảng `farm_account_info`: `@lenam16696` được gán chính xác tại `may = 63, tik = 6, host_id = 'kibe'`.
     - Máy 16 có chính xác 8 nick (Slot 1–8).
   - Thiết bị vật lý: Máy 16 không hề chứa nick `@lenam16696`. Đây thuần túy là lỗi hiển thị lọc chuỗi con của giao diện web.

## 3. Quy tắc Fix & Chống Va Chạm Định Danh (Identifier Query Isolation)
Khi thiết kế bộ lọc hoặc công cụ tìm kiếm có kết hợp lọc theo ID thiết bị/slot:
1. **Phân loại Query trước khi Match (Typed Query Classification):**
   - Kiểm tra nếu query mang định dạng mã máy (`/^m\d+$/i`): CHỈ match chính xác theo trường số máy (`item.may && ('m' + item.may).toLowerCase() === query`). TUYỆT ĐỐI CẤM fallback so sánh chuỗi con với `username`, `status`, hay `created_at`.
   - Kiểm tra nếu query mang định dạng slot Tik (`/^(t|tik\s*)\d+$/i`): CHỈ match chính xác theo trường slot `item.tik`.
   - Chỉ khi query là chuỗi tự do (tên nick, ngày tháng, trạng thái) mới cho phép tìm chuỗi con trên `username`.

2. **Kỷ luật Đối soát DB trước khi phán xét thiết bị:**
   - Khi giao diện hiển thị số nick bất thường (>8 nick trên 1 máy), Coordinator BẮT BUỘC kiểm tra trực tiếp qua DB `tiktok_tracker.db` (`SELECT username, may, tik FROM farm_account_info WHERE may = ?`) và `inspect_machine.py`.
   - CẤM vội vàng kết luận máy bị parasite/văng nick hay can thiệp ADB logout khi chưa đối chiếu Source of Truth.
