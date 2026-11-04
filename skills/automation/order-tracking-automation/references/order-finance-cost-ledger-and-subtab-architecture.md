# Order Finance & Cost Ledger Architecture (Bảng Lời Lỗ & Giá Vốn Đơn Hàng)

## 1. Bối cảnh & Yêu cầu Người dùng
Người dùng yêu cầu bổ sung bảng dữ liệu quản lý tài chính / giá vốn hàng hóa ngay trên Web Dashboard (`:1905`) trong tab "🧾 Đơn Hàng TikTok":
- Bổ sung thẻ con (sub-tab) thứ 3 bên cạnh 2 thẻ hiện tại:
  1. `[📦 Đơn Đang Theo Dõi]`
  2. `[✅ Đơn Đã Xong]`
  3. `[💰 Bảng Lời Lỗ & Giá Vốn]` (Finance Subtab)
- Yêu cầu hạch toán chi tiết:
  * **Giá bán:** Số tiền thực thu COD / Tổng tiền của đơn hàng (`cod_amount` hoặc `item.total`).
  * **Giá nhập (Giá vốn):** Cho phép nhập trực tiếp trên từng đơn hàng qua ô `<input type="number">`, tự động lưu ngay khi Enter hoặc rời chuột (blur).
  * **Tiền lời:** Tự động tính toán theo công thức: `Tiền Lời = Giá Bán - Giá Nhập`. Mức lời hiển thị xanh lá `+...₫`, nếu lỗ hiển thị đỏ `-...₫`.
  * **Tổng lời & Thống kê KPI:** 3 thẻ chỉ số trên đầu bảng cập nhật thời gian thực (Tổng Doanh Thu, Tổng Vốn Nhập, Tổng Tiền Lời và Tỷ suất lợi nhuận Margin %).

## 2. Thiết kế Cơ sở Dữ liệu (SQLite SSOT `farm_master.db`)
- Bảng `orders` được bổ sung trường `cost_price INTEGER DEFAULT 0`.
- Cơ chế đồng bộ kép (Dual Sync):
  ```python
  def update_order_cost(order_id: str, cost_price: int) -> bool:
      import json
      oid = str(order_id).strip()
      with connect(write=True) as conn:
          row = conn.execute("SELECT raw_json FROM orders WHERE order_id = ?", (oid,)).fetchone()
          if not row:
              return False
          data = json.loads(row["raw_json"]) if row["raw_json"] else {}
          data["cost_price"] = int(cost_price)
          raw_json_updated = json.dumps(data, ensure_ascii=False)
          try:
              conn.execute("UPDATE orders SET cost_price = ?, raw_json = ? WHERE order_id = ?", (int(cost_price), raw_json_updated, oid))
          except Exception:
              conn.execute("UPDATE orders SET raw_json = ? WHERE order_id = ?", (raw_json_updated, oid))
      sync_orders_json_from_sqlite()
      return True
  ```

## 3. Kiến trúc API Backend (`tiktok_dashboard.py`)
Thêm endpoint xử lý cập nhật giá vốn tức thời:
- Endpoint: `POST /api/orders/update-cost`
- Request: `{"order_id": "DH-YYYYMMDD-XXX", "cost_price": 50000}`
- Response: `{"success": true, "order_id": "DH-YYYYMMDD-XXX", "cost_price": 50000}`

## 4. Giao diện Người dùng & Trải nghiệm Nhập Liệu
- Sub-tab navigation: Sử dụng `switchOrderSubTab(t)` điều hướng giữa `'active'`, `'done'`, `'finance'`. Không làm người dùng phải cuộn chuột dài từ trên xuống dưới.
- Tự động tính toán không cần tải lại trang (Zero Reload):
  * Khi người dùng nhập giá nhập vào ô input `#cost-input-{oid}`:
  * Sự kiện `onkeydown (Enter)` hoặc `onblur` gọi `saveOrderCost(oid, value)`.
  * Phản hồi thị giác tức thì: hiển thị tick xanh `✓ Đã lưu` trong 2.5 giây.
  * Cập nhật ngay lập tức cột Tiền Lời `#row-profit-{oid}` tương ứng.
  * Gọi `recalcFinanceTotals()` tính toán lại 3 thẻ KPI trên cùng và dòng Footer `TỔNG CỘNG` của bảng.
