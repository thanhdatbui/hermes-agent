# Quy Chuẩn Tra Cứu Ngược & Chống Logout Nhầm Tài Khoản Farm (2026-09-25)

## 1. Bối cảnh & Lỗi Vận Hành (User chửi: "Làm lol có chuyện nick trên máy mà k có trong data, tra lại cho tao")
Trong quá trình vận hành Farm và xử lý lỗi trần 8 nick (`MACHINE_FULL_8_ACCOUNTS`):
- Khi thấy một nick nằm trên thiết bị thật nhưng tìm nhanh trong `taikhoan_dat_v2_updated .xlsx` không thấy, Agent thường có phản xạ sai lầm:
  * Vội vàng gán nhãn: *"Nick lạ không rõ nguồn gốc / Nick rác không có trong cơ sở dữ liệu"*
  * Lập tức thực hiện quy trình đăng xuất (Logout) để giải phóng slot máy.
- **HẬU QUẢ NGHIÊM TRỌNG:**
  * Logout mất tài khoản chính chủ của Farm đã đăng ký thành công và đang lưu phiên hoạt động bình thường trên thiết bị.
  * Vi phạm trực tiếp Hard Invariant: **"Mọi nick là tài sản (CẤM xóa/đè)"**.

---

## 2. Vì Sao Nick Thật Trên Máy Lại Biến Mất Khỏi File Excel Hiện Hành?

Ba nguyên nhân kỹ thuật phổ biến dẫn đến tình trạng "Nick trên máy nhưng mất dấu trên Excel":

1. **Cơ chế Purge Mail DIE tự động (`die_purge`):**
   - Định kỳ, hệ thống chạy batch checkmail.live để thanh lọc kho mail. Những Gmail/Hotmail bị checkpoint hoặc Google quét DIE sẽ bị script `remove_captcha_dead_email_from_source()` xóa khỏi `gmail_clean_v2.xlsx`.
   - Bản lưu trước khi xóa được ghi vào: `backup_clean_v2_before_die_purge_<timestamp>.xlsx`.
   - Hộp thư Gmail bị DIE nhưng **phiên TikTok trên app Android vẫn đang sống và hoạt động bình thường**. Khi mail bị xóa khỏi kho, nick TikTok trên máy bỗng nhiên trở thành "vô gia cư" trên bảng tính hiện hành.

2. **Tiến trình ghi Workbook bị lỗi dở dang (Uncommitted Tracking / Crash):**
   - Khi chạy batch reg TikTok đêm, tài khoản đã đăng ký thành công trên app TikTok, nhưng tiến trình ghi ngược vào `taikhoan_dat_v2_updated .xlsx` bị đứt gãy do:
     * Timeout sync OneDrive / File lock conflict.
     * Vi phạm `_validate_tracking_overwrite_guard` khiến script nhảy vào khối exception `deferred_result` nhưng chưa kịp sync sequential.
   - Hậu quả: Dòng slot của máy đó trên Excel (ví dụ Row 25 của Máy 3) vẫn mang giá trị `None`, trong khi app thật đã có nick.

3. **Thuật toán sinh Username tự động của TikTok:**
   - Khi đăng ký TikTok bằng Email (ví dụ: `an.nhuan.work64541@gmail.com`), TikTok tự động lấy prefix email `an.nhuan` và sinh đuôi ngẫu nhiên, ví dụ: `@annhubvqttr`.
   - Nếu tìm kiếm exact match chuỗi `@annhubvqttr` trên file Excel thì không thấy, nhưng nếu tìm prefix `an.nhuan` trong kho mail thì ra ngay lập tức.

---

## 3. Quy Trình 4 Bước Tra Cứu Ngược Bắt Buộc (Reverse Audit Protocol)

**CẤM TUYỆT ĐỐI logout bất kỳ nick nào trên máy khi chưa hoàn tất 4 bước tra cứu:**

### Bước 1: Tra cứu kho Backup Purge Mail (`backup_clean_v2_before_die_purge*`)
- Mở và tìm kiếm prefix của username (bỏ các ký tự random cuối) trong các file:
  `D:/OneDrive/TaadaaData/kibe/backup_clean_v2_before_die_purge_*.xlsx`
- Tìm kiếm cả trong `gmail_clean_v2_backup_*.xlsx` và `master_gmail_manager*.xlsx`.

### Bước 2: Tra cứu lịch sử cấp phát mail theo STT Máy
- Lọc xem máy đó (ví dụ Máy 3) trong quá khứ từng được cấp phát những email nào trong `gmail_clean_v2*.xlsx` và `social_reg_log.txt`.
- Đối chiếu danh sách email từng cấp cho máy với danh sách 7 nick đã biết. Email nào thừa ra chính là chủ sở hữu của nick thứ 8 trên app!

### Bước 3: Tra cứu các file Backup Workbook Data (`taikhoan_dat_v2_updated.bak*`)
- Quét các bản backup của `taikhoan_dat_v2_updated` xem dòng slot đó trong quá khứ đã từng có dữ liệu chưa, hay bị ghi đè nhầm ở máy khác (như trường hợp Máy 61 và 76 bị ghi đè sang Máy 28 và 36).

### Bước 4: Ra quyết định phân loại chuẩn xác
- **Trường hợp A (Nick chính chủ bị sót dữ liệu / Mail bị purge):**
  * Tìm thấy mail gốc trong file backup purge.
  * **HÀNH ĐỘNG:** BẮT BUỘC giữ lại nick, lấy thông tin (Gmail, Pass, 2FA, Ngày sinh) từ file backup để **Backfill vào ô trống của máy trên Excel**. TUYỆT ĐỐI CẤM logout!
- **Trường hợp B (Nick ký sinh thực sự từ máy khác):**
  * Nick này thuộc về một máy khác trong farm (đã có trên dòng máy khác) nhưng bị login nhầm sang máy này.
  * **HÀNH ĐỘNG:** Xác minh nick chính chủ ở máy gốc an toàn $\rightarrow$ tiến hành logout trên máy hiện tại theo đúng canonical tool `do_logout_account.py`.
