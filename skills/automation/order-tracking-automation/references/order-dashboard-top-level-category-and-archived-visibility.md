# Order Dashboard Top-Level Category Architecture & Archived Visibility Triage

## 1. Ngữ Cảnh & Vấn Đề
- Người dùng yêu cầu đưa mục Đơn Hàng lên thanh điều hướng chính (`.main-category-tabs`) ngang hàng với `Giám Sát TikTok`, `Sổ Cái Farm (SQLite)`, và `Quản Lý Proxy`.
- Người dùng phản ánh: *"hiện tại t chưa thấy đơn hoàn thành có trong site"*.
- Nguyên nhân: Trước đó, nút Đơn Hàng nằm lọt thỏm trong thanh toolbar con (`.toolbar .filter-buttons`) bên dưới KPI cards. Người dùng truy cập tab Đơn Hàng nhưng vì khối đơn đang theo dõi dài và trang chưa scroll xuống dưới nên không thấy khối `✅ ĐƠN ĐÃ XONG (8)` (nằm ở vị trí scroll Y ~1580px). Hơn nữa, việc để nút ở toolbar con khiến người dùng phải cuộn qua các bảng số liệu farm gây rối mắt.

## 2. Kiến Trúc Điều Phối Top-Level Tabs (`main-category-tabs`)
Để đưa `🧾 Đơn Hàng TikTok` lên làm Menu chính cấp cao nhất:

### Bước 1: HTML Injection vào `.main-category-tabs`
Trong `tiktok_dashboard.py` (hàm `render_html_page`):
```html
<div class="main-category-tabs" style="display:flex; gap:10px; margin-bottom:14px; border-bottom:2px solid #2a2f3a; padding-bottom:10px; flex-wrap:wrap;">
    <button class="btn-filter active" id="main-tab-tiktok" onclick="switchMainCategory('tiktok')" style="font-size:1rem; font-weight:700; padding:8px 16px;">📊 Giám Sát TikTok</button>
    <button class="btn-filter" id="main-tab-orders" onclick="switchMainCategory('orders')" style="font-size:1rem; font-weight:700; padding:8px 16px;">🧾 Đơn Hàng TikTok</button>
    <button class="btn-filter" id="main-tab-ledger" onclick="switchMainCategory('ledger')" style="font-size:1rem; font-weight:700; padding:8px 16px;">📓 Sổ Cái Farm (SQLite)</button>
    <button class="btn-filter" id="main-tab-proxy" onclick="switchMainCategory('proxy')" style="font-size:1rem; font-weight:700; padding:8px 16px;">🌐 Quản Lý Proxy</button>
</div>
```
Đồng thời **gỡ bỏ** nút `<button id="btn-orders">` trong `.toolbar` để chống trùng lặp.

### Bước 2: Đồng Bộ Hàm Điều Hướng `switchMainCategory(cat)`
Hàm `switchMainCategory` được khai báo trong `dashboard/ledger_component.py` và nhúng vào trang. Bắt buộc xử lý rạch ròi 4 trạng thái:
1. `cat === 'orders'`:
   - Active tab: `main-tab-orders`
   - Ẩn: `.kpi-grid`, `.toolbar`, `#row-cluster`, `#row-tik-filter`, `#row-delta-filter`, `#ledgerContainer`, `#proxyManagerContainer`, `#mainTableContainer`, `#fleetContainer`, `#followHealthContainer`, `#nurtureHealthContainer`.
   - Hiện: `#ordersContainer`.
   - Gọi: `setView('orders')` hoặc `renderOrdersView()`.
2. `cat === 'tiktok'`:
   - Active tab: `main-tab-tiktok`
   - Hiện: `.kpi-grid`, `.toolbar`, `#row-cluster`, `#row-tik-filter`.
   - Khôi phục view bảng tài khoản TikTok (`setView('all')`).
3. `cat === 'ledger'` / `cat === 'proxy'`:
   - Chuyển tab tương ứng, ẩn `#ordersContainer`.

### Bước 3: Đồng Bộ Hàm `setView('orders')` trong `_ORDERS_VIEW_JS`
Khi người dùng bấm vào tab đơn hàng, `setView` phải active đúng cả nút `main-tab-orders`:
```javascript
const mOrders = document.getElementById('main-tab-orders');
if (mOrders) mOrders.classList.add('active');
```

## 3. Quy Chuẩn Hiển Thị Đơn Hoàn Thành (`✅ ĐƠN ĐÃ XONG`)
- Không để đơn hoàn thành bị che khuất hay chìm dưới đáy trang mà không có chỉ dẫn.
- Chia 2 danh sách rõ rệt qua `isOrderDone(order)`:
  - `activeOrders = data.filter(o => !isOrderDone(o))` -> Tiêu đề: `📦 ĐƠN ĐANG THEO DÕI (${activeOrders.length})`
  - `doneOrders = data.filter(o => isOrderDone(o))` -> Tiêu đề: `✅ ĐƠN ĐÃ XONG (${doneOrders.length})`
- Đơn đã xong hiển thị gọn gàng, có link tra cứu bưu cục (`862635932520 ↗`), trạng thái badge xanh `Đã giao hàng thành công (Đã ký nhận)` và nút accordion xem ảnh/chi tiết.
- Khi báo cáo người dùng: Chỉ rõ vị trí hiển thị (nằm ngay dưới khối đơn đang theo dõi, scroll chuột xuống) kèm liệt kê danh sách cụ thể từng đơn đã xong đã nạp trong DB để đối soát.

## 4. Kỷ Luật Reload Dashboard & Process Management
- Trên Windows, sau khi sửa code dashboard/ledger, chạy `python D:/Taadaa/tools/restart_tiktok_dashboard.py` hoặc kill tận gốc các process `pythonw.exe` / `python.exe` đang chiếm port `1905`.
- Kiểm tra liveness bằng curl hoặc `urllib.request.urlopen('http://127.0.0.1:1905/health', timeout=5)` trước khi truy cập bằng browser tools.
- Dùng browser tool click vào tab và kiểm tra `document.getElementById('ordersContainer').innerHTML` để xác thực visual evidence thực tế trước khi phản hồi người dùng.
