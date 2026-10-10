# Hotmail GPM Security Change Flow, 6H Reporting, and iec=500 Pitfalls

## 1. Chuẩn hóa 5 Bước Bảo Mật Hotmail qua GPM (100% PC, Không Dùng S7)
Quy trình đổi bảo mật trên profile GPM theo runner canonical `gpm_change_hotmail_security.py`:
1. **Bước 1 (Bật 2FA TOTP):** Sinh Secret Key offline (`pyotp`), nạp xác thực vào Microsoft proofs, lưu Secret Key vào Cột 4 Excel `gmail_clean_v2.xlsx`.
   *BẮT BUỘC add 2FA thành công mới được sang Bước 2. CẤM đổi pass mù khi chưa có 2FA.*
2. **Bước 2 (Đổi Mật khẩu):** Sinh pass mạnh ngẫu nhiên $\ge 14$ ký tự, đổi pass thành công ghi ngay vào Cột G `taikhoan_dat_v2_updated .xlsx` và Cột 3 `gmail_clean_v2.xlsx`.
3. **Bước 3 (Sign Out Everywhere):** Bấm "Đăng xuất khỏi mọi nơi" và xác nhận dialog để thu hồi token bên bán trên toàn cầu.
4. **Bước 4 (Relogin Live pass mới + TOTP):** Điều hướng trực tiếp `login.live.com`, đăng nhập lại bằng email + pass mới + giải 2FA TOTP, tích "Không hỏi lại trên thiết bị này".
5. **Bước 5 (KMSI - Duy trì đăng nhập):** Đóng Cookie consent banner và bấm [Có] tại màn hình "Duy trì đăng nhập?" để lưu sống cookie/phiên vĩnh viễn trên profile GPM.
6. **Xóa Token Cột 9 & Cooldown:** Xóa trắng Cột 9 (`token = None`) trong `gmail_clean_v2.xlsx`, gán cooldown 24h cho Egress IP và Proxy port.

## 2. Kỷ Luật Báo Cáo Định Kỳ 6H (cron_hotmail_gpm_lifecycle_6h_report.py)
- **Tách riêng lỗi BLOCKED:** TUYỆT ĐỐI KHÔNG gộp số nick bị lỗi/kẹt vào hàng đợi đang chờ (`CHANGE_INFO`). Báo cáo bắt buộc phải có dòng riêng:
  `⚠️ Lỗi / Kẹt cần cứu (BLOCKED): N (Kibe: X | Admin: Y)`
- **Hàng đợi CHANGE_INFO:** Chỉ tính các nick có status bình thường (`PENDING`, `WAITING`, `COMPLETED`), đã ngâm đủ $\ge 7$ ngày, đã reg TikTok và ChatGPT thành công.

## 3. Pitfall Lớn: Microsoft `iec=500` & Phân Loại Nick Có/Không Có Mail Khôi Phục
Khi gọi CDP nạp 2FA Authenticator tại `https://account.live.com/proofs/manage/additional`:
- **Nhóm nick ĐÃ CÓ mail khôi phục (e.g. fviainboxes.com):**
  Microsoft cho phép click `#AddProofLink` -> `#Add_msAuthApp` ("Sử dụng ứng dụng") để hiện ngay khóa bí mật `#iPlainTextData`.
- **Nhóm nick CHỈ CÓ mật khẩu (chưa có mail khôi phục hay SĐT):**
  Microsoft backend từ chối thêm app đơn lẻ và tự động redirect về:
  `https://account.live.com/proofs/Manage?iec=500&apt=3`
  Hệ quả: Modal không hiển thị khóa bí mật, script đợi `#iPlainTextData` quá 35s sẽ timeout và bị set `BLOCKED`.
- **Giải pháp xử lý:**
  - Với nick chưa có mail khôi phục: Bắt buộc chuyển hướng sang wizard cài đặt cưỡng bức qua URL: `https://account.live.com/proofs/EnableTfa` (hoặc add mail khôi phục trước).
  - Re-authentication challenge: Khi vào các trang bảo mật nhạy cảm (`EnableTfa` / `AddProof`), Microsoft thường yêu cầu đăng nhập lại (redirect sang `login.live.com`). Runner bắt buộc phải kiểm tra và giải re-auth (`#i0116` + `#idSIButton9` -> `#i0118` + `#idSIButton9` -> `#idSIButton9` KMSI) trước khi tìm tiếp selector wizard.
