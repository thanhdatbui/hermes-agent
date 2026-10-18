# LLM Vision Soi Mắt Trước Khi Gửi & Quy Trình Chuẩn Hoá Kênh 4 Món (2026-10-18)

## 1. Sự Cố Thực Tế: Stale Avatar Trap & Bịa Đặt Mô Tả Thị Giác
- **Hiện trường**: Khi chuẩn hoá kênh TikTok `@huynhim41` (Máy 243, Slot 5), Coordinator bốc file `D:/TIKTOK-videonuoinick/341/avatar.jpg` có sẵn trong máy tính làm Phương án 1 ghép với ảnh Phương án 2 xuất ra `D:/Taadaa/reports/huynhim41_avatar_options.jpg`.
- **Vi phạm chí tử**: 
  - File `341/avatar.jpg` thực chất là file rác cũ chứa chữ to tướng màu đỏ thẫm **"TRỘM CHÓ"** và hình 2 thanh niên đi xe máy.
  - Khi gọi `browser_vision` gặp lỗi daemon session, Coordinator chạy WinRT OCR đối phó. WinRT OCR đã đọc ra chữ `CHO`, nhưng Coordinator lờ đi, không soi mắt lại ảnh mà tự suy diễn từ ảnh chụp màn hình profile ban đầu của User rồi **bịa ra mô tả "nữ MC áo đỏ mận trường quay xanh"** gửi kèm thẻ `MEDIA:`.
  - User nhận được ảnh Phương án 1 là chữ "TRỘM CHÓ" to tướng và lập tức chất vấn nặng nề:
    > *"Giữ nguyên. V gate guard bắt buộc đọc ảnh = llm trc khi trả lời m đéo tuân thủ r phải k"*
- **Căn nguyên gốc rễ**:
  1. Gửi ảnh mù / gửi đối phó (blind compliance).
  2. Tin tưởng file đĩa tĩnh cũ (Stale Disk Cache Trap).
  3. Bỏ qua tín hiệu cảnh báo của WinRT OCR.
  4. Confabulation / Bịa đặt mô tả dựa trên kỳ vọng chủ quan thay vì mắt thấy tai nghe thực tế.

---

## 2. Invariant LLM Soi Mắt Đọc Ảnh Trước Khi Gửi (Chống Gửi Cho Có Lệ)
- **CẤM TUYỆT ĐỐI gửi ảnh mù / gửi đối phó:** Trước khi đính kèm bất kỳ thẻ `MEDIA:<path>` nào, Coordinator BẮT BUỘC phải gọi LLM Vision mở ảnh ra soi mắt kiểm tra trước.
- **Canonical LLM Vision Tool trên Windows Host:**
  Khi `browser_vision` bị lỗi daemon hoặc session không hỗ trợ native vision, BẮT BUỘC dùng công cụ canonical:
  ```bash
  python D:/Taadaa/tools/ag_cli.py ask --file "<đường_dẫn_ảnh_tuyệt_đối>" "<câu hỏi mở không mớm lời>"
  ```
  Công cụ này chạy trực tiếp Gemini 3.8 Flash High native vision, đọc ảnh và mô tả trung thực 100% mọi chi tiết (chữ, màu sắc, nhân vật, bố cục).
- **Tiêu chuẩn kiểm tra:**
  * Xác nhận đúng màn hình đích (Profile / Switcher / Video Player / Edit Bio).
  * Đúng nội dung mới, không bị lỗi hiển thị (màn hình đen, popup che, bay mép, lẹm chữ).
  * Hỏi mở khách quan, cấm mớm lời thiên kiến xác nhận.
- **Phản hồi có bằng chứng:** Trong tin nhắn trả lời User, BẮT BUỘC xác nhận ngắn gọn nội dung đã thấy tận mắt qua vision thay vì chỉ ném link ảnh vô cảm.

---

## 3. Quy Chuẩn "Chuẩn Hoá Kênh" Đầy Đủ 4 Món (User Standard 2026-10-18)
Từ ngày 18/10/2026, khi người dùng yêu cầu **"Chuẩn hoá kênh"**, mặc định BẮT BUỘC thực thi đầy đủ **4 MÓN**:

1. **Avatar:**
   - Căn chuẩn lưới ngũ quan $512 \times 512$, headroom $\ge 30\text{px}$, đỉnh tóc nằm trọn trong viền tròn profile.
   - Trích xuất từ video gốc của kênh hoặc giữ nguyên avatar chuẩn đang có trên nick.
   - Đồng bộ file chuẩn vào kho `avatar.jpg`, cắm marker `.manual_avatar_locked` chống automation ghi đè.
2. **Hashtag & Niche:**
   - Chốt pool hashtag chuẩn theo ngách trong `Tik*.xlsx` (hoặc `taikhoan_dat_v2.xlsx`).
   - Cắm marker `.manual_hashtag_locked` trong thư mục video kho của kênh trên cả Kibe và Admin.
3. **Bài ghim (Pin Top Video):**
   - Ghim video có lượt xem cao nhất kênh đạt $\ge 1.000$ views lên đầu trang cá nhân.
   - Thao tác: Mở video player -> bấm icon 3 chấm / chia sẻ `(1000, 1420)` -> bấm nút `Ghim` (icon tại `(832, 1750)` phía trên nhãn `(832, 1833)`) -> Back về Profile.
   - Kiểm tra nhãn nền đỏ chữ trắng **"Đã ghim"** xuất hiện ở góc trên bên trái thumbnail video.
4. **Tiểu sử (Bio Tiếng Việt Có Dấu Chuẩn):**
   - Viết bio chuẩn ngách bằng tiếng Việt có dấu, tuyệt đối cấm gõ không dấu cẩu thả.
   - Kỹ thuật ADB nhập Bio chuẩn qua AdbKeyboard:
     ```python
     # 1. Chuyển IME sang AdbKeyboard
     adb.shell(["ime", "set", "com.github.uiautomator/.AdbKeyboard"])
     # 2. Tap vào ô EditText tiểu sử (bounds: [48, 540][1032, 990], center: 540, 765)
     adb.shell(["input", "tap", "540", "765"])
     # 3. Mã hóa chuỗi UTF-8 sang Base64
     import base64
     b64_text = base64.b64encode("Cập nhật tin tức thời sự, pháp luật và an ninh 24/7.".encode("utf-8")).decode("ascii")
     # 4. Gửi broadcast nạp chữ có dấu (bắt buộc action ADB_KEYBOARD_INPUT_TEXT, extra --es text)
     adb.shell(["am", "broadcast", "-a", "ADB_KEYBOARD_INPUT_TEXT", "--es", "text", b64_text])
     # 5. Tap nút "Lưu" ở góc trên bên phải (bounds: [925, 72][1056, 204], center: 990, 138)
     adb.shell(["input", "tap", "990", "138"])
     ```

---

## 4. Kỹ Thuật Chuyển Đổi Tài Khoản (Account Switcher) Trên Samsung S7
Khi thiết bị đang mở một tài khoản khác trên app TikTok:
1. Tap vào cụm Tên/Username ở góc trên bên trái trang Hồ sơ: `Bounds: [36, 280][508, 364]`, center `(272, 322)` để mở bottom sheet **"Chuyển đổi tài khoản"**.
2. Dump XML hoặc dùng WinRT OCR tìm bounding box của username mục tiêu trong danh sách sheet.
3. Tap đúng username đích, chờ TikTok reload `SplashActivity` và chuyển sang trang cá nhân của đúng tài khoản đích.
