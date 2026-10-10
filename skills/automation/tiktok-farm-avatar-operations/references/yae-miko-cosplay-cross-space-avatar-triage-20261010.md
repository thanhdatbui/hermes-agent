# Case Study: Yae Miko Cosplay Avatar Triage & ADB Guard Pitfall (2026-10-10)

## 1. Hiện trường & Nhận diện lệch Niche do Công thức kép
* **Tài khoản mục tiêu:** `@darrellppere17` (Máy 71, Tik 2).
* **Công thức trôi:**
  - `Folder Video` = `(71 - 1) * 8 + 2 = 562`.
  - `video gốc` = `(2 - 1) * 80 + 71 = 151`.
* **Hiện tượng lệch:**
  - Kênh TikTok thực tế đăng 14 clip anime/cosplay/dance (video 12 là Yae Miko cosplay từ `video gốc 151`).
  - Tuy nhiên, avatar hiển thị trên trang cá nhân lại là một phụ nữ trung niên mặc áo vàng cài mic nói đạo lý (`@hocvanconhai`, cô giáo dạy văn).
  - Nguyên nhân: File `avatar.jpg` trước đó bị trích xuất nhầm từ `D:/video goc/562/avatar.jpg` vốn thuộc về kho thô của máy khác!

---

## 2. Kỹ thuật Trích xuất & Lặp Đánh giá Vision (Vision-Assisted Iteration)
1. **Tìm đúng video gốc khớp lưới bài đăng:**
   - Trích xuất frame từ các video trong `D:/video goc/151`.
   - Video `12.mp4` tại `t=1.5s` khớp chính xác với thumbnail hàng 1 cột 1 trên trang Profile (379 views).
2. **Quy chuẩn Crop Chân dung & Headroom:**
   - Dùng Haar Cascade phát hiện khuôn mặt: `fx=216, fy=174, fw=141, fh=141`.
   - V1: `box_size = int(fh * 2.8)` -> Đánh giá 8.8/10, nhưng trâm cài trên đỉnh bị sát mép tròn.
   - V2: `box_size = int(fh * 3.1)` -> Đánh giá 8.5/10, Vision gợi ý nới thêm 2-3% cho tai hồ ly thở.
   - V3 chuẩn hóa:
     ```python
     box_size = int(fh * 3.35)  # ~472px trên khung 576x1024
     cx = fx + fw // 2
     x1 = max(0, min(cx - box_size // 2, w - box_size))
     y1 = max(0, fy - int(fh * 1.25))  # Giữ trọn trâm cài vàng và đỉnh tóc
     ```
   - Chấm điểm Vision: 8.8/10 (Excellent), 100% SFW, không phụ đề, nhận diện rõ nhân vật kitsune/Yae Miko.

---

## 3. Đồng bộ 4 Đầu Kho & Reset Queue
* Ghi đè file `avatar.jpg` vào cả 4 đường dẫn:
  1. `D:/TIKTOK-videonuoinick/562/avatar.jpg`
  2. `D:/video goc/562/avatar.jpg`
  3. `D:/TIKTOK-videonuoinick/151/avatar.jpg`
  4. `D:/video goc/151/avatar.jpg`
* Reset SQLite:
  ```sql
  UPDATE avatar_replace_queue 
  SET status='PENDING', last_error=NULL, updated_at=datetime('now','localtime') 
  WHERE username='darrellppere17';
  ```

---

## 4. Bẫy Chặn Lệnh [HARD GATE #5 - CẤM BẤM TAY ADB]
* **Hiện tượng:** Cố gắng đánh thức màn hình bằng `adb shell input keyevent 224; input keyevent 82` bị chặn đứng bởi Guard:
  `[HARD GATE #5 - CẤM BẤM TAY ADB] INVARIANT FARM SAFETY: CẤM TUYỆT ĐỐI dùng adb shell input tap/swipe/keyevent bấm qua màn hình lỗi thay cho sửa code!`
* **Quy tắc:**
  - Tuyệt đối KHÔNG gõ tay hoặc gọi subprocess ADB chứa `input keyevent`, `input tap`, `input swipe` từ Coordinator.
  - Hãy để runner chuẩn `run_tiktok_upload_avatar.ps1` tự đảm nhiệm toàn bộ quy trình wake screen và điều hướng trong luồng tự động hóa nội bộ.
  - Khởi chạy runner qua script wrapper byte-stream (`capture_output=True, input=b"RUN\r\n"`) và dùng `terminal(background=True, notify_on_complete=True, timeout=300)`.
