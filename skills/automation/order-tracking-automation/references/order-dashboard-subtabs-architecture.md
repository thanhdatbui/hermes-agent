# Quy chuẩn thiết kế Sub-tabs chuyển đổi Đơn Hàng TikTok Shop trên Dashboard :1905

## 1. Bối cảnh & Vấn đề thực tế (2026-11-04)
- Khi nâng cấp mục Quản lý Đơn hàng lên Dashboard (`:1905`), ban đầu hệ thống render tuần tự dồn cả 2 khối:
  1. `📦 ĐƠN ĐANG THEO DÕI (15)`
  2. `✅ ĐƠN ĐÃ XONG (8)` (Archived)
- Việc render dồn từ trên xuống dưới tạo ra trải nghiệm người dùng tồi tệ:
  - Khối đơn đang theo dõi có 15 đơn chiếm độ cao hơn 1.500px.
  - Người dùng mở trang ra chỉ nhìn thấy đơn đang theo dõi, tưởng nhầm "không có đơn hoàn thành trong site".
  - Phải cuộn chuột mỏi tay từ trên xuống dưới đáy trang mới nhìn thấy danh sách đơn đã xong.
- User phản ánh gay gắt: *"vs t bảo chia 2 tab nhỏ 1 tab đơn đang theo dõi 1 tab đơn đã xong, mày đéo chia v, tự nhiên phải kéo từ trên xuống ms đc xem đơn đã xong"*.

---

## 2. Giải pháp Kiến trúc: Sub-tabs Toggle O(1)

Trong `tiktok_dashboard.py` (`_ORDERS_VIEW_JS`), thay vì render 2 khối nối tiếp nhau, bắt buộc chia thành 2 sub-tabs ngang hàng ngay dưới tiêu đề của tab Đơn Hàng:

```javascript
let currentOrderSubTab = 'active';

function switchOrderSubTab(subTab) {
    currentOrderSubTab = subTab;
    const btnAct = document.getElementById('btn-subtab-active');
    const btnDone = document.getElementById('btn-subtab-done');
    const secAct = document.getElementById('orders-section-active');
    const secDone = document.getElementById('orders-section-done');
    if (btnAct) btnAct.classList.toggle('active', subTab === 'active');
    if (btnDone) btnDone.classList.toggle('active', subTab === 'done');
    if (secAct) secAct.style.display = (subTab === 'active') ? '' : 'none';
    if (secDone) secDone.style.display = (subTab === 'done') ? '' : 'none';
}
```

### Cấu trúc HTML Render trong `renderOrdersView()`:
1. **Thanh nút chuyển tab con (Sub-tabs Bar):**
   ```html
   <div class="filter-buttons" style="margin-bottom:16px; display:flex; gap:10px;">
       <button class="btn-filter active" id="btn-subtab-active" onclick="switchOrderSubTab('active')">
           📦 Đơn Đang Theo Dõi (15)
       </button>
       <button class="btn-filter" id="btn-subtab-done" onclick="switchOrderSubTab('done')">
           ✅ Đơn Đã Xong (8)
       </button>
   </div>
   ```
2. **Khối Đơn Đang Theo Dõi (`id="orders-section-active"`):**
   - Mặc định `display: ''` (hiển thị khi `currentOrderSubTab === 'active'`).
3. **Khối Đơn Đã Xong (`id="orders-section-done"`):**
   - Mặc định `display: 'none'` (chỉ hiển thị khi bấm sang `[✅ Đơn Đã Xong]`). Khi người dùng chọn tab này, 8 thẻ đơn hoàn tất sẽ bung ngay ở đầu trang, triệt tiêu hoàn toàn nhu cầu cuộn màn hình.

---

## 3. Quy chuẩn Hiển thị Thẻ Đơn Gọn Gàng
- **Menu chính:** Thẻ chỉ hiển thị tóm tắt: Mã đơn, Khách hàng, SĐT, Địa chỉ, Tên sản phẩm, Phân loại, Giá COD, và Link tra cứu bưu cục Phase 2 (J&T / GHN / SPX).
- **Ảnh và chi tiết sâu:** Đưa vào accordion pane `order-detail-{oid}` với nút `📸 Chi tiết & Ảnh đặt đơn ▼`, chỉ bung ra khi người dùng chủ động bấm xem.
- **Link Phase 2:** Bắt buộc có cờ `target="_blank" rel="noopener noreferrer"` kèm biểu tượng mũi tên `↗` để bấm trực tiếp sang hệ thống tra cứu hành trình bưu cục.
