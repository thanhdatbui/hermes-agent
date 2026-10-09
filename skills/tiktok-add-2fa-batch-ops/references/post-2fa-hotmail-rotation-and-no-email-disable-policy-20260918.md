# Quy Trình Bỏ Ép Xóa 2FA Email & Chuỗi Cuốn Chiếu Đổi Pass Hotmail Sau 2FA (Chốt 18/09/2026)

## 1. Bối cảnh & Chỉ đạo dứt khoát từ Operator (18/09/2026)
1. **TikTok Add 2FA:** **BỎ HOÀN TOÀN BƯỚC GỠ GMAIL / EMAIL KHỎI BẢO MẬT**.
   - *Nguyên nhân:* TikTok v46+ trên tài khoản no-phone chặn hoàn toàn việc xóa method 2FA Email (server trả toast *"Không thể thay đổi cài đặt vì lý do bảo mật, hãy thử lại sau"*). Việc cố bấm xóa làm kẹt flow, gây timeout và sinh lỗi `EMAIL_DISABLE_NOT_STABLE`.
   - *Luồng 2FA chuẩn:* Chỉ gồm 2 bước:
     1. Bật Trình xác thực (Authenticator TOTP) -> Lưu Secret Key 32 ký tự vào Cột E Excel.
     2. Đổi Mật khẩu TikTok mạnh (`generate_account_password`) -> Lưu Pass TikTok vào Cột D Excel.
     3. Kết thúc -> Giữ nguyên Email song song với TOTP và Mật khẩu.

2. **Chuỗi Cuốn Chiếu Đổi Pass Hotmail Ngay Sau TikTok 2FA:**
   - Sau khi nick hoàn tất Add 2FA TikTok (hoặc trong batch cuốn chiếu), kích hoạt ngay luồng đổi pass Hotmail cho tài khoản đó.
   - **Mục tiêu:** Chống bên bán back tài khoản Hotmail sau khi nick TikTok đã được kích hoạt 2FA.

3. **Nguyên tắc Idempotency: "CHỈ CHANGE HOTMAIL CHƯA TỪNG CHANGE":**
   - Không đổi đè lên các tài khoản Hotmail đã từng được đổi pass.
   - Nhận diện qua 3 lớp:
     1. **Audit Log / State File:** Tra cứu `cron-state/hotmail_changed_tracker.json` hoặc `.ai-runs/hotmail-change-info/`.
     2. **Định dạng mật khẩu Cột G Excel (`PASS_MAIL`):** Nếu mật khẩu đã là dạng random mạnh 14-16 ký tự của farm (thỏa mãn `not password_needs_rotation(pass_mail)`), bỏ qua không đổi lại. Chỉ đổi các mật khẩu còn mang cấu trúc gốc của bên bán (pass ngắn, pass shop lộ liễu).
     3. **Audit DB / JSON:** Ghi nhận `status: SUCCESS` và timestamp ngay khi đổi pass thành công.

---

## 2. Kiến trúc Luồng Cuốn Chiếu 3 Giai Đoạn

```
[TikTok 2FA Hoàn tất] (Authenticator: Bật + Pass TikTok: Bật; KHÔNG gỡ email)
         │
         ▼
[Kiểm tra Hotmail Cột F & G Excel]
         │
         ├── Đã change trước đó (hoặc pass mạnh / có trong state tracker) ──► BỎ QUA (SKIP)
         │
         ▼
[GIAI ĐOẠN 1: Đổi Pass Web Chrome trên S7 qua Proxy máy]
  1. Mở Chrome -> Đăng nhập bằng pass cũ bên bán.
  2. Vào account.live.com/password/change -> Đổi sang Pass Random Mạnh mới.
  3. Xóa mail khôi phục rác của bên bán (nếu có). CẤM GẮN MAIL KHÔI PHỤC CÁ NHÂN!
  4. Bấm "Sign out everywhere" (Đăng xuất khỏi mọi nơi) -> Thu hồi 100% token/session cũ.
         │
         ▼
[GIAI ĐOẠN 2: Đồng bộ Dữ liệu & Ghi nhận Log]
  1. Cập nhật Pass Mới vào Cột G (PASS_MAIL) của file Excel taikhoan_dat_v2_updated .xlsx.
  2. Ghi nhận email vào `hotmail_changed_tracker.json`.
         │
         ▼
[GIAI ĐOẠN 3: Đăng nhập App Outlook trên Máy S7]
  1. Mở app com.microsoft.office.outlook.
  2. Đăng nhập bằng Pass Mới vừa đổi.
  3. Giữ phiên sạch vĩnh viễn trên máy, sẵn sàng bàn giao cho khách mua nick.
```

---

## 3. Quy tắc Bàn giao Sạch (Clean Delivery)
- **CẤM TUYỆT ĐỐI** gắn email khôi phục cá nhân của admin/operator (như `thanhdatbui...` hay `khoale...`) vào Hotmail.
- Bộ sản phẩm xuất xưởng giao khách:
  `ID TikTok | Pass TikTok | Secret 2FA | Hotmail | Pass Hotmail Mới`
- Khách tự cầm trọn quyền cả nick TikTok lẫn hộp thư Hotmail gốc, an toàn tuyệt đối 100%.
