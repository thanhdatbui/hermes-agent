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
Khi chuẩn hoá 1 hoặc 2 kênh cùng lúc, dùng canvas tổng hợp (`D:/Taadaa/tools/create_proposal_canvas.py`) để render ảnh so sánh các phương án Avatar (PA1, PA2), chỉ số, tên mới, bio đề xuất.
- **Trước khi gửi ảnh MEDIA:**
  1. Dùng `browser_navigate` mở ảnh canvas local (`file:///D:/Taadaa/reports/...`).
  2. Dùng `browser_vision` soi mắt kiểm tra: ảnh rõ nét, không lẹm chữ, đúng nội dung.
  3. Đăng ký receipt với Gate kiểm chứng:
     ```bash
     python D:/Taadaa/tools/guard_media_vision_gate.py --register-receipt "<IMAGE_PATH>" --tool browser_vision --ocr "<TEXT>" --entity "avatar" --entity "profile" --entity "bio" --entity "pin"
     ```
  4. Đính kèm thẻ `MEDIA:<path>` trong tin nhắn trả lời User, mô tả chi tiết bằng chứng đã thấy tận mắt.

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
4. Cập nhật Excel `Tik*.xlsx` (Cột Avatar = `'OK'`, Keyword, Hashtag Pool).
5. Đổi Nickname và Bio trên máy bằng runner canonical (`do_rename_canonical_runner.py`), tuyệt đối không gõ adb thô làm mất dấu tiếng Việt.
