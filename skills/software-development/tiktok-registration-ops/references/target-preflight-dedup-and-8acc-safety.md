# TikTok Registration: Preflight Filtering, Mail Deduplication & 8-Account Safety

## 1. Cơ Chế Lọc Preflight & Giới Hạn 8 Tài Khoản/Máy

### Cạm Bẫy `openpyxl.active` Sheet Trong Workbook Tracking
- **Triệu chứng:** Preflight tưởng tất cả các máy đều 0 tài khoản, hoặc không nhận diện được các tài khoản/mailbox đã đăng ký trong `taikhoan_dat_v2_updated .xlsx`.
- **Nguyên nhân gốc rễ:** `load_registered_mailboxes` mặc định gọi `_active_worksheet(workbook)`. Trong `openpyxl`, `workbook.active` trả về sheet được lưu active lần cuối cùng (ví dụ ai đó mở file xem sheet "Proxy" rồi lưu lại). Khi đó, hàm đọc không tìm thấy cột `stt` hay `tiktok_id` trên sheet đó, trả về danh sách đã đăng ký rỗng (`set()`) và bộ đếm máy `{}`.
- **Quy tắc bắt buộc:** Luôn đọc tường minh sheet `'Tài Khoản'`:
  ```python
  if "Tài Khoản" in (workbook.sheetnames or []):
      worksheet = workbook["Tài Khoản"]
  else:
      worksheet = _active_worksheet(workbook, label)
  ```

### Chốt Chặn 2 Tầng Cho Trần 8 Tài Khoản
TikTok Android client giới hạn cứng tối đa **8 tài khoản/thiết bị**. Khi đã đủ 8 nick, TikTok sẽ **ẩn hoàn toàn nút "Thêm tài khoản"** trong bottom sheet Account Switcher.

1. **Tầng 1 - Preflight Filter (`scripts/tiktok_target_eligibility.py`):**
   - Đếm số tài khoản đã có TikTok ID theo từng máy từ sheet `'Tài Khoản'`.
   - Nếu `machine_account_counts.get(stt, 0) >= max_accounts_per_machine` (8 accs), loại bỏ máy ngay lập tức từ vòng chọn target.
2. **Tầng 2 - Device Runtime Gate (`social_reg_v1.py` tại `tap_add_account`):**
   - Không được tin tưởng 100% vào dữ liệu Excel (do có thể bị lệch pha, tài khoản bị đăng nhập tay hoặc từ tool khác).
   - Khi mở Account Switcher, đếm trực tiếp số lượng tài khoản thực tế đang hiển thị trong dropdown.
   - Nếu `acc_count >= 8`:
     + Ghi log cảnh báo: `MACHINE_FULL_8_ACCOUNTS`.
     + Đóng dropdown an toàn, đưa máy về HomeScreen.
     + Thoát gracefully với mã trả về thích hợp, **tuyệt đối CẤM throw `RuntimeError: [04_add_account] Không tìm thấy: ('Thêm tài khoản', ...)`** làm crash vỡ cả batch.

---

## 2. Nguyên Tắc Cấp Phát & Khử Trùng Mail Toàn Cục

### Cạm Bẫy Khi Mua Mail & Nạp Kho `gmail_clean_v2.xlsx`
- **Sự cố thực tế:** Khi cào lại đơn hàng từ shop (ví dụ `hotmail_all_60_bought.txt`), file chứa cả đơn cũ lẫn đơn mới. Nếu dùng `zip(bought_accs, missing_machines)` nạp thẳng vào Excel mà không kiểm tra trùng lặp, cùng 1 email sẽ bị gán cho 2 máy khác nhau (ví dụ `karistinelso@hotmail.com` bị gán cho cả Máy 03 và Máy 05).
- **Quy tắc nạp:** Trước khi ghi bất kỳ mail nào vào `gmail_clean_v2.xlsx`, bắt buộc kiểm tra `if email.lower() in existing_emails: continue`.

### Khử Trùng Mail Toàn Cục Trong Preflight (`select_pending_targets`)
- Dù file nguồn `gmail_clean_v2.xlsx` có bị duplicate dòng giữa các máy, hàm `select_pending_targets` phải đảm bảo tính **toàn vẹn tập hợp**:
  + Một email khi đã được gán làm target cho bất kỳ máy nào (hoặc đã nằm trong `registered_mailboxes`), email đó phải lập tức được thêm vào `used`.
  + Mọi máy duyệt sau nếu thấy email đó trong danh sách ứng viên thì bắt buộc phải skip, đảm bảo **1 email không bao giờ được cấp cho 2 máy chạy song song**.

### Rủi Ro Chế Độ Ghi Hoãn (Deferred Write Collision)
- Nếu 2 máy cùng chạy chung 1 email:
  + Máy A chạy trước tạo file JSON `tracking_result_sttA_mail.json`.
  + Máy B chạy sau tạo file JSON `tracking_result_sttB_mail.json`.
  + Khi tool `apply_deferred_tracking_results.py` chạy khử trùng theo mail và chọn file có timestamp mới nhất, nó sẽ lấy kết quả của Máy B và ghi đè vào slot của Máy B trên Excel, bỏ qua Máy A.
  + Hậu quả: Nick thực tế nằm trên cả 2 máy, nhưng Excel chỉ ghi nhận Máy B, còn Máy A bị để trống slot trên Excel $\rightarrow$ Preflight tiếp tục cử Máy A đi reg và đâm đầu vào trần 8 acc.

---

## 3. Quy Trình Xử Lý Tài Khoản Lệch & Đăng Xuất Chuẩn

Khi phát hiện 1 tài khoản TikTok xuất hiện trên 2 máy hoặc lệch giữa Excel và máy:
1. **Đối chiếu Master Truth:**
   - Kiểm tra `taikhoan_dat_v2_updated .xlsx` (sheet `'Tài Khoản'`) và `taikhoan_run_safe.xlsx` để xác định tài khoản đó chính thức thuộc về máy nào.
   - Giữ nguyên tài khoản trên máy chuẩn.
2. **Đăng xuất tự động trên máy bị gán nhầm:**
   - Mở TikTok trên máy gán nhầm.
   - Vào tab Hồ sơ $\rightarrow$ Mở Switcher $\rightarrow$ Chuyển sang tài khoản cần đăng xuất.
   - Nhấn nút Hamburger Menu (3 gạch góc trên phải) $\rightarrow$ "Cài đặt và quyền riêng tư".
   - Cuộn xuống đáy trang $\rightarrow$ Chọn "Đăng xuất" $\rightarrow$ Xác nhận đăng xuất trong popup.
   - TikTok sẽ tự động chuyển về 1 trong các tài khoản còn lại.
   - Mở Switcher kiểm tra lại: Đảm bảo danh sách chỉ còn các tài khoản hợp lệ của máy đó.
   - Chụp ảnh màn hình lưu `D:/Taadaa/reports/sttXX_after_logout.png` làm bằng chứng nghiệm thu.
   - Đưa máy về HomeScreen (`am force-stop` và `input keyevent 3`).
