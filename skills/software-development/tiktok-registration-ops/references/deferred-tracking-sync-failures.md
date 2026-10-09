# Troubleshooting & Root Cause: Email Bị Báo "Đã Có Tài Khoản TikTok" ([07])

## Hiện tượng
- Chạy batch reg TikTok báo lỗi: `[07] Tat ca N email cua STT <M> da co TK TikTok`.
- Script mở app TikTok, gõ email thì TikTok hiện màn hình OTP / Nhập mật khẩu / "Bạn cần trợ giúp đăng nhập?".

## Nguyên tắc điều tra (BẮT BUỘC)
**CẤM TUYỆT ĐỐI** vội vã kết luận là "bên bán Hotmail/Gmail đã đăng ký trước" hay "mail bị resell".

Thực tế 99% trường hợp trong Farm Taadaa: **Script batch reg đã đăng ký thành công tài khoản này trong các đợt chạy trước đó, nhưng bị KẸT KHÔNG GHI VÀO EXCEL TRACKING**.

---

## Các nguyên nhân khiến Reg thành công nhưng không lưu vào Excel
1. **Lỗi `NO_EMPTY_TRACKING_SLOT` (`deferred_tracking_writer.py`):**
   - Script batch chạy cơ chế deferred tracking: reg xong lưu ra `tracking_result_stt<M>_<email>.json`.
   - Bước sync cuối batch gọi `resolve_tracking_slot()` để tìm dòng trống sẵn của STT máy đó trong `taikhoan_dat_v2_updated .xlsx`.
   - Nếu máy đó đã đầy các dòng tạo sẵn trong template Excel (ví dụ máy chỉ có 4-5 dòng có sẵn), hàm không tự append dòng mới mà trả về `NO_EMPTY_TRACKING_SLOT` / `BLOCKED_DATA_CONFLICT`.
   - Kết quả: Account reg thành công nhưng JSON bị kẹt, Excel không có dữ liệu.

2. **Lỗi file Excel bị khóa (`PermissionError` / `FAILED_SYNC_OSError`):**
   - Tiến trình Excel (`EXCEL.EXE`) đang mở file `taikhoan_dat_v2_updated .xlsx` hoặc `gmail_clean_v2.xlsx`.
   - Quá trình sync batch không acquire được lock hoặc không write được file -> sync thất bại.

3. **Hậu quả vòng lặp:**
   - `_detect_clean.py` đọc file Excel thấy email chưa có TikTok ID -> tiếp tục chọn email đó làm target reg.
   - Máy thật mở lên nhập email -> TikTok nhận diện tài khoản đã tồn tại từ đợt trước -> Bị chặn ở form reg.

---

## Quy trình kiểm tra & Thu hồi tài khoản bị kẹt (Recovery SOP)

1. **Quét toàn bộ artifact JSON deferred runs:**
   ```python
   import glob, json
   json_files = glob.glob('D:/Taadaa/runtime/admin/artifacts/runs/social-batch-all/**/tracking_result_*.json', recursive=True)
   for jf in json_files:
       with open(jf, 'r', encoding='utf-8') as f:
           d = json.load(f)
           if d.get('status') == 'SUCCESS' and d.get('email') == '<target_email>':
               print(f"TÌM THẤY NICK ĐÃ REG: STT={d.get('stt')}, ID=@{d.get('tiktok_id')}, MailPass={d.get('mail_password')}")
   ```

2. **Đối soát với Excel Tracking Master:**
   - Kiểm tra xem email / STT đó đã có trong `taikhoan_dat_v2_updated .xlsx` chưa.
   - Nếu chưa có, thu hồi thông tin từ JSON để append row mới vào Excel Master và đồng bộ sang `taikhoan_run_safe.xlsx`.

3. **Kill tiến trình Excel nếu bị lock:**
   ```bash
   tasklist | grep -i EXCEL
   taskkill /F /PID <PID>
   ```
