# Quy chuẩn Đặt tên Profile GPM & Thứ tự Ưu tiên Kho Tài khoản (2026-09-02)

## 1. Quy chuẩn Đặt tên Profile trên GPMLogin
Để quản lý trực quan trên giao diện GPM và khớp 1:1 với proxy/dàn máy:
- **Cú pháp bắt buộc:** `[Port/Số Máy] - [Địa chỉ Gmail]`
- **Ví dụ chuẩn:**
  * `10008 - allisononelsonojj67@gmail.com`
  * `10009 - crystalwwilsonlypp1@gmail.com`
  * `10010 - jorgeomasonrjom2@gmail.com`
  * `16 - chuanh250416@gmail.com`

---

## 2. Thứ tự Ưu tiên Nguồn Tài khoản (Account Pool Waterfall)
Khi cần nạp tài khoản Gmail cho cụm Profile GPM (như cụm 28 port MikroTik Admin hoặc dàn Farm):
1. **Ưu tiên 1 (Kho Mail Đạt / Pass Chuẩn):**
   - Nguồn: `C:\Users\Kibe\iCloudDrive\MAIl\gmail-đạt.xlsx`
   - Đặc điểm: Chứa mật khẩu thật chuẩn 100% (`N0spam@@`, `Btmyclrlw`, `Hnpixpbvnfun`...), có mail recovery tương ứng.
2. **Ưu tiên 2 (Kho Mail Clean v2):**
   - Nguồn: `D:\OneDrive\TaadaaData\kibe\gmail_clean_v2.xlsx`
   - Dùng cho dàn 80 máy Kibe, có pass dạng `@Ks` và secret 2FA RFC Base32 chuẩn.
3. **Ưu tiên 3 (Kho Mail Thô Dự Phòng - Sau khi kiểm tra checklive):**
   - Nguồn: `C:\Users\Kibe\Downloads\Telegram Desktop\600 gmail old.xlsx` và `2592 Gmail old.txt`
   - Chỉ dùng sau khi đã vét hết kho Ưu tiên 1 & 2. Bắt buộc lọc qua `checkmail.live` và kiểm chứng mật khẩu trước khi nạp hàng loạt.

---

## 3. Cấu trúc File Quản lý Mail Tổng (`master_gmail_manager.xlsx`)
File tổng quản lý toàn bộ tài khoản tại `D:\OneDrive\TaadaaData\kibe\master_gmail_manager.xlsx` (BẮT BUỘC 100% tài khoản là Gmail, loại bỏ hoàn toàn Hotmail/Outlook) gồm 4 Sheet:
- **`Master_All`**: Tổng hợp toàn bộ tài khoản toàn hệ thống, tự động dedup loại trùng lặp.
- **`Gmail_Dat`**: Danh sách 50 tài khoản ưu tiên từ file `gmail-đạt.xlsx`.
- **`Kibe_Farm_S7`**: Danh sách 341 tài khoản dàn Kibe tương ứng từng máy `S7_May_1`..`S7_May_80`.
- **`Admin_GPM_Pool`**: Phân bổ 28 tài khoản đầu tiên từ kho Đạt vào 28 port MikroTik Admin (`10008`..`10035`).

Các cột chuẩn:
1. `STT`: Số thứ tự
2. `Email`: Địa chỉ Gmail (`@gmail.com` only)
3. `Password`: Mật khẩu
4. `Recovery_Email`: Email khôi phục
5. `2FA_Secret`: Khóa bí mật TOTP (Base32)
6. `SDT`: Số điện thoại liên kết (nếu có)
7. `Trạng Thái`: `Live` / `Die` / `Logged_GPM` / `Pending_GPM` / `PROMPT_PHONE` / `FAILED`
8. `Vị Trí Gán`: `GPM_Port_10008`, `GPM_Port_10009`, `S7_May_16`...
9. `Tên Profile GPM`: Khớp 1:1 với tên profile trên app GPM (`10008 - <email>`)
10. `Nguồn`: `gmail-dat` / `clean_v2` / `2592_old`
11. `Ghi Chú`: Chi tiết IP public, trạng thái xác thực
12. `Cập Nhật`: Timestamp cập nhật mới nhất

---

## 4. Xử lý Thử thách Xác minh Thiết bị (Google Prompt trên Galaxy S7)
Khi đăng nhập tài khoản Gmail đã lưu trên thiết bị Android farm (Samsung Galaxy S7):
- Google sẽ gửi prompt *"Kiểm tra Galaxy S7 của bạn ... Nhấn vào số XX"*.
- **Cách xử lý:**
  1. Nếu máy S7 đó đang cắm online trên dàn: Dùng lệnh ADB mở notification và tap đúng số xác nhận.
  2. Hoặc click `"Thử cách khác"` $\rightarrow$ Chọn `"Xác nhận email khôi phục"` $\rightarrow$ Điền email recovery từ kho dữ liệu.
