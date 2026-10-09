# Avatar & Name Triage From Profile Screenshot (Single-Nick Recovery)

## Overview
Khi Operator gửi ảnh màn hình Profile TikTok từ điện thoại cá nhân (iOS/Android) kèm lệnh ngắn gọn: *"Đổi tên + ava nick này"* hoặc *"Thay ava nick này"*, quy trình định danh O(1), trích xuất avatar chuẩn niche và xử lý an toàn trên Taadaa Farm gồm các bước chuẩn sau.

---

## 1. Định danh O(1) từ Screenshot vào Farm Machine & Slot
1. **OCR / Vision bóc tách Handle:**
   - Dùng WinRT OCR (`python scripts/winrt_ocr.py <path>`) hoặc 9Router Vision trích xuất username `@handle` (ví dụ: `@hectornwrigh45`).
2. **Truy vấn định vị máy và slot trong SQLite & Excel:**
   - Database: `D:/Taadaa/data/tiktok_tracker.db`
     - `SELECT * FROM account_mapping WHERE username='<handle>'` $\to$ Trả về `(username, may, tik)`.
     - `SELECT * FROM avatar_replace_queue WHERE username='<handle>'` $\to$ Trả về `(folder_video, video_goc, queue_status)`.
   - Hoặc tra cứu `D:/OneDrive/TaadaaData/kibe/Tik<N>.xlsx` và `taikhoan_dat_v2_updated .xlsx` để lấy chính xác:
     - **Số Máy:** ví dụ Máy 46 (Serial: `ce0916092531413504`).
     - **Slot Tik:** ví dụ Tik 3.
     - **Folder Video (render):** ví dụ 363.
     - **Video Gốc:** ví dụ 206.
     - **Keyword Video / Niche:** ví dụ "Thời trang" (Street Snap / Hot girl dạo phố).

---

## 2. Kiểm toán Avatar Nguồn & Cắt Lại Chuẩn Niche (Chống Rác/Lệch Vibe)
1. **Bẫy file avatar cũ bị rác:**
   - Không được tin tưởng file `avatar.jpg` đang có sẵn trong folder. Các đợt tạo avatar tự động trước đây có thể cắt trúng mô hình giấy, cọc tiêu giao thông, hoặc clip truyền hình có logo/phụ đề.
   - Luôn kiểm tra ảnh nguồn qua Vision (`http://127.0.0.1:20128/v1/chat/completions`) trước khi up.
2. **Quy trình cắt chân dung cận cảnh (Portrait with Headroom):**
   - Quét qua các video 1, 3, 4, 5 trong thư mục `D:/TIKTOK-videonuoinick/<Folder Video>/` tại timestamp 1.5s - 4.5s.
   - Dùng OpenCV Haar Cascade (`haarcascade_frontalface_default.xml`) tìm khuôn mặt đơn (`minSize=(90, 90)`).
   - **Tính toán khung crop vuông cân đối (có khoảng thở đỉnh đầu - Headroom):**
     ```python
     box_size = int(fh * 2.4)
     box_size = min(box_size, w, h)
     cx = fx + fw // 2
     x1 = max(0, min(cx - box_size // 2, w - box_size))
     y1 = max(0, fy - int(fh * 0.55))  # Giữ trán và tóc phía trên
     if y1 + box_size > h:
         y1 = max(0, h - box_size)
     cropped = frame[y1:y1+box_size, x1:x1+box_size]
     ```
   - Tối ưu màu sắc/độ nét nhẹ (`ImageEnhance.Sharpness(1.25)`, `Contrast(1.08)`) để ảnh rõ nét khi thu nhỏ vào khung tròn TikTok.
3. **Đồng bộ cả 2 đầu kho:**
   - Copy ảnh tối ưu vào cả:
     - `D:/TIKTOK-videonuoinick/<Folder Video>/avatar.jpg`
     - `D:/video goc/<Folder Video>/avatar.jpg`
   - Cập nhật SQLite: `UPDATE avatar_replace_queue SET status='PENDING', last_error=NULL, updated_at=datetime('now','localtime') WHERE username='...';`

---

## 3. Quy chuẩn Đổi Tên (Display Name) Tự Nhiên
- Với nick reg từ email ngoại (như `hectornwright4i52a@gmail.com` hay `francesuhunt5@gmail.com`), tuyệt đối không giữ nguyên display name là chuỗi ký tự email thô.
- Đặt tên tiếng Việt tự nhiên theo niche:
  - Niche Thời trang / Gái xinh: **Khánh Vy**, **Phương Thảo**, **Ngọc Linh**, **Hà My**.
  - Áp dụng quy chuẩn `account-profile-entropy` (`make_tiktok_name()`).

---

## 4. Pitfall: Samsung S7 Thấp RAM & Xử Lý Kẹt UI Profile
1. **Dọn sạch RAM trước khi chạy:**
   - Samsung S7 (Android 8.0) chạy lâu ngày tích tụ tiến trình nền (Chrome, Instagram, Facebook, Google Photos) chiếm hơn 500MB RAM, dễ gây SIGABRT / Thread suspension timeout khi mở TikTok.
   - Giải phóng RAM trước khi thao tác:
     `adb -s <SERIAL> shell "am force-stop com.android.chrome; am force-stop com.instagram.android; am force-stop com.facebook.katana; am force-stop com.google.android.apps.photos"`
2. **Account Switcher Navigation khi Profile không hiện nút Sửa:**
   - Một số biến thể UI TikTok mới ẩn nút "Sửa hồ sơ" và cây bút, avatar nằm góc phải và tên nằm bên trái.
   - Khi cần chuyển đúng nick trong 8 acc: cuộn nhẹ profile lên để hiện header username $\to$ tap header mở sheet "Chuyển đổi tài khoản" $\to$ dùng WinRT OCR tìm đúng dòng text `@handle` mục tiêu để tap chuyển đổi.
