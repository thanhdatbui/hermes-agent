# Hotmail/Outlook & TikTok Reg Batch Lessons (2026-08-18)

## 1. Màn hình Profile vs Home Feed trong `_is_home_feed_xml`
- **Triệu chứng:** Máy đã có sẵn tài khoản TikTok cũ (ví dụ Máy 3, 10, 11, 12, 25...), khi mở app vào trang Profile cá nhân thì `_is_home_feed_xml` trả về `True` vì thanh bottom nav bên dưới có nút "Trang chủ" (`o74`).
- **Hậu quả:** `_is_personal_profile_screen_xml` bị trả về `False` -> script tưởng máy mới tinh chưa có acc -> bypass bước mở dropdown tài khoản và nhảy thẳng vào màn chọn email -> timeout/fail ở `[06] Không thấy màn chọn phương thức đăng nhập`.
- **Giải pháp chuẩn:**
  - `_is_home_feed_xml` phải loại trừ ngay từ đầu nếu XML chứa các đặc trưng của Profile cá nhân: `"them tieu su"`, `"sua ho so"`, `"anh ho so"`, hoặc tab Hồ sơ đang selected.

## 2. Nhập mã OTP vào ô 6 số trên S7
- **Hiện tượng:** Màn hình OTP TikTok dạng 1 trường `EditText` lớn chứa 6 ô vuông thị giác. Nếu gọi `type_into_node(..., sensitive=True)` (dùng broadcast `ADB_KEYBOARD_INPUT_TEXT`), nếu bàn phím hệ thống Samsung (`SamsungKeypad`) đang mở thì broadcast không ăn vào trường -> 6 ô trống.
- **Giải pháp:** Đối với OTP 6 số, dùng `type_into_node(..., sensitive=False)` (gõ trực tiếp qua `input text` hoặc keyevent) sau khi tap focus vào ô.

## 3. Stale Lock của Proxy Fleet (`gan_proxy_fleet.py`)
- **Nguyên nhân:** Khi host bị tràn RAM / paging file đầy do tác vụ nặng (như render/download), tiến trình `gan_proxy_fleet.py` có thể bị đứng/kẹt khiến các file lock `C:\Users\Kibe\.codex\device-locks\machine_*.lock.json` không được giải phóng.
- **Xử lý:** Kiểm tra PID của lock file, nếu tiến trình kẹt thì `taskkill /F /PID <pid>` và xóa các file lock của `gan-proxy` / `vi_changer` để nhả máy cho batch reg chạy.

## 4. Quy tắc vận hành User
- Khi user yêu cầu "chạy reg tiktok các máy đó luôn đi", phải quét manifest target và cho chạy batch đồng loạt toàn bộ các máy rảnh (`_run_all_targets.py --full-scope-takeover`), không chỉ chạy thử nghiệm 1 máy trừ khi user chỉ định cụ thể.
