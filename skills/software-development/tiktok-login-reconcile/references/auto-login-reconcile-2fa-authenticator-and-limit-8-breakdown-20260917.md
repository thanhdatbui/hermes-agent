# Auto-Login Reconcile: Phân tích thất bại (Timeout 900s & Exit code 4) do 2FA Authenticator & Lệch danh tính nick thiếu

## 1. Bối cảnh sự cố (2026-09-17)
- **Triệu chứng**: Alert farm báo lỗi hàng loạt máy (M1, M14, M50, M51, M59, M60, M66, M71, M74) dừng phiên với chữ ký lỗi:
  `manual-needed:account-switcher-missing-expected: expected account not found in account switcher`.
- **Cơ chế Case 74**: Trong `feed_swipe_smoke.py`, hook `_maybe_recover_missing_account_via_login()` tự động kích hoạt subprocess chạy `reconcile_tiktok_accounts.py` để bù nick thiếu từ master Excel vào thiết bị.
- **Thực tế thất bại**: Subprocess con hoặc bị **Timeout sau 900 giây (15 phút)** hoặc kết thúc với **Returncode = 4 (FINAL_BLOCKED)**.

---

## 2. Nguyên nhân cốt lõi (Root Causes)

### A. Lệch phạm vi đăng nhập (All Assigned vs Single Expected Account)
- Khi `verify_and_switch_profile` phát hiện thiếu tài khoản mục tiêu (ví dụ `@lipsellczaw` ở Ca 1 / Row 1), `_maybe_recover_missing_account_via_login` gọi `reconcile_tiktok_accounts.py --machines <M>`.
- CLI `reconcile_tiktok_accounts.py` so sánh toàn bộ 8 tài khoản gán trong `safe.xlsx` với thiết bị (`device_missing = set(assigned) - set(device_accounts)`).
- Nếu máy đang thiếu nhiều hơn 1 nick (ví dụ thiếu cả Slot 1 `@lipsellczaw` và Slot 5 `@buithudung2011`), runner login tuần tự theo thứ tự xuất hiện trong workbook thay vì ưu tiên đúng nick mà ca chạy đang cần.

### B. Kẹt 2FA OTP Authenticator & Màn hình TikTok mới
- Khi tiến hành đăng nhập bằng Email/Password, TikTok xuất hiện màn hình xác thực 2 bước:
  - Header: `"Xác minh 2 bước"`
  - Title: `"Ứng dụng xác thực"` (`com.ss.android.ugc.trill:id/f4c`)
  - Subtitle: `"Mã đã được gửi đến ứng dụng xác thực của bạn"` (`:id/f2k`)
  - Checkbox tin tưởng thiết bị: resource-id `:id/dvy` / container `:id/dvt` (thay vì `:id/dly` ở các bản TikTok cũ).
- Trong `social_reg_v1.py` / `tiktok_login_v1.py`:
  1. `handle_tiktok_authenticator_2fa` chỉ tìm checkbox `dly`, không nhận diện `dvy` để tick chọn "Tin tưởng thiết bị".
  2. TOTP code được tính dựa trên epoch của thiết bị. Nếu màn hình yêu cầu phương thức xác thực khác hoặc TikTok từ chối mã (`"Nhập mã hợp lệ"`), vòng lặp lặp lại 6 rounds và rơi vào bẫy rate-limit hoặc timeout 900s.

### C. Chạm trần 8 nick trên thiết bị do Nick Ngoài Luồng / Nick Ký Sinh
- Trên các máy như M14, M66, Switcher trên app thực tế đã có đủ 8 nick (danh sách đã đầy, không còn nút *"Thêm tài khoản"*).
- `login_one_account` gọi `ensure_login_entry_screen` -> `tap_add_account`, không tìm thấy nút "Thêm tài khoản" -> ném exception: `Máy đã có ... tài khoản — đạt giới hạn tối đa 8` (exit code 4).
- Trên M1 xuất hiện nick `@ahmetsguthe17` không nằm trong danh sách quản lý của M1 ở cả `taikhoan_run_safe.xlsx` lẫn master `taikhoan_dat_v2_updated .xlsx`, chiếm mất 1 slot trống khiến app không cho thêm nick chính chủ.

---

## 3. Quy chuẩn Khắc phục & Vận hành Chuẩn

1. **Khóa Batch khi gặp Lỗi Lan Rộng (Canary Policy)**:
   - Khi có >5 máy dính cùng một lỗi account-switcher, TUYỆT ĐỐI KHÔNG retry hàng loạt.
   - Bắt buộc inspect O(1) hiện trường 1 máy đại diện (screencap + dumpsys/ATX XML).

2. **Dọn Nick Ký Sinh / Nick Ngoài Luồng Trước Khi Login Bù**:
   - Trước khi nạp nick thiếu, kiểm tra số lượng nick trong Switcher:
     - Nếu app có $\ge 8$ nick: BẮT BUỘC xác định nick ký sinh / nick rác không có trong workbook và đăng xuất (hoặc gỡ qua màn hình Fast Login / One-tap) để đưa số nick về $<8$.
     - TUYỆT ĐỐI KHÔNG bấm "Đăng xuất" trong Settings (sẽ làm văng toàn bộ các nick còn lại).

3. **Cập nhật Bộ Selector 2FA Authenticator**:
   - Mở rộng nhận diện checkbox "Tin tưởng thiết bị" gồm cả `dly`, `dvy`, `dvt` và text `Tin tưởng thiết bị này`.
   - Bổ sung kiểm tra rate-limit / invalid code để fail-soft sớm, tránh đốt hết 900s timeout.
