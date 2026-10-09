# Farm Alert Preflight Reg Triage Reference (Row 8 Backfill)

## 1. Phân loại mã lỗi thường gặp khi chạy Batch Reg bù (Row 8)

### A. MACHINE_FULL_8_ACCOUNTS
- **Dấu hiệu:** `[04_add_account] MACHINE_FULL_8_ACCOUNTS: Thiết bị đã đạt giới hạn 8 tài khoản TikTok`.
- **Nguyên nhân gốc rễ:** 
  - Máy đã có đủ 7 slot chính thức trong các file `Tik1.xlsx` đến `Tik7.xlsx`.
  - Trên app TikTok thực tế đang có 1 tài khoản thứ 8 (ký sinh, nick test cũ, hoặc tài khoản đăng ký dang dở chưa dọn).
  - Khi script bung switcher, đếm số node account `_acc_count >= 8` -> kích hoạt invariant dừng để bảo vệ nick.
- **Quy trình xử lý:**
  - Tuyệt đối không force tap đè hay xóa bừa.
  - Sử dụng công cụ `clean_and_reconcile_farm_accounts.py` hoặc `watchdog_idle_parasite_reconcile.py` để scan và đối chiếu danh sách account trên thiết bị với danh sách 7 tài khoản hợp lệ trong Excel.
  - Nếu phát hiện tài khoản ngoại lai (không thuộc Tik1 - Tik7), thực hiện quy trình logout an toàn theo chuẩn `exact_logout.py` / `do_logout_account.py` trước khi chạy lại batch reg cho Row 8.

### B. ADB Timeout & MTP/USB Connection Block
- **Dấu hiệu:** `[adb-timeout] device=<serial> timeout=20s` hoặc lệnh ADB treo / chậm.
- **Nguyên nhân:**
  - Thiết bị Samsung S7 sau khi khởi động lại hoặc cắm lại cáp USB thường hiện pop-up chọn phương thức kết nối: `com.samsung.android.MtpApplication/.USBConnection`.
  - Màn hình USB Connection cản trở tương tác UI và đôi khi làm nghẽn daemon ADB.
- **Xử lý nhanh:**
  - Bắn keyevent Back (4) hoặc Home (3) để giải phóng màn hình MTP về Home launcher.
  - Kiểm tra lại bằng `dumpsys window | grep -E "mCurrentFocus|mFocusedApp"`.

### C. Không tìm thấy nút "Thêm tài khoản" / Lỗi vào tab Profile
- **Dấu hiệu:** `[04_add_account] Không tìm thấy: ('Thêm tài khoản', ...)` hoặc `Lỗi vào tab Profile`.
- **Nguyên nhân:**
  - TikTok khởi động chậm, kẹt tại `SplashActivity` hoặc xuất hiện các pop-up che khuất:
    + Pop-up lưu thông tin đăng nhập (`Smart Lock` / `Save login info`).
    + Dialog cập nhật ứng dụng TikTok.
    + Prompt yêu cầu thêm số điện thoại (`Add phone` / `so dien thoai cua ban`).
    + Tooltip hướng dẫn người dùng mới / badge che mất avatar tab Profile ở góc dưới bên phải.
- **Xử lý:**
  - Kiểm tra file ảnh và XML chụp tại hiện trường trong thư mục `screenshots_social/fail_04_add_account` hoặc `fail_03_account_dropdown_verify`.
  - Định vị tọa độ pop-up và gọi hàm dismiss pop-up tương ứng trước khi bung dropdown switcher.

### D. Máy Offline (Hardware / Cable)
- **Dấu hiệu:** `TikTok not foreground after clean launch` kèm `adb devices` không thấy serial xuất hiện.
- **Xử lý:**
  - Tra cứu serial máy trong `Tik1.xlsx`.
  - Đối chiếu với danh sách `adb devices`. Nếu serial biến mất hoàn toàn, đây là lỗi phần cứng/cáp USB hoặc máy bị sập nguồn, cần cô lập máy khỏi batch và báo cáo farm master kiểm tra vật lý.
