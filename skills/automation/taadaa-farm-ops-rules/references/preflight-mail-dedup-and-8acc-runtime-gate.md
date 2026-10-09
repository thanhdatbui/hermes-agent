# Quản Lý Target Reg, Khử Trùng Mail Toàn Cục & Khắc Phục Lệch 8 Tài Khoản TikTok

## 1. Cạm Bẫy Preflight Excel & Cơ Chế Chặn 2 Tầng Cho Trần 8 Tài Khoản

### Cạm bẫy `openpyxl.active` sheet
- **Hiện tượng:** Hàm nạp tracking `load_registered_mailboxes` mặc định gọi `_active_worksheet(workbook)`. Trong `openpyxl`, `workbook.active` trả về sheet được active khi người dùng lưu file Excel lần cuối (ví dụ sheet 'Proxy', 'Accounts' hoặc sheet rác).
- **Hậu quả:** Hàm không tìm thấy các cột `stt` hoặc `tiktok_id` trên sheet active đó, dẫn đến việc trả về tập hợp registered rỗng (`set()`) và bộ đếm máy rỗng (`{}`). Preflight tưởng toàn bộ 80 máy đều chưa có tài khoản nào $\rightarrow$ Tiếp tục cấp target cho các máy đã đầy.
- **Quy tắc bắt buộc:** Luôn đọc tường minh sheet `'Tài Khoản'`:
  ```python
  if "Tài Khoản" in (workbook.sheetnames or []):
      worksheet = workbook["Tài Khoản"]
  else:
      worksheet = _active_worksheet(workbook, label)
  ```

### Chốt chặn 2 tầng chống tràn 8 tài khoản
TikTok Android client giới hạn cứng tối đa **8 tài khoản/thiết bị**. Khi đã đủ 8 nick, app ẩn nút "Thêm tài khoản".
1. **Tầng 1 - Preflight Filter (`tiktok_target_eligibility.py`):**
   - Đếm số nick đã có ID trên sheet `'Tài Khoản'`.
   - Bỏ qua ngay các máy có `counts.get(stt, 0) >= max_accounts_per_machine` (8 accs).
2. **Tầng 2 - Device Runtime Gate (`social_reg_v1.py` tại `tap_add_account`):**
   - Mở Account Switcher, đếm trực tiếp số nick thực tế trên app.
   - Nếu `acc_count >= 8`: ghi log `MACHINE_FULL_8_ACCOUNTS`, đóng dropdown về HomeScreen và thoát gracefully. Tuyệt đối cấm throw `RuntimeError: [04_add_account] Không tìm thấy: ('Thêm tài khoản', ...)` làm sập cả batch.

---

## 2. Khử Trùng Mail Toàn Cục & Cạm Bẫy Khi Nạp Kho `gmail_clean_v2.xlsx`

### Cạm bẫy crawl lại đơn hàng cũ nạp vào kho
- **Nguyên nhân gốc rễ:** Khi cào lại danh sách mua từ web shop (ví dụ `hotmail_all_60_bought.txt`), danh sách chứa cả đơn cũ lẫn mới. Nếu dùng vòng lặp `zip(bought_accs, missing_machines)` nạp thẳng vào Excel mà không kiểm tra trùng lặp với các dòng hiện có, cùng 1 email sẽ bị gán cho nhiều máy khác nhau (ví dụ `karistinelso@hotmail.com` bị gán cho cả Máy 03 và Máy 05).
- **Quy tắc nạp kho:** Luôn kiểm tra `if email.lower() in existing_emails: continue` trước khi ghi dòng mới vào `gmail_clean_v2.xlsx`.

### Khử trùng mail toàn cục trong Preflight (`select_pending_targets`)
- Hàm chọn target phải đảm bảo: Dù kho nguồn có bị gán trùng email giữa các máy, một email khi đã được chọn cho 1 máy (hoặc đã nằm trong `registered_mailboxes`) thì lập tức được thêm vào `used`. Mọi máy sau gặp email đó đều bị bỏ qua, **tuyệt đối không cấp cùng 1 email cho 2 máy chạy song song**.

### Rủi ro Deferred Write Collision
- Khi 2 máy cùng chạy 1 email, máy chạy sau tạo file JSON có timestamp mới hơn. Tool `apply_deferred_tracking_results.py` lấy file mới nhất ghi đè vào slot của máy chạy sau, bỏ rơi máy chạy trước. Kết quả: tài khoản nằm trên cả 2 máy nhưng Excel chỉ ghi 1 máy, máy còn lại bị trống slot trên Excel và liên tục bị Preflight cử đi reg đè.

---

## 3. Quy Trình Chuẩn Xử Lý Tài Khoản Bị Trùng / Lệch Trên Thiết Bị

Khi phát hiện 1 tài khoản TikTok xuất hiện trên 2 máy:
1. **Tra cứu Master Truth:** Kiểm tra `taikhoan_dat_v2_updated .xlsx` (sheet `'Tài Khoản'`) và `taikhoan_run_safe.xlsx` để xác định nick thuộc máy nào. Giữ nguyên nick trên máy chuẩn.
2. **Đăng xuất tự động trên máy thừa:**
   - Mở TikTok trên máy thừa $\rightarrow$ Chuyển sang nick cần gỡ trong Account Switcher.
   - Menu 3 gạch $\rightarrow$ "Cài đặt và quyền riêng tư" $\rightarrow$ Cuộn đáy $\rightarrow$ "Đăng xuất" $\rightarrow$ Xác nhận popup.
   - Kiểm tra lại Switcher xác nhận máy chỉ còn 7 nick.
   - Chụp ảnh màn hình lưu `D:/Taadaa/reports/sttXX_after_logout.png` làm bằng chứng nghiệm thu và đưa máy về Home.
