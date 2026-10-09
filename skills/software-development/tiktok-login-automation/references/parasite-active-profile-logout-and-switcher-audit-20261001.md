# Cạm bẫy đối soát tài khoản ký sinh: Active Profile vs Account Switcher & Quy trình Logout an toàn (2026-10-01)

## 1. NGUYÊN NHÂN LỌT LƯỚI TÀI KHOẢN KÝ SINH (PARASITE ACCOUNT TRAP)
- **Hiện tượng**: Script dọn dẹp tài khoản ký sinh (`watchdog_idle_parasite_reconcile.py`) kiểm tra máy M34, báo tài khoản ký sinh `@anillpboe98` (thuộc M56) "không còn trong switcher", ghi nhận `DONE`. Nhưng khi chạy ca nuôi Row 1, runner văng lỗi `ACCOUNT_MISSING: expected account was not found`.
- **Cơ chế UI TikTok**:
  - Khi mở Bottom-Sheet Switcher (`Chuyển đổi tài khoản`), TikTok **chỉ hiển thị các tài khoản phụ** có thể switch sang.
  - Nếu tài khoản ký sinh đang là **ACTIVE PROFILE** (tài khoản đang mở trực tiếp trên màn hình Hồ sơ chính), tên của nó hiển thị trên header/bio của Profile, **KHÔNG nằm trong danh sách switch của bottom-sheet**.
  - Logic cũ: Quét XML cây bottom-sheet switcher không thấy `@anillpboe98` $\rightarrow$ Kết luận nhầm là máy đã sạch $\rightarrow$ Bỏ qua. Thực tế nick ký sinh vẫn chiếm trọn 1 slot và đứng án ngữ ở Profile active suốt nhiều tuần!

---

## 2. QUY TRÌNH ĐỐI SOÁT 2 BƯỚC BẮT BUỘC (DUAL-SURFACE AUDIT)
Khi kiểm tra tài khoản trên máy (kể cả kiểm tra acc ký sinh hay kiểm đếm 8 slot):
1. **Bước 1 — Audit Active Profile**:
   - Vào tab Hồ sơ (`bounds: [864,1794][1080,1920]`).
   - Trích xuất handle qua XML (`resource-id` chứa `rz5`, `profile_header_name`, `account_name`) hoặc WinRT OCR.
   - Ghi nhận `active_account`.
2. **Bước 2 — Audit Switcher List (Kèm cuộn bottom-sheet)**:
   - Tap dropdown switcher (tên/avatar hoặc chevron `rv5`).
   - Cuộn bottom-sheet từ `[540, 1400]` lên `[540, 600]` để đọc hết các nick bị khuất.
   - Tổng danh sách tài khoản trên máy = `[active_account] + [switcher_sub_accounts]`.

---

## 3. QUY TRÌNH LOGOUT TÀI KHOẢN KÝ SINH ĐANG ACTIVE
### 🛑 CỔNG KIỂM TRA MÁY CHÍNH CHỦ TRƯỚC KHI LOGOUT (User chốt 2026-10-02)
- **Quy tắc bắt buộc**: Trước khi thực hiện logout nick ký sinh trên máy phụ, BẮT BUỘC kiểm tra thực tế trên máy chính chủ (`owner_stt`) xem nick đó ĐÃ CÓ MẶT VÀ ĐANG ĐĂNG NHẬP TRÊN MÁY CHÍNH CHỦ CHƯA (chụp ảnh Switcher/Profile máy chính chủ làm bằng chứng `MEDIA:<path>`).
- **Nguyên tắc quyết định**:
  * Nếu máy chính chủ **ĐÃ CÓ** nick: Cho phép logout nick ký sinh trên máy phụ để giải phóng slot.
  * Nếu máy chính chủ **CHƯA CÓ** nick: **CẤM TUYỆT ĐỐI LOGOUT** trên máy phụ vì sẽ làm mất phiên duy nhất của tài sản farm! Bắt buộc giữ nguyên phiên và báo cáo User.

