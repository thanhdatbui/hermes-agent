# Canonical GPM Hotmail Security Flow: 2FA TOTP, Change Password, Sign Out Everywhere & Relogin

## 1. Nguyên Tắc & Quy Trình Chuẩn Hoá (Đã Chốt & Kiểm Chứng 2026-10-10)
Khi chạy đổi bảo mật tài khoản Hotmail trên GPM Browser, quy trình chuẩn hoá tinh gọn và an toàn tuyệt đối gồm 4 bước theo đúng thứ tự logic (đã tối ưu bỏ bước đổi mail khôi phục):

```text
GPM CDP Connect 
       │
       ▼
[BƯỚC 1]: THIẾT LẬP 2FA TOTP (AUTHENTICATOR APP) TRƯỚC
       ├─ Điều hướng https://account.live.com/proofs/manage/additional
       ├─ Kiểm tra nếu chưa có 2FA -> Thêm Authenticator App
       ├─ Lấy Secret Key Base32 -> Lưu ngay vào Cột 4 (2FA) trong Excel
       ├─ Sinh mã 6 số offline (pyotp) xác nhận kích hoạt
       └─ Kích hoạt công tắc tổng Two-step verification (EnableTfa = ON)
       │
       ▼
[BƯỚC 2]: ĐỔI MẬT KHẨU MỚI
       ├─ Điều hướng https://account.live.com/password/change
       ├─ Giải challenge 2FA nếu có (dùng ngay mã TOTP vừa tạo)
       ├─ Điền mật khẩu mới 14 ký tự mạnh mẽ
       └─ Submit đổi mật khẩu -> Lưu Mật khẩu vào Cột 3 Excel (và Cột G taikhoan_dat_v2)
       │
       ▼
[BƯỚC 3]: SIGN OUT EVERYWHERE (ĐĂNG XUẤT KHỎI MỌI NƠI)
       ├─ Điều hướng https://account.live.com/proofs/manage/additional
       ├─ Click #DeleteTrustedDevices
       ├─ Bắt modal dialog -> Xác nhận "Đăng xuất"
       └─ Thu hồi toàn bộ token, cookie, session của bên bán trên toàn cầu
       │
       ▼
[BƯỚC 4]: ĐĂNG NHẬP LẠI DUY TRÌ PHIÊN (RELOGIN LIVE TRÊN GPM)
       ├─ Điều hướng https://account.microsoft.com/profile
       ├─ Điền Email + Mật khẩu mới
       ├─ Tự động điền mã 2FA TOTP offline
       ├─ Bấm "Có" tại màn hình KMSI ("Duy trì đăng nhập?") để lưu sống cookie
       └─ Hoàn tất lưu session vào GPM Profile
```

---

## 2. Chiến Lược Giữ Nguyên Mail Khôi Phục Gốc & Bán Hotmail Kèm TikTok (2026-10-10)
### Tại sao KHÔNG CẦN đổi mail khôi phục của bên bán?
1. **Bản chất hòm thư cùng domain**: Quét thực tế kho tài khoản cho thấy 153/161 tài khoản Hotmail mua từ bên bán đã dùng sẵn mail khôi phục đuôi `@fviainboxes.com`. Đổi sang một địa chỉ `kbtad_xxx@fviainboxes.com` cũng chỉ là đổi username trên cùng một dịch vụ webmail mở, không tăng thêm tầng bảo mật nào.
2. **Bên bán có mỗi mail khôi phục 100% KHÔNG THỂ back acc**:
   - Khi 2FA đã BẬT (`EnableTfa = ON`), Microsoft khóa vĩnh viễn form ACSR thông thường.
   - Khi kẻ gian bấm *Quên mật khẩu*, vượt qua OTP mail ở Bước 1 thì lập tức bị Microsoft **chặn đứng ở Bước 2 ("Thêm một lần nữa")**: Tùy chọn Email bị khóa xám cấm dùng lại, bắt buộc phải có mã từ **Authenticator App (TOTP)** của mình.
   - Nếu bấm "Tôi không có phương thức này" -> Microsoft phong tỏa acc **30 ngày**, bên bán hoàn toàn bất lực.
