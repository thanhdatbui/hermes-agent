# Kỷ luật Sổ Đơn Hàng Nhập Tay Độc Lập & Tổng Kết Tháng (Clean Manual Accounting Ledger)

## 1. Bối cảnh & Bài học thực tế từ User
- **Sai lầm của Agent:** Tự động lấy toàn bộ danh sách 23 đơn hàng TikTok cào được trong hệ thống đổ vào bảng tài chính để tính tiền lời / giá vốn khiến người dùng bị ngợp, rối mắt và dữ liệu bị rác.
- **Yêu cầu dứt khoát của User:** 
  > *"K tự động nhập hết đơn vào như v nhé xoá hết đi. T sẽ yêu cầu nhập vào sau. Làm bảng dữ liệu đơn giản thôi kiểu mã đơn mặt hàng r giá nhập giá bán lời. Xong có tổng kết tháng. À thêm ngày nhập nữa."*
- **Quy tắc bất biến:**
  1. **Tách biệt hoàn toàn:** Bảng hạch toán giá vốn / lời lỗ (Sổ Đơn Hàng Nhập Tay) PHẢI ĐỘC LẬP HOÀN TOÀN với bảng theo dõi bưu cục Phase 1/Phase 2 (`orders` table). CẤM tự động sync hay tự động map đơn farm vào bảng tính lời khi User chưa yêu cầu!
  2. **Bắt đầu trống trơn (Clean State):** Bảng kế toán ban đầu phải sạch sẽ (0 đơn), để trống cho User tự điền từng đơn.
  3. **Đúng cấu trúc 6 trường tối giản:**
     - `order_date`: Ngày nhập hàng (`YYYY-MM-DD`).
     - `order_code`: Mã đơn (VD: `DH-01`, `DH-20261105-001`).
     - `item_name`: Mặt hàng / Sản phẩm.
     - `cost_price`: Giá nhập (tiền vốn).
     - `sale_price`: Giá bán (doanh thu).
     - `profit`: Tiền lời (`Giá bán - Giá nhập`, tự động tính).
  4. **Có tổng kết theo Tháng:**
     - Bộ lọc dropdown chọn Tháng (`YYYY-MM`) hoặc `Tất cả các tháng`.
     - 3 KPI trên đầu bảng tự động gom số liệu theo tháng đang chọn:
       * 📦 **Tổng Vốn Nhập Tháng** (`sum(cost_price)`)
       * 💵 **Tổng Doanh Thu Tháng** (`sum(sale_price)`)
       * 📈 **Tổng Tiền Lời Tháng** (`sum(profit)` kèm % tỷ suất lợi nhuận).

---

## 2. Thiết kế CSDL SQLite (`farm_master.db`)

Bảng SQLite SSOT chuyên biệt `order_accounting`:
```sql
CREATE TABLE IF NOT EXISTS order_accounting (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_code TEXT,
    item_name TEXT,
    import_date TEXT,
    import_price INTEGER DEFAULT 0,
    sale_price INTEGER DEFAULT 0,
    profit INTEGER DEFAULT 0,
    note TEXT,
    created_at TEXT
);
```

Hàm truy vấn chuẩn trong DAL (`farm_db.py`):
```python
def get_accounting_records(month_str=None) -> list:
    """Lấy danh sách các dòng ghi chép đơn hàng nhập tay từ SQLite."""
    sql = "SELECT id, order_code, item_name, import_date, import_price, sale_price, profit, note, created_at FROM order_accounting"
    params = []
    if month_str and month_str != 'all':
        sql += " WHERE import_date LIKE ?"
        params.append(f"{month_str}%")
    sql += " ORDER BY import_date DESC, id DESC"
    with connect() as conn:
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

def add_accounting_record(order_code, item_name, import_date, import_price, sale_price, note='') -> int:
    """Thêm 1 dòng ghi chép đơn hàng nhập tay vào SQLite."""
    from datetime import datetime
    p_import = int(import_price or 0)
    p_sale = int(sale_price or 0)
    p_profit = p_sale - p_import
    with connect(write=True) as conn:
        cur = conn.execute(
            "INSERT INTO order_accounting (order_code, item_name, import_date, import_price, sale_price, profit, note, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (str(order_code or '').strip(), str(item_name or '').strip(), str(import_date or '').strip(), p_import, p_sale, p_profit, str(note or '').strip(), datetime.now().isoformat())
        )
        return cur.lastrowid
```

---

## 3. Quy chuẩn Giao diện UI Dashboard (`:1905`)

1. **Vị trí Tab:** Là Sub-tab thứ 3 `💰 Sổ Đơn Hàng Nhập Tay` nằm ngang hàng với:
   - `[📦 Đơn Đang Theo Dõi]`
   - `[✅ Đơn Đã Xong]`
   - `[💰 Sổ Đơn Hàng Nhập Tay]`
2. **Form Nhập Nhanh:** Ngay phía trên bảng dữ liệu, gồm:
   - Ô Ngày nhập (`input type="date"`, mặc định ngày hiện tại).
   - Ô Mã đơn (`input type="text"`).
   - Ô Mặt hàng (`input type="text"`).
   - Ô Giá nhập (`input type="number"` viền cam).
   - Ô Giá bán (`input type="number"` viền xanh dương).
   - Ô Ghi chú (tùy chọn).
   - Nút `+ Thêm Đơn` (màu xanh lá): Khi bấm sẽ tự động tính lời, thêm vào bảng và cập nhật ngay 3 thẻ KPI tổng kết tháng mà không cần tải lại toàn bộ trang.
3. **Cơ chế Xóa:** Cột cuối có nút `✕` để xóa dòng nhầm lẫn và cập nhật lại KPI tức thì.
