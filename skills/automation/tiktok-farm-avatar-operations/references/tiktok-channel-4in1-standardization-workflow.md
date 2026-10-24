# Quy Trình Chuẩn Hoá Kênh TikTok Toàn Diện 4-in-1 (Avatar, Nickname, Bio, Hashtag & Pin)

## 1. Bản Chất & Định Nghĩa Chuẩn Hoá Kênh
Chuẩn hoá kênh không chỉ đơn thuần là đổi avatar, mà là quy trình đồng bộ 4 món (4-in-1) trên toàn hệ thống:
1. **Avatar (Ảnh đại diện):** Trích frame đẹp từ video gốc / render, crop vuông 1:1 (512x512) cận cảnh chủ thể/nhân vật, không dính chữ rác/logo, tạo preview tròn (circle preview) để User chọn hoặc tự động áp dụng khi đã duyệt. Khóa `.manual_avatar_locked` tại cả 2 đầu kho (F_src và F_vid) và cập nhật registry `manual_avatar_protected_folders.json`.
2. **Nickname (Tên hiển thị):**
   - 100% tiếng Việt có dấu, họ tên thật hoặc nghệ danh chuẩn theo ngách và username (dùng `smart_name_generator.py`).
   - **CẤM TUYỆT ĐỐI** hậu tố rác (Sữa, Chanh, Heo, Cún, Miu, Xù...).
   - **CÚ PHÁP ADBKEYBOARD BẮT BUỘC:** Khi nạp chữ tiếng Việt qua ADB, BẮT BUỘC dùng đúng cú pháp:
     `am broadcast -a ADB_KEYBOARD_INPUT_TEXT --es text <BASE64_UTF8>`
     (CẤM dùng nhầm `ADB_INPUT_B64 --es msg` hoặc fallback cao bồi `input text "Hong%sDung"` làm mất dấu tiếng Việt).
3. **Tiểu sử (Bio):**
   - 100% tiếng Việt có dấu, câu văn tự nhiên, súc tích, phản ánh đúng ngách nội dung kênh.
   - **CẤM TRÙNG LẶP** giữa các nick, lọc bỏ ký tự `@` (tránh dính chính sách điều hướng của TikTok).
   - Xoá hoàn toàn bio rác mặc định lúc reg nick (`Đang hỗ trợ: WWF-UK` hoặc `Tôi tạo nội dung về...`).
4. **Hashtag & Pin Top Video:**
   - **Hashtag:** Rà soát Keyword và Hashtag Pool trong file Excel (`Tik1`..`Tik8.xlsx` tại Kibe và Admin), sửa đúng ngách thực tế của video (tránh lệch ngách như Bánh ngọt vs Vũ đạo, Lập trình vs Gia đình). Cắm marker `.manual_hashtag_locked` tại F_src và F_vid.
   - **Ghim bài (Pin Top):** Chỉ ghim khi có video đạt trần $\ge 1.000$ views. Video $\ge 1.000$ view ghim trước; nếu nhiều video thì ghim tăng dần để video view cao nhất nằm ở ô số 1. Nếu toàn bộ video dưới 1.000 view -> KHÔNG ghim, giữ nguyên thứ tự tự nhiên.

---

## 2. Quy Trình Điều Phối Hiện Trường O(1)

### Bước 1: Tra cứu toạ độ O(1)
Chạy lệnh canonical duy nhất để lấy thông tin máy, slot, kho video:
```bash
python D:/Taadaa/tools/lookup_channel.py --username <username>
```
Lệnh trả về JSON: Host (Kibe/Admin), Machine ID, Tik workbook, Slot, `folder_video_render` (F_vid), `folder_video_goc` (F_src), thống kê video, view, follower, tim.

