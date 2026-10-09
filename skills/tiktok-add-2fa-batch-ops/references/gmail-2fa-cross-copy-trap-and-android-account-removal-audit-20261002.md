# Bẫy Sao Chép Nhầm 2FA Gmail Sang TikTok & Kỹ Thuật Truy Vết Lịch Sử Dỡ Bỏ Tài Khoản Qua Dumpsys Account (02/10/2026)

## 1. Hiện Tượng & Phát Hiện Gốc Rễ

### 1.1 Bẫy Sao Chép 2FA Gmail Sang Cột 2FA TikTok (44 Tài Khoản)
- Khi đối soát giữa file quản lý Gmail `gmail_clean_v2.xlsx` (sheet `Gmail Accounts`) và file tài khoản farm `taikhoan_dat_v2_updated .xlsx` (sheet `Tài Khoản`):
  - Phát hiện **44 tài khoản TikTok** có chuỗi bí mật trong cột E (`2FA`) trùng khớp 100% với Secret Key Google Authenticator của hòm thư Gmail (cột D trong `gmail_clean_v2.xlsx`).
  - Điển hình: Dòng 25 Máy 3 nick `@annhubvqttr` có mã 2FA `UJSOJQH2RMY6PCCU26NI3KI6FYBKYFCE`. Mã này thực chất là 2FA của Gmail `an.nhuan.work64541@gmail.com` tại dòng 518 `gmail_clean_v2.xlsx`.
- **Hệ quả liên hoàn:**
  1. TikTok thực tế **CHƯA TỪNG BẬT 2FA AUTHENTICATOR** (hoặc chỉ đăng ký bằng Gmail rồi ngâm).
  2. File Excel ghi nhận có 2FA, khiến script login (`tiktok_login_v1.py`) và batch runner 2FA bị đánh lừa:
     - Tưởng tài khoản đã bật 2FA nên bỏ qua (`already-enabled` hoặc skip enroll).
     - Nếu cột PASS bị rỗng, script login không thể lật sang form nhập pass + 2FA mà bị ép fallback sang luồng Email OTP.

---

## 2. Kỹ Thuật Điều Tra Khoa Học: "Tại Sao Gmail Live Mà Lại Biến Mất Khỏi Điện Thoại?"

### 2.1 Nhật Ký Phần Cứng Android Gốc (`dumpsys account`)
Khi đối mặt với nghi vấn: *"Tại sao Gmail đăng ký trên máy này lại không còn trên máy này?"*, tuyệt đối không phỏng đoán hay nghi ngờ bừa bãi. Android lưu trữ toàn bộ lịch sử thao tác thêm/xóa tài khoản trong bảng `Accounts History` của `AccountManagerService`:

```bash
adb -s <SERIAL> shell dumpsys account
```

Trích xuất lịch sử trên Máy 3 (`9885e6344655484754`):
```text
  -1,action_called_account_add,2026-09-08 01:04:18,10125,accounts,47
  13,action_account_add,2026-09-08 01:09:12,10024,accounts,48
  13,action_clear_password,2026-09-16 22:33:03,10024,accounts,50
  13,action_called_account_remove,2026-09-28 15:53:44,1000,accounts,4
  13,action_account_remove,2026-09-28 15:53:45,10024,accounts,5
  -1,action_called_account_add,2026-09-28 16:01:38,10125,accounts,6
  14,action_account_add,2026-09-28 16:07:18,10024,accounts,7
```

### 2.2 Bóc Tách Sự Thật Hiện Trường
1. **Ngày 08/09/2026 lúc 01:09:** Gmail `an.nhuan.work64541@gmail.com` (Account ID 13) **chính xác đã được tạo và nằm trên máy này**.
2. **Ngày 28/09/2026 lúc 15:53:** Script dọn dẹp xoay vòng S7 (`preflight_s7_rolling_cleanup.py`) đã kích hoạt lệnh gỡ tài khoản (`action_account_remove`) để giải phóng máy.
3. **Lúc 16:07 cùng ngày:** Script nạp đè tài khoản Gmail mới `chi.tieu.eyww770@gmail.com` (Account ID 14).
4. **Vết hở kịch bản:** Quy trình yêu cầu Gmail sau khi gỡ khỏi S7 phải được đồng bộ profile sang GPMLogin để nuôi tiếp. Tuy nhiên tài khoản này bị sót không được tạo profile GPM, dẫn đến việc hòm thư Gmail vẫn LIVE 100% nhưng không còn hiện diện trên bất kỳ thiết bị nào.

---

## 3. Ma Trận Quyết Định Triage: "Cứu Nick" vs "Thay Thế Slot"

Khi một tài khoản TikTok bị kẹt đăng nhập (vướng OTP mail do mất Gmail trên máy, hoặc vướng reCAPTCHA Google):

### 3.1 Định Lượng Giá Trị Tài Sản Kênh Trước Khi Hành Động
Trước khi tiêu tốn thời gian và can thiệp thủ công (nhờ user giải captcha, audio solver, proxy bypass), **BẮT BUỘC tra cứu ngay tài sản thực tế của kênh** trong `taikhoan_run_safe.xlsx` và `Tik<N>.xlsx`:
- **Ngày tạo / Tuổi nick:** Ví dụ 24 ngày tuổi.
- **Số lượng video đã đăng (`video_count`):**
  - Nếu `video_count == 0`: Nick chưa từng đăng clip, không có view, không có follower. Giá trị kênh gần như bằng 0 (chỉ là nick reg ngâm).
  - Nếu `video_count >= 6` hoặc kênh có view/follower lớn: Đây là tài sản quý, bắt buộc ưu tiên quy trình Cứu Nick.

### 3.2 So Sánh Chi Phí & Rủi Ro Vận Hành
| Tiêu chí | Phương Án 1: Cứu Nick Cũ | Phương Án 2: Đổi Nick Mới |
| :--- | :--- | :--- |
| **Thao tác** | Mở Android Settings -> Thêm Google -> Vượt reCAPTCHA -> Điền Pass + 2FA Google -> Mở TikTok gửi OTP -> Nhập mã -> Đổi pass TikTok. | Bốc 1 nick TikTok từ kho đã có ID + PASS + 2FA chuẩn nạp vào slot máy. |
| **Thời gian** | 15 – 30 phút, dễ vướng checkpoint IP/SMS của Google. | 1 – 2 phút, tự động hóa 100%. |
| **Ảnh hưởng Fleet** | Giữ máy bận, cản trở ca chạy feed/video tiếp theo. | Dàn máy đủ 8/8 acc và tiếp tục vận hành ngay. |
| **Áp dụng khi** | Nick có `video_count > 0`, view cao, tài sản quan trọng. | Nick có `video_count == 0` (chỉ là nick ngâm). |

---

## 4. Kỷ Luật Ứng Xử & Khắc Phục Sau Kiểm Tra

1. **Khắc phục dữ liệu bị sao chép nhầm:**
   - Với các tài khoản phát hiện cột 2FA là mã của Gmail nhưng TikTok chưa từng bật 2FA: Reset cột 2FA về rỗng trong file Excel để tránh đánh lừa các script tự động.
2. **Kỷ luật giao tiếp với User:**
   - Tránh nói "cột PASS = None" gây hiểu nhầm là script điền chữ "none" vào Excel. Giải thích rõ là ô trống (`blank cell`).
   - Luôn đưa ra bằng chứng số liệu (`dumpsys account`, ngày giờ remove, `video_count = 0`) để User có đủ cơ sở đưa ra quyết định nghiệp vụ chuẩn xác nhất.
