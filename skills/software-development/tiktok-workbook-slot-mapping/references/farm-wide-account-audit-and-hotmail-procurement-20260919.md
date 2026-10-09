# Báo Cáo & Phương Pháp Thống Kê Nhu Cầu Mua Hotmail Toàn Farm Kibe & Admin (2026-09-19)

## 1. Bối cảnh & Mục đích
Để ước tính số lượng Hotmail/Outlook Graph API Zin cần mua mới nhằm phủ kín chuẩn 8 nick/máy trên cả 2 dàn máy:
- **Dàn Kibe:** 80 máy vật lý (Máy 1..80), quản trị tại `D:/OneDrive/TaadaaData/kibe/`
- **Dàn Admin:** 80 máy vật lý (Máy 201..280), quản trị tại `D:/OneDrive/TaadaaData/admin/`

## 2. Phương pháp kiểm toán dữ liệu (Audit Protocol)
1. **Kiểm tra hiện trạng Master DAT (`taikhoan_dat_v2_updated .xlsx` sheet `Tài Khoản`):**
   - Đọc Cột A (`Máy`), Cột C (`ID`), Cột F (`GMAIL`).
   - Tài khoản tính là hợp lệ (`filled`) khi Cột C có giá trị và `ID.lower() != 'none'`.
   - Mỗi máy chuẩn có 8 slot. Tổng số nick thiếu của máy = `8 - số nick hợp lệ`.
2. **Kiểm tra kho mail Zin nội bộ (`gmail_clean_v2.xlsx`):**
   - Thu thập toàn bộ email trong `gmail_clean_v2.xlsx`.
   - Lọc bỏ các email đã được dùng trong Master DAT (`used_emails`).
   - Lọc các domain mail Microsoft: `@hotmail.`, `@outlook.`, `@live.`, `@msn.` có token OAuth2 / Graph API.
   - Số mail sạch sẵn có = `len(unused_hotmail)`.
3. **Công thức tính nhu cầu mua bù ròng:**
   $$\text{Net Buy Needed} = \max(0, \text{Total Missing Accs} - \text{Unused Hotmail in Stock})$$

## 3. Bảng số liệu thống kê chi tiết (Thời điểm 19/09/2026)

### A. Dàn Kibe (80 máy: 1..80)
- **Chỉ tiêu:** 80 máy × 8 slot = **640 tài khoản**.
- **Đã có nick:** **605 nick**.
- **Tổng số nick còn khuyết:** **35 nick** (trên 35 máy, mỗi máy có 7/8 nick).
  - Slot 1..4, 6: Đã đủ 80/80 máy.
  - Slot 5 (Row 5): Khuyết 1 máy (Máy 80).
  - Slot 7 (Row 7): Khuyết 6 máy (`27, 32, 42, 52, 53, 63`).
  - Slot 8 (Row 8): Khuyết 28 máy (`2, 3, 4, 5, 6, 8, 10, 20, 22, 24, 28, 30, 36, 37, 40, 44, 46, 48, 54, 55, 61, 62, 64, 66, 69, 73, 75, 76`).
- **Kho Hotmail Zin nội bộ hiện có:** **23 mail Zin Graph API**.
- **Nhu cầu mua bù cho Kibe:** $35 - 23 =$ **12 mail** (đề xuất mua 15–20 mail có dự phòng).

### B. Dàn Admin (80 máy: 201..280)
- **Chỉ tiêu:** 80 máy × 8 slot = **640 tài khoản**.
- **Đã có nick:** **332 nick** (hiện mới nạp các slot 1..5, slot 6..8 hầu như chưa nạp).
- **Tổng số nick còn khuyết:** $640 - 332 =$ **308 nick**.
- **Kho Hotmail Zin nội bộ hiện có:** **114 mail Zin Graph API**.
- **Nhu cầu mua bù cho Admin:** $308 - 114 =$ **194 mail**.

### C. Tổng hợp toàn Farm (160 máy)
- **Tổng số nick thiếu:** **343 nick**.
- **Kho mail Zin sẵn có:** **137 mail**.
- **Tổng số Hotmail Zin cần mua bù toàn hệ thống:** **206 mail** (đề xuất đặt hàng 210–220 mail).
