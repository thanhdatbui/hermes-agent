# Bẫy Fail-Safe Add 2FA Bỏ Trống Pass, Hệ Quả Login & Kỷ Luật Giao Tiếp Với User (2026-10-02)

## 1. Nguồn Gốc Nick Có 2FA Nhưng Cột Password Bị Để Trống

### Quy trình 2 bước trong Phase B Add 2FA (`tiktok-add-bao-mat-f2a`):
1. **Bước 1**: Bật Trình xác thực (Authenticator) $\rightarrow$ Trích xuất Secret Key 32 ký tự $\rightarrow$ Ghi vào Cột E (`2FA`) của workbook.
2. **Bước 2 (`ensure_account_password_saved`)**: Chuyển sang Cài đặt $\rightarrow$ Tài khoản $\rightarrow$ Mật khẩu để đổi/đặt mật khẩu ngẫu nhiên mạnh $\rightarrow$ Ghi vào Cột D (`PASS`).

### Điểm nghẽn Fail-Safe (Commit `36de9fe` ngày 12/09/2026):
Tại cuối hàm `ensure_account_password_saved`:
```python
# Fail-safe: Nếu sau 8 lần điều hướng không vào được form đổi mật khẩu (do TikTok
# đổi nhánh UI / yêu cầu OTP email không có method password), giữ nguyên mật khẩu
# hiện tại trong workbook, không ném ngoại lệ làm crash toàn bộ phiên add 2FA đã thành công.
return
```
- **Hệ quả**: Nếu nick đã bật 2FA thành công ở Bước 1, nhưng sang Bước 2 TikTok đổi nhánh giao diện hoặc yêu cầu OTP email khiến script không vào được form mật khẩu sau 8 lần Back:
  - Script **soft-return** để không làm sập batch 40 máy.
  - Cột E (`2FA`) đã có mã, nhưng Cột D (`PASS`) **bị bỏ trống hoàn toàn**.
  - Toàn farm qua đối soát có 17 tài khoản rơi vào tình trạng này.

---

## 2. Hệ Quả Chuyền Dây Khi Chạy Auto-Login (`tiktok_login_v1.py`)

- **Bản chất 2FA TikTok**: Trình xác thực Authenticator là bước **Xác thực 2 yếu tố** xuất hiện SAU KHI đã xác thực xong `ID + Mật khẩu`.
- **Cơ chế phân luồng login**:
  ```python
  login_target = account["login_email"] if (force_otp or not (account.get("id") and account.get("tiktok_pass"))) else (account.get("id") or "").strip()
  ```
  - Khi Cột D bị trống, script thấy `not (id and tiktok_pass)` là `True`.
  - Script không thể chọn luồng ID + Pass, buộc phải chọn luồng điền Email (`login_target = account["login_email"]`).
  - TikTok đưa tài khoản vào luồng **Xác minh Email (Email OTP / Passwordless)**, hoàn toàn không chạm đến màn 2FA Authenticator.
  - Nếu hòm thư chưa nạp vào máy hoặc TikTok rate-limit/shadow-drop không phát OTP mail, phiên login văng lỗi `[7c] Không lấy được OTP`.

---

## 3. Kỷ Luật Giao Tiếp Với User (Chống Gây Hiểu Nhầm Về Dữ Liệu)

- **Tín hiệu bức xúc từ User**: *"Làm gì có chuyện có 2fa mà k có pass. R cơ chế nào óc chó thay vì để trống pass lại đi ghi chữ none vào v"*
- **Bài học xương máu**:
  - Trong Excel, ô đó là **Ô TRỐNG HOÀN TOÀN** (`blank cell`, không có bất kỳ ký tự nào).
  - Khi thư viện Python (`openpyxl`) đọc ô trống, nó trả về kiểu dữ liệu `None` (`<class 'NoneType'>`).
  - **CẤM TUYỆT ĐỐI** dùng thuật ngữ kỹ thuật code `PASS = None` hay `ghi chữ None` khi giải thích với User. Điều này khiến User hiểu nhầm là có tool/script ngớ ngẩn nào đó đã gõ chuỗi chữ `"none"` vào file Excel của họ.
  - **BẮT BUỘC** diễn đạt chuẩn xác: *"Ô mật khẩu trong file Excel đang để trống (blank cell)"*.

---

## 4. Quy Trình Khắc Phục (Remediation)

1. **Đối soát mật khẩu**:
   - Kiểm tra cột `PASS MAIL` trong file master: nhiều tài khoản lúc đăng ký ban đầu được đặt mật khẩu TikTok trùng với mật khẩu email.
2. **Chạy canary đổi pass độc lập**:
   - Sử dụng cờ `--password-only` của `run_capture_phase_b.py`:
     ```bash
     python python_runner/run_capture_phase_b.py \
       --machine <M> --serial <SERIAL> --expected-username <ID> --source-row <ROW> \
       --workbook-path "D:\OneDrive\TaadaaData\kibe\taikhoan_dat_v2_updated .xlsx" \
       --workbook-sheet "Tài Khoản" --password-only --live
     ```
   - Script chỉ thực hiện đúng bước đặt mật khẩu TikTok mạnh mới và flush ngay vào Cột D của workbook, hoàn thiện bộ 3: **ID + PASS + 2FA Key**.
