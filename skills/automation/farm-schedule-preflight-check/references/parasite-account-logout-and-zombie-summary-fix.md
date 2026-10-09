# Kỷ Luật Xử Lý Nick Ký Sinh & Phòng Ngừa Zombie Summary (24/09/2026)

## 1. Bản Chất Nick Ký Sinh (Parasite Accounts) & Đăng Xuất An Toàn Từ Cài Đặt
- **Hiện tượng:** Một tài khoản thuộc máy này (ví dụ `@anggiathinh2905` thuộc Máy 28 STT 221) bị đăng nhập nhầm vào một máy khác (Máy 61), khiến máy đó chạm trần tối đa 8 tài khoản (`MACHINE_FULL_8_ACCOUNTS`) và chặn đứng mọi tiến trình reg bù tự động.
- **Xác nhận từ User & Thực tế Vận Hành:**
  - *"Log out kí sinh đc mà k lỗi đâu"*: Việc đăng xuất nick ký sinh **HOÀN TOÀN AN TOÀN KHI THỰC HIỆN QUA SETTINGS CỦA TIKTOK**.
  - Không có hiện tượng TikTok xóa sạch phiên làm việc của các nick khác khi logout riêng 1 nick được switch.
- **Quy trình chuẩn hóa trong `watchdog_idle_parasite_reconcile.py`:**
  1. Mở Switcher (`open_account_dropdown`), chọn đúng nick ký sinh mục tiêu.
  2. Vào *Hồ sơ* -> Menu 3 gạch (`tap(1005, 150)`) -> Chọn *Cài đặt và quyền riêng tư*.
  3. Vuốt xuống đáy trang, bấm *Đăng xuất* -> Xác nhận popup Đăng xuất.
  4. TikTok chỉ đăng xuất riêng nick đó và quay về danh sách tài khoản còn lại.
  5. Chụp ảnh nghiệm thu tại Account Switcher (`D:/Taadaa/reports/m<M>_switcher_verified_logout.png`) trước khi hoàn tất.

---

## 2. Phòng Ngừa Báo Cáo Ma (Zombie Summary) Trong `ensure_row_accounts.py`
- **Nguyên nhân gốc rễ:**
  - Trong `ensure_row_accounts.py`, hàm `send_telegram_summary` lấy thư mục chạy mới nhất (`dirs[0]`) từ `runtime/kibe/artifacts/runs/social-batch-all/` mà không lọc theo thời điểm batch bắt đầu (`batch_start_time`).
  - Khi một Row (ví dụ Row 5) được preflight kiểm tra nhưng không có máy nào đủ điều kiện reg mới, script nhặt lại kết quả của đợt chạy trước (Row 8 chạy cách đó 1.5 giờ) và gửi thông báo với tiêu đề `[PREFLIGHT REG BÙ ROW 5]` kèm danh sách lỗi của Row 8, gây hiểu lầm.
- **Giải pháp:** Bắt buộc đối soát `batch_start_time` và chỉ gửi summary khi batch hiện tại thực sự phát sinh lượt chạy mới.

---

## 3. Khắc Phục Treo Cổng ADB :5037 Do Zombie Process
- **Hiện tượng:** Lệnh ADB bị timeout, báo `could not read ok from ADB Server` hoặc hàng loạt thiết bị chuyển sang trạng thái `offline`.
- **Xử lý dứt điểm:** Quét sạch toàn bộ các tiến trình `adb.exe` zombie bằng lệnh:
  ```bash
  cmd.exe /c "taskkill /f /im adb.exe"
  ```
  ADB daemon sẽ tự spawn lại phiên làm việc mới sạch sẽ, phục hồi toàn bộ kết nối USB của farm.
