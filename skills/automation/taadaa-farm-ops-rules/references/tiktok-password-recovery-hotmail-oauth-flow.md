# Quy trình cứu & khôi phục nick TikTok bị lệch Pass qua Hotmail / Microsoft Graph API

Ngày đúc kết: 2026-09-18
Phạm vi: Toàn Phone Farm Taadaa (Máy Android Samsung Galaxy S7 / SM-G930K, TikTok v46+, Hotmail/Outlook)

---

## 1. Bản chất gốc rễ sự cố "Sai mật khẩu TikTok trên hàng loạt máy"
1. **Lúc Reg nick:** Nhiều đợt reg tài khoản TikTok bằng Email, TikTok skip màn hình đặt mật khẩu và cho vào thẳng Profile. Tài khoản TikTok thực tế trên server **hoàn toàn chưa có mật khẩu**.
2. **Bug ghi Excel cũ (`social_reg_v1.py`):** Thay vì để trống cột PASS, script cũ tự động chạy hàm fallback `tiktok_pw = make_tiktok_password(mail_pw)` bịa ra một chuỗi mật khẩu random ghi vào Excel.
3. **Hậu quả:** File Excel có mật khẩu nhưng server TikTok không có. Khi đăng nhập lại trên máy mới / login lại, TikTok báo: `Sai tài khoản hoặc mật khẩu`.

---

## 2. Kỷ luật mật khẩu mới (Operator Rule 2026-08-25 & 2026-09-17)
- **TUYỆT ĐỐI CẤM dùng mật khẩu có đuôi `@Ks`** (ví dụ `Susan123@Ks`, `Linhle1505@Ks` là format cũ cấm dùng).
- **Mật khẩu chuẩn mạnh mới:** Bắt buộc dùng `generate_account_password(16)` từ `tiktok-add-bao-mat-f2a/python_runner/core/passwords.py` sinh chuỗi 16-18 ký tự ngẫu nhiên (chữ hoa, thường, số, gạch ngang `-`, không đuôi cố định).
- **Khi reg không có pass:** Cột PASS trong Excel **BẮT BUỘC ĐỂ TRỐNG (`None` / `""`)**. Tuyệt đối không sinh pass ảo ghi vào file.

---

## 3. Vì sao không Reset Password được trên App TikTok mà phải dùng Web Chrome?
- **App TikTok:** Khi bấm *"Bạn cần trợ giúp đăng nhập?"* -> *"Đặt lại mật khẩu bằng email"*, sau khi nhập OTP từ email, app TikTok trên thiết bị mới (Trust score thấp) thường **tự động đá văng về màn hình đăng nhập hoặc màn hình FAQ Hỗ trợ**, không cho mở form đặt mật khẩu mới.
- **Trình duyệt Chrome (`tiktok.com/login/email/forget-password`):**
  + Giao diện web cho phép điền email -> nhận mã OTP -> **nhập mật khẩu mới trực tiếp**.
  + Sau khi submit mật khẩu mới trên web thành công, quay lại App TikTok đăng nhập bằng Email + Mật khẩu mới vừa tạo là vào thẳng Profile 100%.

---

## 4. Quy trình xử lý Hotmail khi bị sai pass / checkpoint Microsoft
1. **Trường hợp có sẵn OAuth Token trong `hotmail_all_60_bought.txt`:**
   - Dùng Graph API lấy OTP trực tiếp ngầm trong 1 giây qua `read_tiktok_otp_from_graph_token` hoặc `exchange_refresh_token()`. Không cần mở app mail, không sợ kẹt browser.
2. **Trường hợp Hotmail phôi cũ (chỉ có mail|pass mail):**
   - **CẤM dùng App Outlook Android:** App Outlook trên Android 8 khi gặp tài khoản lạ thường tự động chuyển hướng WebView sang `Tạo tài khoản Microsoft mới (@outlook.com.vn)`, gây lỗi không tìm thấy ô nhập pass.
   - **BẮT BUỘC dùng Web Chrome (`login_web_legacy`):**
     + Mở `login.live.com` qua Chrome Android.
     + Nếu Microsoft báo mật khẩu sai và hiện link `Gửi mã đến th*****@gmail.com`:
       Tap vào link -> Điền `thanhdatbui1995@gmail.com` -> Bấm gửi mã.
     + Chạy script IMAP `flows/hotmail_recovery.py` kết nối `imap.gmail.com:993` tự động đọc mã OTP Microsoft gửi về hộp thư của user.
     + Điền mã OTP vào web Microsoft -> Bấm Back đóng popup passkey -> Bấm `Có` duy trì đăng nhập -> Vào thẳng Inbox `outlook.live.com/mail/0/inbox` để đọc mã TikTok.

---

## 5. Đồng bộ dữ liệu Excel ngay sau khi cứu nick
Ngay khi đăng nhập thành công vào TikTok, BẮT BUỘC cập nhật đồng bộ mật khẩu mới vào cả 3 file dữ liệu:
1. `D:\OneDrive\TaadaaData\kibe\taikhoan_dat_v2_updated .xlsx` (cột D)
2. `D:\OneDrive\TaadaaData\kibe\taikhoan_run_safe.xlsx` (cột D)
3. File workbook tương ứng của ca (`Tik1.xlsx` -> `Tik8.xlsx`)
