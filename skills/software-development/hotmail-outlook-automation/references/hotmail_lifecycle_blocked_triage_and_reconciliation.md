# Hotmail Lifecycle BLOCKED Triage, Reconciliation & Data Source Alignment

## 1. Bản Chất Hiện Tượng 28 Nick BLOCKED Trong Báo Cáo 6H
Trong báo cáo định kỳ 6h (`cron_hotmail_gpm_lifecycle_6h_report.py`), các tài khoản bị lỗi hoặc kẹt trong quá trình vận hành được tách riêng rõ ràng:
```text
⚠️ Lỗi / Kẹt cần cứu (BLOCKED): 28 (Kibe: 28 | Admin: 0)
```
Thực tế đối soát state file `batch_gpm_5profiles_supervisor_state.json`:
- **1 nick kẹt `HOTMAIL_LOGIN` (`status: QUARANTINE`)**: Ví dụ Máy 32 (`ahmiyaattikar@hotmail.com`) do vượt quá 3 lần thử đăng nhập thất bại. Nick này đã được gắn mail khôi phục chính chủ (`thanhdatbui1995@gmail.com`) nhưng bị Microsoft rate-limit gửi OTP trong ngày.
- **27 nick kẹt `CHANGE_INFO` (`status: BLOCKED`)**: Đã đăng ký ChatGPT thành công, đã ngâm đủ 7 ngày (`WAIT_7D`), nhưng khi Supervisor kích hoạt `gpm_change_hotmail_security.py` thì gặp lỗi (Microsoft service error *"Tạm thời có lỗi với dịch vụ"*, timeout bung form `#iPlainTextData` khi lấy TOTP key, hoặc thiếu mail khôi phục để giải identity challenge).

---

## 2. Bẫy Lệch Nguồn Dữ Liệu Giữa 2 File Excel Kho Tài Khoản
### Hiện Tượng:
- `taikhoan_dat_v2_updated .xlsx` (Sheet `'Tài Khoản'`): Là bảng điều phối theo máy farm (chứa 410 Hotmail trên Kibe).
- `gmail_clean_v2.xlsx` (Sheet `'Gmail Accounts'`): Là Single Source of Truth chứa thông tin bảo mật Hotmail (Cột 2: Email, Cột 3: PASS, Cột 4: 2FA Secret Key, Cột 5: Recovery Email).
- **Độ lệch thực tế**: Quét đối soát cho thấy có tới **151 tài khoản Hotmail** có mặt trong `taikhoan_dat_v2_updated .xlsx` nhưng **CHƯA ĐƯỢC ĐỒNG BỘ** sang `gmail_clean_v2.xlsx`.

### Tác Động Khi Change Info:
1. `gpm_change_hotmail_security.py` bốc tài khoản từ `taikhoan_dat_v2_updated .xlsx` qua hàm `find_target_accounts()`.
2. Tuy nhiên, khi cần tra cứu Recovery Email hoặc 2FA Secret Key, script gọi `get_recovery_email()` và `get_2fa_secret()`, hai hàm này lại đọc từ `gmail_clean_v2.xlsx` (`GMAIL_CLEAN_PATH`).
3. Nếu tài khoản nằm trong nhóm 151 nick chưa có trong `gmail_clean_v2.xlsx`, hoặc ô Cột 5 Recovery Email là `None`:
   - Khi Microsoft dựng challenge đòi xác minh danh tính qua mail khôi phục, script không có email để nhập -> Thất bại ngay lập tức.
   - Khi Microsoft phát hiện truy cập bất thường trên tài khoản không có phương thức bảo mật phụ, Microsoft chặn form đổi pass với câu *"There's a temporary problem with the service"* -> Script kích hoạt Fail-Fast dừng ngay và Supervisor đánh dấu `status: BLOCKED`.

---

## 3. Kỷ Luật An Toàn Của Supervisor: Fail-Closed Cho `CHANGE_INFO`
- **Khác biệt giữa `HOTMAIL_LOGIN` và `CHANGE_INFO`**:
  * `HOTMAIL_LOGIN`: Supervisor có bộ đếm `login_retry_count` và tự động unblock sau 48h cooldown nếu `retry_count < 3`.
  * `CHANGE_INFO`: Supervisor **KHÔNG TỰ ĐỘNG RETRY** tài khoản đã bị `status in {"BLOCKED", "FAILED", "ERROR"}`.
- **Lý do thiết kế**: Đổi mật khẩu và thiết lập 2FA là thao tác nhạy cảm cao. Cố chấp thử lại tự động trên nick đang bị Microsoft nghi ngờ hoặc thiếu dữ liệu bảo mật sẽ kích hoạt Fraud Detection, dẫn tới khóa tài khoản vĩnh viễn và làm hỏng uy tín IP proxy di động.

---

## 4. Quy Trình Triage & Unblock Chuẩn Cho Coordinator
Khi cần xử lý các nick bị kẹt `BLOCKED` ở `CHANGE_INFO`:
1. **Kiểm tra hiện trường lỗi**:
   - Đọc `last_result` trong state file của profile.
   - Soi ảnh lỗi thực tế tại `D:/Taadaa/runtime/artifacts/gpm_error_<safe_email>.png` (hoặc các checkpoint pre/post).
2. **Đối soát dữ liệu bảo mật**:
   - Kiểm tra xem email đã có trong `gmail_clean_v2.xlsx` chưa.
   - BẮT BUỘC đảm bảo Cột 5 (Recovery Email) có dữ liệu hợp lệ (ví dụ `@fviainboxes.com` hoặc Gmail chính chủ) trước khi chạy. Nếu thiếu, phải backfill từ đơn hàng / file gốc trước.
3. **Kiểm tra IP Cooldown 24h**:
   - Tra cứu `state["proxy_cooldowns"]` và `state["ip_cooldowns"]` trong `hotmail_changed_tracker.json`. Đảm bảo cổng proxy của máy đã qua đủ 24h kể từ lần thao tác gần nhất.
4. **Tái nạp cuốn chiếu an toàn**:
   - Sau khi thỏa mãn điều kiện dữ liệu và IP cooldown, cập nhật state file:
     ```json
     "status": "PENDING",
     "stage": "CHANGE_INFO"
     ```
   - Supervisor ở nhịp chạy kế tiếp (5 phút) sẽ tự động bốc tài khoản vào hàng đợi 5 worker phân tán 5 cổng proxy riêng biệt.
