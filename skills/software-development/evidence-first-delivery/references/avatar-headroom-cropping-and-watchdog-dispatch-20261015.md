# Bẫy Lệch Tâm Avatar, Kích Hoạt FORCE_UPLOAD Và Đối Soát Watchdog Tránh Hứa Suông (2026-10-15)

## 1. Sự Cố Thực Tế: Avatar Lệch Tâm "Chỉ Thấy Tóc Hoặc Cắt Cụt Ngũ Quan"
Trong phiên chuẩn hóa avatar cho kênh `@nhathasz4vw` (Folder 396) và `@pegsofuh038` (Folder 325):
- Avatar preview hình tròn viền xanh được tạo ra nhưng người dùng phản ứng gay gắt: *"Ava loz gì k thấy ng hoặc thấy mỗi cái tóc v"*.
- **Căn nguyên kỹ thuật:**
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

## 2. Bẫy Hứa Hẹn Watchdog Khi Chưa Kiểm Tra Logic Thực Tế ("Nói Mõm Cho Vui")
Khi máy bị vướng Device Lock của ca nuôi, Coordinator giải thích *"hệ thống có watchdog tự động canh để up khi máy rảnh"*. Người dùng lập tức chất vấn: *"Có watchdog canh k hay nói mõm cho vui? R nãy ca nuôi kết thúc có chạy chưa?"*.

### Phân tích lỗ hổng:
1. **Lỗ hổng trạng thái Excel:** Cột `Avatar` của các nick trong `Tik*.xlsx` đang ghi `OK`. Watchdog `post_evening_avatar_watchdog.py` chỉ tìm các máy có `Avatar != 'OK'`. Do đó, nếu Coordinator không can thiệp đổi sang `FORCE_UPLOAD`, watchdog **sẽ không bao giờ bốc máy lên chạy** dù máy có rảnh.
2. **Lỗ hổng khung giờ của Watchdog:** Code watchdog có hàm `is_post_evening_window(now)` chỉ cho phép chạy trong 3 khung giờ an toàn (sáng `08:30-11:05`, tối `20:15-23:45`, đêm `03:15-05:05`). Ca trưa kết thúc lúc `13:58` hoàn toàn nằm ngoài khung giờ của watchdog, đồng thời `14:03` ca nuôi Phiên 2 đã gối đầu ngay lập tức.
3. **Bài học kỷ luật:**
   - Khi khẳng định có watchdog xử lý tiếp: **BẮT BUỘC kiểm tra cả điều kiện dữ liệu (Excel cột Avatar có phải FORCE_UPLOAD không) VÀ điều kiện khung giờ thực tế của script watchdog**.
   - Phải chạy lệnh xác thực `resolve_avatar_pending_machines.py <Tik>` để chứng minh máy đã nằm trong hàng đợi thật của watchdog trước khi báo cáo.
   - Nếu ngoài khung giờ an toàn của watchdog mà người dùng muốn làm ngay: Phải chủ động đề xuất phương án can thiệp trực tiếp độc lập ngay khi máy nhả Device Lock.
