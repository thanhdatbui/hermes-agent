# Quy Trình Trích Xuất Avatar Khuôn Mặt Đủ Headroom & Điều Phối Watchdog (2026-10-15)

## 1. Vấn Đề Lệch Tâm & Cắt Ngũ Quan (Cắt Mất Cằm, Mất Trán, Chỉ Thấy Tóc)
Khi dùng OpenCV Haar Cascade hoặc các detector trích xuất chân dung từ video dọc 1080x1920:
- **Nguyên nhân lỗi trôi tâm:**
  1. Box Haar Cascade chỉ bao quanh vùng từ lông mày xuống cằm (bỏ qua trán và đỉnh đầu).
  2. Khi tính tâm crop `y0 = head_center_y - side / 2`, nếu không đệm headroom thì đỉnh tóc bị chạm viền trên, hoặc nếu tâm đặt quá thấp thì cằm bị văng ra ngoài khung tròn.
  3. Khi frame bị resize/downscale để detect nhanh, box tọa độ trả về phải nhân ngược lại tỉ lệ scale (`fx / scale, fy / scale`) trước khi áp vào ảnh full-resolution.
- **Công thức chuẩn hóa Crop Chân Dung 512x512 có Headroom:**
  ```python
  def crop_portrait_headroom(box, frame_w, frame_h):
      fx, fy, fw, fh = box
      head_center_x = fx + fw * 0.5
      # Đặt trọng tâm y dịch nhẹ xuống cằm một chút (~0.55 - 0.6) để đỉnh tóc có khoảng thở phía trên
      head_center_y = fy + fh * 0.55
      # Chiều dài cạnh hình vuông lấy theo chiều rộng mặt và tỷ lệ khung hình
      side = int(min(fw * 2.6, frame_w * 0.9, frame_h * 0.55))
      x0 = int(head_center_x - side / 2)
      y0 = int(head_center_y - side * 0.5)
      # Bắt buộc clamp không cho văng ra ngoài frame
      x0 = max(0, min(x0, frame_w - side))
      y0 = max(0, min(y0, frame_h - side))
      return x0, y0, side
  ```
- **Quy tắc Kiểm Định Bằng Mắt (Invariant Soi Mắt - Gate 6):**
  * Không bao giờ được báo hoàn tất khi chưa mở ảnh circle preview kiểm tra qua `browser_vision` hoặc OCR WinRT.
  * Phải thấy rõ ngũ quan (2 mắt, sống mũi, miệng, cằm, trán) nằm trọn vẹn ở trung tâm hình tròn, đỉnh đầu cách mép trên ~35-50px.

---

## 2. Kích Hoạt Cưỡng Chế Watchdog Upload Avatar (`FORCE_UPLOAD`)
Watchdog `post_evening_avatar_watchdog.py` tự động quét các workbook Excel qua `resolve_avatar_pending_machines.py`.
- **Nếu cột `Avatar` trong Excel đã ghi `OK`:** Watchdog sẽ bỏ qua và không thực hiện lại.
- **Để đưa nick vào hàng đợi ưu tiên của Watchdog:**
  Ghi đè giá trị cột `Avatar` trong sheet `TaiKhoan` thành **`FORCE_UPLOAD`**.
- **Kiểm tra danh sách chờ thực tế:**
  ```bash
  python D:/Taadaa/Tiktok-video/scripts/resolve_avatar_pending_machines.py <Tik_Index>
  ```
  Khi số máy mục tiêu xuất hiện trong stdout, watchdog ở chu kỳ kế tiếp sẽ tự động bốc máy để thực thi.

---

## 3. Khung Giờ An Toàn Của Watchdog & Điều Kiện Lock
- Watchdog kiểm tra chặt chẽ khung giờ an toàn (`is_post_evening_window`) nhằm tránh xung đột với các ca nuôi feed và lịch tự khởi động lại máy (Auto-Reboot):
  * Khung sáng: `08:30 -> 11:05` (né reboot 11:20)
  * Khung tối: `20:15 -> 23:45`
  * Khung đêm: `03:15 -> 05:05` (né reboot 05:20)
- Nếu người dùng yêu cầu can thiệp ngay lập tức ngoài khung giờ (`Option 1`), Coordinator phải:
  1. Kiểm tra tiến trình nuôi feed (`psutil` / lock file) xem đã nhả máy chưa.
  2. Dùng wrapper giữ Device Lock an toàn:
     ```bash
     python D:/Taadaa/tools/with_device_lock.py --machine <N> -- <command...>
     ```
  3. Nạp ảnh avatar vào máy qua ADB và phát broadcast quét thư viện:
     ```bash
     adb -s <serial> push <avatar_512.jpg> /sdcard/DCIM/Camera/avatar_<username>.jpg
     adb -s <serial> shell am broadcast -a android.intent.action.MEDIA_SCANNER_SCAN_FILE -d file:///sdcard/DCIM/Camera/avatar_<username>.jpg
     ```
  4. Thực thi ghim video top view bằng `pin_top_videos.py` với tài khoản chỉ định rõ `--account <username>` để tránh nhầm nick khi máy đang ở nick nuôi khác.
