# Samsung MTP USB Popup & Account Reconcile Lessons (2026-09-20)

## 1. Samsung MtpApplication USB Popup Lockout & Permanent Disable
- **Triệu chứng**: Khi cắm cáp USB hoặc điện áp chập chờn trên Samsung Galaxy S7 (Android 7/8), dịch vụ `com.samsung.android.MtpApplication` tự động bung dialog modal:
  `"Chú ý: Thiết bị được kết nối không thể truy cập dữ liệu trên thiết bị này..."` (`.USBConnection Activity`).
- **Hậu quả**: Modal này chặn toàn bộ focus của các ứng dụng chính (TikTok, Chrome, Outlook), cản trở `uiautomator dump` và làm nghẽn transport socket của ADB dẫn đến lỗi `[adb-timeout] device=... timeout=20 command=...`.
- **Cách xử lý triệt để & vĩnh viễn**:
  Không chỉ tap Cancel / phím Back tạm thời, mà phải vô hiệu hóa tận gốc package hệ thống cho user 0:
  ```bash
  adb -s <serial> shell pm disable-user --user 0 com.samsung.android.MtpApplication
  ```
  Sau khi disable, popup không bao giờ xuất hiện lại khi cắm/rút cáp hay khởi động lại máy, giải phóng hoàn toàn ADB channel.

## 2. Invariant "Tài sản Farm": Cơ chế Reconcile Nick dư trên máy vs Giới hạn 8 tài khoản
- **Nguyên tắc tối thượng**: **"Mọi nick trên farm là tài sản của user, CẤM coi là rác lạ hoặc tự ý xóa/logout bừa bãi"**.
- **Nguyên nhân cốt lõi gây lỗi `MACHINE_FULL_8_ACCOUNTS` / `Không tìm thấy nút Thêm tài khoản`**:
  - Khi TikTok trên máy đã đủ 8 nick (chạm trần tối đa của TikTok), ứng dụng **tự động ẩn hoàn toàn nút 'Thêm tài khoản'**.
  - Trên phiên bản TikTok cũ: Bộ đếm resource-id (`lli`, `n72`) đếm được 8 node -> ném `MACHINE_FULL_8_ACCOUNTS`.
  - Trên phiên bản TikTok mới (46.x): Resource-id obfuscated (`omm`, `omr`, `onj`) làm bộ đếm cũ về 0, nhưng vì nút "Thêm tài khoản" bị ẩn nên rơi xuống ném `Không tìm thấy: ('Thêm tài khoản')`.
- **Nguồn gốc các nick "dư"**:
  - Do cơ chế cũ trước ngày 17/09/2026 của file launcher `_run_all_targets.py` chạy ở chế độ "proof-only" (chỉ lưu kết quả reg thành công ra file JSON deferred tracking tại `artifacts/runs/social-batch-all/` mà không đồng bộ vào master Excel).
  - Detector đọc Excel thấy slot Row 8 vẫn rỗng nên phát lệnh reg bù -> TikTok mở lên thấy máy đã đủ 8 nick -> crash.
  - Toàn bộ thông tin đăng nhập của các nick này (TikTok ID, TT Pass, Email, Mail Pass) đều nằm đầy đủ trong kho JSON artifacts và các bản backup master DAT.
- **Quy trình xử lý chuẩn khi gặp máy báo Full 8 nick**:
  1. Đọc danh sách username hiển thị trong Switcher qua ATX JSON-RPC hoặc dump XML.
  2. Tra cứu thông tin nick đó trong kho JSON artifact (`D:\Taadaa\runtime\kibe\artifacts\runs\social-batch-all\`) hoặc master DAT backup.
  3. Kiểm tra xem nick đó có bị trùng lặp trên máy khác không (CHỈ giữ ở đúng 1 máy duy nhất).
  4. Nếu nick độc quyền và hợp lệ: **Backfill trực tiếp thông tin vào Row 8 của máy đó** trong `taikhoan_dat_v2_updated .xlsx` và `Tik8.xlsx`, không cần tốn công reg mới và bảo toàn 100% tài sản cho user.
