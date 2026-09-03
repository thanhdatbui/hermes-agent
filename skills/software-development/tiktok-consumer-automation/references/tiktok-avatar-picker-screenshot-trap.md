# Pitfall & Fix: Quản lý chọn Avatar TikTok khi có ảnh Screenshot / OTP cũ

## Hiện tượng (Phát hiện 20/08/2026 trên Máy 43 / nick `minh.minh.chu7`)
- Khi thực hiện upload Avatar TikTok trên thiết bị farm, quy trình push file `avatar.jpg` vào `/sdcard/Pictures/` hoặc `/sdcard/DCIM/Camera/` và quét MediaStore.
- Tuy nhiên, nếu trên thiết bị trước đó có phát sinh các ảnh chụp màn hình (ví dụ: ảnh chụp mã OTP `_ss.png`, ảnh thông báo hệ thống, ảnh recovery...), các file này cũng nằm trong MediaStore.
- Khi giao diện Media Picker của TikTok mở ra (danh mục "Gần đây"), các ảnh chụp màn hình này có thể nằm ở ô đầu tiên (vị trí 1/2) và bị chọn nhầm làm avatar thay vì ảnh chân dung người thật.

## Bài học & Giải pháp phòng tránh
1. **Dọn dẹp ảnh tạm trước khi push avatar:**
   - Trước khi upload avatar, chạy lệnh dọn dẹp các file screenshot tạm cũ trong thiết bị:
     ```bash
     adb -s <serial> shell rm -f /sdcard/_ss.png /sdcard/_ss_social.png /sdcard/Pictures/_ss*
     ```
2. **Kiểm tra Media Picker bằng Vision / Coordinate Detection:**
   - Không tap mù ô đầu tiên (Top-Left 0,0) nếu chưa xác nhận ô đó là ảnh chân dung.
   - Chụp màn hình Media Picker và dùng Vision check để xác định đúng vị trí ô ảnh chân dung (ô chứa người thật, không phải văn bản/screenshot lỗi).
3. **Ưu tiên ảnh chân dung nghệ thuật chất lượng cao:**
   - Luôn đối chiếu ảnh nguồn trong folder `D:\TIKTOK-videonuoinick\<folder>\avatar.jpg` hoặc `D:\video goc\<folder>\avatar.jpg`.
