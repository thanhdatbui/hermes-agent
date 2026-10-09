# Chẩn Đoán Lệch Mapping Tài Khoản: Nick Login Trùng 2 Máy & Ảo Tưởng Thiếu Slot (Trần Cứng 8 Nick)

## 1. Bối cảnh & Hiện tượng (Incident Pattern)
- **Cảnh báo từ hệ thống:** Runner nuôi nick/lướt feed báo lỗi cấu hình hàng loạt: `account row N is empty (no username) for machine X, skipping`.
- **Preflight Reg Bù thất bại:** Hệ thống tự kích hoạt `ensure_row_accounts.py <row>` để reg bù, nhưng runner crash với ngoại lệ:
  `RuntimeError: [04_add_account] Không tìm thấy: ('Thêm tài khoản', 'Add account', ...)`
- **Nghịch lý ban đầu:** Excel ghi nhận máy đó bị thiếu (ví dụ Row 7 = None, Row 8 bị copy đè trùng nick Row 6), nhưng trên app điện thoại thực tế lại **đã đủ 8 tài khoản**. Nút "Thêm tài khoản" bị ẩn hoàn toàn do trần cứng TikTok 8 nick/máy.

## 2. Nguyên nhân Cốt lõi: Hiện Tượng Nick Ký Sinh (Cross-Device Duplicate Login)
1. **Lịch sử nạp mail Hotmail trùng nhau:**
   - Trước khi có cơ chế khóa và cô lập mail cho từng máy, cùng 1 email Hotmail từng bị gán/mua nhầm cho 2 máy khác nhau.
   - Khi Máy B chạy flow login/reg với email đó, app đăng nhập vào chính tài khoản TikTok mà Máy A đã reg trước đó.
2. **Lệch mapping giữa Excel và UI Thực tế:**
   - Nick chính chủ thuộc về Máy A (đã ghi nhận trong Excel ở Máy A).
   - Trên Máy B, nick này nằm "ký sinh" trên app TikTok mà không hề có trong danh sách 8 slot của Máy B trên file Excel (`taikhoan_dat_v2_updated .xlsx` / `taikhoan_run_safe.xlsx`).
   - Hậu quả:
     - Máy B thực tế có 8 nick trên app -> Biến mất nút Add account.
     - Excel của Máy B chỉ có 6-7 nick (dòng còn lại là None hoặc trùng lặp) -> Preflight tưởng thiếu nên liên tục spawn reg bù vô vọng.
     - 2 máy cùng chạy feed/nuôi 1 nick TikTok tại 2 thời điểm khác nhau, tiềm ẩn rủi ro TikTok checkpoint/ban nick do login đa thiết bị bất thường.

## 3. Quy trình Điều tra O(1) Bằng Bằng Chứng Thật (Coordinator Protocol)
1. **Tuyệt đối không phán bừa là "nick rác ngoại lai" hay "app lỗi".**
2. **Kiểm tra UI XML của máy báo lỗi `fail_04_add_account_*.xml`:**
   - Trích xuất toàn bộ `content-desc` hoặc text từ các node `id/lpw` hoặc `id/lli` trong sheet *Chuyển đổi tài khoản*.
   - Đếm số lượng nick đang đăng nhập trên máy. Nếu đủ 8 nick -> Đã chạm trần cứng.
3. **Truy vấn chéo danh sách nick trong Excel:**
   - Dùng Python đọc `taikhoan_dat_v2_updated .xlsx` / `taikhoan_run_safe.xlsx` để tìm xem các nick trên app đang thuộc về STT máy nào.
   - Kiểm tra các máy chính chủ (ví dụ M13 có nick của M37; M24 có nick của M51).
   - Kiểm tra UI XML của máy chính chủ trong các phiên chạy gần nhất (`summary.txt`, `ui.xml`) để xác nhận nick đó có thực sự đang đăng nhập ở cả 2 máy hay không.

## 4. Quy trình Khắc Phục (Remediation)
1. **Xác định máy chính chủ và máy ký sinh:**
   - Máy chính chủ: Máy có nick đó được ghi nhận rõ ràng trong Excel và có lịch trình chạy feed theo ca.
   - Máy ký sinh: Máy đang chứa nick trên app nhưng trong Excel không có mapping.
2. **Logout nick ký sinh:**
   - Thực hiện lệnh logout nick ký sinh ra khỏi máy thứ 2 (chỉ logout duy nhất nick đó, tuyệt đối không `pm clear` TikTok làm mất các nick khác).
   - Sau khi logout, số lượng nick trên app giảm về 7 -> Nút "Thêm tài khoản" tự động xuất hiện trở lại.
3. **Thực hiện Reg bù hợp lệ:**
   - Chạy lại `ensure_row_accounts.py <row>` có chủ đích cho máy vừa được giải phóng slot.
   - Cập nhật đúng thông tin nick mới vào dòng `None` trong file Excel và đồng bộ sang safe workbook.
