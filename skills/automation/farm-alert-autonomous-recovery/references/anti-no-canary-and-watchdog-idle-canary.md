# Chống Lạm Dụng --no-canary & Cơ Chế Watchdog Canh Rảnh Máy Thật

## 1. Nguyên Tắc Cốt Lõi
- **CẤM TUYỆT ĐỐI trốn việc bằng `--no-canary`:** Khi sửa script trên máy farm (`D:/Taadaa/Tiktok-video`, `tiktok-follow`...), Coordinator KHÔNG ĐƯỢC tự ý miễn trừ canary máy thật với lý do "bảo vệ ca nuôi" hay "máy bận lock".
- **CẤM kêu gọi con người / can thiệp thủ công (Anti-Overengineering):** Không thiết kế cơ chế hỏi ý kiến người dùng hay xin token thủ công khi máy bận lock, vì điều đó làm bại liệt tính tự động và gây over-engineering.

## 2. Quy Trình Cơ Giới Hóa O(1) Khi Máy Canary Bị Lock
1. **Gate 6 Guard tại `unified_patch_pipeline.py`:**
   - Tự động chặn và vô hiệu hóa cờ `--no-canary` khi repo thuộc farm/device.
2. **Watchdog Canh Rảnh (Auto-Canary on Idle):**
   - Khi máy mục tiêu có active lock do ca nuôi chính đang chạy, pipeline không được fail-closed hay đóng băng.
   - Kích hoạt chế độ watchdog định kỳ kiểm tra trạng thái lock thiết bị (`reap-dead-owner-locks.py`).
   - Ngay khi máy mục tiêu nhả lease về màn hình chính (Launcher/HOME), watchdog tự động kích hoạt `canary_runner.py` trên đúng máy đó để lấy bằng chứng thực tế (Ảnh + OCR).
3. **Sửa Lỗi Gap Numbering Nguồn Video:**
   - Khi folder render khuyết số (ví dụ có `1..11` rồi nhảy sang `27..61`), Gate 5 bắt buộc dùng Auto-fallback: bốc file số nhỏ nhất còn tồn tại `>= next_video` (`min(rem)`), cấm skip `video_not_rendered` khi kho vẫn còn video chưa đăng.
