# Phân Biệt Nick Ký Sinh vs Nick Reg Chưa Ghi Info & Nguyên Tắc Bảo Toàn Tài Sản Farm

## 1. Bản chất cốt lõi: Mọi nick trên máy đều là tài sản farm
Khi kiểm tra Switcher máy thật thấy xuất hiện nick không khớp với Excel hiện tại của máy đó, **CẤM TUYỆT ĐỐI** gọi chung là "nick rác ngoài luồng" và vứt/xóa bỏ tùy tiện.
Trên máy farm, một nick không có trong slot Excel của máy đó CHỈ THUỘC 1 TRONG 2 TRƯỜNG HỢP:

### Trường hợp 1: Nick ký sinh (Đã đăng ký và đã có máy chủ sở hữu gốc)
- **Định nghĩa**: Nick này là nick chính chủ của một máy khác trong farm (đã được ghi nhận vào `taikhoan_dat_v2_updated .xlsx` hoặc `taikhoan_run_safe.xlsx` ở máy khác, hoặc cùng tài khoản Hotmail đã đăng nhập ở máy khác).
- **Nguyên nhân**: Quá trình reg/login hoặc cắm proxy/test trước đó bị nhảy máy hoặc lộn serial giữa các luồng.
- **Xử lý**: 
  - Tra cứu chéo toàn bộ workbook và log để xác định chính xác máy gốc sở hữu nick.
  - Sau khi xác nhận nick đã có mặt hoặc thuộc quyền quản lý của máy gốc $\rightarrow$ **Đăng xuất (Logout)** khỏi máy hiện tại để giải phóng slot, tránh kẹt trần `MACHINE_FULL_8_ACCOUNTS`.

### Trường hợp 2: Nick reg thành công nhưng chưa kịp ghi info (Tài sản mới chưa backfill)
- **Định nghĩa**: Nick này do chính runner vừa reg thành công trên máy (hoặc đợt reg trước đó) từ email cấp cho máy đó trong `gmail_clean_v2.xlsx`, nhưng tiến trình bị crash, timeout, hoặc văng exception ở bước ghi nhận vào Excel / deferred result.
- **Dấu hiệu nhận biết**:
  - Tra cứu log reg của máy thấy có bước submit form, nhập OTP email thành công và tạo username này.
  - Email tương ứng nằm trong danh sách cấp phát của máy đó.
  - Excel của máy đó hiện vẫn đang trống slot.
- **Xử lý**: 
  - **BẢO TOÀN TUYỆT ĐỐI**, CẤM LOGOUT / CẤM VỨT BỎ!
  - **Backfill ngay lập tức**: Ghi nhận bổ sung ID nick, email, mật khẩu mail vào đúng slot còn trống của máy đó trên cả Master DAT (`taikhoan_dat_v2_updated .xlsx`) và Safe Workbook (`taikhoan_run_safe.xlsx`).
  - Coi như máy đó đã hoàn tất slot đó, không cần chạy reg lại.

## 2. Quy trình chuẩn khi gặp lỗi `MACHINE_FULL_8_ACCOUNTS` (8/8 nick)
1. **Kiểm tra hiện trường Switcher**: Dump UI XML hoặc OCR chụp ảnh màn hình Switcher để liệt kê toàn bộ 8 username thực tế trên máy.
2. **Đối soát 3 chiều**:
   - Đối chiếu với 8 slot của máy trong `taikhoan_dat_v2_updated .xlsx`.
   - Đối chiếu với kho mail `gmail_clean_v2.xlsx` của máy đó.
   - Quét log `social_reg_log.txt` tìm lịch sử tạo username đó.
3. **Phân loại từng nick lạ**:
   - Nếu là Nick ký sinh (đã có máy khác giữ) $\rightarrow$ Logout qua quy trình an toàn (Settings $\rightarrow$ Logout nick đó).
   - Nếu là Nick vừa reg chưa ghi info $\rightarrow$ Giữ nguyên, backfill vào slot trống của Excel.
4. **Xác nhận mở lại nút "Thêm tài khoản"**: Sau khi xử lý đưa số lượng nick về $<8$, kiểm tra lại Switcher xem nút *"Thêm tài khoản"* đã xuất hiện trở lại hay chưa trước khi chạy ca tiếp theo.