### Các bước thực hiện logout nếu tài khoản cần đăng xuất đang là `active_account`:
1. **Không tìm trong Switcher**: Tuyệt đối không cố tap switcher để tìm nút logout của chính nó.
2. **Điều hướng Menu Cài đặt**:
   - Tap menu 3 gạch (`Profile menu`) tại góc phải trên: `tap(1005, 150)`.
   - Tap `Cài đặt và quyền riêng tư` (`Settings and privacy`): `tap(548, 1276)`.
   - Cuộn xuống đáy màn hình Cài đặt (vuốt 3-4 lần `[540, 1400]` $\rightarrow$ `[540, 400]`).
   - Tìm và tap `Đăng xuất` (`Log out`) tại toạ độ nút đỏ dưới cùng (`bounds` thường khoảng `y=1662`).
   - Xác nhận pop-up dialog: Tap `Đăng xuất` / `Log out` màu đỏ.
3. **Nghiệm thu giải phóng slot (Capture-before-cleanup)**:
   - Chờ app chuyển về màn hình tài khoản kế tiếp hoặc Profile.
   - Mở lại Switcher: Kiểm tra nút `+ Thêm tài khoản` (`Add account`) đã xuất hiện trở lại ở đáy bottom-sheet.
   - Chụp ảnh WinRT OCR xác nhận slot trống trước khi nạp tài khoản mới.

---

## 4. TRUY VẾT LỊCH SỬ REG GỐC KHI NICK TRÊN MÁY KHÔNG CÓ TRONG EXCEL (ROW OVERWRITE TRAP)
- **Hiện tượng**: Nick thực tế lưu phiên trên app (ví dụ `@gaetiwcu04c` trên M66) hoàn toàn không có trong `taikhoan_run_safe.xlsx` hay `taikhoan_dat_v2_updated .xlsx`.
- **Cấm đoán**: Tuyệt đối **CẤM GÁN NHÃN NICK RÁC** và cấm logout khi chưa điều tra lịch sử reg.
- **Phương pháp truy vết**:
  1. Tìm trong log reg tổng: `D:\Taadaa\Tiktok_Reg\social_reg_log.txt` theo handle hoặc tên hiển thị.
  2. Tìm trong kho artifact lưu kết quả reg gốc:
     `D:\Taadaa\runtime\kibe\artifacts\runs\social-batch-all\<date>\batch_*\stt_<M>\tracking_result_stt<M>_<email>.json`.
  3. Đọc file JSON để lấy email đăng ký, pass mail, pass TikTok và ngày tạo.
- **Căn nguyên Row Overwrite**: Các đợt reg tài khoản mới trong quá khứ có thể đã ghi đè vào đúng hàng (row) của nick cũ trong file Excel, nhưng trên thiết bị Android app chưa từng logout nick cũ. Đây là **tài sản chính chủ hợp pháp của máy**, cần khôi phục thông tin vào Excel thay vì xóa phiên.

---

## 5. CẠM BẪY PARSER `find_column_indices` TRONG `logout_guard.py` (2026-10-02)
- **Hiện tượng**: Nick ký sinh rõ ràng thuộc máy khác trong Excel nhưng `evaluate_logout` trả về `code='UNRECORDED'` và từ chối cấp phép logout.
- **Nguyên nhân gốc rễ**: Header `"Folder Video"` chứa chữ `"id"` trong `"video"`. Logic `any(k in h for k in ("tiktok", "tik tok", "username", "id"))` match nhầm `"Folder Video"` làm `col_id` (chứa số folder như 167) thay vì cột `"ID"`, khiến guard đọc sai TikTok ID và ném lỗi `UNRECORDED` giả.
- **Giải pháp chuẩn**: Bắt buộc kiểm tra loại trừ:
  `(h == "id" or any(k in h for k in ("tiktok", "tik tok", "username"))) and "video" not in h and "device" not in h`.