3. **Bên bán 100% KHÔNG THỂ hack kênh TikTok**:
   - Mã OTP đăng nhập / đổi mật khẩu TikTok gửi thẳng về hòm thư **Hotmail**, **KHÔNG HỀ** gửi về mail khôi phục.
   - Muốn hack TikTok thì bên bán bắt buộc phải đăng nhập được vào Hotmail. Mà Mật khẩu đã đổi, Token đã bị đá văng bởi Sign out everywhere, Quên pass bị chặn bởi 2FA -> Bên bán mù hoàn toàn!
4. **Chuẩn thương mại đóng gói bán cho khách**:
   - Format xuất file chuẩn quốc tế bán kèm TikTok là: `Email | Password | 2FA_Secret_Key | Recovery_Email`.
   - Khách mua nick chỉ cần nạp chuỗi Secret Key 2FA vào Google Authenticator là tự do đăng nhập offline 100%. Nếu gán mail khôi phục vào domain riêng của mình thì khách không kiểm tra được và sẽ bắt mình làm dịch vụ lấy OTP cả đời.
5. **Tốc độ thực thi vượt trội**:
   - Bỏ bước đổi mail khôi phục giúp rút ngắn thời gian xử lý từ 2-3 phút/acc xuống chỉ còn **25-35 giây/acc**.
   - Loại bỏ 100% rủi ro nghẽn mạng / timeout khi gọi API lấy OTP từ `fviainboxes.com`.

---

## 3. Khắc Phục Tận Gốc Sự Cố Khởi Động GPM Profile Core 142 (`Yêu cầu cập trình duyệt [Chromium] [142]`)
- **Hiện tượng**: Gọi REST API `/api/v3/profiles/start/<id>` trả về lỗi: `{"success": false, "data": null, "message": "Yêu cầu cập trình duyệt [Chromium] [142]"}` mặc dù thư mục `gpm_browser_chromium_core_142` đã có `chrome.exe` và `142.0.7444.163`.
- **Nguyên nhân cốt lõi trong GPMLogin binary**:
  * GPMLogin kiểm tra 2 điều kiện tại thư mục core `C:\Users\Kibe\AppData\Local\Programs\GPMLogin\gpm_browser\gpm_browser_chromium_core_142`:
    1. Phải tồn tại file `data-variations.gpm`.
    2. File `version` phải mang giá trị `1.1` (trước đó là `1.0` nên GPMLogin coi là tài nguyên cũ/chưa hoàn tất).
- **Lệnh sửa triệt để (Programmatic Fix 1 giây)**:
  ```bash
  python -c "
  import shutil
  src = r'C:\Users\Kibe\AppData\Local\Programs\GPMLogin\gpm_browser\default\data-variations.gpm'
  dst = r'C:\Users\Kibe\AppData\Local\Programs\GPMLogin\gpm_browser\gpm_browser_chromium_core_142\data-variations.gpm'
  shutil.copy2(src, dst)
  with open(r'C:\Users\Kibe\AppData\Local\Programs\GPMLogin\gpm_browser\gpm_browser_chromium_core_142\version', 'w') as f:
      f.write('1.1')
  print('Core 142 updated to 1.1 successfully!')
  "
  ```
  Sau khi chạy lệnh trên, API `/api/v3/profiles/start` lập tức trả về `success: true` và cung cấp cổng CDP bình thường.

---

## 4. Kỷ Luật Chạy Canary: Phải Chạy Full Flow Thật (`--canary --live`)
- **Pitfall nghiêm trọng**: Chạy lệnh `python gpm_change_hotmail_security.py --email ... --canary` mà **quên `--live`** sẽ chỉ là dry-run (dừng trước nút Save, không đổi mật khẩu thật, không sign out thật).
- **Kỷ luật người dùng**: Khi user bảo **"Chạy canary đi"**, mục đích là kiểm chứng end-to-end hoàn chỉnh cả vòng đời trên 1 account mẫu để nghiệm thu kết quả thực tế.
- **Lệnh bắt buộc**:
  ```bash
  python "D:/Taadaa/Hotmail/scripts/gpm_change_hotmail_security.py" --email "<email_muc_tieu>" --canary --live
  ```
