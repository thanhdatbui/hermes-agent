# Media Picker Gallery Pollution & Profile Screenshot Mis-selection Trap

## Hiện tượng (Failure Signature)
Khi thực hiện quy trình upload Avatar (hoặc upload Video/Story) trên farm TikTok:
- App mở `MvChoosePhotoActivity` (Gallery/Media Picker) nhưng thay vì chọn file avatar/video mục tiêu, script lại click nhầm vào ảnh chụp màn hình chính trang Profile TikTok của máy đó.
- Sau đó script bấm "Tiếp" / "Next", đẩy tài khoản vào trình biên tập Post/Story thay vì màn hình Crop Avatar, hoặc đăng một bài viết ảnh chụp màn hình rác lên trang cá nhân, dẫn tới flop kênh / bot flag / timeout kẹt máy.

## Nguyên nhân gốc rễ
1. **Gallery Pollution (Ô nhiễm thư viện do Audit Screencap):**
   - Các bước kiểm tra trạng thái profile, lấy username hoặc chụp bằng chứng trước khi đổi avatar (`avatar-recovery-before.png`, layout evidence) lưu ảnh trực tiếp vào các thư mục công khai của thiết bị như `/sdcard/DCIM/Screenshots/`, `/sdcard/Pictures/` hoặc `/sdcard/Download/`.
   - Android Media Scanner tự động index các file ảnh này vào thư viện `MediaStore`.
2. **Reverse Chronological Sorting (Xếp mới nhất lên đầu):**
   - Màn hình chọn media của TikTok (`MvChoosePhotoActivity`) mặc định sắp xếp danh sách ảnh theo thời gian tạo mới nhất (`date_added DESC`).
   - Vì ảnh chụp màn hình profile vừa được chụp ngay trước khi mở picker, timestamp của nó mới hơn file avatar/video được push từ host vào trước đó.
   - Do đó, ảnh chụp profile nghiễm nhiên nằm tại tọa độ ô đầu tiên `(0, 0)` trong Gallery tab `Ảnh`.
3. **Naive First-Item Picker Click:**
   - Kịch bản tự động hóa chỉ click mù vào ô media đầu tiên (thường là góc trên bên trái của lưới ảnh) thay vì so khớp tên file, timestamp, hoặc cách ly thư mục.

## Quy chuẩn phòng ngừa & khắc phục (Invariants)

1. **Cách ly thư mục lưu Screenshot / Evidence (`.nomedia`):**
   - TUYỆT ĐỐI KHÔNG lưu ảnh chụp màn hình hiện trường, bằng chứng audit vào `/sdcard/DCIM/`, `/sdcard/Pictures/` hay `/sdcard/Download/`.
   - BẮT BUỘC lưu vào thư mục riêng có chứa file `.nomedia` (ví dụ: `/sdcard/.evidence/` hoặc thư mục private của package `/sdcard/Android/data/...`) để Android Media Scanner bỏ qua, không đưa vào Gallery.
2. **Purge Media Stale trước khi Push Avatar/Video:**
   - Trước khi push file avatar mới (`avatar.jpg`) vào thiết bị, BẮT BUỘC thực hiện lệnh dọn dẹp các ảnh rác/ảnh chụp màn hình cũ:
     `adb -s <serial> shell "rm -f /sdcard/Pictures/*.png /sdcard/DCIM/Screenshots/*.png /sdcard/DCIM/Camera/*.png"`
   - Kích hoạt rescan MediaStore hoặc xóa dòng index media cũ qua `content delete --uri content://media/external/images/media`.
3. **Cập nhật mtime / Timestamp khi Push Media:**
   - Khi push file media mới vào thiết bị qua ADB, cập nhật timestamp (`touch` / `setmtime`) lên thời điểm hiện tại `int(time.time())` để đảm bảo file media đích luôn có thời gian mới nhất trong thư viện.
4. **Teardown phục hồi khẩn cấp khi máy bị kẹt:**
   - Khi phát hiện máy kẹt tại `MvChoosePhotoActivity`:
     1. Chụp ảnh hiện trường (`MEDIA:<path>`).
     2. Thoát ứng dụng: `adb -s <serial> shell am force-stop com.ss.android.ugc.trill`.
     3. Về màn hình chính: `adb -s <serial> shell input keyevent KEYCODE_HOME`.
     4. Xóa các file screenshot rác trong thư mục DCIM/Pictures trước khi tái khởi động workflow.
