# Quy chuẩn Đặt tên Profile GPM & Thứ tự Ưu tiên Kho Tài khoản (2026-09-04)

## 1. Quy chuẩn Đặt tên Profile trên GPMLogin
Để quản lý trực quan trên giao diện GPM và khớp 1:1 với proxy/dàn máy:
- **Cú pháp bắt buộc:** `[Số Máy / Port Admin] - [Địa chỉ Gmail] - [Port Proxy]`
- **Ví dụ chuẩn:**
  * Farm S7: `01 - duongkien12022001@gmail.com - 5101`
  * Farm S7: `03 - lequynh27032002@gmail.com - 5103`
  * Farm S7: `16 - chuanh250416@gmail.com - 5118`
  * Farm S7 (Máy 41 dùng mobi3): `41 - marcusephillips52sns@gmail.com - 5103`
  * Admin Pool: `10008 - marcusephillips52sns@gmail.com - 10008`
  * Admin Pool: `10009 - allisononelsonojj67@gmail.com - 10009`

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
File tổng quản lý toàn bộ tài khoản tại `D:\OneDrive\TaadaaData\kibe\master_gmail_manager.xlsx` (BẮT BUỘC 100% tài khoản là Gmail, loại bỏ hoàn toàn Hotmail/Outlook) gồm 5 Sheet:
- **`Master_All`**: Tổng hợp toàn bộ tài khoản toàn hệ thống đang LIVE, tự động dedup loại trùng lặp.
- **`Gmail_Dat`**: Danh sách tài khoản LIVE ưu tiên từ file `gmail-đạt.xlsx`.
- **`Kibe_Farm_S7`**: Danh sách tài khoản LIVE dàn Kibe tương ứng từng máy S7. Cho phép nhiều tài khoản / profile trên cùng 1 máy (ví dụ Máy 01 có cả `01 - duongkien12022001@gmail.com` và `01 - thanhdatbui19951@gmail.com`).
- **`Admin_GPM_Pool`**: Phân bổ tài khoản LIVE từ kho Đạt vào các port MikroTik Admin (`10008`..`10035`).
- **`Gmail_DIE_Archive`**: Lưu trữ tách biệt 100% tài khoản Gmail DIE (được dọn sạch khỏi các sheet LIVE ở trên). Lưu trọn vẹn toàn bộ 16 cột thông tin gốc (mật khẩu, recovery, 2FA, SĐT đã ver SIM, profile GPM) để không làm mất tài khoản ChatGPT/OpenAI/Codex đã liên kết và có thể giải checkpoint khôi phục sau này.

Các cột chuẩn (16 cột):
1. `STT`: Số thứ tự
2. `Email`: Địa chỉ Gmail (`@gmail.com` only)
3. `Password`: Mật khẩu
4. `Recovery_Email`: Email khôi phục
5. `2FA_Secret`: Khóa bí mật TOTP (Base32)
6. `SDT`: Số điện thoại liên kết / đã ver SIM cũ
7. `Trạng Thái`: `LIVE` / `DIE` / `Logged_GPM` / `Pending_GPM` / `PROMPT_PHONE` / `FAILED`
8. `ChatGPT_Reg`: Trạng thái đăng ký / liên kết ChatGPT & Codex (`YES` / `CHATGPT_READY` / trống)
9. `Số Máy Farm`: `Máy 01`..`Máy 80` hoặc `Admin_Port_10008`..`Admin_Port_10035` / `Chưa gán máy`
10. `Model Điện Thoại`: `Samsung Galaxy S7` hoặc `GPM Browser / PC`
11. `Serial Thiết Bị (Device ID)`: Serial ADB của máy S7 (hoặc `MikroTik_Admin`)
12. `Proxy Đang Dùng`:
    - Với Farm S7: Format `http://192.168.110.2:{20000+mobi_idx} (test.taadaa.click:{5100+mobi_idx})`.
      *Lưu ý quan trọng:* Cổng Singbox tính theo index của mobile proxy (`mobiX`), tra từ `PROXYgandienthoai.xlsx` (ví dụ Máy 41 dùng mobi3 → `20003:5103`, Máy 42 dùng mobi4 → `20004:5104`, Máy 60 dùng mobi26 → `20026:5126`), KHÔNG tính theo số máy `20000+số máy`.
    - Với Admin pool: Format `http://192.168.110.2:200XX` (tương ứng port MikroTik `100XX`).
13. `Tên Profile GPM`: Khớp 1:1 với tên profile trên GPM (`[Số máy/Port] - [Email]`, ví dụ `41 - marcusephillips52sns@gmail.com`, `01 - thanhdatbui19951@gmail.com`)
14. `Nguồn`: `gmail-dat` / `clean_v2` / `rua_legacy` / `2592_old`
15. `Ghi Chú`: Chi tiết IP public, trạng thái xác thực, profile path
16. `Cập Nhật`: Timestamp cập nhật mới nhất (YYYY-MM-DD)

---

## 4. Nguyên tắc Bắt buộc: Bảo toàn Profile GPM & Tài sản ChatGPT / Codex (INVARIANT)
1. **CẤM TUYỆT ĐỐI xoá profile GPM khi Gmail DIE**:
   - Profile GPM chứa phiên đăng nhập, cookie, refresh token và liên kết tài khoản OpenAI / ChatGPT / Codex đã tốn tiền thuê SIM verify số điện thoại (5sim).
   - Trong các cronjob dọn dẹp (như `sync_gpm_lifecycle.py`), BẮT BUỘC chỉ đồng bộ tạo mới cho Gmail LIVE, cấm gọi API delete profile GPM gắn với Gmail DIE.
2. **Gmail DIE không đồng nghĩa ChatGPT DIE**:
   - Hệ thống Farm dùng email + mật khẩu riêng cho ChatGPT (CẤM Google SSO). Do đó khi Google khoá hoặc bắt checkpoint Gmail, tài khoản ChatGPT vẫn đăng nhập và hoạt động bình thường trên web / API.
3. **Chiến lược xử lý Google Checkpoint SĐT**:
   - **Check xác nhận số cũ (Confirm phone number):** Không gửi SMS, chỉ đối chiếu số cũ. Lấy đúng SĐT lưu tại cột `SDT` của sheet `Gmail_DIE_Archive` dán vào là vượt qua.
   - **Check SMS số mới (Mandatory Phone SMS):** Dùng API 5sim thuê số `google` (Việt Nam ~$0.18, Indo/Phil ~$0.08) để giải checkpoint, không bỏ acc.

---

## 5. Xử lý Thử thách Xác minh Thiết bị (Google Prompt trên Galaxy S7)
Khi đăng nhập tài khoản Gmail đã lưu trên thiết bị Android farm (Samsung Galaxy S7):
- Google sẽ gửi prompt *"Kiểm tra Galaxy S7 của bạn ... Nhấn vào số XX"*.
- **Cách xử lý:**
  1. Nếu máy S7 đó đang cắm online trên dàn: Dùng lệnh ADB mở notification và tap đúng số xác nhận.
  2. Hoặc click `"Thử cách khác"` $\rightarrow$ Chọn `"Xác nhận email khôi phục"` $\rightarrow$ Điền email recovery từ kho dữ liệu.
