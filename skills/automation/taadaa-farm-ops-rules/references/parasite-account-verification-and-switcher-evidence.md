# Quy Trình Đối Soát Nick Ký Sinh & Bằng Chứng Nghiệm Thu Account Switcher (Gate 6)

## 1. Bản Chất Nick Ký Sinh & Lỗ Hổng Đối Soát Bằng Excel

### Sai lầm chết người: Chỉ đối soát trên Excel
- **Biểu hiện:** Script chạy kiểm tra các dòng trong workbook `taikhoan_dat_v2_updated .xlsx` hoặc `taikhoan_run_safe.xlsx`, thấy mỗi dòng 1 UID riêng biệt, không có UID nào trùng lặp trên sheet -> Vội vàng kết luận "đã sạch nick ký sinh / không còn nick trùng".
- **Thực tế:** Nick ký sinh **KHÔNG HỀ NẰM TRÊN EXCEL CỦA MÁY ĐÓ**, mà nó nằm **CHUI LỦI TRỰC TIẾP TRÊN THIẾT BỊ THẬT (TRONG APP TIKTOK)**.
  - Ví dụ: Máy 53 trong Excel chỉ có 7 dòng nick (Slot 7 trống), nhưng trên máy Samsung S7 thực tế, đợt reg nhầm serial đã login nick `@chichi13853` (vốn thuộc Máy 26).
  - Khi reg bù hoặc kiểm tra, script thấy máy đã có 8 nick trong Switcher -> ném lỗi `MACHINE_FULL_8_ACCOUNTS` hoặc ẩn nút "Thêm tài khoản".
- **Quy tắc bất biến:** KHÔNG BAO GIỜ được tuyên bố "hết nick ký sinh" nếu chỉ kiểm tra dữ liệu Excel. BẮT BUỘC phải đối soát O(1) từ **UI XML thật hoặc ảnh Screencap của Account Switcher** trên thiết bị đối chiếu ngược lại danh sách được phân bổ cho máy đó.

---

## 2. Invariant Gate 6: Bằng Chứng Nghiệm Thu Logout Nick Ký Sinh

### User Rule (Bị phạt nếu vi phạm):
*"Mày dọn xong thì gửi ảnh ở account switcher t xem là dọn kí sinh chưa chứ gửi ảnh này chi v"*

### Quy định ảnh nghiệm thu bắt buộc khi xử lý Nick Ký Sinh:
1. **Màn hình đích duy nhất hợp lệ:** **MÀN HÌNH ACCOUNT SWITCHER BOTTOM SHEET** (Màn hình "Chuyển đổi tài khoản" liệt kê danh sách tài khoản dạng bottom sheet).
2. **CẤM TUYỆT ĐỐI:**
   - Chụp màn hình Home / Launcher làm ảnh nghiệm thu.
   - Chụp màn hình Cài đặt & Quyền riêng tư (Settings) làm ảnh nghiệm thu.
   - Chụp màn hình video feed / profile tab bình thường làm ảnh nghiệm thu.
   - Teardown (`am force-stop`, `input keyevent 3`) trước khi chụp ảnh Switcher.
3. **Tiêu chuẩn nghiệm thu trên ảnh Account Switcher:**
   - Nick ký sinh mục tiêu **KHÔNG CÒN XUẤT HIỆN** trong danh sách tài khoản.
   - Nút **"Thêm tài khoản"** (Add account) đã **XUẤT HIỆN TRỞ LẠI** (hoặc tổng số tài khoản giảm xuống đúng 7).
   - Đính kèm `MEDIA:<path_anh>` dòng riêng ngay trong báo cáo.
