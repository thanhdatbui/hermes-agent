# Kỷ Luật Thực Thi Khi User Chọn PA 4 (Giữ Nguyên Gốc / No-Avatar-Change)

## 1. Bản Chất Khi User Chọn PA 4
- Khi User duyệt **PA 4** (hoặc gõ ngắn gọn `"4"`): User muốn giữ nguyên avatar hiện tại trên thiết bị / profile TikTok, không upload đè avatar mới và không tráo đổi nhân vật persona.
- **CẤM:** Cố tình upload đè avatar khác hoặc ép đổi Display Name sang giới tính/nhân vật khác gây mâu thuẫn trực tiếp với avatar hiện tại.

## 2. Quy Trình Thi Công Đầy Đủ Cho PA 4 (Disk & Registry Lockdown)
Ngay khi User chọn PA 4, Coordinator thực thi trọn vẹn quy trình cơ giới hóa:
1. **Bảo toàn & Khóa Media Trên Đĩa:**
   - Đảm bảo file `avatar.jpg` hiện tại được lưu vào cả `F_src` (`D:/video goc/<id>/avatar.jpg`) và `F_vid` (`D:/TIKTOK-videonuoinick/<id>/avatar.jpg`).
   - Cắm cờ khóa cứng `.manual_avatar_locked` và `.manual_hashtag_locked` tại cả 2 thư mục này.
2. **Đăng Ký Danh Sách Bảo Vệ (Protected Registries):**
   - Bổ sung cả 2 folder ID vào:
     + `D:/Taadaa/data/manual_avatar_protected_folders.json`
     + `D:/Taadaa/data/manual_hashtag_protected_folders.json`
   - Ngăn chặn triệt để các cronjob nuôi nick tự động, upload hook hoặc watchdog tráo đổi avatar/hashtag ở các ca kế tiếp.
3. **Đồng Bộ Sổ Cái Workbook (`Tik<N>.xlsx`):**
   - Kiểm tra và sửa triệt để lệch ngách: Cập nhật cột `Keyword Video` và `Hashtag Pool` khớp với nội dung thực tế (ví dụ: sửa từ `"Câu chuyện"` sang `"Vlog đời thường / Phong cách sống"`).
   - Đảm bảo cột `Avatar` = `"OK"`, cột `Kiểm Tra Dữ Liệu` = `"OK"`.
4. **Kỷ Luật Ghim Top Video (Pin Top):**
   - Nếu video cao nhất $< 1.000$ views: **TUYỆT ĐỐI KHÔNG GHIM ÉP** video view thấp, giữ nguyên để tài khoản phát triển tự nhiên theo thuật toán TikTok.
5. **Nghiệm Thu Thị Giác (Gate 6 & Vision Receipt):**
   - Xuất canvas tổng kết nghiệm thu hoàn tất thi công.
   - Bắt buộc quét WinRT OCR xác nhận nội dung và đăng ký `create_vision_receipt` trước khi gửi `MEDIA:` cho User.

## 3. Cảnh Báo An Toàn: Hard Gate #5 (Cấm Bấm Tay ADB)
- Mọi can thiệp vào thiết bị thật bắt buộc phải bọc qua `with_device_lock.py` hoặc runner chính thức (`do_rename_canonical_runner.py`, `pin_top_videos.py`).
- CẤM TUYỆT ĐỐI gõ trực tiếp `adb shell input tap/swipe/keyevent` để lách qua giao diện.

## 4. Bẫy Lệch Giữa Ảnh Card 4 Trên Canvas vs Hiện Trạng App Thật (Canvas Image Drift & Force Upload Trap)
- **Cơ chế bẫy:** File `avatar.jpg` trong kho `F_vid` hoặc `F_src` đã được lưu từ trước (ví dụ ảnh bạn nữ đeo kính), nhưng CHƯA ĐƯỢC BƠM LÊN APP TIKTOK THẬT (trên app TikTok thật vẫn là ảnh cũ lúc reg nick như ảnh nam, ảnh dính chữ). Khi Coordinator render Card 4 lên Canvas, ảnh hiển thị mắt thấy là bạn nữ đeo kính, nhưng nhãn text lại ghi *"Avatar hiện tại"*.
- **Hành vi User:** User nhìn vào hình mắt thấy trên Card 4 và chọn `"4"` là **CHỌN HÌNH ẢNH ĐANG HIỂN THỊ TRÊN CARD 4 ĐÓ**, chứ KHÔNG PHẢI chọn giữ cái ảnh rác/ảnh cũ đang nằm trên app TikTok thật!
- **Hành động bắt buộc:**
  1. Khi User chọn PA 4: Soi mắt kiểm tra xem ảnh hiển thị ở Card 4 có khớp 100% với ảnh đang nằm trên app TikTok thật hay không.
  2. **NẾU ẢNH TRÊN CARD 4 KHÁC VỚI ẢNH TRÊN PHONE THẬT:** BẮT BUỘC kích hoạt ngay launcher upload avatar chính thức để bơm ảnh đó lên phone thật:
     `powershell -File D:/Taadaa/Tiktok-video/run_tiktok_upload_avatar.ps1 -Tik <Tik> -ForceAvatarMachineList <Machine> -MaxParallel 1 -HostConfigPath <config>`
     (hoặc script `run_avatar_m<N>.py` chạy nền có `TIKTOK_VIDEO_AUTOMATION_CORE_VERSION=0.4.44` và input `RUN\r\n`).
  3. Sau khi upload thành công (`AVATAR_SMOKE_SUCCESS` / `FORCED_REPLACED_VERIFIED`), lấy bằng chứng màn hình `avatar-uploaded-confirmed.png` (hoặc chụp màn hình Sửa hồ sơ / Profile) quét WinRT OCR xác nhận ảnh mới đã hiển thị trên app rồi mới nghiệm thu gửi `MEDIA:` cho User. CẤM TUYỆT ĐỐI suy diễn suông là *"không cần upload vì đã là PA 4"*.
