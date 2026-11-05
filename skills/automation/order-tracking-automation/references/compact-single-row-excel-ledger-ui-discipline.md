# Kỷ luật Trình Bày Bảng Kế Toán Đơn Hàng Dạng Excel 1 Dòng (Compact 1-Row Excel Ledger Discipline)

## 1. Bối cảnh & Vấn đề (The Issue)
Khi xây dựng Bảng Lời Lỗ & Giá Vốn (hoặc Sổ Kế Toán Đơn Hàng), Agent có xu hướng thiết kế giao diện theo kiểu "thẻ chi tiết" hoặc bảng lồng nhiều dòng trong 1 ô (multi-line):
- Cột Mã đơn kèm dòng nhỏ hiển thị ngày/giờ (`<br><span style="font-size:0.75rem;">🕒 2026-10-29 11:52</span>`).
- Cột Sản phẩm kèm dòng phân loại (`<br><span>PL: Mặc định</span>`).
- Cột Khách hàng lồng tên và SĐT trên 2 dòng.
- Cột Trạng thái chiếm thêm diện tích.

**Hậu quả:**
Bảng bị giãn cao, rối mắt, người dùng không thể nhìn bao quát nhiều đơn cùng lúc như bảng tính Excel thông thường. User phản hồi gắt: *"Làm bảng gọn gàng như kiểu excel ấy làm dài dòng quá. Mỗi đơn 1 dòng 1 hàng thôi."*

---

## 2. Invariant Quy Chuẩn Trình Bày (Hard Invariants)

1. **Chuẩn 1 Dòng 1 Hàng Duy Nhất (Single-Line Row Invariant):**
   - TUYỆT ĐỐI CẤM dùng thẻ `<br>` làm rớt dòng nội dung bên trong cell.
   - Thêm thuộc tính CSS `white-space: nowrap !important;` và `vertical-align: middle !important;` cho toàn bộ `td` trong bảng.
   - Tên sản phẩm quá dài thì đặt `max-width: 240px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;` kèm thuộc tính `title="..."` để rê chuột vào xem đầy đủ, không để tên hàng đẩy vỡ layout dòng.

2. **Lọc Bỏ Cột Thừa Không Cần Thiết Ở Bảng Kế Toán:**
   - Bảng tài chính / kế toán lời lỗ CHỈ tập trung vào thông số kinh doanh.
   - **CẮT BỎ HOÀN TOÀN:** Cột Tên Khách Hàng / SĐT (đã có ở tab Đang Theo Dõi / Đã Xong), Cột Trạng Thái chi tiết.
   - **CHỈ GIỮ LẠI ĐÚNG 6-7 CỘT CHUẨN:**
     * `#` (STT căn giữa)
     * `MÃ ĐƠN` (Code ngắn gọn, font monospace)
     * `MẶT HÀNG` (Tên sản phẩm 1 dòng)
     * `NGÀY NHẬP` (Chỉ lấy `YYYY-MM-DD`, cắt bỏ giờ phút giây)
     * `GIÁ BÁN` (Căn phải, màu nổi bật cyan/sky)
     * `GIÁ NHẬP` (Ô input số hoặc text số căn phải)
     * `TIỀN LỜI` (Căn phải, xanh lá nếu lời `+...₫`, đỏ nếu lỗ `-...₫`)

3. **Cấu trúc HTML/CSS Mẫu Chuẩn Excel:**

```html
<div class="table-container" style="max-height:650px; overflow-y:auto; background:#1e293b; border-radius:8px; border:1px solid rgba(148,163,184,0.2);">
    <table style="width:100%; border-collapse:collapse; font-size:0.86rem;">
        <thead>
            <tr style="background:#0f172a; color:#94a3b8; text-transform:uppercase; font-size:0.75rem;">
                <th style="width:38px; text-align:center; padding:8px 6px;">#</th>
                <th style="padding:8px 6px;">Mã Đơn</th>
                <th style="padding:8px 6px;">Mặt Hàng</th>
                <th style="padding:8px 6px; width:110px;">Ngày Nhập</th>
                <th style="padding:8px 6px; text-align:right; width:120px;">Giá Nhập</th>
                <th style="padding:8px 6px; text-align:right; width:120px;">Giá Bán</th>
                <th style="padding:8px 6px; text-align:right; width:120px;">Tiền Lời</th>
            </tr>
        </thead>
        <tbody id="orders-finance-tbody">
            <tr style="border-bottom:1px solid rgba(148,163,184,0.15);">
                <td style="text-align:center; color:#94a3b8; padding:8px 6px;">1</td>
                <td style="padding:8px 6px;"><strong style="color:#38bdf8; font-family:monospace;">DH-20261029-005</strong></td>
                <td style="padding:8px 6px; font-weight:600; color:#f8fafc; white-space:nowrap; max-width:240px; overflow:hidden; text-overflow:ellipsis;">Dầu Ăn Simply Đậu Nành Nguyên Chất</td>
                <td style="padding:8px 6px; color:#cbd5e1; font-family:monospace;">2026-10-29</td>
                <td style="padding:8px 6px; text-align:right;"><input type="number" value="8000" style="width:90px; padding:3px 6px; border-radius:4px; border:1px solid #f97316; background:#0f172a; color:#f8fafc; font-weight:700; text-align:right;"></td>
                <td style="padding:8px 6px; text-align:right; font-weight:700; color:#38bdf8;">55.000 ₫</td>
                <td style="padding:8px 6px; text-align:right;"><strong style="color:#22c55e;">+47.000 ₫</strong></td>
            </tr>
        </tbody>
    </table>
</div>
```

---

## 3. Checklist Kiểm Tra Giao Diện Trước Khi Báo Cáo
- [ ] Đã bỏ hết toàn bộ `<br>` trong các cell?
- [ ] Ngày nhập chỉ hiện `YYYY-MM-DD`, không hiện `HH:MM:SS`?
- [ ] Bảng đã ẩn cột Khách hàng/SĐT và cột Trạng thái dài dòng?
- [ ] Chiều cao mỗi dòng (`tr`) nằm gọn trong khoảng 36px - 40px (chuẩn bảng tính Excel)?
- [ ] Đã chụp ảnh xác nhận thực tế (Native Multimodal) trên giao diện trước khi gửi báo cáo?
