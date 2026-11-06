# Kỷ Luật Bộ Lọc Tháng và Tổng Kết Lũy Kế Trên Bảng Tài Chính Đơn Hàng (Monthly Filter & Dual Totals Invariant)

## 1. Bối cảnh & Hiện tượng (The Problem)
Khi thiết kế bảng quản lý tài chính / kế toán đơn hàng (nhập vốn, giá bán, tiền lời), người dùng thường phát lệnh:
*"Tao cần xem theo tháng và theo tổng, hiện tại mới hiện theo tổng thôi"*
Nếu agent chỉ hiển thị một con số tổng duy nhất (All-time Cumulative) mà không có cơ chế lọc tháng, người dùng sẽ không nắm được doanh số và lợi nhuận của tháng hiện tại hoặc các tháng trước đó.

## 2. Nguyên nhân cốt lõi (Root Cause)
1. Thiếu Dropdown/Selector lọc thời gian: Bảng dữ liệu gom chung toàn bộ lịch sử đơn hàng vào một danh sách phẳng.
2. Không phân tách giữa Tổng Kỳ (Month Total) và Tổng Lũy Kế (Grand Total):
   - Khi chưa chọn tháng: Phải hiển thị tổng toàn bộ ("Tất cả các tháng").
   - Khi chọn một tháng cụ thể (VD: "Tháng 10/2026"): Các thẻ KPI (Tổng Doanh Thu, Tổng Vốn Nhập, Tổng Tiền Lời) và các dòng dữ liệu BẮT BUỘC phải tự động tính toán lại và chỉ hiển thị đúng số liệu phát sinh trong tháng đó.

## 3. Quy chuẩn kiến trúc & Triển khai bắt buộc (Implementation Rules)

### A. Chuẩn hóa trích xuất Tháng (`getOrderMonth`)
Ngày đặt đơn / ngày nhập trong CSDL hoặc payload có thể ở nhiều định dạng (`YYYY-MM-DD HH:MM`, `YYYY-MM-DD`, `DD/MM/YYYY`). Hàm bóc tách tháng bắt buộc phải hỗ trợ chuẩn hóa về dạng `YYYY-MM`:
```javascript
function getOrderMonth(dateStr) {
    if (!dateStr) return '';
    let m = String(dateStr).match(/^(\d{4})[-/](\d{1,2})/);
    if (m) return `${m[1]}-${m[2].padStart(2, '0')}`;
    m = String(dateStr).match(/(\d{1,2})[-/](\d{1,2})[-/](\d{4})/);
    if (m) return `${m[3]}-${m[2].padStart(2, '0')}`;
    return '';
}
```

### B. Dropdown lọc tháng linh hoạt và tự động nhận diện tháng mới
1. Quét toàn bộ danh sách đơn hàng đã có hạch toán tài chính (`cost_price > 0` hoặc `sale_price > 0`).
2. Tập hợp các tháng duy nhất (`Set()`) và sắp xếp giảm dần theo thời gian (tháng mới nhất lên đầu).
3. Thêm tùy chọn mặc định: `📅 Tất cả các tháng`.
4. Gắn Dropdown trực tiếp lên thanh tiêu đề của bảng:
```html
<div class="orders-section-title" style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;">
    <span>💰 BẢNG LỜI LỖ & GIÁ VỐN</span>
    <div style="display:flex; align-items:center; gap:8px; font-size:0.88rem;">
        <label for="finance-month-select" style="color:#94a3b8; font-weight:600;">Lọc theo tháng:</label>
        <select id="finance-month-select" onchange="recalcFinanceTotals()" style="background:#0f172a; color:#f1f5f9; border:1px solid #475569; border-radius:6px; padding:4px 10px; font-size:0.85rem; font-weight:600; cursor:pointer;">
            <option value="all">📅 Tất cả các tháng</option>
            <!-- Render options theo tháng -->
        </select>
    </div>
</div>
```

### C. Tính toán KPI và lọc dòng tức thời (`recalcFinanceTotals`)
Mỗi hàng đơn hàng trong `<tbody>` bắt buộc mang thuộc tính `data-month="YYYY-MM"`, `data-revenue="..."`, `data-cost="..."`. Khi người dùng đổi tháng trên dropdown, hàm tính toán lập tức:
1. So khớp `match = (selMonth === 'all' || rowMonth === selMonth)`.
2. Ẩn dòng không khớp (`tr.style.display = 'none'`), hiện dòng khớp (`tr.style.display = ''`).
3. Chỉ cộng dồn `totRev` và `totCost` trên các dòng thỏa mãn `match`.
4. Cập nhật ngay 3 thẻ KPI:
   - 💵 **Tổng Doanh Thu** (theo tháng hoặc toàn bộ).
   - 📦 **Tổng Vốn Nhập** (theo tháng hoặc toàn bộ).
   - 📈 **Tổng Tiền Lời** = `Tổng Doanh Thu - Tổng Vốn Nhập` (xanh nếu >= 0, đỏ nếu < 0).

## 4. Checklist nghiệm thu thị giác (Visual Acceptance)
1. Truy cập giao diện trên Browser:
   - Xác nhận có dropdown `Lọc theo tháng:` ở góc phải tiêu đề bảng.
   - Khi ở `📅 Tất cả các tháng`: 3 thẻ KPI hiển thị tổng lũy kế toàn bộ.
   - Khi chọn một tháng cụ thể (VD: `Tháng 10/2026`): 3 thẻ KPI và các dòng trong bảng tự động co lại đúng số liệu của tháng đó.
2. Kiểm tra tính toàn vẹn: Không sinh lỗi console, thao tác chuyển đổi giữa các tab không làm mất trạng thái tháng đang chọn.
