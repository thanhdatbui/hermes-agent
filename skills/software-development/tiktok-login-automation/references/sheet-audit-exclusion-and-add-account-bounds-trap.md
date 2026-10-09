# Bẫy Sheet Audit/Nháp Khi Load Tracking & Tọa Độ Tap Nút "Thêm Tài Khoản"

> **Áp dụng**: `D:\Taadaa\Tiktok_Reg\tiktok_login_v1.py`, `social_reg_v1.py` và các luồng auto-login recovery từ feed runner (`tiktok-luot nuoi acc`).

---

## 1. BẪY DUYỆT SHEET AUDIT TRONG TRACKING WORKBOOK (`load_tracking_accounts_for_stt`)

### 1.1. Hiện tượng & Triệu chứng lỗi
- Khi ca nuôi acc hoặc runner phát hiện thiếu nick trong switcher, runner gọi:
  ```bash
  python D:/Taadaa/Tiktok_Reg/tiktok_login_v1.py <STT> --email <username> --ss --allow-parent-lock
  ```
- Tiến trình login bị văng lỗi ngay lập tức:
  ```text
  STOPPED: Khong tim thay Gmail live tren may khop local-part 'duongthimyngoc190320011903' de xac nhan domain
  ```
- Khi kiểm tra máy, nick `@m.ngc4624` trong sheet chính `Tài Khoản` có đầy đủ:
  - TikTok ID: `m.ngc4624`
  - Mật khẩu: `Ngocduong1903@`
  - 2FA TOTP: `RKWWYQCQDTTV6TMBOLME5PE7EENXVOF6`
  - Email đầy đủ: `duongthimyngoc190320011903@gmail.com`
  Nhưng script vẫn cố mở Gmail trên máy và crash!

### 1.2. Nguyên nhân cốt lõi (Anti-Pattern)
- Trong file `taikhoan_dat_v2_updated .xlsx`, ngoài sheet chính `Tài Khoản` (hoặc `Accounts`), còn có các sheet nháp / audit như `Khong Co Trong GmailClean`, `Audit Pending`, `Máy Thiếu Acc`...
- Ở sheet `Khong Co Trong GmailClean`, dòng tương ứng lưu email dạng cụt: `duongthimyngoc190320011903` (không có đuôi `@gmail.com`).
- Hàm `load_tracking_accounts_for_stt()` lặp qua toàn bộ `wb.worksheets`:
  ```python
  # ANTI-PATTERN: Quét mọi sheet trong workbook
  for ws in wb.worksheets:
      for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
          ...
  ```
- Cả 2 dòng (dòng chuẩn từ `Tài Khoản` và dòng nháp từ `Khong Co Trong GmailClean`) đều được nạp vào danh sách. Dòng nháp bị gán issue `email_missing_domain`.
- Khi `pick_accounts(accounts, email_filter="m.ngc4624")` chạy, nó match cả 2 dòng hoặc chọn trúng dòng nháp.
- Hàm `resolve_missing_domains_from_device()` thấy có `email_missing_domain` liền kiểm tra `live_gmail_accounts(device_id)`. Do tài khoản này đã đăng ký từ lâu và không nằm trong app Gmail trên máy, script raise `RuntimeError` gây dừng toàn bộ quá trình cứu hộ.

### 1.3. Giải pháp chuẩn (Pattern Chuẩn)
1. **Khóa chặt phạm vi sheet trong `load_tracking_accounts_for_stt`**:
   Chỉ đọc duy nhất sheet canonical (`Tài Khoản` hoặc `Accounts`), loại trừ mọi sheet nháp/audit:
   ```python
   if "Tài Khoản" in wb.sheetnames:
       worksheets = [wb["Tài Khoản"]]
   elif "Accounts" in wb.sheetnames:
       worksheets = [wb["Accounts"]]
   else:
       worksheets = [
           ws for ws in wb.worksheets
           if ws.title not in ("Khong Co Trong GmailClean", "Máy Thiếu Acc", "Audit Pending")
       ] or [wb.active]
   ```
2. **Ưu tiên record canonical trong `pick_accounts`**:
   Nếu có nhiều record trùng ID, ưu tiên record từ `Tài Khoản`/`Accounts` và record không có issue `email_missing_domain`.
3. **Fallback suy luận cho login ID + Password**:
   Trong `resolve_missing_domains_from_device`, nếu account có đủ `id` + `tiktok_pass` và không chạy cờ `--otp-only`, tự động fallback sang `{local_part}@gmail.com` để tiếp tục luồng login ID+Pass+TOTP thay vì ném ngoại lệ dừng script.

---

## 2. BẪY VÙNG CHẠM DƯỚI ĐÁY MÀN HÌNH KHI BẤM NÚT "THÊM TÀI KHOẢN"

### 2.1. Hiện tượng & Triệu chứng lỗi
- Máy đã có 7 tài khoản trong app TikTok (chưa chạm trần 8).
- Khi mở Account Switcher Sheet, danh sách 7 tài khoản chiếm gần hết chiều cao màn hình.
- Nút `Thêm tài khoản` nằm ở hàng cuối cùng dưới đáy sheet với bounds: `[0,1788][1080,1920]`.
- Script cố gắng tap vào tâm bounds `(540, 1854)`.
- **Hậu quả**: Tọa độ `y=1854` nằm sát đáy mép màn hình 1920px (rơi vào vùng cảm ứng nhạy của Samsung Navigation Bar / Gesture area), khiến sự kiện tap bị hệ điều hành nuốt hoặc TikTok không nhận được sự kiện click, dẫn tới bước `[4] Tap Add account` bị timeout 300s.

### 2.2. Giải pháp chuẩn (Safe Tap Bounds)
- Không tap mù vào tâm hình học `center_y` khi node nằm sát đáy (`y2 >= 1900` trên màn hình 1080x1920).
- Khi phát hiện node `Thêm tài khoản` nằm ở hàng đáy (`bounds[3] >= 1900`):
  - Tính tọa độ tap an toàn lệch về phía trên của row:
    ```python
    x = (bounds[0] + bounds[2]) // 2  # 540
    y = bounds[1] + int((bounds[3] - bounds[1]) * 0.35)  # ~1834px thay vì 1854px
    # Hoặc clamp y trong khoảng an toàn: min(y, 1835)
    ```
  - Luôn đảm bảo tọa độ tap nằm cách mép dưới màn hình ít nhất 80-90px trên thiết bị Galaxy S7 (1080x1920) để tránh xung đột với thanh điều hướng hệ thống.