### Bước 2: Soạn ảnh Proposal Canvas & Đăng ký Vision Receipt
Khi chuẩn hoá kênh, dùng canvas tổng hợp để render ảnh so sánh các phương án Avatar (PA1, PA2, PA3), chỉ số, tên mới, bio đề xuất:
- **Trước khi gửi ảnh MEDIA:**
  1. WinRT OCR / Vision kiểm chứng chữ trên màn hình proposal.
  2. Đăng ký receipt với Gate kiểm chứng:
     ```bash
     python D:/Taadaa/tools/guard_media_vision_gate.py --register-receipt "<IMAGE_PATH>" --ocr "<TEXT>"
     ```
  3. Đính kèm thẻ `MEDIA:<path>` trong tin nhắn trả lời User, mô tả chi tiết bằng chứng đã thấy tận mắt.

### Bước 3: Đồng bộ kho và cắm marker bảo vệ
Khi phương án được duyệt:
1. Đồng bộ file ảnh `avatar.jpg` vào:
   - `D:/video goc/<F_src>/avatar.jpg`
   - `D:/TIKTOK-videonuoinick/<F_vid>/avatar.jpg`
   - (Nếu máy Admin): `D:/TIKTOK-videonuoinick-admin/<F_vid>/avatar.jpg`
2. Cắm marker bảo vệ:
   - Tạo file `.manual_avatar_locked` tại F_src và F_vid.
   - Tạo file `.manual_hashtag_locked` tại F_src và F_vid.
3. Cập nhật registries JSON:
   - `D:/Taadaa/data/manual_avatar_protected_folders.json`
   - `D:/Taadaa/data/manual_hashtag_protected_folders.json`
4. Cập nhật SQLite `D:/Taadaa/data/tiktok_tracker.db` bảng `avatar_replace_queue` thành `PENDING` và Excel `Tik*.xlsx` (Cột Avatar = `'OK'`).

### Bước 4: Đổi Bio và Nickname có dấu trên thiết bị
Chạy runner canonical:
```bash
python D:/Taadaa/tools/do_rename_canonical_runner.py --machine <M> --serial <SERIAL> --username <username> --bio "<Nội dung Bio có dấu>" --bio-only
```
- Nếu cần đổi cả tên: bỏ flag `--bio-only` và truyền `--name "<Tên mới có dấu>"`.
- Tuyệt đối không gõ adb thô làm mất dấu tiếng Việt.

### Bước 5: Ghim video Top View (Pin Top)
Chạy script chuyên dụng:
```bash
python D:/Taadaa/tools/pin_top_videos.py --machine <M> --account <username> --min-views 1000
```
- Script tự động wrap `operator_device_lock` với `force_preempt=True`, parse views chính xác (K/M), mở action sheet và ghim LIFO để video top view luôn đứng ở vị trí ô 1.
- Lưu ý về Device Lock: Nếu máy đang có lock reservation queue (ví dụ từ batch 2FA/nuôi), theo User Profile: CẤM kill tool khác; chờ lượt queue hoặc dùng `with_device_lock.py --force-preempt` khi máy đang rảnh (Launcher).

### Bước 6: Nghiệm thu thực tế & Đăng ký HMAC Vision Receipt
1. Chụp ảnh màn hình profile sau khi hoàn tất:
```bash
python D:/Taadaa/tools/with_device_lock.py --machine <M> --force-preempt -- "C:/Program Files (x86)/xiaowei/tools/adb.exe" -s <SERIAL> shell screencap -p /sdcard/m<M>_final.png
python D:/Taadaa/tools/with_device_lock.py --machine <M> --no-lock -- "C:/Program Files (x86)/xiaowei/tools/adb.exe" -s <SERIAL> pull /sdcard/m<M>_final.png D:/Taadaa/reports/m<M>_<user>_standardized.png
```
2. Soi mắt WinRT OCR:
```bash
python D:/Taadaa/tools/winrt_ocr_util.py "D:/Taadaa/reports/m<M>_<user>_standardized.png"
```
Xác nhận: Tên đúng, Username đúng, Bio hiển thị chuẩn có dấu, nhãn đỏ "Đã ghim" trên video top.
3. Đăng ký receipt:
```bash
python D:/Taadaa/tools/guard_media_vision_gate.py --register-receipt "D:/Taadaa/reports/m<M>_<user>_standardized.png" --ocr "<các từ khoá chính xác nhận qua OCR>"
```
4. Đính kèm thẻ `MEDIA:<path>` trong tin nhắn báo cáo User.
