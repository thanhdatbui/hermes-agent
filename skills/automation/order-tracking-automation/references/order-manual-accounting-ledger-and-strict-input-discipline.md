# Kỷ Luật Hạch Toán Kế Toán Đơn Hàng Nhập Tay (Clean Manual Accounting Ledger & Strict Input Discipline)

## 1. Bối cảnh & Bài học thực tế (Session 2026-11-05)
Trong quá trình xây dựng tính năng kế toán theo dõi lời lỗ cho farm đơn hàng TikTok Shop:
- **Lỗi 1 (Tự động nạp toàn bộ đơn cũ):** Agent tự ý map 23 đơn hàng TikTok (gồm dầu ăn, sạc, thư cảm ơn, nước mắm...) từ bảng `orders` của hệ thống bưu cục vào bảng tính tài chính, khiến bảng bị đầy rác và làm User khó chịu ("K tự động nhập hết đơn vào như v nhé xoá hết đi. T sẽ yêu cầu nhập vào sau").
- **Lỗi 2 (Tự suy diễn ghi nhận tài chính khi User chỉ báo trạng thái bưu cục):** Khi User thông báo:
  * `DH-20261029-005` và `006`: "2 đơn này đã nhận và bán ra đc 55.000 mỗi đơn."
  * `DH-20261029-007`: "đơn này đã nhận."
  * `DH-20261029-013`: "đơn này đã nhận."
  * `DH-20261029-009`: "đơn này nhận và thành tiền đc 23.000"
  Agent đã tự ý đưa cả đơn 007 (Nước hoa) và 013 (Cáp sạc) vào bảng sổ kế toán với Doanh thu = 0đ và tính tiền lời âm (-1đ và -39.000đ), dẫn đến User phản ứng gay gắt: *"tao có bảo mày ghi nc hoa vs cáp sạc vào đâu? ủa chứ t cung cấp thông tin gì thì ghi đúng cái đó thôi"*.

---

## 2. Nguyên tắc Bất biến: Strict Input Discipline (Cung cấp gì ghi đúng cái đó)
1. **Phân định rạch ròi 2 mục đích dữ liệu:**
   - **Mục đích 1: Quản lý bưu cục / Nhận hàng (`orders` table):**
     * Khi User báo "đã nhận" hoặc "đã nhận hàng", thao tác này thuộc về **Vòng đời đơn hàng bưu cục**.
     * BẮT BUỘC cập nhật `status = 'Đã giao hàng thành công (Đã ký nhận)'` và `archived = 1` để đưa vào tab **[✅ Đơn Đã Xong]**.
   - **Mục đích 2: Sổ kế toán lời lỗ (`order_accounting` table):**
     * CHỈ ĐƯỢC PHÉP ghi nhận dòng tài chính vào bảng kế toán khi User **CUNG CẤP GIÁ BÁN / THÀNH TIỀN THỰC TẾ** (ví dụ: "bán ra được 55.000", "thành tiền được 23.000").
     * Đơn hàng chỉ mới "đã nhận" mà User CHƯA cung cấp giá bán ➔ **TUYỆT ĐỐI CẤM TỰ ĐỘNG GHI SỔ KẾ TOÁN VỚI DOANH THU 0Đ HAY TẠM TÍNH LỜI ÂM!** Phải đợi User bán được và yêu cầu ghi sổ mới được nhập.

2. **Khởi tạo Bảng Kế Toán Sạch Sẽ (Clean Slate Invariant):**
   - Bảng tài chính `order_accounting` ban đầu BẮT BUỘC phải **trống trơn (0 dòng, Tổng Doanh Thu = 0₫, Tổng Vốn = 0₫, Tổng Lời = 0₫)**.
   - CẤM TUYỆT ĐỐI tự động duyệt CSDL bưu cục để đổ hàng loạt đơn hàng vào bảng kế toán.

---

## 3. Kiến trúc CSDL & 6 Trường Chuẩn Hóa
Bảng SQLite SSOT riêng biệt: `order_accounting`
```sql
CREATE TABLE IF NOT EXISTS order_accounting (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_code TEXT,       -- Mã đơn (DH-20261029-005)
    item_name TEXT,        -- Mặt hàng (Dầu Ăn Simply 1L)
    import_date TEXT,      -- Ngày nhập (YYYY-MM-DD)
    import_price INTEGER,  -- Giá nhập / vốn (8.000)
    sale_price INTEGER,    -- Giá bán / doanh thu (55.000)
    profit INTEGER,        -- Tiền lời = sale_price - import_price (47.000)
    note TEXT,             -- Ghi chú (Đã nhận và bán ra 55k)
    created_at TEXT        -- Timestamp tạo
);
```

---

## 4. Giao diện Sổ Đơn Hàng & Bộ Lọc Tổng Kết Tháng
- **Dropdown chọn Tháng:** Lọc động theo `YYYY-MM` (hoặc `Tất cả các tháng`).
- **3 KPI Tổng Kết Tháng:**
  * 📦 **Tổng Vốn Nhập:** `SUM(import_price)` của tháng được chọn.
  * 💵 **Tổng Doanh Thu:** `SUM(sale_price)` của tháng được chọn.
  * 📈 **Tổng Tiền Lời:** `SUM(profit)` của tháng được chọn (xanh lá nếu `>= 0`, đỏ nếu `< 0`, kèm tỷ suất lợi nhuận `%`).
- **Form Nhập Tay:** Gồm Ngày nhập (date), Mã đơn (text), Mặt hàng (text), Giá nhập (number), Giá bán (number), Ghi chú (text), Nút `+ Thêm Đơn`.

---

## 5. Quy trình Xử lý Chuẩn khi nhận tin nhắn User
Khi nhận danh sách đơn từ User:
1. Duyệt từng dòng thông tin của User:
   - Nếu có từ khóa "đã nhận" / "nhận rồi": Chuyển trạng thái đơn sang Đã xong trong `orders` (`archived = 1`).
   - Nếu CÓ ghi kèm "bán ra được X" hoặc "thành tiền X": Lấy đúng giá bán đó, truy xuất vốn (`import_price`), tính tiền lời và INSERT vào `order_accounting`.
   - Nếu KHÔNG ghi giá bán: KHÔNG đụng vào bảng kế toán `order_accounting`.
2. Báo cáo trực diện:
   - Danh sách đơn đã chuyển sang [Đã Xong].
   - Danh sách đơn được ghi nhận vào Sổ Kế Toán (đầy đủ Vốn, Bán, Lời).
   - Tổng kết tài chính đợt đó.
