# Quy trình Đối soát & Xử lý Máy Chạm Trần 8 Nick do Nick Ký Sinh (MACHINE_FULL_8_ACCOUNTS)

## 1. Bối cảnh & Dấu hiệu Nhận biết
- **Triệu chứng**: Khi kích hoạt runner đăng ký bù (ví dụ Row 8) hoặc bù nick thiếu:
  `[04_add_account] MACHINE_FULL_8_ACCOUNTS: Thiết bị đã đạt giới hạn tối đa 8 tài khoản`
  Tiến trình dừng ngay lập tức do không tìm thấy nút *"Thêm tài khoản"* (Add account) trong Switcher.
- **Nghịch lý dữ liệu**:
  - Kiểm tra trên master Excel (`taikhoan_dat_v2_updated .xlsx`) và runtime (`taikhoan_run_safe.xlsx`): Máy chỉ đang có 6 hoặc 7 tài khoản (vẫn còn slot trống).
  - Kiểm tra thực tế trên app TikTok thiết bị: Switcher đã chứa đủ 8 tài khoản $\rightarrow$ TikTok tự động ẩn nút *"Thêm tài khoản"*.

---

## 2. Nguyên nhân cốt lõi (Root Cause)
1. **Nick ký sinh / Nick ngoài luồng (Parasite Account)**:
   - Nick từ máy khác vô tình đăng nhập nhầm vào máy trong các phiên test hoặc lỗi điều phối trước đó (ví dụ `@annapmfdh0a` của M44 nằm trên M28; `@verdhsclf6f` của M16 nằm trên M40; `@anggiathinh2905` của M28 nằm trên M61).
   - Nick rác tự do được reg thành công trên máy nhưng không pass preflight audit hoặc không ghi nhận vào workbook.
2. **Kẹt trần Switcher**:
   - TikTok giới hạn tối đa 8 tài khoản trong Switcher cùng lúc. Một khi chạm trần 8 nick, app không cho phép mở luồng đăng nhập/đăng ký tài khoản mới trừ khi có 1 nick được đăng xuất ra ngoài.

---

## 3. Quy trình Đối soát & Dọn dẹp Chuẩn (5 Bước An Toàn)

### Bước 1: Rà soát & Đối chiếu 3 chiều
- Đối soát danh sách username được gán trong `taikhoan_dat_v2_updated .xlsx` (cột C) và `taikhoan_run_safe.xlsx` với danh sách tài khoản thực tế trong Switcher trên app (`adb shell uiautomator dump /sdcard/sw.xml` hoặc ATX XML).
- Bóc tách danh tính:
  - Tài khoản chính chủ của máy: Giữ nguyên tuyệt đối.
  - Tài khoản ký sinh / không có trong danh bạ máy: Đưa vào danh sách mục tiêu cần logout.

### Bước 2: Tuân thủ van an toàn Device Lock (Event-Driven)
- **CẤM TUYỆT ĐỐI** can thiệp hoặc đăng xuất khi máy đang có lock nuôi (`machine_X.lock.json` hoặc `serial_Y.lock.json`).
- Bắt buộc kiểm tra máy ở trạng thái rảnh (`0 lock` và HomeScreen/Idle) trước khi tác động.

### Bước 3: Đăng xuất cục bộ đúng nick ký sinh (Targeted Logout)
- Mở TikTok $\rightarrow$ Vào tab Profile $\rightarrow$ Mở dropdown Switcher.
- Chuyển (Switch) trực tiếp sang tài khoản ký sinh mục tiêu.
- Mở Menu 3 gạch $\rightarrow$ *Cài đặt và quyền riêng tư (Settings and privacy)* $\rightarrow$ Cuộn xuống đáy chọn *Đăng xuất (Log out)*.
- **LƯU Ý QUAN TRỌNG**: Chỉ bấm Đăng xuất khi đã switch sang đúng nick ký sinh. Tuyệt đối không xóa dữ liệu app (Clear Data) vì sẽ làm bay toàn bộ 7 nick còn lại.

### Bước 4: Nghiệm thu hiện trường & Khôi phục slot
- Mở lại Switcher: Đếm số lượng tài khoản thực tế phải còn đúng 7 nick.
- Kiểm tra sự xuất hiện của nút **"Thêm tài khoản"** (Add account) ở cuối danh sách Switcher.
- Đưa app về Home/Launcher an toàn (`am force-stop` + `input keyevent 3`).

### Bước 5: Ghi nhận State & Mở khóa Runner
- Lưu log trạng thái xử lý vào file state (ví dụ `parasite_reconcile_state.json`) để tránh quét lặp.
- Mở lại tiến trình reg bù / nạp nick cho slot còn trống.