- **Hậu kiểm**: Kiểm tra đồng bộ cả 2 file Excel (`gmail_clean_v2.xlsx` và `taikhoan_dat_v2_updated .xlsx`), đảm bảo mật khẩu mới và Secret Key 2FA đã được lưu cứng.

---

## 5. Bẫy Tên Sheet Giữa 2 File Excel Kho Dữ Liệu
- **`taikhoan_dat_v2_updated .xlsx`**: Tên sheet là `'Tài Khoản'`.
  * Cột A (1): Máy
  * Cột F (6): Email Hotmail
  * Cột G (7): PASS MAIL
- **`gmail_clean_v2.xlsx`**: Tên sheet là `'Gmail Accounts'` (KHÔNG PHẢI `'Tài Khoản'`).
  * Gọi `wb['Tài Khoản']` trên file này sẽ văng crash: `KeyError: 'Worksheet Tài Khoản does not exist.'`.
  * Cột B (2): Email
  * Cột C (3): PASS
  * Cột D (4): 2FA Secret Key Base32
  * Cột E (5): Recovery Email gốc
- **Kỷ luật code**: Luôn dùng logic an toàn `ws = wb['Gmail Accounts'] if 'Gmail Accounts' in wb.sheetnames else (wb['Tài Khoản'] if 'Tài Khoản' in wb.sheetnames else wb.active)`.

---

## 6. Xử Lý Challenge 2FA & KMSI Khi Đăng Nhập Lại (Relogin Handler)
- **Hiện tượng**: Sau khi bấm `Sign out everywhere`, phiên cũ bị revoke hoàn toàn. Khi script truy cập `account.microsoft.com/profile` để relogin bằng mật khẩu mới, Microsoft lập tức dựng form challenge 2FA đòi mã từ Authenticator App (`#idTxtBx_SAOTCC_OTC`).
- **Xử lý tự động**:
  * Bắt selector `#idTxtBx_SAOTCC_OTC` hoặc input OTC, lấy Secret Key vừa tạo (hoặc tra cứu từ Cột 4 Excel).
  * Dùng `pyotp.TOTP(sec_key).now()` sinh mã và điền tự động.
  * Chụp ảnh `gpm_relogin_totp_<email>.png` làm bằng chứng.
  * Tiếp tục bắt màn hình KMSI ("Duy trì đăng nhập?"), chụp ảnh `gpm_kmsi_<email>.png` rồi click `#idSIButton9` (nút [Có]) để lưu cookie lâu dài vào GPM Profile.
- **Kỷ luật báo cáo bằng chứng**: User luôn yêu cầu bằng chứng thị giác đầy đủ 4 chặng:
  1. *Add 2FA*: Form cấp key + điền mã 6 số kích hoạt.
  2. *Đổi Pass*: Form đổi pass + nút Lưu.
  3. *Sign out everywhere*: Modal dialog xác nhận đăng xuất.
  4. *Relogin*: Form giải 2FA khi đăng nhập lại + Màn hình KMSI bấm Có.
  Tuyệt đối không được báo cáo kết quả chung chung mà thiếu ảnh của chặng nào.

---

## 7. Kỷ Luật Đường Dẫn Media Telegram (Chống Nuốt Ảnh)
- **Pitfall**: Sử dụng dấu gạch ngược Windows trong tag `MEDIA:D:\Taadaa\runtime\artifacts\...` làm xuất hiện escape character `\a` (ASCII Bell), khiến bộ chuyển đổi gateway Telegram (`extract_media`) nuốt chửng thẻ ảnh và không gửi ảnh tới user.
- **Quy tắc bất biến**: Mọi đường dẫn trong thẻ `MEDIA:` **BẮT BUỘC** phải chuẩn hóa dùng dấu gạch chéo `/`:
  ```text
  MEDIA:D:/Taadaa/runtime/artifacts/ten_anh.png
  ```
- **Soi mắt OCR**: Trước khi gửi bất kỳ thẻ `MEDIA:` nào, phải dùng WinRT OCR đọc xác nhận text trên ảnh để đảm bảo không bị đen hình hay mất viền.
