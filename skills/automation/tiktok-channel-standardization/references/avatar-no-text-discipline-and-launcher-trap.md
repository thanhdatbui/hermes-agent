# Kỷ Luật Trích Xuất Avatar Không Dính Chữ (No-Text Invariant) & Bẫy Chụp Lộn Launcher Khi Watchdog Xong

## 1. Kỷ Luật Trích Xuất Avatar Sạch Chữ 100% (No-Text / No-Overlay Invariant)
- **Tín hiệu từ User:** *"tìm ảnh khác k dính chữ"*
- **Bối cảnh & Bẫy:**
  - Khi trích xuất frame từ video ngắn (TikTok/Reels/Shorts), rất nhiều clip có phụ đề (subtitles), tiêu đề chèn giữa màn hình, nhãn dán, watermark tài khoản hoặc chữ chạy karaoke.
  - Nếu Coordinator lười biếng chỉ chạy face detection hoặc crop nhanh theo timestamp đầu tiên mà không soi mắt bằng `browser_vision` để kiểm tra vùng ngực, vai, trán hoặc xung quanh mặt xem có chữ đè lên không, ảnh xuất ra sẽ bị dính chữ (ví dụ: chữ tiêu đề đè qua trán/vai của nhân vật).
- **Quy chuẩn bắt buộc:**
  - **Kiểm tra chữ trước khi đưa vào Canvas:** Trước khi ghép candidate vào bảng Proposal Canvas, BẮT BUỘC dùng `browser_vision` soi trực tiếp từng crop $512\times512$.
  - **Tiêu chuẩn "Sạch chữ 100%":**
    * Không dính phụ đề (hardsub) ở nửa dưới hoặc trôi ngang người.
    * Không dính watermark, logo kênh ở các góc.
    * Không dính chữ tiêu đề clip đè lên đầu/trán/vai/ngực.
  - **Cách tìm frame sạch chữ nhanh O(1):**
    * Lấy mẫu ở các giây đầu (0.5s - 1.5s) hoặc các đoạn chuyển cảnh B-roll, đoạn nhân vật dạo phố/ngoài trời không có chữ giải thích.
    * Quét nhanh các clip khác nhau trong kho (`D:/video goc/<N>` hoặc `D:/TIKTOK-videonuoinick/<N>`), ưu tiên các clip quay ngoại cảnh hoặc vlog đời thường không chèn text đồ họa.

## 2. Bẫy Chụp Lộn Màn Hình Launcher Khi Watchdog Hoàn Tất (Home Screen Capture Trap)
- **Hiện tượng:**
  - Runner upload avatar (`run_tiktok_upload_avatar.ps1`) sau khi đổi avatar xong thường bấm nút Home hoặc kill app, đưa điện thoại về màn hình chính (Launcher/Home Screen).
  - Watchdog chỉ đơn thuần gọi `screencap` ngay sau khi runner exit mà không mở lại Profile TikTok:
    * Kết quả ảnh nghiệm thu chụp được là màn hình chính của Samsung (`LauncherActivity`, icon Facebook, Bộ sưu tập, Đồng hồ...).
    * Dù `run_winrt_ocr.py` trả về `ocr_status=OK`, nhưng text OCR chỉ toàn app system của điện thoại, KHÔNG HỀ có text của Profile TikTok.
- **Quy chuẩn bắt buộc (Profile-Guaranteed Capture sau Watchdog):**
  - **CẤM TUYỆT ĐỐI chụp mù ngay khi runner exit.**
  - **Bắt buộc FSM kiểm tra Profile:** Sau khi upload avatar, BẮT BUỘC gọi `do_rename_canonical_runner.py` để verify hoặc chạy script mở lại TikTok và tap vào tab Hồ sơ `(972, 1857)` cho đến khi OCR xác nhận `state == PROFILE`.
  - **Kiểm tra Token OCR Profile trước khi gửi `MEDIA:`:**
    * BẮT BUỘC có các token: `Hồ sơ`, `@username`, Tên hiển thị, `Follower`.
    * Nếu thấy các token của launcher như `Facebook`, `Bộ sưu tập`, `Điện thoại`, `Máy tính`, `Lịch`: DỪNG LẠI NGAY, tuyệt đối không gửi ảnh launcher đối phó cho User.
