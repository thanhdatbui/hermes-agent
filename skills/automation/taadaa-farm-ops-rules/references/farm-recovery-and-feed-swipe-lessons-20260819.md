# Bài Học Vận Hành & Khắc Phục Lỗi Feed / Follow / Auto-Recovery (19/08/2026)

## 1. Cơ Chế Vuốt Retry 2 Lần Trên Vòng Lặp Feed Chính (`feed_swipe_smoke.py`)
- **Quy tắc:** Khi lướt feed gặp bất kỳ lỗi lạ/popup/dialog nào (`status == "failed"` hoặc `ExitStatus.MANUAL_NEEDED`) mà KHÔNG thuộc nhóm màn hình nhạy cảm (`login`, `captcha`, `verification`, `security`) $\rightarrow$ **Tự động kích hoạt cơ chế VUỐT RETRY 2 LẦN (`_swipe_recovery_on_stuck`)** để lướt qua video tiếp theo.
- Sau khi vuốt mà phát hiện máy đã sang video đề xuất tiếp theo bình thường $\rightarrow$ Reset cờ `_swipe_recovery_used = False`, cập nhật kết quả `SUCCESS` và cho phép phiên nuôi tiếp tục mượt mà.

## 2. Khóa Cứng Xoay Màn Hình Bằng Android Content Provider
- Trên các dòng Samsung TouchWiz/OneUI cũ, lệnh `settings put system accelerometer_rotation 0` có thể bị hệ điều hành tự động ghi đè lại thành `1` khi gặp video dạng ngang hoặc rung lắc cảm biến.
- **Giải pháp:** Chạy kết hợp cả lệnh ghi vào Content Provider:
  - `content insert --uri content://settings/system --bind name:s:accelerometer_rotation --bind value:i:0`
  - `content insert --uri content://settings/system --bind name:s:user_rotation --bind value:i:0`

## 3. Khắc Phục Khởi Động Khi Recents Apps Sạch Bóng (`startup.py`)
- Trong `prepare_android_for_automation`, khi máy vừa mở khóa mà danh sách app gần đây đã sạch (không có nút "Xóa tất cả / Đóng tất cả") $\rightarrow$ Không được coi là lỗi, tự động gửi phím `Home` và tiếp tục mở TikTok chạy nuôi acc bình thường.

## 4. Xử Lý Kẹt Bàn Phím / Overlay Khi Mở Account Switcher
- Khi tap vào tên tài khoản ở trang Profile để mở switcher mà bị bàn phím ảo hoặc ô bình luận `@f` che khuất $\rightarrow$ Tự động gửi phím `BACK (keyevent 4)` để đóng overlay, sau đó tap lại vào `switch_anchor` lần 2 để mở danh sách tài khoản.

## 5. Dọn Dẹp Ứng Dụng Về Home Khi Phát Hiện Nhả Follow
- Khi tài khoản dính `FOLLOW_FAILED` (TikTok không nhận follow sau khi reload) $\rightarrow$ Tự động gọi `adapter.close_all_apps()`, xóa Recent Apps và đưa máy về màn hình chính (Home) sạch sẽ để bảo vệ tài nguyên và giữ an toàn cho nick.

## 6. Chuyển Đổi Não Vision Sang Gemini 3.7 Flash (`vision_client.py`)
- Nạp Master Key 9Router vào file `.env` (`NINEROUTER_API_KEY=***`).
- Cấu hình model Vision: **`ag/gemini-3.7-flash-high`** cho tốc độ phản hồi siêu nhanh (~1.2s), nhận diện chính xác các nút bấm Tiếng Việt ("Đóng", "Thử lại", "Follow lại") trên màn hình farm.
