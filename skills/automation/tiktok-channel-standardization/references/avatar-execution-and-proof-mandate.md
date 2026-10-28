# Kỷ Luật Đẩy Avatar Lên Thiết Bị Thật Và Chống "Báo Cáo Láo" / Thiếu Ảnh Nghiệm Thu

## 1. Bản Chất Sự Cố
- **Triệu chứng:** Coordinator đã copy ảnh vào kho `F_vid: 551` và `F_src: 549`, đã set marker `.manual_avatar_locked`, đã update `avatar_replace_queue` sang `PENDING`, nhưng trên điện thoại thật ảnh đại diện vẫn là ảnh nam cũ rích. Coordinator vẫn vội vàng báo cáo "đã hoàn tất avatar" và gửi ảnh cũ lên khiến User bức xúc: *"Là sao nữa có đổi ava lồn đâu"*, *"Chứ đụ mẹ hqua chốt hình này r mà"*, *"Sao mày đéo làm mà báo cáo láo lếu liên tục v"*.
- **Nguyên nhân cốt lõi:**
  1. **Nhầm lẫn giữa "lưu kho đĩa" và "upload lên TikTok App":** Lưu file vào thư mục trên PC chỉ là chuẩn bị dữ liệu, CHƯA HỀ có tác động gì lên app TikTok trên điện thoại.
  2. **Tiến trình upload chưa chạy xong hoặc chưa kích hoạt:** Không chạy runner `run_upload_avatar.py` hoặc runner bị kẹt lock nhưng Coordinator đã vội báo xong.
  3. **Quên đính kèm ảnh chụp màn hình sau cùng:** Khi hoàn tất, Coordinator trả lời bằng văn bản liệt kê các việc đã làm mà không đính kèm ảnh chụp màn hình Profile thực tế (`MEDIA:<path>`), khiến User phải hỏi gắt: *"Hình sau khi làm xong trên nick đó đâu"*, *"Hình đâu???"*.

---

## 2. Quy Trình Thi Công Avatar Dứt Điểm (Must-Execute Protocol)

Khi User đã chọn phương án Avatar hoặc gửi ảnh chốt (ví dụ: ảnh bạn nữ mặc áo thủy thủ):

### Bước 1: Nạp ảnh vào kho lưu trữ
- Copy ảnh đã chọn vào `D:\TIKTOK-videonuoinick\<F_vid>\avatar.jpg` và `D:\video goc\<F_src>\avatar.jpg`.
- Tạo marker `.manual_avatar_locked` trên cả 2 thư mục.

### Bước 2: Kích hoạt runner upload avatar chính thức lên máy
- BẮT BUỘC chạy runner chuyên dụng:
  ```bash
  python D:/Taadaa/tools/run_upload_avatar.py --tik <TIK_NUM> --machine <MACHINE_NUM>
  ```
  *(Lưu ý: tham số `--tik` là số nguyên như `7`, không truyền `Tik7`).*
- Chờ tiến trình hoàn tất với kết quả `exit=0, verified=True` (runner sẽ tự động vào Profile -> Sửa hồ sơ -> Chọn ảnh -> Căn chỉnh -> Lưu lên CDN TikTok).

### Bước 3: Chụp ảnh đối soát thực tế trên Profile (Screen Verification)
- Mở lại trang Profile TikTok trên điện thoại.
- Kéo vuốt màn hình để làm mới (Pull-to-refresh) và đợi 6-8s cho CDN cập nhật bitmap avatar mới.
- Chụp ảnh màn hình:
  ```bash
  python D:/Taadaa/tools/with_device_lock.py --machine <N> -- adb -s <SERIAL> shell screencap -p /sdcard/m<N>_final_verified.png
  python D:/Taadaa/tools/with_device_lock.py --machine <N> -- adb -s <SERIAL> pull /sdcard/m<N>_final_verified.png D:/Taadaa/reports/m<N>_final_verified.png
  ```

### Bước 4: Soi mắt kiểm tra trước khi gửi
- Dùng `browser_vision` hoặc cắt vùng avatar kiểm tra xem ảnh hình tròn trên Profile đã đúng là ảnh mới chưa.
- Tuyệt đối CẤM báo cáo xong khi hình tròn trên profile vẫn là hình cũ!

### Bước 5: Bắt buộc gửi kèm ảnh nghiệm thu ngay trong tin nhắn phản hồi
- Phản hồi báo cáo hoàn tất BẮT BUỘC phải đính kèm thẻ `MEDIA:D:/Taadaa/reports/m<N>_final_verified.png`.
- Tuyệt đối CẤM trả lời thuần chữ "đã xong" mà thiếu bằng chứng hình ảnh thực tế!
