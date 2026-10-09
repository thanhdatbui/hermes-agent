# QUY TẮC PHÒNG CHỐNG NICK KÝ SINH (PARASITE ACCOUNT PREVENTION) & ĐĂNG NHẬP CHÉO MÁY TRÊN TAADAA FARM

> **Sự cố thực tế (Incident 2026-09-24):** 
> Coordinator test email `odessostuffen14@hotmail.com` trên Máy 201. Khi TikTok trả về màn hình "Bạn đã đăng ký", Coordinator tiện tay bấm "Tiếp tục" rồi gọi Graph API lấy mã OTP nhập vào. Hậu quả: Tài khoản `@lethanhlan14` (vốn đã được reg thành công trên Máy 22 trưa cùng ngày) bị đăng nhập phiên song song lên cả Máy 201, biến thành nick ký sinh 2 thiết bị vật lý khác nhau (Kibe vs Admin), làm sai lệch mapping và có nguy cơ bị TikTok trảm vì login bất thường.

---

## 1. NGUYÊN TẮC BẤT BIẾN (INVARIANTS)

1. **SOURCE-OF-TRUTH FIRST — TRA CỨU TRƯỚC KHI THAO TÁC:**
   - Trước khi mang bất kỳ email / account nào đi test đồ, reg thử hay probe:
     👉 **BẮT BUỘC tra cứu mapping trước** (`taikhoan_dat_v2_updated .xlsx`, `taikhoan_run_safe.xlsx`, `tiktok_tracker.db`, hoặc log `social_reg_log.txt`).
   - Nếu account đã thuộc sở hữu của Máy A: **CẤM TUYỆT ĐỐI** mang sang Máy B gõ vào form.

2. **CẤM BIẾN TOOL REG THÀNH TOOL LOGIN LÉN (SCREEN-STATE CHOKEPOINT):**
   - Trong luồng đăng ký (`social_reg_v1.py`), khi điền email mà TikTok trả về:
     - *"Bạn đã đăng ký"* (You've already registered)
     - Màn hình nhập password nick cũ
     - Màn hình OTP của nick cũ
   - 👉 **HÀNH ĐỘNG DUY NHẤT ĐƯỢC PHÉP:** Chụp ảnh hiện trường, ghi nhận kết quả *"Email đã đăng ký"*, BACK hoặc force-stop về Home.
   - 👉 **CẤM TUYỆT ĐỐI:** Bấm *"Tiếp tục"* và lấy OTP nhập vào để mở phiên. Tool reg chỉ được phép tạo nick mới, không được tự ý đăng nhập nick cũ.

3. **PHÂN BIỆT RẠCH RÒI REG vs LOGIN:**
   - **Tạo nick mới:** Dùng `social_reg_v1.py` (chỉ chấp nhận email Zin, gặp mail cũ phải thoát).
   - **Login lại nick cũ khi bị văng:** Dùng `tiktok_login_v1.py` (chỉ cho phép login vào đúng STT máy đã được gán trong workbook, kiểm tra qua `assert_account_machine_binding`).

4. **CƠ CHẾ DI CHUYỂN MÁY (MIGRATION) HỢP LỆ:**
   - Khi máy cũ chết/hỏng hoặc operator chủ ý chuyển nick từ Máy A sang Máy B:
     - Cách 1: Cập nhật STT mới trong workbook tracking (`taikhoan_dat_v2_updated .xlsx` hoặc `taikhoan_run_safe.xlsx`).
     - Cách 2: Gọi `tiktok_login_v1.py <STT_mới> --email <nick> --override-machine` (cờ override tường minh của operator).

---

## 2. QUY TRÌNH XỬ LÝ SỰ CỐ KHI LỠ ĐĂNG NHẬP NHẦM MÁY (REMEDIATION)

Nếu phát hiện nick đang ở sai máy (nick ký sinh):
1. **Tuyệt đối không để nguyên phiên:** Bắt buộc đăng xuất ngay lập tức.
2. **Quy trình đăng xuất chuẩn trên thiết bị:**
   - Mở app TikTok -> Tap tab `Hồ sơ` (Profile, góc dưới cùng bên phải: `972 1857`).
   - Mở menu hồ sơ 3 gạch (góc trên bên phải: `1002 144`).
   - Chọn `Cài đặt và quyền riêng tư` (Settings & privacy).
   - Cuộn xuống đáy trang Settings (swipe 4-5 lần).
   - Tap nút `Đăng xuất` (Logout).
   - Xác nhận `Đăng xuất` tại popup.
   - Kiểm tra lại Switcher tài khoản bằng screencap + OCR để bảo đảm nick ký sinh đã biến mất hoàn toàn và danh sách tài khoản của máy đã trở về trạng thái sạch sẽ.
3. Force-stop app TikTok và đưa máy về Launcher HOME an toàn.
