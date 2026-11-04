# Order Dashboard UI Accordion & Archived Split Specification

## 1. Yêu Cầu Thiết Kế Giao Diện Đơn Hàng Trên Web Dashboard (:1905)
Người dùng yêu cầu giao diện quản lý đơn hàng TikTok Shop trên Dashboard web phải gọn gàng, trực quan và không bị ngợp bởi các ảnh chụp màn hình lớn:

1. **Phân tách 2 phân hệ rõ rệt (Archived State Separation):**
   - **`📦 ĐƠN ĐANG THEO DÕI (<count>)`**: Dành cho các đơn đang trong vòng đời (chờ người bán giao hàng, đang bóc mã trên app máy farm, hoặc đang luân chuyển bưu cục). Điều kiện: `order.archived != 1` và status chưa hoàn thành.
   - **`✅ ĐƠN ĐÃ XONG (<count>)`**: Gom toàn bộ các đơn đã hoàn tất chu trình vào một khu vực riêng biệt phía dưới (hoặc collapsible). Điều kiện: `order.archived == 1` hoặc trạng thái chứa các từ khóa (`đã giao`, `giao thành công`, `đã ký nhận`, `ký nhận`, `hoàn thành`, `đã hủy`, `trả hàng`).

2. **Thẻ đơn hàng tinh gọn ở menu ngoài (Concise Exterior Card):**
   - **Không hiển thị ảnh đặt đơn mặc định:** Tuyệt đối không đập ngay ảnh chụp màn hình đặt đơn kích thước lớn vào mắt người dùng ở menu chính làm vỡ bố cục và tốn diện tích cuộn trang.
   - **Các trường tóm tắt bắt buộc:**
     * Mã đơn & Badge trạng thái (`order_id`, `status`).
     * Khách hàng: `👤 <Tên khách> · 📞 <SĐT>`
     * Địa chỉ: `📍 <Địa chỉ>`
     * Sản phẩm: `🏷️ <Tên sản phẩm> (<Phân loại>)` · SL: `<Số lượng>` · Tổng: `<Tiền COD>`
     * Link tra cứu Phase 2 (nếu có): Nếu có `tracking_url` hoặc `tracking_code`, hiển thị badge link nổi bật:
       `<a class="order-track-link" href="${url}" target="_blank">🚚 Tra cứu ${carrier}: ${tracking_code} ↗</a>`
   - **Cơ chế Bung / Thu gọn (Accordion Toggle):**
     * Đặt nút: `<button class="order-toggle-btn" onclick="toggleOrderDetail(...)">📸 Chi tiết & Ảnh đặt đơn ▼</button>`.
     * Khi người dùng click vào mới bung ra (`display: block`) khung chi tiết gồm:
       - Ảnh chụp màn hình đặt đơn gốc (`order-thumb-wrap`).
       - Thông tin máy farm, slot row, tài khoản TikTok đặt đơn, email.
       - Tên shop, dự kiến giao, nhật ký mốc vận chuyển và ghi chú nội bộ.

---

## 2. Kỷ Luật Đồng Bộ Trạng Thái Đã Xong Vào SQLite SSOT
- **SSOT duy nhất:** Bảng `orders` trong `D:/Taadaa/data/farm_master.db`.
- **Cơ chế đồng bộ chuẩn:**
  Sử dụng lệnh chính quy:
  ```bash
  python D:/Taadaa/tools/manage_orders.py --sync-excel
  ```
  Hàm `archived_value(status)` trong `manage_orders.py` tự động nhận diện các trạng thái kết thúc để gán `archived = 1` và lưu đồng thời vào cả cột `archived` lẫn `raw_json`.
- **Chốt chặn an toàn:**
  Tuyệt đối không để đơn đã ký nhận ở trạng thái `archived: 0`. Việc thiếu cờ `archived: 1` sẽ khiến script phân loại vòng đời `order_lifecycle.py` tưởng đơn chưa bóc được mã vận đơn và đẩy nhầm vào hàng đợi bóc mã trên app điện thoại farm.

---

## 3. Cạm Bẫy Gate B Planner & Escape Regex JS Trong Monolith
- **Triệu chứng lỗi:**
  Khi giao task sửa code JavaScript nhúng trong Python (`_ORDERS_VIEW_JS`) qua `unified_patch_pipeline.py`, Advisor Gemini/Sol thường bị lỗi:
  `old_string not unique in tiktok_dashboard.py: count=0`
- **Nguyên nhân:**
  Trong chuỗi JS có đoạn regex tách tên file ảnh:
  `const imgName = String(order.local_image_path || '').split(/[\\/]/).pop();`
  Khi LLM sinh JSON, dấu backslash bị escape kép dẫn đến chuỗi JSON serialize thành `[\/]` thay vì `[\\/]`. Khi Gate B giải mã và so khớp chuỗi thô với file thực tế trên đĩa, `file_text.count(old_string)` trả về 0.
- **Đối sách O(1):**
  Khi soạn task hoặc contract patch cho worker, Coordinator bắt buộc neo vào các mốc text thuần không chứa regex backslash (ví dụ: neo vào `.orders-error { color: #ef4444; }` hoặc `return <article class="order-card">` trở xuống), tránh đưa cả khối chứa `split(/[\\/]/)` vào `old_string`.
