# On-Demand Reg Bù, Deferred Tracking Apply & Master-to-Safe Sync Pitfalls

## 1. Cơ Chế 2 Tầng Workbook & Cron Auto-Sync
- **Master Workbook (`taikhoan_dat_v2_updated .xlsx`):** Lưu trữ toàn bộ thông tin tài khoản (username, password, 2FA, email, email pass, ngày sinh, ngày tạo, device serial). Chỉ các tiến trình quản trị/reg/đổi pass mới ghi vào đây.
- **Safe Workbook (`taikhoan_run_safe.xlsx`):** Chỉ lưu 4 trường tối thiểu (`[STT, Serial, Username, Video Đã Đăng]`) phục vụ bot nuôi feed/upload.
- **Cron Auto-Sync (`taikhoan-run-safe-sync` - ID `95f8cd3f4e52`):**
  - Chạy chu kỳ mỗi 5 phút qua script `taikhoan_sync_cron_launcher.py`.
  - Tự động so sánh hash nội dung của file Master `taikhoan_dat_v2_updated .xlsx`. Nếu phát hiện có dòng mới hoặc thay đổi, nó lập tức cập nhật sang `taikhoan_run_safe.xlsx`.
  - **Lưu ý quan trọng:** Cron này hoàn toàn tự động và live 100%. Nếu bot feed báo "Trống slot/chưa có nick" sau khi reg bù, nguyên nhân **luôn luôn nằm ở khâu ghi vào file Master bị nghẽn**, chứ không phải do cron sync hỏng.

## 2. Pitfall 1: Slot Picker Quét Từ Đỉnh (First-Empty Bias) Gây Lệch Row
- **Triệu chứng:** Script chạy reg bù cho Ca 4 (Row 8), reg thành công nhưng nick lại bị gán vào Row 5 hoặc Row 7; Row 8 vẫn trống trơn.
- **Nguyên nhân:** Hàm `find_deferred_tracking_slot(stt, email)` trong `social_reg_v1.py` duyệt từ dòng đầu tiên của máy đó xuống và bốc ngay ô trống đầu tiên (`all(_cell_blank(v))`). Nếu máy đó chưa đủ 8 slot (ví dụ còn trống slot 5, 6, 7), nó sẽ gán nick mới vào slot 5 hoặc 7 thay vì đúng Row 8 đang cần nuôi.
- **Giải pháp:** Khi kích hoạt on-demand reg bù theo Row chỉ định (`ensure_row_accounts.py <row>`), bắt buộc ép chặt `target_row` và `tik` tương ứng với đúng slot của Row đó trong mảng 8 slot của máy (`machine_slots[m][row - 1]`), cấm dùng first-empty tự do.

## 3. Pitfall 2: Dữ Liệu Rác Ở Cột Pass/ID Chặn Đứng Toàn Batch Apply
- **Triệu chứng:** Máy reg thành công (có JSON tracking result, có proof screenshot), nhưng `apply_deferred_tracking_results.py` trả về exit code 1 (`BLOCKED_DATA_CONFLICT`), toàn bộ file kết quả trong batch bị bỏ rơi không ghi được vào Master.
- **Nguyên nhân:**
  1. Trong master workbook, một ô trống bị dính chuỗi rác (ví dụ: `mailto:...` hoặc chuỗi text lạ lọt vào cột Password).
  2. Hàm `resolve_tracking_slot` kiểm tra `not _cell_blank(row_id) or not _cell_blank(row_pass)` $\rightarrow$ báo `NO_EMPTY_TRACKING_SLOT` $\rightarrow$ sinh ra JSON tracking result có `tracking_row: ""` và `tik: ""`.
  3. Khi `apply_deferred_tracking_results.py` chạy theo danh sách nhiều file, chỉ cần 1 file có `tracking_row: ""` sẽ kích hoạt `BLOCKED_DATA_CONFLICT` (`RESULT_MISSING_ROW_OR_TIK`), làm terminating toàn bộ chuỗi apply.
- **Giải pháp:**
  - Tiền kiểm tra (Sanitize) dọn dẹp các ô rác `mailto:...` trên master workbook trước khi chạy reg.
  - Trong script apply, xử lý ghi độc lập từng file (per-item isolation) để lỗi dữ liệu ở 1 máy không kéo theo hủy bỏ kết quả của các máy thành công khác.

## 4. Pitfall 3: Thư Mục Run Retry Trống Đè Mất Kết Quả Của Run Trước
- **Triệu chứng:** Đợt 1 reg được 12 nick; đợt 2 chạy retry các máy fail nhưng 0 máy thành công; sau đó script apply báo `Khong co tracking result moi de merge`.
- **Nguyên nhân:**
  `latest_run = sorted(runs_dir.glob("20*"), key=lambda d: d.stat().st_mtime, reverse=True)[0]` chỉ bốc đúng thư mục mới nhất. Khi đợt retry sinh ra thư mục mới mà không có file JSON thành công nào, nó che khuất hoàn toàn thư mục đợt 1 vừa chạy trước đó 30 phút.
- **Giải pháp:**
  Khi quét thư mục run để merge kết quả: Bắt buộc lặp qua các thư mục run gần nhất trong ngày (`within_hours=4`) và gom toàn bộ các file `tracking_result_*.json` có `status == SUCCESS` chưa được apply vào workbook, thay vì chỉ đọc duy nhất `dirs[0]`.
